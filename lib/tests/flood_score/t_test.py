import importlib.util
import os
import sys

import pandas as pd
import matplotlib.pyplot as plt


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
   """Return metadata for the flood score profile test."""

   return tc.read_t_config()["info"]


def run(profile_context, profile_report, level_name):
   """Combine event frequency and timestamp compactness into a flood score."""

   df = profile_context["df"]
   stage = profile_context["stage"]
   event_column_list = profile_context["event_column_list"]
   output_dir = profile_context["run_output_abs_path"]
   verb = profile_context["trim_verb"]
   config = tc.read_t_config()
   params = config["params"]
   idx_column = profile_context["idx_column"]

   test_result = preport.new_test_result("flood_score", level_name, stage)
   tlib.vprint(verb, f"{stage} flood_score:", 1)

   count_threshold = max(params["flood_count_threshold"],
                  int(len(df) * params["flood_frac_threshold"]))

   flood_score_df = tlib.flood_event_stats(df, event_column_list, count_threshold)
   while count_threshold > 0 and len(flood_score_df) < 10:
      count_threshold = int(count_threshold // 3)
      flood_score_df = tlib.flood_event_stats(df, event_column_list, count_threshold)

   tlib.vprint(verb, f"{stage} flood_score: count_threshold = {count_threshold}", 1)
   tlib.vprint(verb, f"{stage} flood_score: flood_score_df has {len(flood_score_df)} rows", 1)

   preport.add_metric(test_result, "count_threshold", count_threshold)
   preport.add_metric(test_result, "flood_score_df_len", len(flood_score_df))
   preport.add_metric(test_result, "event_uniqueness_score",
         preport.get_metric(profile_report, "event_uniqueness", "anomaly_score", 0.0))
   preport.add_metric(test_result, "time_dist_score",
         preport.get_metric(profile_report, "time_dist", "anomaly_score", 0.0))

   if len(flood_score_df) < 1 or \
         flood_score_df['Occurrences'].max() < params["flood_count_threshold"]:
      tlib.vprint(verb, f"No events have high occurrence rate.", 1)
      tlib.vprint(verb, f"{stage} flood_score: outlier_score = 0.0", 1)
      test_result["status"] = "skipped"
      preport.add_metric(test_result, "anomaly_score", 0.0)
      preport.add_metric(test_result, "dataset_score", 0.0)
      preport.add_warning(test_result, "No events have high occurrence rate.")
      return test_result

   flood_score_df.sort_values(by='AverageTimestamp', inplace=True)

   outlier_score, small_cluster, small_centroid, large_centroid, \
         labels = tlib.clustering_outlier_score(flood_score_df['FloodScore'].tolist())

   preport.add_metric(test_result, "anomaly_score", outlier_score)
   preport.add_metric(test_result, "dataset_score", outlier_score)
   preport.add_feature(test_result, "clustering", {
      "method": "kmeans_2",
      "outlier_cluster": small_cluster,
      "outlier_centroid": small_centroid,
      "baseline_centroid": large_centroid
   })

   if len(small_cluster) == 0:
      tlib.vprint(verb, f"{stage} flood_score: No clustering found", 1)
      tlib.vprint(verb, f"{stage} flood_score: outlier_score = 0.0", 1)
      test_result["status"] = "skipped"
      preport.add_warning(test_result, "No flood score clustering found.")
      return test_result

   flooding_events_df = pd.DataFrame()
   flood_index_list = []
   flood_trim_nr = 0

   if outlier_score > params["fs_anom_cutoff_score"]:
      occurence_mask = flood_score_df['FloodScore'].isin(small_cluster)
      flooding_events_df = flood_score_df[occurence_mask]
      tlib.vprint(verb, f"{stage} flood_score: flooding_events_df", 3)
      tlib.vprint(verb, f"{stage} flood_score: flooding_events_df:", 1)
      tlib.vprint(verb, f"{flooding_events_df}", 1)

      merged_df = pd.merge(df, flooding_events_df, on=event_column_list, how='inner')
      flood_index_list = merged_df[idx_column + '_x'] \
               if idx_column in event_column_list else merged_df[idx_column]
      flood_index_list = flood_index_list.tolist()
      flood_trim_nr = int(0.9 * len(flood_index_list))

      tlib.vprint(verb, f"Flood suggested trim rows: {flood_trim_nr}", 1)
      tlib.vprint(verb, f"Flood index list of length {len(flood_index_list)}", 1)
      tlib.vprint(verb, f"{flood_index_list}", 3)

      for _, row in flooding_events_df.iterrows():
         values = {col: row[col] for col in event_column_list}
         event_index_list = merged_df[
            (merged_df[event_column_list] == row[event_column_list]).all(axis=1)
         ][idx_column].tolist() if idx_column in merged_df.columns else flood_index_list
         preport.add_suspicious_unit(
            test_result,
            "event",
            suspicion_measure={
               "metric": "flood_score",
               "value": float(row["FloodScore"])
            },
            values=values,
            index_list=event_index_list
         )

      preport.add_recommendation(
         test_result,
         "trim_rows",
         flood_trim_nr,
         index_list=flood_index_list
      )
      tlib.vprint(verb,
           (f"= REC flood_score: To reduce flooding it is recommended to trim "
            f"at least {flood_trim_nr} events"), 1)

   flood_score_df['AverageTimestamp'] = flood_score_df['AverageTimestamp'].astype(int)
   plt.scatter(flood_score_df['AverageTimestamp'].apply(tlib.epoch_to_datetime),
               flood_score_df['FloodScore'], marker='o', color='black', alpha=0.5)
   plt.yscale('log')
   plt.xlabel("timestamp")
   plt.ylabel(f"{stage} event flood score")
   plt.xticks(fontsize=6)
   if outlier_score > params["fs_anom_cutoff_score"]:
      plt.title((f"Flood anomaly score = {outlier_score:.1f},"
                 f" {len(small_cluster)} flooding events"), fontsize=10)
   else:
      plt.title(f"Flood anomaly score = {outlier_score:.1f}", fontsize=10)

   plot_path = f"{output_dir}/profile_flood_score_{stage}.png"
   csv_path = f"{output_dir}/profile_flood_score_{stage}.csv"
   plt.savefig(plot_path, dpi=300, bbox_inches='tight')

   if verb > 1:
      plt.show()
   plt.close()

   flood_score_df.sort_values(by='FloodScore', ascending=False, inplace=True)
   tlib.r_df_to_csv(flood_score_df, csv_path)

   preport.add_table(test_result, "flood_score_df", flood_score_df)
   if len(flooding_events_df) > 0:
      preport.add_table(test_result, "flooding_events_df", flooding_events_df)
   preport.add_artifact(test_result, "plot", "flood_score", plot_path)
   preport.add_artifact(test_result, "csv", "flood_score", csv_path)

   tlib.vprint(verb, f"{flood_score_df}", 3)
   return test_result
