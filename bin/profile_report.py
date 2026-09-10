##########################################################
# file_name: profile_report.py
# update_date: 2026-08-09
# brief:
#    Defines the standard profiling result structures and helper APIs for 
#    creating, updating, and reading profile reports and test results.
#
# functions:
#    new_test_result(test, level, stage, status="completed"): Create the standard result dictionary for one profile test and returns it.
#    new_profile_report(stage): Create the standard report dictionary for one profiling stage and returns it.
#    add_metric(test_result, metric_name, metric_value):
#       Add one metric to a test result and returns the updated test result.
#       Note: metric includes compact summary values produced by a profile test.
#    add_feature(test_result, feature_name, feature_value):
#       Add one extracted feature object to a test result and returns the updated test result.
#       Note: Features mean characteristics extracted during a test, usually with more detail than a single metric.
#    add_table(test_result, table_name, table_df): Add one DataFrame table to a test result and returns the updated test result.
#    add_artifact(test_result, artifact_type, artifact_name, artifact_path): Add one output file(figure/csv or other format) record to a test result and returns the updated test result.
#    add_suspicious_unit(test_result, unit_type, suspicion_measure=None, **kwargs): Add one suspicious unit record from a test to the test's result and returns the updated test result.
#    add_recommendation(test_result, rec_type, value, **kwargs): Add one test-level recommendation to a test result and returns the updated test result.
#    add_warning(test_result, warning):
#       Add one warning message to a test result and returns the updated test result.
#       Note: Current warnings are produced when a test cannot complete its anomaly analysis, such as
#           "No event occurrence clustering found.",
#           "No real timestamp column defined.",
#           "All timestamps are equal.",
#           "Not enough time bins for anomaly analysis.",
#           "No time density clustering found.",
#           "No events have high occurrence rate.", or
#           "No flood score clustering found."
#    add_test_result(profile_report, test_result): Add one completed test result to a profile report and returns the updated profile report.
#    get_test_result(profile_report, test_name, default=None): Read one test result from a profile report and returns it.
#    get_metric(profile_report, test_name, metric_name, default=None): Read one metric from a test result and returns it.
#    get_feature(profile_report, test_name, feature_name, default=None): Read one feature from a test result and returns it.
#    get_table(profile_report, test_name, table_name, default=None): Read one table from a test result and returns it.
#    get_suspicious_units(profile_report, unit_type=None, test_name=None): Read suspicious units from a profile report and returns a copied list.
#    get_recommendations(profile_report, rec_type=None, test_name=None): Read recommendations from a profile report and returns a copied list.
#    get_artifacts(profile_report, artifact_type=None, test_name=None): Read artifacts from a profile report and returns a copied list.
##########################################################
import copy

def new_test_result(test, level, stage, status="completed"):
   """brief:
      Create the standard result dictionary for one profile test.

   paras:
      test: Profile test identifier, such as "event_uniqueness".
      level: Profile level identifier, such as "l1" or "l2".
      stage: Dataset stage label, such as "initial".
      status: Execution status for the test result.

   return:
      New test result dictionary with standard result fields.
   """

   return {
      "test": test,
      "level": level,
      "stage": stage,
      "status": status,
      "metrics": {},
      "features": {},
      "suspicious_units": [],
      "tables": {},
      "artifacts": [],
      "recommendations": [],
      "warnings": []
   }


def new_profile_report(stage):
   """brief:
      Create the standard report dictionary for one profiling stage.

   paras:
      stage: Dataset stage label, such as "initial".

   return:
      New profile report dictionary with level, test, artifact, and warning
      containers.
   """

   return {
      "stage": stage,
      "levels": {},
      "tests": {},
      "artifacts": [],
      "warnings": []
   }


def add_metric(test_result, metric_name, metric_value):
   """brief:
      Add one metric value to a test result.

   paras:
      test_result: Test result dictionary to update.
      metric_name: Metric field name to add.
      metric_value: Metric value to store.

   return:
      Updated test result dictionary.
   """

   test_result["metrics"][metric_name] = metric_value
   return test_result


def add_feature(test_result, feature_name, feature_value):
   """brief:
      Add one extracted feature to a test result.

   paras:
      test_result: Test result dictionary to update.
      feature_name: Feature field name to add.
      feature_value: Feature value or object to store.

   return:
      Updated test result dictionary.
   """

   test_result["features"][feature_name] = feature_value
   return test_result


def add_table(test_result, table_name, table_df):
   """brief:
      Add one table object to a test result.

   paras:
      test_result: Test result dictionary to update.
      table_name: Table field name to add.
      table_df: DataFrame table to store.

   return:
      Updated test result dictionary.
   """

   test_result["tables"][table_name] = table_df
   return test_result


def add_artifact(test_result, artifact_type, artifact_name, artifact_path):
   """brief:
      Add one saved output artifact to a test result.

   paras:
      test_result: Test result dictionary to update.
      artifact_type: Artifact category, such as "plot" or "csv".
      artifact_name: Artifact identifier inside the test result.
      artifact_path: File path to the saved artifact.

   return:
      Updated test result dictionary.
   """

   test_result["artifacts"].append({
      "type": artifact_type,
      "artifact": artifact_name,
      "path": artifact_path
   })
   return test_result


def add_suspicious_unit(test_result, unit_type, suspicion_measure=None, **kwargs):
   """brief:
      Add one suspicious unit detected by a profile test.

   paras:
      test_result: Test result dictionary to update.
      unit_type: Suspicious unit category, such as "event" or "time_window".
      suspicion_measure: Unit-level measurement that explains why this unit is
         suspicious.
      **kwargs: Additional fields for this suspicious unit.

   return:
      Updated test result dictionary.
   """

   if suspicion_measure is None:
      suspicion_measure = {}
   suspicious_unit = {
      "unit_type": unit_type,
      "suspicion_measure": suspicion_measure
   }
   suspicious_unit.update(kwargs)
   test_result["suspicious_units"].append(suspicious_unit)
   return test_result


def add_recommendation(test_result, rec_type, value, **kwargs):
   """brief:
      Add one recommendation generated by a profile test.

   paras:
      test_result: Test result dictionary to update.
      rec_type: Recommendation category, such as "trim_rows".
      value: Main recommendation value.
      **kwargs: Additional fields for this recommendation.

   return:
      Updated test result dictionary.
   """

   recommendation = {
      "type": rec_type,
      "value": value
   }
   recommendation.update(kwargs)
   test_result["recommendations"].append(recommendation)
   return test_result


def add_warning(test_result, warning):
   """brief:
      Add one warning message generated while running a profile test.

   paras:
      test_result: Test result dictionary to update.
      warning: Warning message to store.

   return:
      Updated test result dictionary.
   """

   test_result["warnings"].append(warning)
   return test_result


def add_test_result(profile_report, test_result):
   """brief:
      Add one profile test result to the stage-level profile report.

   paras:
      profile_report: Profile report dictionary to update.
      test_result: Completed test result dictionary to add.

   return:
      Updated profile report dictionary.
   """

   level_name = test_result["level"]
   test_name = test_result["test"]

   if level_name not in profile_report["levels"]:
      profile_report["levels"][level_name] = []
   if test_name not in profile_report["levels"][level_name]:
      profile_report["levels"][level_name].append(test_name)

   profile_report["tests"][test_name] = test_result
   profile_report["artifacts"].extend(test_result["artifacts"])
   profile_report["warnings"].extend(test_result["warnings"])

   return profile_report


def get_test_result(profile_report, test_name, default=None):
   """brief:
      Read one test result from a profile report.

   paras:
      profile_report: Profile report dictionary to read from.
      test_name: Profile test identifier to read.
      default: Value returned when the test result does not exist.

   return:
      Test result dictionary, or default when it is not found.
   """

   return profile_report.get("tests", {}).get(test_name, default)


def get_metric(profile_report, test_name, metric_name, default=None):
   """brief:
      Read one metric from a stored test result.

   paras:
      profile_report: Profile report dictionary to read from.
      test_name: Profile test identifier to read.
      metric_name: Metric field name to read.
      default: Value returned when the test or metric does not exist.

   return:
      Metric value, or default when it is not found.
   """

   test_result = get_test_result(profile_report, test_name)
   if not test_result:
      return default
   return test_result.get("metrics", {}).get(metric_name, default)


def get_feature(profile_report, test_name, feature_name, default=None):
   """brief:
      Read one feature from a stored test result.

   paras:
      profile_report: Profile report dictionary to read from.
      test_name: Profile test identifier to read.
      feature_name: Feature field name to read.
      default: Value returned when the test or feature does not exist.

   return:
      Feature value, or default when it is not found.
   """

   test_result = get_test_result(profile_report, test_name)
   if not test_result:
      return default
   return test_result.get("features", {}).get(feature_name, default)


def get_table(profile_report, test_name, table_name, default=None):
   """brief:
      Read one table from a stored test result.

   paras:
      profile_report: Profile report dictionary to read from.
      test_name: Profile test identifier to read.
      table_name: Table field name to read.
      default: Value returned when the test or table does not exist.

   return:
      Table object, or default when it is not found.
   """

   test_result = get_test_result(profile_report, test_name)
   if not test_result:
      return default
   return test_result.get("tables", {}).get(table_name, default)


def get_suspicious_units(profile_report, unit_type=None, test_name=None):
   """brief:
      Read suspicious units from stored test results.

   paras:
      profile_report: Profile report dictionary to read from.
      unit_type: Optional suspicious unit category filter.
      test_name: Optional profile test identifier filter.

   return:
      Copied list of suspicious unit dictionaries.
   """

   suspicious_units = []

   for cur_test_name, test_result in profile_report.get("tests", {}).items():
      if test_name and cur_test_name != test_name:
         continue
      for suspicious_unit in test_result.get("suspicious_units", []):
         if unit_type and suspicious_unit.get("unit_type") != unit_type:
            continue
         suspicious_units.append(copy.deepcopy(suspicious_unit))

   return suspicious_units


def get_recommendations(profile_report, rec_type=None, test_name=None):
   """brief:
      Read recommendations from stored test results.

   paras:
      profile_report: Profile report dictionary to read from.
      rec_type: Optional recommendation category filter.
      test_name: Optional profile test identifier filter.

   return:
      Copied list of recommendation dictionaries.
   """

   recommendations = []

   for cur_test_name, test_result in profile_report.get("tests", {}).items():
      if test_name and cur_test_name != test_name:
         continue
      for recommendation in test_result.get("recommendations", []):
         if rec_type and recommendation.get("type") != rec_type:
            continue
         recommendations.append(copy.deepcopy(recommendation))

   return recommendations


def get_artifacts(profile_report, artifact_type=None, test_name=None):
   """brief:
      Read artifacts from stored test results.

   paras:
      profile_report: Profile report dictionary to read from.
      artifact_type: Optional artifact category filter.
      test_name: Optional profile test identifier filter.

   return:
      Copied list of artifact dictionaries.
   """

   artifacts = []

   for cur_test_name, test_result in profile_report.get("tests", {}).items():
      if test_name and cur_test_name != test_name:
         continue
      for artifact in test_result.get("artifacts", []):
         if artifact_type and artifact.get("type") != artifact_type:
            continue
         artifacts.append(copy.deepcopy(artifact))

   return artifacts
