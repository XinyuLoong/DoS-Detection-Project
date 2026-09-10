import os
import sys

import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt


TPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../bin"))
sys.path.insert(0, TPATH)

import trim_lib as tlib
import profile_report as preport


def get_info():
   """Return metadata for the time distribution profile test."""

   return {
      "name": "time_dist",
      "level": "l1",
      "description": "Profile timestamp density and find suspicious time windows.",
      "dependencies": [],
      "supports_iteration": True
   }


def run(profile_context, profile_report, level_name):
   """Profile timestamp density and find suspicious time windows."""

   df = profile_context["df"]
   stage = profile_context["stage"]
   output_dir = profile_context["run_output_abs_path"]
   verb = profile_context["trim_verb"]
   config = profile_context["trim_config"]
   timestamp_column = profile_context["timestamp_column"]

   test_result = preport.new_test_result("time_dist", level_name, stage)

   if profile_context["fake_timestamp"]:
      tlib.vprint(verb, f"{stage} time_dist: No timestamp column defined. No test", 1)
      test_result["status"] = "skipped"
      preport.add_warning(test_result, "No real timestamp column defined.")
      return test_result

   tlib.vprint(verb, f"{stage} time_dist: Timestamp column: {timestamp_column}", 1)

   time_dist_df = df[[timestamp_column]]
   min_val = time_dist_df[timestamp_column].min()
   max_val = time_dist_df[timestamp_column].max()
   outlier_score = 0.0
   small_cluster = []
   small_centroid = 0.0
   large_centroid = 0.0

   if min_val == max_val:
      tlib.vprint(verb, f"{stage} time_dist: All timestamps are equal. No test", 1)
      test_result["status"] = "skipped"
      preport.add_metric(test_result, "anomaly_score", outlier_score)
      preport.add_warning(test_result, "All timestamps are equal.")
      return test_result

   timebin = min(config["profile"]["time_bin"], int((max_val-min_val)/10))
   if timebin < 1:
      timebin = 1
   start_bin = min_val - (min_val % timebin)
   end_bin = max_val + \
         (timebin - max_val % timebin) if max_val % timebin != 0 else max_val
   bin_edges = np.arange(start_bin, end_bin + timebin, timebin)
   bin_start_time_list = bin_edges[:-1]
   bin_counts, _ = np.histogram(time_dist_df[timestamp_column], bins=bin_edges)

   preport.add_feature(test_result, "time_bin", timebin)
   preport.add_feature(test_result, "bin_counts", list(bin_counts))
   preport.add_feature(test_result, "bin_edges", list(bin_edges))

   if len(bin_counts) < 3:
      tlib.vprint(verb,
          f"profile_time_dist: Not enough data for time distribution anomaly analysis.", 1)
      tlib.vprint(verb, f"{stage} time_dist: outlier_score = 0.0", 1)
      test_result["status"] = "skipped"
      preport.add_metric(test_result, "anomaly_score", outlier_score)
      preport.add_warning(test_result, "Not enough time bins for anomaly analysis.")
      return test_result

   outlier_score, small_cluster, small_centroid, large_centroid, labels = \
                         tlib.clustering_outlier_score(bin_counts.tolist())
   preport.add_metric(test_result, "anomaly_score", outlier_score)
   preport.add_feature(test_result, "clustering", {
      "method": "kmeans_2",
      "outlier_cluster": small_cluster,
      "outlier_centroid": small_centroid,
      "baseline_centroid": large_centroid
   })

   if len(small_cluster) == 0:
      tlib.vprint(verb, f"{stage} time_dist: No clustering found", 1)
      tlib.vprint(verb, f"{stage} time_dist: outlier_score = 0.0", 1)
      test_result["status"] = "skipped"
      preport.add_warning(test_result, "No time density clustering found.")
      return test_result

   flood_time_limits = []
   flood_time_dates = []
   if outlier_score > config["profile"]["td_anom_cutoff_score"]:
      mask = labels == labels[0]
      bin_start_time_list_1 = bin_start_time_list[mask]
      bin_start_time_list_2 = bin_start_time_list[~mask]
      if len(bin_start_time_list_1) > len(bin_start_time_list_2):
         bin_start_time_short = bin_start_time_list_2
      else:
         bin_start_time_short = bin_start_time_list_1
      bin_end_time_short = bin_start_time_short + timebin
      flood_times = np.sort(np.column_stack(
                           (bin_start_time_short, bin_end_time_short)).flatten())
      equal_mask = np.diff(flood_times) == 0
      remove_mask = np.hstack(([False], equal_mask)) | np.hstack((equal_mask, [False]))
      flood_time_limits = flood_times[~remove_mask]
      flood_time_dates = tlib.epoch_to_datetime(flood_time_limits)
      tlib.vprint(verb, f"profile_time_dist: Flood time limits:", 1)
      tlib.vprint(verb, f"{list(flood_time_limits)}", 1)
      tlib.vprint(verb, f"profile_time_dist: Flood time limit dates:", 1)
      tlib.vprint(verb, f"{flood_time_dates}", 1)

      for i in range(0, len(flood_time_limits), 2):
         if i + 1 >= len(flood_time_limits):
            break
         start_time = flood_time_limits[i]
         end_time = flood_time_limits[i + 1]
         index_list = df[
            (df[timestamp_column] >= start_time) &
            (df[timestamp_column] < end_time)
         ][profile_context["idx_column"]].tolist()
         preport.add_suspicious_unit(
            test_result,
            "time_window",
            suspicion_measure={
               "metric": "event_count",
               "value": len(index_list)
            },
            start=start_time,
            end=end_time,
            index_list=index_list
         )

   sns.kdeplot(df[timestamp_column].apply(tlib.epoch_to_datetime).iloc[1:-1],
               bw_adjust=0.5, color="black", linestyle="-", linewidth=2)

   plt.xlabel("timestamp")
   plt.ylabel(f"{stage} density")
   plt.yscale('log')
   plt.xticks(fontsize=6)
   if outlier_score > config["profile"]["td_anom_cutoff_score"]:
      plt.title((f"Time anomaly score = {outlier_score:.1f}, "
                 f"avg {small_centroid:.0f} hourly flood events "
                 f"for {len(small_cluster)} hrs"), fontsize=10)
      for pos in flood_time_dates:
         plt.axvline(x=pos, linestyle="dotted", color="black", alpha=0.7)
   else:
      plt.title(f"Time anomaly score = {outlier_score:.1f}", fontsize=10)

   plot_path = f"{output_dir}/profile_time_dist_{stage}.png"
   csv_path = f"{output_dir}/profile_time_dist_{stage}.csv"
   plt.savefig(plot_path, dpi=300, bbox_inches='tight')

   if verb > 1:
      plt.show()
   plt.close()

   tlib.r_df_to_csv(time_dist_df, csv_path)

   preport.add_table(test_result, "time_dist_df", time_dist_df)
   preport.add_artifact(test_result, "plot", "time_dist", plot_path)
   preport.add_artifact(test_result, "csv", "time_dist", csv_path)

   tlib.vprint(verb, f"{time_dist_df}", 3)
   return test_result
