import os
import sys

import pandas as pd
import matplotlib.pyplot as plt


TPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../bin"))
sys.path.insert(0, TPATH)

import trim_lib as tlib
import profile_report as preport


def get_info():
   """Return metadata for the event uniqueness profile test."""

   return {
      "name": "event_uniqueness",
      "level": "l1",
      "description": "Profile event occurrence counts and find high-repeat event patterns.",
      "dependencies": [],
      "supports_iteration": True
   }


def run(profile_context, profile_report, level_name):
   """Profile event occurrence counts and find high-repeat event patterns."""

   df = profile_context["df"]
   stage = profile_context["stage"]
   event_column_list = profile_context["event_column_list"]
   output_dir = profile_context["run_output_abs_path"]
   verb = profile_context["trim_verb"]
   config = profile_context["trim_config"]

   test_result = preport.new_test_result("event_uniqueness", level_name, stage)
   tlib.vprint(verb, f"{stage} event_uniqueness:", 1)

   repetition_counts = df.groupby(event_column_list).size()
   repetition_counts_max = max(repetition_counts.tolist())
   outlier_score = 0.0
   small_cluster = []
   small_centroid = 0.0
   large_centroid = 0.0

   if repetition_counts_max > 1:
      outlier_score, small_cluster, small_centroid, large_centroid, labels = \
                  tlib.clustering_outlier_score(repetition_counts.tolist())

   preport.add_metric(test_result, "anomaly_score", outlier_score)
   preport.add_metric(test_result, "max_occurrences", repetition_counts_max)
   preport.add_metric(test_result, "unique_event_count", len(repetition_counts))
   preport.add_feature(test_result, "clustering", {
      "method": "kmeans_2",
      "outlier_cluster": small_cluster,
      "outlier_centroid": small_centroid,
      "baseline_centroid": large_centroid
   })

   if len(small_cluster) == 0:
      tlib.vprint(verb, f"{stage} event_uniqueness: No clustering found", 1)
      tlib.vprint(verb, f"{stage} event_uniqueness: outlier_score = 0.0", 1)
      test_result["status"] = "skipped"
      preport.add_warning(test_result, "No event occurrence clustering found.")
      return test_result

   event_uniqueness_df = pd.DataFrame({
        'Events': repetition_counts.value_counts().values,
        'Occurrences': repetition_counts.value_counts().index,
   }).sort_values(by='Occurrences')

   event_counts_df = repetition_counts.reset_index(name="Occurrences")
   suspicious_event_df = event_counts_df[
      event_counts_df["Occurrences"].isin(small_cluster)
   ]
   if outlier_score > config["profile"]["eu_anom_cutoff_score"]:
      for _, row in suspicious_event_df.iterrows():
         values = {col: row[col] for col in event_column_list}
         preport.add_suspicious_unit(
            test_result,
            "event",
            suspicion_measure={
               "metric": "occurrences",
               "value": float(row["Occurrences"])
            },
            values=values
         )

   plt.scatter(event_uniqueness_df['Occurrences'], event_uniqueness_df['Events'],
               color='black', marker='o', alpha=0.5)
   plt.xlabel("occurrences")
   plt.ylabel(f"{stage} events")
   plt.xscale('log')
   plt.yscale('log')
   if outlier_score > config["profile"]["eu_anom_cutoff_score"]:
      plt.title((f"Uniq anomaly score = {outlier_score:.1f}, "
                 f"{len(small_cluster)} events, "
                 f"{small_centroid:.0f} avg occurrences"), fontsize=10)
   else:
      plt.title(f"Uniq anomaly score = {outlier_score:.1f}", fontsize=10)

   plot_path = f"{output_dir}/profile_event_uniqueness_{stage}.png"
   csv_path = f"{output_dir}/profile_event_uniqueness_{stage}.csv"
   plt.savefig(plot_path, dpi=300, bbox_inches='tight')

   if verb > 1:
      plt.show()
   plt.close()

   tlib.r_df_to_csv(event_uniqueness_df, csv_path)

   preport.add_table(test_result, "event_uniqueness_df", event_uniqueness_df)
   preport.add_table(test_result, "suspicious_event_df", suspicious_event_df)
   preport.add_artifact(test_result, "plot", "event_uniqueness", plot_path)
   preport.add_artifact(test_result, "csv", "event_uniqueness", csv_path)

   tlib.vprint(verb, f"{event_uniqueness_df}", 3)
   return test_result
