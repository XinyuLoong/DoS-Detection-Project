import importlib.util
import os
import sys


TPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../bin"))
sys.path.insert(0, TPATH)

import trim_lib as tlib
import profile_report as preport


# Load the sibling config module by path to keep different tests isolated.
config_path = os.path.join(os.path.dirname(__file__), "t_config.py")
config_spec = importlib.util.spec_from_file_location(f"{__name__}_config", config_path)
tc = importlib.util.module_from_spec(config_spec)
config_spec.loader.exec_module(tc)


def get_info():
   """Return metadata for the duplicate row/event profile test."""

   return tc.read_t_config()["info"]


def run(profile_context, profile_report, level_name):
   """Profile duplicate rows and duplicate event patterns."""

   df = profile_context["df"]
   stage = profile_context["stage"]
   event_column_list = profile_context["event_column_list"]
   timestamp_column = profile_context["timestamp_column"]
   verb = profile_context["trim_verb"]

   test_result = preport.new_test_result("row_dup", level_name, stage)
   tlib.vprint(verb, f"{stage} row_dup:", 1)

   row_col_list = event_column_list + [timestamp_column]
   row_dup_df = tlib.flood_event_stats(df, row_col_list, 1)
   row_dup_df.drop(columns=["FloodScore", "AverageTimestamp", "StdDevTimestamp"],
                   inplace=True)

   event_dup_df = tlib.flood_event_stats(df, event_column_list, 1)
   event_dup_df.drop(columns=["FloodScore", "AverageTimestamp", "StdDevTimestamp"],
                   inplace=True)

   row_dup_list = row_dup_df['Occurrences'].tolist()
   row_dup_trim_nr = sum(row_dup_list) - len(row_dup_list)

   event_dup_list = event_dup_df['Occurrences'].tolist()
   event_dup_trim_nr = sum(event_dup_list) - len(event_dup_list)

   preport.add_metric(test_result, "dup_row_nr", row_dup_trim_nr)
   preport.add_metric(test_result, "dup_event_nr", event_dup_trim_nr)
   preport.add_metric(test_result, "dup_row_ratio", row_dup_trim_nr / len(df))
   preport.add_metric(test_result, "dup_event_ratio", event_dup_trim_nr / len(df))
   preport.add_table(test_result, "dup_row_df", row_dup_df)
   preport.add_table(test_result, "dup_event_df", event_dup_df)

   if row_dup_trim_nr > 0:
      preport.add_recommendation(
         test_result,
         "inspect_duplicate_rows",
         row_dup_trim_nr
      )
      tlib.vprint(verb, f"= REC {stage} row_dup: Duplicate rows = {row_dup_trim_nr}", 1)
      tlib.vprint(verb,
           (f"= REC {stage} row_dup: Duplicate row ratio = "
            f"{row_dup_trim_nr/len(df):.3f}"), 1)
   else:
      tlib.vprint(verb, f"{stage} row_dup: No duplicate rows found", 1)

   if event_dup_trim_nr > 0:
      preport.add_recommendation(
         test_result,
         "inspect_duplicate_events",
         event_dup_trim_nr
      )
      tlib.vprint(verb, f"= REC {stage} row_dup: Duplicate events = {event_dup_trim_nr}", 1)
      tlib.vprint(verb,
           (f"= REC {stage} row_dup: Duplicate event ratio = "
            f"{event_dup_trim_nr/len(df):.3f}"), 1)
   else:
      tlib.vprint(verb, f"{stage} row_dup: No duplicate events found", 1)

   return test_result
