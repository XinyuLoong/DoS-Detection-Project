"""Copy this directory to create a profile test; see README.md for the steps."""

# ================= COMMON: Framework imports =================
import importlib.util
import os
import sys


# =============== OPTIONAL: Test-specific imports ==============
# Import only the libraries your algorithm or plots need here.
# For example: import matplotlib.pyplot as plt
# ====================== END OPTIONAL =========================


# ================= COMMON: Module loading ====================
TPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../bin"))
sys.path.insert(0, TPATH)

import trim_lib as tlib
import profile_report as preport


# Load this test's sibling config module without sharing another test's module.
config_path = os.path.join(os.path.dirname(__file__), "t_config.py")
config_spec = importlib.util.spec_from_file_location(f"{__name__}_config", config_path)
tc = importlib.util.module_from_spec(config_spec)
config_spec.loader.exec_module(tc)


def get_info():
   """Return the five metadata fields from this test's configuration."""
   return tc.read_t_config()["info"]


def run(profile_context, profile_report, level_name):
   """Analyze the shared input and return this test's standard result."""

   # ================= COMMON: Setup ==========================
   config = tc.read_t_config()
   test_name = config["info"]["name"]
   params = config["params"]
   df = profile_context["df"]
   stage = profile_context["stage"]
   verb = profile_context["trim_verb"]

   test_result = preport.new_test_result(test_name, level_name, stage)
   tlib.vprint(verb, f"{stage} {test_name}:", 1)

   # ================ TODO: Required inputs ===================
   # Read only the extra context fields this test needs. Examples:
   # event_column_list = profile_context["event_column_list"]
   # timestamp_column = profile_context["timestamp_column"]
   # idx_column = profile_context["idx_column"]
   #
   # Decide how to handle empty data, missing columns, and too few observations.
   # If modifying df in place, first use df = df.copy() so later tests are safe.
   # Example for a test that requires a real timestamp:
   # if profile_context["fake_timestamp"]:
   #    test_result["status"] = "skipped"
   #    preport.add_warning(test_result, "No real timestamp column defined.")
   #    return test_result
   # ====================== END TODO ==========================

   # ============== OPTIONAL: Previous results =================
   # Declare dependencies in the YAML and schedule them before this test in
   # profile_levels. The runner does not resolve dependencies automatically.
   # Example for a required event_uniqueness result:
   # previous = preport.get_test_result(profile_report, "event_uniqueness")
   # if previous is None or previous["status"] != "completed":
   #    test_result["status"] = "skipped"
   #    preport.add_warning(test_result, "Required event_uniqueness result unavailable.")
   #    return test_result
   # Read the required metric, feature, or table and handle missing values.
   # ==================== END OPTIONAL ========================

   # ================= TODO: Computation ======================
   # Inputs: df, params, any selected context fields, and required prior results.
   # Implement this test's calculations and store values for the result section.
   # Read adjustable parameters from params; validate them in t_config.py.
   # Replace the exception below with the actual implementation.
   raise NotImplementedError(f"Implement the {test_name} profile test.")
   # ====================== END TODO ==========================

   # ================= TODO: Record results ===================
   # Record the useful outputs calculated above using preport helpers.
   # Replace example names/variables with your actual outputs:
   # preport.add_metric(test_result, "metric_name", calculated_value)
   # preport.add_feature(test_result, "feature_name", calculated_feature)
   # preport.add_table(test_result, "table_name", calculated_df)
   # Only use the result categories this test produces.
   # No anomalies after a successful analysis still means "completed".
   # ====================== END TODO ==========================

   # =============== OPTIONAL: Files and plots =================
   # output_dir = profile_context["run_output_abs_path"]
   # Example after creating calculated_df:
   # csv_path = os.path.join(output_dir, f"profile_{test_name}_{stage}.csv")
   # tlib.r_df_to_csv(calculated_df, csv_path)
   # preport.add_artifact(test_result, "csv", test_name, csv_path)
   # For plots: create the figure, save under output_dir, register its path with
   # add_artifact(..., "plot", ...), and close the figure. Do not return early
   # while leaving a figure open. Give multiple outputs distinct file names.
   # ==================== END OPTIONAL ========================

   # =========== OPTIONAL: Suspicious units / advice ===========
   # Add these only when justified by the calculations above. Examples:
   # preport.add_suspicious_unit(
   #    test_result, "event",
   #    suspicion_measure={"metric": "metric_name", "value": calculated_value},
   #    values=event_values
   # )
   # preport.add_recommendation(test_result, "recommendation_type", suggested_value)
   # ==================== END OPTIONAL ========================

   # ================= COMMON: Return =========================
   return test_result
