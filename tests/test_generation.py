"""Behavioral tests for event groups, reproducibility, plugins, and the CLI."""

import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))
from generation_runner import generate_dataset
from lib.generators.common import DEFAULT_EVENT_COLUMNS, event_index


def reference_data():
    return pd.DataFrame([
        {"scope": f"group_{group}", "source": "host", "field": "login",
         "value": f"value_{i}", "signature": f"signature_{i}",
         "updated": (group * 12 + i) * 100}
        for group in range(3) for i in range(12)
    ])


def attack(name, group, kind="exact", **params):
    defaults = {"n_rows": 8, "duration": 60, "attack_start": 1000}
    if kind == "distributed":
        defaults.update(n_rows=4, shared_fields=3)
    defaults.update(params)
    return {"id": name, "type": kind, "event_group": group, "params": defaults}


def experiment(*attacks, background_rows=20):
    return {
        "seed": 42, "event_columns": list(DEFAULT_EVENT_COLUMNS),
        "timestamp_column": "updated",
        "background": {"type": "normal", "params": {"n_rows": background_rows}},
        "attacks": list(attacks),
    }


def events(data, attack_id):
    return set(data.loc[data.attack_id == attack_id, DEFAULT_EVENT_COLUMNS].itertuples(index=False, name=None))


def attack_rows(data, attack_id):
    return data.loc[data.attack_id == attack_id].sort_values(list(data.columns)).reset_index(drop=True)


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.reference = reference_data()

    def test_exact_reuse_disjointness_counts_and_windows(self):
        config = experiment(
            attack("a", "same"), attack("b", "same", n_rows=15, attack_start=2000),
            attack("c", "other"),
        )
        data, report = generate_dataset(self.reference, config)
        self.assertEqual(len(data), 20 + 8 + 15 + 8)
        self.assertEqual(events(data, "a"), events(data, "b"))
        self.assertTrue(events(data, "a").isdisjoint(events(data, "c")))
        self.assertEqual(data.groupby("attack_id").size().to_dict(), {"": 20, "a": 8, "b": 15, "c": 8})
        for item in config["attacks"]:
            rows = data.loc[data.attack_id == item["id"]]
            start = item["params"]["attack_start"]
            self.assertTrue(rows.updated.between(start, start + 59).all())
            self.assertTrue((rows.truth_label == 1).all())
        self.assertEqual(len(report["event_groups"]), 2)
        json.dumps(report, allow_nan=False)

    def test_distributed_reuses_set_and_excludes_other_groups(self):
        config = experiment(
            attack("d1", "same", "distributed"),
            attack("d2", "same", "distributed", attack_start=2000),
            attack("d3", "other", "distributed"),
            attack("e", "same"),
        )
        data, report = generate_dataset(self.reference, config)
        self.assertEqual(len(events(data, "d1")), 4)
        self.assertEqual(events(data, "d1"), events(data, "d2"))
        self.assertTrue(events(data, "d1").isdisjoint(events(data, "d3")))
        for group in report["event_groups"]:
            if group["type"] == "distributed":
                selected = pd.DataFrame(group["events"])
                shared = group["metadata"]["shared_columns"]
                self.assertEqual(len(shared), 3)
                self.assertEqual(len(selected[shared].drop_duplicates()), 1)

    def test_repeatability_order_independence_and_input_isolation(self):
        config = experiment(attack("a", "same"), attack("b", "other", "distributed"))
        original, original_config = self.reference.copy(deep=True), copy.deepcopy(config)
        first, manifest = generate_dataset(self.reference, config)
        second, repeated_manifest = generate_dataset(self.reference, config)
        assert_frame_equal(first, second)
        self.assertEqual(manifest, repeated_manifest)
        config["attacks"].reverse()
        reordered, _ = generate_dataset(self.reference, config)
        assert_frame_equal(first, reordered)
        assert_frame_equal(self.reference, original)
        config["attacks"].reverse()
        self.assertEqual(config, original_config)

    def test_experiment_overrides_do_not_change_module_defaults(self):
        from lib.generators.exact.g_config import read_g_config

        defaults = read_g_config()
        overridden = read_g_config({"n_rows": 17})
        self.assertEqual(overridden["params"]["n_rows"], 17)
        overridden["info"]["selection_params"].append("n_rows")
        self.assertEqual(read_g_config(), defaults)

    def test_changing_one_exact_count_keeps_other_attack_and_background(self):
        config = experiment(attack("a", "same"), attack("b", "same", attack_start=None))
        before, _ = generate_dataset(self.reference, config)
        config["attacks"][0]["params"]["n_rows"] = 100
        after, _ = generate_dataset(self.reference, config)
        assert_frame_equal(attack_rows(before, "b"), attack_rows(after, "b"))
        assert_frame_equal(attack_rows(before, ""), attack_rows(after, ""))

    def test_distributed_conflicting_selection_parameters(self):
        for change in ({"n_rows": 5}, {"shared_fields": 2}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "selection parameters"):
                generate_dataset(self.reference, experiment(
                    attack("a", "same", "distributed"), attack("b", "same", "distributed", **change)
                ))

    def test_insufficient_events_and_invalid_configs(self):
        cases = [
            (experiment(attack("same", "a"), attack("same", "b")), "unique"),
            (experiment(attack("a", "")), "event_group"),
            (experiment(attack("a", "a", n_rows=True)), "integer"),
            (experiment(attack("a", "a", duration=0)), "duration"),
            (experiment(attack("a", "a", unknown=1)), "Unknown parameters"),
            (experiment(attack("a", "a", "distributed", n_rows=100)), "largest remaining"),
            (experiment(attack("a", "a", "distributed", shared_fields=5)), "smaller"),
            (experiment(attack("a", "a", "../exact")), "Invalid generator"),
            (experiment(background_rows=0), "at least one row"),
        ]
        for config, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                generate_dataset(self.reference, config)
        with self.assertRaisesRegex(ValueError, "No unused event"):
            generate_dataset(self.reference.iloc[:1], experiment(attack("a", "a"), attack("b", "b")))

    def test_background_only_attack_only_and_no_leakage(self):
        data, report = generate_dataset(self.reference, experiment())
        self.assertTrue((data.truth_label == 0).all())
        self.assertTrue((data.attack_id == "").all())
        self.assertEqual(report["event_groups"], [])
        data, _ = generate_dataset(self.reference, experiment(attack("a", "a"), background_rows=0))
        self.assertEqual(len(data), 8)
        with self.assertRaisesRegex(ValueError, "reserved"):
            generate_dataset(data, experiment())
        with self.assertRaisesRegex(ValueError, "Missing reference columns"):
            generate_dataset(self.reference.drop(columns="scope"), experiment())

    def test_window_equal_to_reference_range_and_outside_warning(self):
        data, report = generate_dataset(self.reference, experiment(
            attack("a", "a", duration=3500, attack_start=None),
            attack("b", "a", attack_start=-10),
        ))
        self.assertEqual(report["attacks"][0]["metadata"]["attack_start"], 0)
        self.assertTrue(report["attacks"][1]["warnings"])
        with self.assertRaisesRegex(ValueError, "shorter"):
            generate_dataset(self.reference, experiment(attack("a", "a", duration=3501, attack_start=None)))

    def test_missing_event_values_and_extra_reference_columns(self):
        self.reference["scope"] = None
        self.reference["extra"] = "reference-only"
        data, report = generate_dataset(self.reference, experiment(
            attack("a", "same", "distributed"), attack("b", "other", "distributed")
        ))
        first = event_index(data.loc[data.attack_id == "a"], DEFAULT_EVENT_COLUMNS)
        second = event_index(data.loc[data.attack_id == "b"], DEFAULT_EVENT_COLUMNS)
        self.assertFalse(first.isin(second).any())
        self.assertTrue(data.loc[data.attack_id == "a", "extra"].isna().all())
        self.assertTrue(report["attacks"][0]["warnings"])
        json.dumps(report, allow_nan=False)

    def test_missing_or_fractional_timestamps_are_rejected(self):
        for times in (
            pd.Series([0, None] + list(range(2, 36)), dtype="Int64"),
            pd.Series([0.5] + list(range(1, 36))),
        ):
            reference = self.reference.copy()
            reference["updated"] = times
            with self.subTest(dtype=str(times.dtype)), self.assertRaisesRegex(ValueError, "finite integer"):
                generate_dataset(reference, experiment())

    def test_new_type_uses_generic_loading_and_groups(self):
        # An independently named module pair exercises the plugin contract;
        # no runner registry or type branch is changed for this generator.
        from lib.generators.exact import g_generate, g_config
        generator = types.ModuleType("lib.generators.probe.g_generate")
        configuration = types.ModuleType("lib.generators.probe.g_config")

        def read(overrides=None):
            result = g_config.read_g_config(overrides)
            result["info"]["name"] = "probe"
            return result

        generator.get_info = lambda: read()["info"]
        generator.select_events = g_generate.select_events
        generator.run = g_generate.run
        configuration.read_g_config = read
        modules = {generator.__name__: generator, configuration.__name__: configuration}
        with patch.dict(sys.modules, modules):
            data, _ = generate_dataset(self.reference, experiment(
                attack("a", "same", "probe"), attack("b", "same", "probe"), attack("c", "other", "probe")
            ))
        self.assertEqual(events(data, "a"), events(data, "b"))
        self.assertTrue(events(data, "a").isdisjoint(events(data, "c")))

    def test_cli_configured_experiments(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            reference_path = directory / "reference.csv"
            self.reference.to_csv(reference_path, index=False)
            config_path = directory / "experiment.yaml"
            configurations = [
                experiment(attack("a", "a"), attack("d", "d", "distributed")),
                experiment(),
                experiment(attack("a", "a", n_rows=7), background_rows=0),
                experiment(attack("d", "d", "distributed")),
            ]
            for index, config in enumerate(configurations):
                with self.subTest(config=config):
                    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
                    output = directory / f"result_{index}.csv"
                    command = [sys.executable, str(ROOT / "input/data_generate.py"),
                               "-i", str(reference_path), "-o", str(output)]
                    result = subprocess.run(command + ["--config", str(config_path)],
                                            text=True, capture_output=True, cwd=directory)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    data = pd.read_csv(output)
                    manifest = json.loads(output.with_suffix(".json").read_text())
                    self.assertEqual(len(data), manifest["total_rows"])
                    self.assertIn("attack_id", data)
                    self.assertTrue(data[manifest["timestamp_column"]].is_monotonic_increasing)
            result = subprocess.run(command, text=True, capture_output=True, cwd=directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(output.with_suffix(".json").read_text())
            default_config = yaml.safe_load((ROOT / "etc/generation_config/_template.yaml").read_text())
            self.assertEqual(manifest["experiment_config"], default_config)
            result = subprocess.run(command + ["--config", str(directory / "missing.yaml")],
                                    text=True, capture_output=True, cwd=directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing.yaml", result.stderr)
            result = subprocess.run(command + ["--config", str(config_path), "--seed", "42"],
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unrecognized arguments: --seed 42", result.stderr)

    def test_default_outputs_are_separate_profiling_inputs(self):
        spec = importlib.util.spec_from_file_location("generation_cli", ROOT / "input/data_generate.py")
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            reference = directory / "reference.csv"
            self.reference.to_csv(reference, index=False)
            configs = [
                ("generation_normal", experiment(), "synthetic_normal"),
                ("generation_exact_one_event", experiment(attack("a", "a")), "synthetic_exact_one_event"),
                ("generation_exact_two_events", experiment(attack("a", "a"), attack("b", "b", n_rows=11)),
                 "synthetic_exact_two_events"),
                ("_template", experiment(), "synthetic"),
            ]
            with patch.object(cli, "ROOT", directory), patch("sys.stdout", new_callable=io.StringIO):
                for config_name, config, dataset_name in configs:
                    config_path = directory / f"{config_name}.yaml"
                    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
                    cli.main(["-i", str(reference), "--config", str(config_path)])
                    output = directory / "input" / f"{dataset_name}.csv"
                    self.assertTrue(output.is_file())
                    manifest = json.loads(output.with_suffix(".json").read_text())
                    self.assertEqual(manifest["output_file"], str(output.resolve()))
                    self.assertEqual(len(pd.read_csv(output)), manifest["total_rows"])
                self.assertEqual(len(list((directory / "input").glob("*.csv"))), 4)
                self.assertFalse((directory / "output").exists())

                # An automatically chosen output must not overwrite its reference.
                original = output.read_bytes()
                with patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(SystemExit) as error:
                    cli.main(["-i", str(output), "--config", str(config_path)])
                self.assertEqual(error.exception.code, 2)
                self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
