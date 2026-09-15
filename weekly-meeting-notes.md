## Weekly Meeting Notes

## September 8, 2026
- [X] create a specific config file for each test following the existing model configuration pattern. Move hardcoded messages in get_info() into the configuration files
- [X] create a reusable test template to make it easier to add new tests (which needs to be revised after a more specific tests system is designed)
- [ ] design a clear workflow for iterative testing and refinement
[plan]: 
- 1. iteration params are not recorded in YAML
- 2. add a new file: profile_iteration.py, for (1) prepareing candidate parameters; (2) calling run(); (3) recording outputs for reference; (4) evaluating and analysising; (5) ouputing final params.
- 3. (not sure yet) add a new feature: running each test isolatedly (for example, when running a level 1 test, we don't need to run the other level 1 tests and following higher-level tests)

## September 15, 2026
- [ ] implement the iteration
- Note #1: Integrate automatic parameter tuning into the main workflow. The workflow should automatically select a suitable parameter configuration for each dataset using a predefined validation metric.
- Note #2: Define configurable iteration limits and convergence criteria. Set N_max as the maximum number of iterations and E_min as the minimum error / improvement. Stop when N_max is reached or when the error is less than a number / when improvement remains below E_min. Retain the best configuration found during the search.
- Question for N#2: how to make it converge? How to measure the Error or Improvement?
- Note #3: Run from the top level: running a higher-level test should automatically trigger parameter tuning for its dependencies in the required order. Reuse saved tuning results when the dataset and relevant configurations are unchanged
- Note #4: run iteration for each important params within the test.
- [ ] figure out the criteria for parameters selection
- F1 score: for the dataset I made up for testing, we have a label to calculate F1 score; but for a real log data, it has no labels.
- design a better criteria for parameter calibration...


