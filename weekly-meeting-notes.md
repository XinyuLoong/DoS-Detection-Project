## Weekly Meeting Notes

## September 8, 2026
- [X] create a specific config file for each test following the existing model configuration pattern. Move hardcoded messages in get_info() into the configuration files
- [X] create a reusable test template to make it easier to add new tests (which needs to be revised after a more specific tests system is designed)
- [ ] design a clear workflow for iterative testing and refinement
[plan]: 
- 1. iteration params are not recorded in YAML
- 2. add a new file: profile_iteration.py, for (1) prepareing candidate parameters; (2) calling run(); (3) recording outputs for reference; (4) evaluating and analysising; (5) ouputing final params.
- 3. (not sure yet) add a new feature: running each test isolatedly (for example, when running a level 1 test, we don't need to run the other level 1 tests and following higher-level tests)


