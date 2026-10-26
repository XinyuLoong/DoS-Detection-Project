"""
Load generators, resolve event groups, and build one synthetic experiment.
"""

import copy
import importlib
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.generators.common import (
    DEFAULT_EVENT_COLUMNS, LABEL_COLUMNS, event_index, json_safe,
    make_rng, require_int, validate_reference,
)


def check_mapping(value, allowed, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    unknown = set(value) - set(allowed)
    if unknown:
        raise ValueError(f"Unknown {label} keys: {sorted(unknown, key=str)}")


def load_generator(name):
    if (not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name)):
        raise ValueError(f"Invalid generator type: {name!r}")
    try:
        module = importlib.import_module(f"lib.generators.{name}.g_generate")
        config_module = importlib.import_module(f"lib.generators.{name}.g_config")
    except ImportError as error:
        raise ValueError(f"Cannot load generator {name}: {error}") from error
    for function in ("get_info", "select_events", "run"):
        if not callable(getattr(module, function, None)):
            raise ValueError(f"Generator {name} must define {function}()")
    if not callable(getattr(config_module, "read_g_config", None)):
        raise ValueError(f"Generator {name} must define read_g_config()")
    info = module.get_info()
    if not isinstance(info, dict) or info.get("name") != name:
        raise ValueError(f"Generator metadata name must equal {name}")
    return module, config_module


def prepare_instance(spec, role):
    allowed = {"type", "params"} if role == "background" else {"id", "type", "event_group", "params"}
    check_mapping(spec, allowed, role)
    module, config_module = load_generator(spec.get("type"))
    config = config_module.read_g_config(spec.get("params", {}))
    info = config["info"]
    if info.get("role") != role:
        raise ValueError(f"Generator {spec['type']} cannot be used as {role}")
    require_int(config["params"].get("n_rows"), "n_rows", 0 if role == "background" else 1)
    if role == "attack":
        for key in ("id", "event_group"):
            if not isinstance(spec.get(key), str) or not spec[key].strip():
                raise ValueError(f"Every attack requires a non-empty {key}")
    return {"spec": copy.deepcopy(spec), "module": module, "config": config}


def make_context(reference, columns, timestamp, seed, identity, available):
    # Each call gets copies so plugins cannot contaminate later attacks or the caller.
    return {
        "reference_df": reference.copy(deep=True),
        "event_columns": list(columns),
        "timestamp_column": timestamp,
        "rng": make_rng(seed, *identity),
        "available_events": available.copy(deep=True),
    }


def validate_selection(selection, available, columns, label):
    if not isinstance(selection, dict) or not isinstance(selection.get("metadata"), dict):
        raise ValueError(f"{label}: selection must contain events and metadata")
    events = selection.get("events")
    if (not isinstance(events, pd.DataFrame) or list(events.columns) != columns
            or events.empty or events.duplicated().any()):
        raise ValueError(f"{label}: selection must contain distinct events with the configured columns")
    if not event_index(events, columns).isin(event_index(available, columns)).all():
        raise ValueError(f"{label}: selected events must come from available_events")


def validate_result(result, instance, columns, timestamp, selected):
    name = instance["spec"].get("id", "background")
    if (not isinstance(result, dict) or not isinstance(result.get("metadata"), dict)
            or not isinstance(result.get("warnings"), list)
            or not all(isinstance(item, str) for item in result["warnings"])):
        raise ValueError(f"{name}: run() must return data, metadata, and string warnings")
    data = result.get("data")
    if not isinstance(data, pd.DataFrame) or not data.columns.is_unique:
        raise ValueError(f"{name}: generated data must be a DataFrame with unique columns")
    if len(data) != instance["config"]["params"]["n_rows"]:
        raise ValueError(f"{name}: generated row count does not match n_rows")
    if not set(columns + [timestamp]).issubset(data.columns):
        raise ValueError(f"{name}: generated data is missing event or timestamp columns")
    if set(LABEL_COLUMNS) & set(data.columns):
        raise ValueError(f"{name}: label columns are assigned by the runner")
    times = data[timestamp]
    if (not pd.api.types.is_numeric_dtype(times) or pd.api.types.is_bool_dtype(times)
            or pd.api.types.is_complex_dtype(times) or times.isna().any()
            or not np.isfinite(times).all() or not (times == np.floor(times)).all()):
        raise ValueError(f"{name}: generated timestamps must be finite integers")
    if len(times) and (int(times.min()) < -(2**63) or int(times.max()) >= 2**63):
        raise ValueError(f"{name}: generated timestamps exceed the int64 range")
    if instance["config"]["info"]["role"] == "attack":
        actual = event_index(data, columns)
        expected = event_index(selected["events"], columns)
        if not actual.isin(expected).all() or not expected.isin(actual).all():
            raise ValueError(f"{name}: generated events must match the selected event set")


def generate_dataset(reference_df, experiment_config):
    """Return (DataFrame, JSON-safe manifest); do not read/write output files."""
    check_mapping(experiment_config, {
        "seed", "event_columns", "timestamp_column", "background", "attacks"
    }, "experiment")
    config = copy.deepcopy(experiment_config)
    seed = config.get("seed", 42)
    require_int(seed, "seed", 0)
    columns = config.get("event_columns", list(DEFAULT_EVENT_COLUMNS))
    timestamp = config.get("timestamp_column", "updated")
    validate_reference(reference_df, columns, timestamp)
    reference = reference_df.copy(deep=True)
    reference[timestamp] = reference[timestamp].astype(np.int64)
    available = reference[columns].drop_duplicates().reset_index(drop=True)
    background = prepare_instance(config.get("background", {"type": "normal"}), "background")
    specs = config.get("attacks", [])
    if not isinstance(specs, list):
        raise ValueError("attacks must be a list")
    attacks = [prepare_instance(spec, "attack") for spec in specs]
    ids = [item["spec"]["id"] for item in attacks]
    if len(ids) != len(set(ids)):
        raise ValueError("Attack IDs must be unique")
    if background["config"]["params"]["n_rows"] + sum(
            item["config"]["params"]["n_rows"] for item in attacks) == 0:
        raise ValueError("The experiment must generate at least one row")

    # Group scope is (generator type, event_group). Check all reuse constraints
    # before generation; sort groups so reordering the attack list is harmless.
    groups = {}
    for instance in attacks:
        spec, local = instance["spec"], instance["config"]
        key = (spec["type"], spec["event_group"])
        signature = {field: local["params"][field] for field in local["info"]["selection_params"]}
        if key in groups and signature != groups[key]["signature"]:
            raise ValueError(f"{key}: same event_group requires matching selection parameters {signature}")
        groups.setdefault(key, {"instance": instance, "signature": signature})

    used = {}
    group_records = []
    for (name, group), state in sorted(groups.items()):
        instance = state["instance"]
        pool = available
        if name in used:
            pool = available.loc[~event_index(available, columns).isin(event_index(used[name], columns))]
        context = make_context(reference, columns, timestamp, seed, ("selection", name, group), pool)
        selection = instance["module"].select_events(context, copy.deepcopy(instance["config"]["params"]))
        validate_selection(selection, pool, columns, f"{name}/{group}")
        selection = copy.deepcopy(selection)
        state["selection"] = selection
        used[name] = pd.concat([used.get(name, available.iloc[:0]), selection["events"]], ignore_index=True)
        group_records.append({
            "type": name, "event_group": group,
            "selection_params": state["signature"],
            "events": selection["events"].to_dict(orient="records"),
            "metadata": selection["metadata"],
        })

    frames, records = [], []
    # Stable instance ordering also keeps final output independent of config list order.
    for instance in [background] + sorted(attacks, key=lambda item: item["spec"]["id"]):
        spec, local = instance["spec"], instance["config"]
        is_attack = local["info"]["role"] == "attack"
        identity = ("attack", spec["id"]) if is_attack else ("background", spec["type"])
        context = make_context(reference, columns, timestamp, seed, identity, available)
        if is_attack:
            selection = groups[(spec["type"], spec["event_group"])]["selection"]
        else:
            selection_context = make_context(reference, columns, timestamp, seed, ("background_selection",), available)
            selection = instance["module"].select_events(selection_context, copy.deepcopy(local["params"]))
            validate_selection(selection, available, columns, "background")
        result = instance["module"].run(context, copy.deepcopy(local["params"]), copy.deepcopy(selection))
        validate_result(result, instance, columns, timestamp, selection)
        data = result["data"].copy()
        extra = set(data.columns) - set(reference.columns)
        if extra:
            raise ValueError(f"Generator {spec['type']} returned unexpected columns: {sorted(extra)}")
        warnings = list(result["warnings"])
        missing = [col for col in reference.columns if col not in data.columns]
        if missing:
            warnings.append(f"Non-event reference columns filled with missing values: {missing}")
        data = data.reindex(columns=reference.columns)
        data["truth_label"] = int(is_attack)
        data["attack_type"] = spec["type"]
        data["attack_id"] = spec["id"] if is_attack else ""
        frames.append(data)
        record = {
            "type": spec["type"], "params": local["params"], "generated_rows": len(data),
            "metadata": result["metadata"], "warnings": warnings,
        }
        if is_attack:
            record.update(id=spec["id"], event_group=spec["event_group"])
        records.append(record)

    combined = pd.concat([frame for frame in frames if len(frame)], ignore_index=True)
    combined[timestamp] = combined[timestamp].astype(np.int64)
    combined = combined.sort_values(by=timestamp, ascending=True, kind="stable", ignore_index=True)
    manifest = {
        "schema_version": 1, "seed": seed, "timestamp_column": timestamp,
        "event_columns": columns, "reference_rows": len(reference), "total_rows": len(combined),
        "experiment_config": config, "background": records[0], "attacks": records[1:],
        "event_groups": group_records,
    }
    return combined, json_safe(manifest)
