# Profile test template

## How to use it

Copy this entire directory to create a new profiling test. 
`COMMON` sections provide the framework code, 
`TODO` sections need implementation or review,
`OPTIONAL` sections contain commented examples to enable only when needed.

## Add a test

1. Copy `lib/tests/_template` to `lib/tests/<new_test_name>` inside this project.
   Keep the same directory depth so the existing module paths work.
2. Edit `etc/t_config.yaml` in the copy: set `info.name` to the directory name,
   describe the test, and review `level`, `dependencies`, and `supports_iteration`.
   Add calculation parameters under `params`, or keep `params: {}`.
3. In `t_config.py`, add checks for every parameter used by the algorithm.
   Retain the shared metadata and configuration checks.
4. In `t_test.py`, select inputs, implement computation, and record useful results.
   Replace `NotImplementedError` with your implementation. Uncomment and adapt
   optional examples only after defining their input variables. Keep `get_info()`
   and the `run(profile_context, profile_report, level_name)` signature.
5. Verify the new test with representative data, unsuitable input, and changed or
   invalid parameters. Check that it returns a standard result and does not alter
   shared input unexpectedly. An unfinished copy intentionally raises
   `NotImplementedError` instead of reporting an empty successful result.
6. Add the new name to the appropriate existing `profile.profile_levels` entry
   in the project's `etc/trim_config.yaml`, after any required tests.
   Keep `_template` out of the enabled test list.

For example, to enable a completed test called `new_test`, append `new_test` to
the `tests` list of its chosen level. Preserve the existing tests and their order.

## Inputs available to `run()`

| Input | Meaning |
| --- | --- |
| `profile_context["df"]` | Shared input DataFrame; copy before in-place edits. |
| `profile_context["stage"]` | Dataset stage, such as `initial` or `trimmed`. |
| `profile_context["event_column_list"]` | Columns that together identify an event pattern. |
| `profile_context["timestamp_column"]` | Timestamp column name. |
| `profile_context["fake_timestamp"]` | Whether timestamps are artificial. |
| `profile_context["idx_column"]` | Generated row identifier column name. |
| `profile_context["run_output_abs_path"]` | Directory for this run's output files. |
| `profile_context["trim_verb"]` | Output verbosity. |
| `profile_context["trim_config"]` | Shared application configuration; keep new test parameters in local `params`. |
| `profile_report` | Results already recorded by earlier tests. |
| `level_name` | Actual execution level selected by the runner. |

The runner currently checks the metadata name but does not use `info.level`,
`dependencies`, or `supports_iteration` to schedule execution. Configure the
actual order in `profile_levels`. If a previous result is required, use
`preport.get_test_result()`, check its status, and handle missing fields explicitly.
Use `get_metric()`, `get_feature()`, or `get_table()` to retrieve specific outputs;
an absent result should not silently become a valid zero measurement.

## Results and status

Initialize results with `preport.new_test_result()` and return `test_result`.
The runner inserts it into the shared report; the test does not need to do that.

| Helper | Use |
| --- | --- |
| `add_metric()` | Summary numbers such as counts, ratios, or scores. |
| `add_feature()` | More detailed calculated features. |
| `add_table()` | DataFrames associated with the analysis. |
| `add_artifact()` | Register paths of CSV files or figures already saved. |
| `add_suspicious_unit()` | Events, rows, or time windows identified as suspicious. |
| `add_recommendation()` | Suggested actions supported by the analysis. |
| `add_warning()` | Explanations, including why analysis was skipped. |

Use only the result categories your test produces. A successful analysis with no
anomalies remains `completed`. When input is unsuitable, set `status` to `skipped`,
add a warning explaining why, and return. Do not hide implementation or
configuration errors as skipped analyses. Save files inside the supplied output
directory, include the test name and stage in filenames, and close plot figures.

## Existing examples

- `row_dup`: counts, ratios, tables, and recommendations without plots.
- `event_uniqueness`: local threshold, clustering, and suspicious event patterns.
- `time_dist`: timestamp prerequisites, skipped results, and time windows.
- `flood_score`: reading earlier metrics, several parameters, and recommendations.

this template's default `params` is empty, and it assumes no particular scoring formula, plotting library, or dependency.
