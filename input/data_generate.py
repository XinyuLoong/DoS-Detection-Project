#!/usr/bin/env python3
"""Generate synthetic datasets for DoS / DDoS profiling experiments.

DATA GENERATION WORKFLOW

1. Copy/edit an experiment YAML under etc/generation_config/ BEFORE running:
   - _template.yaml is a complete experiment template and the CLI default.
     Copy it to a named experiment or edit one of the existing experiment files.
   - Set seed, timestamp_column, and event_columns for the reference CSV.
   - Set background.type and background.params.n_rows.
   - Configure the attacks list. Each entry needs a unique id, a type,
     an event_group, and optional params such as n_rows, duration, and
     attack_start. Use attacks: [] to generate background data only.
   - Experiment params override defaults in
     lib/generators/<type>/g_config.py without modifying the module defaults.

   Event groups are scoped by type. Within one type, the same event_group
   reuses the selected event set; different groups have disjoint event sets.
   Exact groups select one event, so attack counts and windows can differ.
   Distributed groups select multiple distinct events; same-group attacks
   must have matching n_rows and shared_fields, but windows can differ.
   A null attack_start chooses a random window within the reference range.

2. Run from the project root with the reference CSV and experiment config.
   Simple test:
    python input/data_generate.py -i input/history_scram-0f.csv

   Generated data defaults to the project's input/ directory for later profiling.
   The filename comes from the config: generation_normal.yaml produces
   input/synthetic_normal.csv; _template.yaml produces input/synthetic.csv.
   A sibling JSON file records generation details. Both the default config
   and output directory are resolved from the project location, independently
   of the working directory. Use -o input/custom.csv to choose another path.
   To use a separate experiment, copy/edit a YAML and select it explicitly:
    python input/data_generate.py -i input/history_scram-0f.csv \
        --config etc/generation_config/experiment2.yaml

3. Inspect the output CSV, its sibling JSON generation record, and the
   printed summary. The JSON records effective parameters, selected events,
   actual attack windows, generated row counts, and warnings.
   CSV labels truth_label, attack_type, and attack_id identify row provenance.
   Exclude all three labels from detector input features.

INTERNAL EXECUTION FLOW

This entry point reads the CSV and experiment YAML, then calls
bin/generation_runner.py:
   validate configuration and reference fields
   -> dynamically load generators and merge their default parameters
   -> resolve event groups using independent, reproducible random streams
   -> generate background and each attack
   -> validate results, add labels, combine rows, and shuffle
   -> return the dataset and generation record to this script.
This script then saves the CSV/JSON and prints the summary.

ADDING AN ATTACK TYPE

1. Copy lib/generators/_template/ to lib/generators/<new_type>/.
   Use a lowercase name such as burst. Keep g_generate.py and g_config.py
   in the copied directory. No type-specific YAML file is needed.
2. Edit DEFAULT_CONFIG in the new type's g_config.py:
   - Set info.name to the directory name and keep info.role as "attack".
   - Describe the type and define its default params.
   - List every parameter affecting event selection in
     info.selection_params. Same-group attacks must agree on these values.
3. In g_config.py, validate all parameters in read_g_config().
   Raise ValueError for invalid settings.
4. Implement the entry points in g_generate.py:
   - get_info(): return the generator metadata from its configuration.
   - select_events(context, params): choose distinct full events only from
     context["available_events"]; return {"events": DataFrame, "metadata": dict}.
     The runner caches this selection for group reuse and excludes events
     already assigned to other groups of the same type.
   - run(context, params, selected_events): generate exactly n_rows records
     using the selected event set; return
     {"data": DataFrame, "metadata": dict, "warnings": list_of_strings}.
     Include event columns and timestamps; the runner adds labels.
   Use context["rng"] for randomness. Do not modify shared inputs, print,
   or write output files inside the generator.
5. Add an entry with type: <new_type> to the experiment YAML's attacks list,
   configure its id/event_group/params, then run this script as above.
   No new type-specific branch or registry entry is needed in the runner.
6. Verify same-group reuse, different-group disjointness, parameter errors,
   insufficient candidates, row counts, and reproducibility for the new type.
   Run the generation checks with:
    python -m unittest discover -s tests -p 'test_generation.py'

The current interface adds records made from reference events. Inventing new
event values or modifying/deleting background records needs an interface
extension. Full details: lib/generators/_template/README.md.
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "bin") not in sys.path:
    sys.path.insert(0, str(ROOT / "bin"))

from generation_runner import generate_dataset
from lib.generators.common import GENERATION_CONFIG_DIR, load_yaml


DEFAULT_CONFIG = GENERATION_CONFIG_DIR / "_template.yaml"


def read_dataset(filepath):
    df = pd.read_csv(filepath)
    if df.empty:
        raise ValueError("Input dataset is empty")
    return df


def print_summary(synthetic, manifest, output_file, manifest_file):
    print(f"Synthetic dataset: {output_file}")
    print(f"Generation record: {manifest_file}")
    print(f"Total rows: {len(synthetic)}")
    print(synthetic.groupby(["attack_type", "attack_id"], dropna=False).size().to_string())
    timestamp = manifest["timestamp_column"]
    print(f"Timestamp range: {synthetic[timestamp].min()} .. {synthetic[timestamp].max()}")
    for record in [manifest["background"]] + manifest["attacks"]:
        for warning in record["warnings"]:
            print(f"WARNING [{record.get('id', 'background')}]: {warning}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate synthetic normal / exact flood / distributed flood datasets."
    )
    parser.add_argument("-i", "--input", required=True, help="Reference CSV dataset")
    parser.add_argument(
        "-o", "--output",
        help="Output CSV (default: project's input/synthetic_<experiment>.csv); writes a sibling JSON",
    )
    parser.add_argument(
        "--config", default=str(DEFAULT_CONFIG),
        help="Experiment YAML (default: project's etc/generation_config/_template.yaml)",
    )
    args = parser.parse_args(argv)
    config_name = Path(args.config).stem
    dataset_name = (
        "synthetic" if config_name == "_template"
        else f"synthetic_{config_name.removeprefix('generation_')}"
    )
    output_path = (
        Path(args.output) if args.output is not None
        else ROOT / "input" / f"{dataset_name}.csv"
    ).resolve()
    manifest_path = output_path.with_suffix(".json")
    protected = {Path(args.input).resolve(), Path(args.config).resolve()}
    if output_path == manifest_path or {output_path, manifest_path} & protected:
        parser.error("CSV and JSON output paths must be distinct from each other and from input/config files")
    reference = read_dataset(args.input)
    config = load_yaml(args.config)
    synthetic, manifest = generate_dataset(reference, config)
    manifest["input_file"] = str(Path(args.input).resolve())
    manifest["output_file"] = str(output_path)
    # Serialize first so metadata errors cannot leave a new CSV without its record.
    manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    synthetic.to_csv(output_path, index=False)
    manifest_path.write_text(manifest_text, encoding="utf-8")
    print_summary(synthetic, manifest, output_path, manifest_path)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
