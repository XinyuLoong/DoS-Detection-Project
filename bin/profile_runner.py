##########################################################
# file_name: profile_runner.py
# update_date: 2026-08-09
# brief:
#    Run the configured profiling workflow. This file builds the shared
#    profile context, reads and validates profile level configuration, executes
#    profile test modules level by level, and returns the profile report.
#
# functions:
#    create_profile_context(df, stage): Collect shared inputs for profile tests and returns a profile context dictionary.
#    get_profile_levels(): Read profile level configuration from trim_config and returns the level list.
#    get_profile_test_base_path(): Return the directory containing profile test modules.
#    load_profile_test(test_name): Load one profile test module by test name.
#    check_profile_levels(profile_levels): Validate profile level configuration and exits when the configuration is invalid.
#    run_profile_tests(df, stage): Run configured profile tests by level, stores each test result in the profile report, return the completed report.
##########################################################
import importlib.util
import os
import sys


TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import trim_lib as tlib
import profile_report as preport


PROFILE_TEST_MODULE_FILE = "t_test.py"


def create_profile_context(df, stage):
   """Create the shared context passed to every profile test."""

   return {
      "df": df,
      "stage": stage,
      "event_column_list": tlib.event_column_list,
      "timestamp_column": tlib.trim_config["cli"]["timestamp_column"],
      "fake_timestamp": tlib.trim_config["cli"]["fake_timestamp"],
      "idx_column": tlib.trim_config["var"]["index_column"],
      "trim_config": tlib.trim_config,
      "run_output_abs_path": tlib.run_output_abs_path,
      "trim_verb": tlib.trim_config["cli"]["trim_verb"]
   }


def get_profile_levels():
   """Read profile levels from config, with profile_list as a legacy fallback."""

   profile_config = tlib.trim_config.get("profile", {})

   if "profile_levels" in profile_config:
      return profile_config["profile_levels"]

   return [{
      "level": "profile",
      "tests": profile_config.get("profile_list", [])
   }]


def get_profile_test_base_path():
   """Return the base directory containing profile test modules."""

   filesystem_config = tlib.trim_config.get("filesystem", {})
   profile_test_path = filesystem_config.get("profile_test_path", "../lib/tests")
   return os.path.abspath(os.path.join(TPATH, profile_test_path))


def get_profile_test_module_path(test_name):
   """Return the expected module path for one profile test."""

   if os.path.basename(test_name) != test_name:
      print(f"Invalid profile test name {test_name}. Exiting", file=sys.stderr)
      sys.exit(1)

   return os.path.join(get_profile_test_base_path(), test_name,
                       PROFILE_TEST_MODULE_FILE)


def load_profile_test(test_name):
   """Load one profile test module from lib/tests."""

   module_path = get_profile_test_module_path(test_name)
   if not os.path.isfile(module_path):
      print(f"No profile test module {module_path}. Exiting", file=sys.stderr)
      sys.exit(1)

   module_name = f"trim_profile_test_{test_name}"
   spec = importlib.util.spec_from_file_location(module_name, module_path)
   if spec is None or spec.loader is None:
      print(f"Cannot load profile test module {module_path}. Exiting",
            file=sys.stderr)
      sys.exit(1)

   test_module = importlib.util.module_from_spec(spec)
   spec.loader.exec_module(test_module)

   for api_name in ["get_info", "run"]:
      if not hasattr(test_module, api_name):
         print((f"Profile test {test_name} must define {api_name}(). "
                f"Exiting"), file=sys.stderr)
         sys.exit(1)
      if not callable(getattr(test_module, api_name)):
         print((f"Profile test {test_name} {api_name} must be callable. "
                f"Exiting"), file=sys.stderr)
         sys.exit(1)

   test_info = test_module.get_info()
   if not isinstance(test_info, dict):
      print(f"Profile test {test_name} get_info() must return a dict. Exiting",
            file=sys.stderr)
      sys.exit(1)
   if test_info.get("name") != test_name:
      print((f"Profile test module name mismatch: config uses {test_name}, "
             f"module reports {test_info.get('name')}. Exiting"), file=sys.stderr)
      sys.exit(1)

   return test_module


def check_profile_levels(profile_levels):
   """Validate the level configuration before running tests."""

   if not isinstance(profile_levels, list):
      print(f"profile_levels must be a list. Exiting", file=sys.stderr)
      sys.exit(1)

   for level_config in profile_levels:
      if not isinstance(level_config, dict):
         print(f"Each profile level must be a dictionary. Exiting", file=sys.stderr)
         sys.exit(1)
      if "level" not in level_config:
         print(f"Each profile level must have a level. Exiting", file=sys.stderr)
         sys.exit(1)
      level_name = level_config["level"]
      if "tests" not in level_config:
         print(f"Profile level {level_name} must have tests. Exiting",
               file=sys.stderr)
         sys.exit(1)
      if not isinstance(level_config["tests"], list):
         print(f"Profile level {level_name} tests must be a list. Exiting",
               file=sys.stderr)
         sys.exit(1)

      for test_name in level_config["tests"]:
         load_profile_test(test_name)


def run_profile_tests(df, stage):
   """Run configured profile tests level by level and return a profile report."""

   profile_context = create_profile_context(df, stage)
   profile_report = preport.new_profile_report(stage)
   profile_levels = get_profile_levels()
   check_profile_levels(profile_levels)

   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], f"Defined profiling levels:", 1)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], profile_levels, 1)

   for level_config in profile_levels:
      level_name = level_config["level"]
      test_name_list = level_config["tests"]
      profile_report["levels"][level_name] = []

      tlib.vprint(tlib.trim_config["cli"]["trim_verb"],
                  f"== create_profile: running level {level_name}", 1)

      for test_name in test_name_list:
         tlib.vprint(tlib.trim_config["cli"]["trim_verb"],
                     f"== create_profile: running {test_name}", 1)
         test_module = load_profile_test(test_name)
         test_result = test_module.run(profile_context, profile_report, level_name)
         preport.add_test_result(profile_report, test_result)

   return profile_report
