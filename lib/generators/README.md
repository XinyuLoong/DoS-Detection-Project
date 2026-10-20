# Synthetic data generation

Run from the repository root:

```bash
python input/data_generate.py -i input/history_scram-0f.csv
```

The command writes `input/synthetic.csv` and `input/synthetic.json`, ready for
later profiling. The JSON records the
effective parameters, input/output paths, seed, selected events, actual attack
windows (exclusive end), counts, and warnings. Reference timestamps must be
finite integer-valued numbers interpreted as seconds. Window starts may be null
for random placement; explicit windows outside the reference range are allowed
with a warning. Overlapping attacks are allowed.

## Configuration and event groups

All generation YAML files are stored under `etc/generation_config/`:

```text
etc/generation_config/
    _template.yaml                     Experiment template and CLI default
    generation_normal.yaml             Background only
    generation_exact_one_event.yaml    One exact target
    generation_exact_two_events.yaml   Two distinct exact targets
```

This directory contains complete experiment configurations only. Copy
`_template.yaml` to create a new experiment, or edit an existing experiment.
Generator metadata and defaults are defined in `DEFAULT_CONFIG` in
`lib/generators/<type>/g_config.py`; no type-specific YAML is required. Experiment `params`
override those defaults in memory. Unknown parameters or configuration keys are
errors. Each attack needs a unique `id` and an explicit `event_group`.

For example, select the two-target experiment with:

```bash
python input/data_generate.py -i input/history_scram-0f.csv \
  --config etc/generation_config/generation_exact_two_events.yaml
```

Without `-o`, output names follow the experiment configuration:

| Configuration | Dataset | Generation record |
| --- | --- | --- |
| `generation_normal.yaml` | `input/synthetic_normal.csv` | `input/synthetic_normal.json` |
| `generation_exact_one_event.yaml` | `input/synthetic_exact_one_event.csv` | `input/synthetic_exact_one_event.json` |
| `generation_exact_two_events.yaml` | `input/synthetic_exact_two_events.csv` | `input/synthetic_exact_two_events.json` |

Groups are scoped by `(type, event_group)`:

- Exact: the same group reuses one complete event. Counts and windows can differ.
- Distributed: the same group reuses the **entire set of complete events**. Both
  `n_rows` and `shared_fields` must match; windows can differ. It does not merely
  reuse a shared-field condition and resample different complete events.
- Different groups of the same type have disjoint complete event sets.
- Different types are not constrained to have disjoint events, even when group
  names match. Background rows may also match attack events.

The distributed same-set behavior is the initial interpretation of the design;
shared-condition reuse would be a distinct future option. The generator retains
the existing no-replacement rule, so each selected event appears once per attack.
Shared fields are chosen automatically by searching for the largest group.
Different groups may have the same shared-field values while their complete
events differ. All groups are allocated greedily in sorted type/group order;
there is no global allocation solver. An allocation failure reports insufficient
candidates instead of silently reusing events.

Example: two distributed attacks using the same events, and a third using a
disjoint set (the reference must contain enough qualifying unique events):

```yaml
seed: 42
timestamp_column: updated
event_columns: [scope, source, field, value, signature]
background:
  type: normal
  params: {n_rows: 10000}
attacks:
  - id: d1
    type: distributed
    event_group: shared
    params: {n_rows: 20, shared_fields: 3, duration: 60}
  - id: d2
    type: distributed
    event_group: shared
    params: {n_rows: 20, shared_fields: 3, duration: 120}
  - id: d3
    type: distributed
    event_group: separate
    params: {n_rows: 20, shared_fields: 3, duration: 60}
```

Use `attacks: []` for background-only data. Background count may be zero when
there are attacks; a completely empty experiment is rejected. Default experiment
event columns are the five reference fields shown above. Declare another schema
explicitly rather than silently dropping missing columns.

## Reproducibility and labels

Named random streams separate background, event-group selection, each attack ID,
and final shuffling. For the same data/configuration/library versions, results
are repeatable and reordering attacks does not change output. Changing the count
of one exact attack does not alter another attack's unshuffled records. Adding,
renaming, or resizing event groups can change allocation for other groups because
they compete for disjoint events. Changing total row count changes final shuffle
positions.

`truth_label`, `attack_type`, and `attack_id` record row provenance; they are not
detector inputs. Exclude all three from profiling event fields. Background rows
receive label 0 and an empty attack ID; injected rows receive label 1 and their
instance ID. Sampling reference rows with replacement can introduce duplicates;
the generator does not verify that the reference is attack-free. Input data must
not already contain the three reserved label columns. Unspecified non-event
reference fields on attack rows are filled with missing values and reported.

## CLI and Python API

The CLI requires `--input`. By default it loads the project's
`etc/generation_config/_template.yaml`, resolved relative to the project location rather
than the working directory. Use `--config path/to/experiment.yaml` to select a
different file; explicitly supplied relative paths use the working directory.
The default output directory is the project's `input/`, independent of the
working directory. Named configs produce `synthetic_<config-stem>.csv`, with
a leading `generation_` removed; `_template.yaml` produces `synthetic.csv`.
The JSON record uses the same basename. Use `--output input/custom.csv` to
override the destination. Re-running the same configuration replaces its
output files; different configuration basenames produce separate datasets.
A missing configuration file is an error. All generation parameters,
including the seed, background count, event columns, and attack settings, belong
in the experiment YAML. Use a one-item `attacks` list for a single attack.

The batch API is `generation_runner.generate_dataset(reference_df, experiment_config)` (add
the repository `bin` directory to the Python import path). It returns a DataFrame
and a JSON-safe manifest without writing files or changing caller data/config.

See `_template/README.md` to add a type. Run validation with:

```bash
python -m unittest discover -s tests -p 'test_generation.py'
```
