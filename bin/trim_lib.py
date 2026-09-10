
##########################################################
# print_nested_dict(dictionary, indent=0): print nested dictionary
# vprint(verb, aaa, level): verbose print
# epoch_to_datetime(epoch_time): timestamp epoch to real date
# find_index_diff(initial_df, trimmed_df): index difference of two dataframes
# flood_event_stats(df, event_columns, count_threshold): statistics on events
# clustering_outlier_score(data_list): clustering-based outlier score
# r_read_csv(csv_file): robust read from csv file
# r_df_to_csv(df, csv_file): robust write dataframe to csv file
# 
##########################################################

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import inspect
import os
import sys

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

# global variables
trim_config = {}
run_output_abs_path = ''
event_column_list = []
db_mod_abs_path = ''
model_mod_abs_path = ''

import trim_config as tc
####################################################################
# print nested dictionary
def print_nested_dict(dictionary, indent=0):
    for key, value in dictionary.items():
        if isinstance(value, dict):
            print("  " * indent + f"{key}:")
            print_nested_dict(value, indent + 1)
        else:
            print("  " * indent + f"{key}: {value}")


###################################################################
# verbose print
def vprint(verb, aaa, level):
   """Verbose levels:
   quiet   -> verb <= 0  -> default
   summary -> verb = 1   -> one liners
   live    -> verb = 2   -> 1 + plots
   debug   -> verb >= 3  -> everything
   """
   #print(f"type of aaa is {type(aaa)}")
   if verb >= level: 
      if type(aaa) is dict:
         print_nested_dict(aaa, 2)   
      else:
         print(aaa)

###################################################################
# timestamp epoch to real date
def epoch_to_datetime(epoch_time):
   """Transforms epoch to real time"""
   global trim_config

   return pd.to_datetime(epoch_time, unit=trim_config["var"]['time_unit'])
   
###################################################################
# find the index difference between the index column of two dataframes
#  --- second df index must be a subset of the first df index  
def find_index_diff(initial_df, trimmed_df):
   
   caller_frame = inspect.stack()[1]  # Get the caller's frame
   # Caller's function name: caller_frame.function
   
   # Convert index columns to sets
   set_A = set(initial_df[trim_config["var"]['index_column']])
   set_B = set(trimmed_df[trim_config["var"]['index_column']])

   # Compute differences and intersection
   only_in_A = set_A - set_B  # In A but not in B
   only_in_B = set_B - set_A  # In B but not in A
   in_both = set_A & set_B    # In both A and B
   
   if only_in_B:
      print(f"{caller_frame.function}: find_index_diff: ", file=sys.stderr)
      print(f"      df2 has rows which are not in df1. Exiting", file=sys.stderr)
      sys.exit(1)
   
   return only_in_A, in_both

###################################################################
# statistics on events: 
def flood_event_stats(df, event_columns, count_threshold):
    """ Group columns by event columns, 
    introduces new columns containing statistics:
    FloodScore - Flooding score = Occurrences / StdDevTimestamp
    Occurrences - count of event appearance
    AverageTimestamp - average of the timestamps
    StdDevTimestamp - standard deviation or timestamps
    FirstIndex index of fisrt event appearance
    """
    event_stats = (df
        .groupby(event_columns)
        .agg(
            Occurrences=(trim_config["var"]["index_column"], 'count'),
            AverageTimestamp=(trim_config["cli"]["timestamp_column"], 'mean'),
            StdDevTimestamp=(trim_config["cli"]["timestamp_column"], 'std'),
            FirstIndex=(trim_config["var"]["index_column"], 'first')
        )
        # keep only events appearing more than count_threshold times
        .query('Occurrences > ' + str(count_threshold))
        # add the ratio column (coefficient of variation)
        .assign(FloodScore=lambda x: (x['Occurrences'] / x['StdDevTimestamp'])
                                      .where(x['Occurrences'] > 2, 0))
        # reset index to make event columns regular columns again
        .reset_index()
    )

    # Reorder columns to match desired output
    cols = ['FloodScore', 'Occurrences', 'AverageTimestamp', 'StdDevTimestamp', 'FirstIndex'] + event_columns
    return event_stats[cols]

###################################################################
# clustering-based outlier score

def clustering_outlier_score(data_list):
   """Calculate an outlier score for a list of numbers (data) assumed
   to contain a few components which are much larger than the rest.
   
   Output:
   outlier_score   = | large_centroid-small_centroid | / stderr(data) *
                     (1 - len(small_cluster) / len(large_cluster) 
   small_cluster   - sublist of data containing outliers  
   small_centroid  - mean(small_cluster)
   large_cluster   - sublist of data containing normal values
   large_centroid  - mean(large_cluster)
   labels          - mask of the same length with data, masking the split
   """

   caller_frame = inspect.stack()[1]  # Get the caller's frame
   # Caller's function name: caller_frame.function
    
   # data as numpy array
   data = np.array(data_list).reshape(-1, 1)  # Reshape for clustering

   # test if there are at least two different values
   if np.unique(data, axis=0).shape[0] < 2:
      return 0., list(), 0., 0., list()

   # Apply K-Means with 2 clusters
   kmeans = KMeans(n_clusters=2, n_init='auto', random_state=42)
   labels = kmeans.fit_predict(data)
   #centroids = kmeans.cluster_centers_.flatten()

   # Identify the smallest cluster (potential outlier group)
   unique_labels, cluster_sizes = np.unique(labels, return_counts=True)
   smallest_cluster_label = unique_labels[np.argmin(cluster_sizes)]

   small_cluster = data[labels == smallest_cluster_label]
   large_cluster = data[labels != smallest_cluster_label]
   if len(small_cluster) == 0 or len(large_cluster) == 0:
      return 0., list(), 0., 0., list()
   #vprint(trim_config["cli"]["trim_verb"], 
   #       f"{caller_frame.function}: labels of type {type(labels)}", 1)
   #vprint(trim_config["cli"]["trim_verb"], 
   #       f"{labels.tolist()}", 3)

   # Compute centroid separation score
   large_centroid = np.mean(large_cluster)
   small_centroid = np.mean(small_cluster)
   separation_score = abs(large_centroid - small_centroid) / np.std(data)
   #separation_score = abs(large_centroid - small_centroid) / np.std(large_cluster)
   vprint(trim_config["cli"]["trim_verb"], 
          f"{caller_frame.function}: separation_score = {separation_score}", 1)

   # Compute the imbalance score (smaller cluster size / larger cluster size)
   imbalance_ratio = len(small_cluster) / len(large_cluster)
   vprint(trim_config["cli"]["trim_verb"], 
          f"{caller_frame.function}: imbalance_ratio = {imbalance_ratio}", 1)

   # Compute final outlier score
   outlier_score = separation_score * (1 - imbalance_ratio)
   vprint(trim_config["cli"]["trim_verb"], 
          f"{caller_frame.function}: outlier_score = {outlier_score}", 1)

   vprint(trim_config["cli"]["trim_verb"], 
        f"{caller_frame.function}: Small cluster of lengts {len(small_cluster)}:", 1)
   vprint(trim_config["cli"]["trim_verb"], 
        f"{small_cluster.flatten().tolist()}", 1)
   vprint(trim_config["cli"]["trim_verb"], 
        f"{caller_frame.function}: Large cluster of lengts {len(large_cluster)}:", 1)
   vprint(trim_config["cli"]["trim_verb"], f"{large_cluster}", 3)

   return outlier_score, small_cluster.flatten().tolist(), small_centroid, \
          large_centroid, labels

###################################################################
# robust read from csv file
def r_read_csv(csv_file):
   caller_frame = inspect.stack()[1]  # Get the caller's frame
   # Caller's function name: caller_frame.function
   try:
      # Read the CSV file into a pandas DataFrame
      df = pd.read_csv(csv_file)
   except FileNotFoundError:
      print(f"Error from {caller_frame.function}: File '{csv_file}' not found.", 
            file=sys.stderr)
      sys.exit(1)
   except pd.errors.ParserError:
      print((f"Error from {caller_frame.function}: Could not parse CSV file "
             f"'{csv_file}'. Check file format."), file=sys.stderr)
      sys.exit(1)
   except Exception as e:
      print(f"An unexpected error occurred from {caller_frame.function}: {e}", 
            file=sys.stderr)
      sys.exit(1)
   return df

###################################################################
# robust write dataframe to csv file
def r_df_to_csv(df, csv_file):

   caller_frame = inspect.stack()[1]  # Get the caller's frame
   # Caller's function name: caller_frame.function

   try:
      # create directory if it doesn't exist
      os.makedirs(os.path.dirname(csv_file), exist_ok=True)
   except OSError as e:
      print((f"Error from {caller_frame.function}: Could not create the directory "
             f"for {csv_file}. Exiting."), file=sys.stderr)
      sys.exit(1)

   try:
      df.to_csv(csv_file, index=False)
   except OSError as e:
      print(f"Error from {caller_frame.function}: Could not write to {csv_file}: {e}",
            file=sys.stderr)
      sys.exit(1)
   except IOError as e:
      print((f"Error from {caller_frame.function}: An I/O error occurred "
             f"while writing to {csv_file}: {e}"), file=sys.stderr)
      sys.exit(1)
   except Exception as e:
      print(f"An unexpected write error occurred from {caller_frame.function}: {e}",
            file=sys.stderr)
      sys.exit(1)

###################################################################
#  










