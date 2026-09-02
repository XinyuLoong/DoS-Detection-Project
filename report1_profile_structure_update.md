# Profiling Code Structure Update Report

## 1. Brief Intro

This update focuses on the profiling part of the TRIM project. The goal is to make the profiling workflow easier to understand, easier to extend, and more suitable for layered profile tests.

The current design separates profiling execution, test implementation, and result storage into different modules. This structure is intended to support future profile tests at different levels, where lower-level tests extract dataset characteristics and higher-level tests reuse those outputs to make broader conclusions.

## 2. Original Profiling Structure

Before the restructuring, most profiling logic was concentrated in `trim_profile.py`. This file handled the profiling entry point, implemented individual profile tests, generated output files, and stored profiling results.

The original profiling workflow was closer to a flat list of tests. Each test produced its own outputs, but there was no clear shared result structure for all tests. As a result, it was difficult for higher-level tests to reliably read and reuse the results of lower-level tests.

## 3. Problems Definition

### 3.1 Profiling Logic Was Too Centralized

`trim_profile.py` contained multiple responsibilities at the same time. It worked as the profiling entry point, the test implementation file, and the result storage location.

This made the file harder to maintain. Adding or modifying one profile test could require more work.

### 3.2 Test Outputs Were Not Standardized

Different profile tests produced different kinds of outputs without a shared result format. Some information was stored in DataFrames, some was written to CSV or plot files, and some was only printed.

This made it difficult to compare test results or pass useful information from lower-level tests to higher-level tests.

### 3.3 Layered Profiling Was Hard to Support

The target design is a layered profiling framework. Level 1 tests should extract dataset characteristics from different perspectives. Level 2 tests should combine and corroborate Level 1 results. Future higher levels may focus on dataset-specific tuning and interpretation.

The previous structure did not clearly represent this layered execution model.

### 3.4 Configuration Was Less Flexible

The original configuration listed profile tests, but it did not organize them clearly by profiling level. This made it less convenient to add, remove, reorder, or move tests between levels.

## 4. Updated Profiling Structure

The profiling code has been separated into four main modules:

- `trim_profile.py`
- `profile_runner.py`
- `profile_report.py`
- `profile_tests.py`

Each file now has a clearer responsibility in the profiling workflow:

`trim_profile.py` remains the profiling entry point. It calls the profiling runner and stores the profile report by dataset stage.

`profile_runner.py` controls the profiling workflow. It creates the shared profile context, reads the configured profile levels, validates the configured tests, executes tests level by level, and returns the final profile report.

`profile_report.py` defines the standard result structures and helper APIs. It creates test result dictionaries, creates profile report dictionaries, adds result fields, and provides getter functions for reading stored results.

`profile_tests.py` stores the actual profiling test implementations. Each test receives the same profile context, creates a standard test result, adds its outputs, and returns the test result to the runner.

## 5. New Module Responsibilities

### 5.1 `trim_profile.py`

`trim_profile.py` is kept as the profiling entrance.

Its main function is `create_profile(df, stg)`. It runs configured dataset profiling for one stage, stores the returned report in `profile_report_dict`, and returns the report.

This keeps the entry layer small and avoids mixing high-level workflow control with individual test logic.

### 5.2 `profile_runner.py`

`profile_runner.py` is responsible for executing profile tests.

It builds a shared `profile_context` dictionary. This context contains common runtime information needed by tests, such as the input DataFrame, dataset stage, event columns, timestamp settings, index column, configuration, output path, and verbosity level.

It then reads `profile_levels` from the configuration, checks that each level and test is valid, and executes the registered tests level by level.

### 5.3 `profile_report.py`

`profile_report.py` defines the standardized result API.

It provides functions to create a new `test_result` and a new `profile_report`. It also provides helper functions to add metrics, features, tables, artifacts, suspicious units, recommendations, and warnings.

It also provides getter functions so that higher-level tests can read lower-level outputs in a consistent way.

### 5.4 `profile_tests.py`

`profile_tests.py` contains the current profile tests:

- `event_uniqueness`
- `time_dist`
- `flood_score`
- `row_dup`

Each test follows the same general pattern:

1. Read required values from `profile_context`.
2. Create a standard `test_result`.
3. Run the test-specific analysis.
4. Add outputs to the test result using `profile_report.py` helper functions.
5. Return the completed test result.

The file also defines `profile_test_dict`, which maps test names from the configuration to the corresponding Python functions.

## 6. Standardized Result Design

Each profile test now returns a standard `test_result` dictionary.

The main fields are:

- `test`: the profile test identifier.
- `level`: the profile level where the test is executed.
- `stage`: the dataset stage being profiled (e.g. initial).
- `status`: the execution status of the test.
- `metrics`: compact summary values, such as anomaly scores, counts, thresholds, or ratios.
- `features`: structured characteristics extracted from the dataset.
- `suspicious_units`: specific events, time windows, rows, or other units detected as suspicious.
- `tables`: detailed DataFrame outputs generated by the test.
- `artifacts`: saved output files, such as plots or CSV files.
- `recommendations`: suggested follow-up actions generated by the test.
- `warnings`: non-fatal warnings generated during test execution.

The stage-level `profile_report` collects all test results for one profiling stage. It stores test results by test name and also keeps a level-to-test mapping.

## 7. Layer-Based Execution Flow

The configuration now supports level-based profile execution through `profile_levels`.

Example:

```yaml
profile:
  profile_levels:
    - level: "l1"
      tests:
        - "event_uniqueness"
        - "time_dist"
        - "row_dup"
    - level: "l2"
      tests:
        - "flood_score"
```

The runner executes the levels in the order defined in the configuration.

The current design treats `event_uniqueness`, `time_dist`, and `row_dup` as Level 1 tests. These tests extract dataset characteristics from specific perspectives.

The current Level 2 test is `flood_score`. It can read lower-level outputs through the profile report API and combine different signals into a higher-level result.

This design makes it possible to add more levels later without changing the main profiling entry point.

## 8. How to Add or Modify Profile Tests

To add a new profile test:

1. Add a new test function in `profile_tests.py`.
2. The function should use the standard signature:

```python
def profile_new_test(profile_context, profile_report, level_name):
```

3. Inside the function, create a standard test result with `preport.new_test_result(...)`.
4. Add outputs using helper functions from `profile_report.py`.
5. Return the completed test result.
6. Register the function in `profile_test_dict`.
7. Add the test name to the desired level in `trim_config.yaml`.

To modify an existing test, most changes should happen inside the corresponding test function in `profile_tests.py`.

To reorganize tests by level, update `profile_levels` in `trim_config.yaml`.

## 9. Current Limitations

The current result structure is standardized, but some test-specific logic is still tightly connected to the current algorithms.

For example, clustering-related features currently use the existing two-cluster KMeans-based outlier score. This works for the current tests, but future algorithms may produce different intermediate outputs. The result structure may need to be adjusted if more diverse anomaly detection methods are added. 
But I decide to leave it untill new algorithm is imported.

The Level 3 design has not been implemented yet. The current work mainly prepares the profiling framework so that future Level 3 tests can be added more easily. 
Also, I decide to leave it untill a real level 3 test is implemented.

Some current tests still generate plots and CSV files directly inside the test functions. This is acceptable for the current stage, but output generation could be further separated later if needed.

## 10. Next Steps

The next steps are:

1. Refine the existing Level 1 tests and verify new Level 1 test ideas.
2. Improve the Level 2 logic so it can better combine and corroborate lower-level results.
3. Design future Level 3 tests for dataset-specific threshold tuning and severity interpretation.

