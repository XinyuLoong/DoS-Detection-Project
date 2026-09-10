
##########################################################
# print_nested_dict(dictionary, indent=0): print nested dictionary
# vprint(verb, aaa, level): verbose print
# epoch_to_datetime(epoch_time): timestamp epoch to real date
# find_index_diff(initial_df, trimmed_df): index difference of two dataframes
# flood_event_stats(df, event_columns, count_threshold): statistics on events
# clustering_outlier_score(data_list): clustering-based outlier score
# reorder_delta0(w_list, ns): return the last ns rows
# reorder_delta1(w_list, ns): return the top ns rows
# reorder_astride(w_list, ns): reorder list by adaptive stride
# reorder_uniform(w_list, ns): reorder list randomly 
# reorder_normal(w_list, ns, nmean=0.5, nstd=6): reorder list with normal distribution
# find_dup_rows(df, columns): duplicate rows by column list, except one occurrence
# group_stats(group): statistics for a group of identical events for plot_info_density
# plot_info_density(df, stage): save/plot event information density for stage
# plot_info_evol(df): save/plot total information evolution
# r_read_csv(csv_file): robust read from csv file
# r_df_to_csv(df, csv_file): robust write dataframe to csv file
# find_power_function_b(x_values, y_values): find what power function fits the points
# n_trimmed_order(df): order of computation by the number of trimmed rows
#
##########################################################

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from scipy.stats import norm
import seaborn as sns
import matplotlib.pyplot as plt
import math
import random
import inspect
import os
import sys
import yaml

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

# global variables
m_config = {}
run_output_abs_path = ''
event_column_list = []

import m_config as mc
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
   global m_config

   return pd.to_datetime(epoch_time, unit=m_config["var"]['time_unit'])
   
###################################################################
# find the index difference between the index column of two dataframes
#  --- second df index must be a subset of the first df index  
def find_index_diff(initial_df, trimmed_df):
   
   caller_frame = inspect.stack()[1]  # Get the caller's frame
   # Caller's function name: caller_frame.function
   
   # Convert index columns to sets
   set_A = set(initial_df[m_config["var"]['index_column']])
   set_B = set(trimmed_df[m_config["var"]['index_column']])

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
    Occurrences - count of event occurrence
    AverageTimestamp - average of the timestamps
    StdDevTimestamp - standard deviation or timestamps
    FirstIndex index of fisrt event occurrence
    """
    event_stats = (df
        .groupby(event_columns)
        .agg(
            Occurrences=('i_Dx', 'count'),
            AverageTimestamp=('updated', 'mean'),
            StdDevTimestamp=('updated', 'std'),
            FirstIndex=('i_Dx', 'first')
        )
        # Filter to keep only events appearing more than 10 times
        .query('Occurrences > ' + str(count_threshold))
        # Add the ratio column (coefficient of variation)
        .assign(FloodScore=lambda x: (x['Occurrences'] / x['StdDevTimestamp'])
                                      .where(x['Occurrences'] > 2, 0))
        # Reset index to make event columns regular columns again
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

   # Apply K-Means with 2 clusters
   kmeans = KMeans(n_clusters=2, n_init='auto', random_state=42)
   labels = kmeans.fit_predict(data)
   #centroids = kmeans.cluster_centers_.flatten()

   # Identify the smallest cluster (potential outlier group)
   unique_labels, cluster_sizes = np.unique(labels, return_counts=True)
   smallest_cluster_label = unique_labels[np.argmin(cluster_sizes)]

   small_cluster = data[labels == smallest_cluster_label]
   large_cluster = data[labels != smallest_cluster_label]
   #vprint(m_config["cli"]["trim_verb"], 
   #       f"{caller_frame.function}: labels of type {type(labels)}", 1)
   #vprint(m_config["cli"]["trim_verb"], 
   #       f"{labels.tolist()}", 3)

   # Compute centroid separation score
   large_centroid = np.mean(large_cluster)
   small_centroid = np.mean(small_cluster)
   separation_score = abs(large_centroid - small_centroid) / np.std(data)
   #separation_score = abs(large_centroid - small_centroid) / np.std(large_cluster)
   vprint(m_config["cli"]["trim_verb"], 
          f"{caller_frame.function}: separation_score = {separation_score}", 1)

   # Compute the imbalance score (smaller cluster size / larger cluster size)
   imbalance_ratio = len(small_cluster) / len(large_cluster)
   vprint(m_config["cli"]["trim_verb"], 
          f"{caller_frame.function}: imbalance_ratio = {imbalance_ratio}", 1)

   # Compute final outlier score
   outlier_score = separation_score * (1 - imbalance_ratio)
   vprint(m_config["cli"]["trim_verb"], 
          f"{caller_frame.function}: outlier_score = {outlier_score}", 1)

   vprint(m_config["cli"]["trim_verb"], 
        f"{caller_frame.function}: Small cluster of lengts {len(small_cluster)}:", 1)
   vprint(m_config["cli"]["trim_verb"], 
        f"{small_cluster.flatten().tolist()}", 1)
   vprint(m_config["cli"]["trim_verb"], 
        f"{caller_frame.function}: Large cluster of lengts {len(large_cluster)}:", 1)
   vprint(m_config["cli"]["trim_verb"], f"{large_cluster}", 3)

   return outlier_score, small_cluster.flatten().tolist(), small_centroid, \
          large_centroid, labels


####################################
# return the last rows
def reorder_delta0(w_list, ns):
   """
      Return ns elements starting from the bottom of the list (lower timestamps).
   """
   if ns > len(w_list):
      # mission impossible
      print((f"Model: trim_stat: delta0: "
             f"Not enough elements {len(w_list)} in the list, to pick {ns}"), 
                   file=sys.stderr)
      sys.exit(1)
   elif ns == len(w_list):
      return w_list
   
   return w_list[-ns:]
   
####################################
# return the top rows
def reorder_delta1(w_list, ns):
   """
      Return ns elements starting from the top of the list (higher timestamps).
   """
   if ns > len(w_list):
      # mission impossible
      print((f"Model: trim_stat: delta1: "
             f"Not enough elements {len(w_list)} in the list, to pick {ns}"), 
                   file=sys.stderr)
      sys.exit(1)
   elif ns == len(w_list):
      return w_list

   return w_list[:ns]

####################################
# reorder list by adaptive stride
def reorder_astride(w_list, ns):
   """
      Reorder w_list by adaptive stride avoiding the start and the end of the list.
      Stride is adjusted to sqrt(len(w_list)) at every pass.
      When stride == 1, what's left from the list is appended at the end in reverse. 
      Return first ns reordered elements.
   """
   # initialize variables
   r_list = list()
   N = len(w_list)
   stride = int(math.sqrt(N))
   
   if ns < 1 or N < ns:
      # mission impossible
      print((f"Model: trim_stat: astride: "
             f"Not enough elements {N} in the list, to pick {ns}"), file=sys.stderr)
      sys.exit(1)
   elif ns == N:
      return w_list
   elif ns == 1:
      return [w_list[-stride]]

   # extract values
   old_stride = 0
   while stride > 1 and len(r_list) < ns:
      N = len(w_list)
      stride = int(math.sqrt(N))
      if stride == old_stride:
         stride += 1

      # extract values
      for i in range(N - stride, stride-1, -stride):
         r_list.append(w_list[i])
      # delete from original list
      for i in range(N - stride, stride-1, -stride):
         del w_list[i]
      
      # save the stride
      old_stride = stride

   # recover what's left in reverse
   if len(r_list) < ns:
      r_list.extend(w_list[::-1])

   return r_list[:ns]

###################################################################
# reorder list randomly with uniform distribution, returning first ns elements

def reorder_uniform(w_list, ns):
   """
      Reorder list randomly with uniform distribution.
      Return first ns elements.
   """

   N = len(w_list)
   if ns < 1 or N < ns:
      # mission impossible
      print((f"Model: trim_stat: uniform: "
             f"Not enough elements {N} in the list, to pick {ns}"), file=sys.stderr)
      sys.exit(1)
   elif ns == N:
      return w_list
   elif ns == 1:
      return [random.choice(w_list)]

   random.shuffle(w_list)

   return w_list[:ns]  

###################################################################
# reorder list with normal distribution (by score), returning first ns elements;
# distribution is centered over nmean*N with std dev N/nstd
def reorder_normal(w_list, ns):
   """
      Reorder list with normal distribution.
      Return first ns elements.
   """
   global m_config

   nmean = m_config["model"]["nmean"]
   nstd = m_config["model"]["nstd"]
   N = len(w_list)
   if ns < 1 or N < ns:
      # mission impossible
      print((f"Model: trim_stat: normal: "
             f"Not enough elements {N} in the list, to pick {ns}"), file=sys.stderr)
      sys.exit(1)
   elif ns == N:
      return w_list

   # distribution characteristics
   mean = (N - 1) * nmean  # Center around the middle of the list
   std_dev = N / nstd  # Approx. 99.7% of values fall within ±3 std deviations

   # shortcut for event trimming
   if ns == 1:
      normal_idx = int(np.random.normal(loc=mean, scale=std_dev))
      while normal_idx < 0:
         normal_idx += N
      while normal_idx >= N:
         normal_idx -= N
      return [w_list[normal_idx]]

   # index list
   idx = list(range(N))
   
   # calculate weights
   weights = norm.pdf(idx, loc=mean, scale=std_dev)
   weights_rand = [x * random.uniform(0, 1) for x in weights]

   # pair elements with weights
   pairs = list(zip(weights_rand, w_list))

   # sort the elements
   pairs.sort(key=lambda x: x[0], reverse=True)

   # get the sorted list
   result = [item[1] for item in pairs]

   return result[:ns]
   
###################################################################
# reorder list with normal distribution, returning first ns elements;
# distribution is centered over nmean*N with std dev N/nstd
def reorder_normal_elim(w_list, ns):
   """
      Reorder list with normal distribution.
      Return first ns elements.
   """
   global m_config

   nmean = m_config["model"]["nmean"]
   nstd = m_config["model"]["nstd"]
   N = len(w_list)
   if ns < 1 or N < ns:
      # mission impossible
      print((f"Model: trim_stat: normal: "
             f"Not enough elements {N} in the list, to pick {ns}"), file=sys.stderr)
      sys.exit(1)
   elif ns == N:
      return w_list

   # distribution characteristics
   mean = (N - 1) * nmean  # Center around the middle of the list
   std_dev = N / nstd  # Approx. 99.7% of values fall within ±3 std deviations

   # index list
   idx = list(range(N))
   
   # calculate weights
   weights = norm.pdf(idx, loc=mean, scale=std_dev)

   # collect results
   result = []
   #while idx:
   while ns:
      # find probabilities
      total = sum(weights)
      prob = [w / total for w in weights]
      
      # pick an element
      chosen_position = random.choices(idx, weights=prob, k=1)[0]

      # Add the element to our result
      result.append(w_list[chosen_position])
 
      # remove the element from idx and weights
      rm_pos = idx.index(chosen_position)
      idx.remove(chosen_position)
      weights = np.delete(weights, rm_pos)
      
      # one more element selected
      ns -= 1

   return result

###################################################################
# find duplicate rows specified by a column list in a dataframe
# except one occurrence;
# return the index of the rows to be deleted 
def find_dup_rows(df, columns):

   global m_config

   # indices of all duplicate rows (keeping the first occurrence)
   dup_mask = df.duplicated(subset=columns, keep='first')

   # extract the idx values from the duplicate rows
   dup_idx = df.loc[dup_mask, m_config['var']['index_column']].tolist()

   # keep only the non-duplicate rows in the dataframe
   # df = df.drop_duplicates(subset=columns_to_check, keep='first')

   return dup_idx
   
###################################################################
# save/plot event information density for stage
def group_stats(group):
   """Creates statistics for a group of identical events.   
   """

   group_sorted = group.sort_values(by=m_config['cli']['timestamp_column'], 
                            ascending=False)

   return pd.Series({
       # Count of occurrences
       'EventCount': len(group),

       # Info value for occurrence with lowest time
       'InfoLowestTime': group_sorted.iloc[-1]['EventInfo'],

       # Info value for occurrence with highest time
       'InfoHighestTime': group_sorted.iloc[0]['EventInfo'],

       # Average info value
       'InfoAverage': group['EventInfo'].mean(),

       # Max index
       'IdxMin': group_sorted.iloc[-1][m_config['var']['index_column']],

       # Min index
       'IdxMax': group_sorted.iloc[0][m_config['var']['index_column']]
    })

def plot_info_density(info_df, stage):

   global run_output_abs_path
   global m_config
   
   vprint(m_config["cli"]["trim_verb"], 
          f"plot_info_density: plotting {stage} information density", 1)

   # select only columns of interest
   df = info_df[[m_config['var']['index_column'], 'EventInfo']]
   
   # save stage event information density from info_df
   r_df_to_csv(df, f"{run_output_abs_path}/info_density_{stage}.csv")
          
   # plot stage event information density
   #sns.kdeplot(df['EventInfo'], 
   #            bw_adjust=0.5, color="black", linestyle="-", linewidth=2)
   min_info = df['EventInfo'].min() * 0.96 
   max_info = df['EventInfo'].max() * 1.04 + 1.0 / len(df)
   info_step = (max_info - min_info) / 50
   bin_edges = np.arange(min_info, max_info, info_step)
   plt.hist(df['EventInfo'], bins=bin_edges, color='grey', 
            alpha = 0.5, edgecolor = 'black')

   # Labels
   plt.xlabel("event information")
   plt.ylabel(f"{stage} count")
   #plt.xlim(0.5, 1.5)
   plt.yscale('log')
   #plt.xticks(fontsize=6)

   # save plot to file
   plt.savefig(f"{run_output_abs_path}/info_bin_count_{stage}.png", 
               dpi=300, bbox_inches='tight')

   # show plot
   if m_config["cli"]["trim_verb"] > 1:
      plt.show()
   plt.close()

   #### event count and information statistics plot
   # Group by the specified columns
   grouped = info_df.groupby(event_column_list)
    
   # save info_df to a file (debug purpose)
   if m_config["cli"]["trim_verb"] > 0 and \
         m_config["cli"]["strategy"] == 'total':
      r_df_to_csv(info_df, f"{run_output_abs_path}/info_df_{stage}.csv")
          
   # Reset index to convert group values to columns
   summary_df = grouped.apply(group_stats).reset_index()
   summary_df.drop(columns=event_column_list, inplace=True)
   summary_df = summary_df.round(4)
   summary_df['EventCount'] = summary_df['EventCount'].astype(int)
   summary_df['IdxMin'] = summary_df['IdxMin'].astype(int)
   summary_df['IdxMax'] = summary_df['IdxMax'].astype(int)
   # columns: EventCount InfoLowestTime InfoHighestTime InfoAverage IdxMin IdxMax

   # order by decreasing EventCount and add index
   summary_df.sort_values(by=['EventCount','InfoAverage'], ascending=[False, True], inplace=True)
   summary_df = summary_df.reset_index(drop=True)

   # save stage unique event count and information from summary_df
   r_df_to_csv(summary_df, f"{run_output_abs_path}/info_event_count_{stage}.csv")

   # some statistics
   count_1_events = (summary_df['EventCount'] == 1).sum()
   total_rows = len(summary_df)

   vprint(m_config["cli"]["trim_verb"], 
         (f"plot_info_density: {stage} count: {count_1_events} events "
          f"without duplicates out of {total_rows} unique events"), 1)

   # Create the primary plot with the first step plot
   fig, ax1 = plt.subplots()

   ax1.set_xlabel('unique event')
   ax1.set_ylabel(f"{stage} occurrence count", color='black')
   line1, = ax1.step(summary_df.index, summary_df['EventCount'], where='post', 
                     color='black', linestyle=':')
   ax1.set_xscale('log')
   ax1.set_yscale('log')

   # Create the secondary y-axis
   ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
   ax2.set_ylabel(f"{stage} average information", color='black') 
   line2, = ax2.step(summary_df.index, summary_df['InfoAverage'], where='post', 
                     color='black', linestyle='-')

   # Create a single figure-level legend
   fig.legend(handles=[line1, line2], 
              labels=['occurrence count', 'avg information'], 
              loc='upper center', bbox_to_anchor=(0.6, 0.96))

   fig.tight_layout()

   # save plot to file
   plt.savefig(f"{run_output_abs_path}/info_event_count_{stage}.png", 
               dpi=300, bbox_inches='tight')

   # show plot
   if m_config["cli"]["trim_verb"] > 1:
      plt.show()
   plt.close()


###################################################################
# save/plot total information evolution
def plot_info_evol(df):

   global m_config

   # information loss density column
   #mask = df['StepTrimmedEvents'] != 0
   df['TrimmedInfo'] = df['TrimmedInfo'].astype(float)
   df['StepTrimmedEvents'] = df['StepTrimmedEvents'].astype(float)
   df['InfoDensityLoss'] = 0.0
   mask = df['StepTrimmedEvents'] > 0.5
   df.loc[mask, 'InfoDensityLoss'] = df.loc[mask, 'TrimmedInfo'] / df.loc[mask, 'StepTrimmedEvents']
   df['StepTrimmedEvents'] = df['StepTrimmedEvents'].astype(int)

   # save total information evolution from info_evol_df
   r_df_to_csv(df, f"{run_output_abs_path}/info_step_trim_evol.csv")

   ###
   vprint(m_config["cli"]["trim_verb"], 
          f"plot_info_evol: plotting information evolution", 1)
   
   total_info = df['TotalInfo'].tolist()
   trimmed_events = [0]
   trimmed_events.extend(df['TotalTrimmedEvents'].iloc[:-1].tolist())
   # plot total information evolution vs remaining events
   plt.scatter(trimmed_events, total_info,
               color='black', marker='o', alpha=0.5)
   plt.xlabel("trimmed events")
   plt.ylabel(f"total information")
   #plt.xscale('log')
   #plt.yscale('log')

   # save plot
   plt.savefig(f"{run_output_abs_path}/info_step_trim_evol.png",
               dpi=300, bbox_inches='tight')
   # show plot
   if m_config["cli"]["trim_verb"] > 1:
      plt.show()
   plt.close()
   
   ###
   vprint(m_config["cli"]["trim_verb"], 
          f"plot_info_evol: plotting information density loss", 1)

   # plot information density loss vs step
   plt.scatter(df['TotalTrimmedEvents'][:-1], df['InfoDensityLoss'][:-1], 
               color='black', marker='o', alpha=0.5)
   plt.xlabel("trimmed events")
   plt.ylabel(f"information density loss")
   #plt.xscale('log')
   #plt.yscale('log')

   # save plot
   plt.savefig(f"{run_output_abs_path}/info_density_loss_evol.png",
               dpi=300, bbox_inches='tight')
   # show plot
   if m_config["cli"]["trim_verb"] > 1:
      plt.show()
   plt.close()   
   

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
# find_power_function_b(x_values, y_values): find what power function fits the points
def find_power_function_b(x_values, y_values):
    """
    Finds the best approximation of power in y = a x^b using linear regression.
    Args:
        x_values: list or NumPy array of x values.
        y_values: list or NumPy array of y values.
    Returns: The best approximation of 'b'.
    """

    if len(x_values) != len(y_values) or len(x_values) < 3:
        print((f"x_values (len {len(x_values)}) and y_values (len {len(y_values)})"
               f" must have the same length of at leats 3. Exiting."),
              file=sys.stderr)
        sys.exit(1)

    x_log = np.log(x_values)
    y_log = np.log(y_values)

    n = len(x_values)
    sum_xy = np.sum(x_log * y_log)
    sum_x = np.sum(x_log)
    sum_y = np.sum(y_log)
    sum_x_squared = np.sum(x_log**2)

    b = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x**2)

    return b

# n_trimmed_order(df): order of computation by the number of trimmed rows
def n_trimmed_order(step_df):
   """
   Finds the order of computation by the number of trimmed rows.
   Input: info_evol_df having the columns CPUtime0, TotalTrimmedEvents
   Prints the result to the standard output.
   The first row is discarded to eliminate latency; at least 6 rows needed in total.
   """
   if len(step_df) < 6:
      vprint(m_config["cli"]["trim_verb"], (f"n_trimmed_order: "
         f"Computation order by trimmed rows: cannot be determined, not enough data."), 1)
      return

   # build lists and remove the first element to reduce latency
   cpu_time = step_df['CPUtime0'].tolist()
   del cpu_time[0]
   trimmed_rows = step_df['TotalTrimmedEvents'].iloc[:-1].tolist()
   steps = step_df['Step'].iloc[:-1].tolist()

   # calculate CPU times
   initial_cpu_time = cpu_time.pop(0)
   cpu_time = [tm - initial_cpu_time for tm in cpu_time]

   # calculate trimmed events
   initial_trimmed_rows = trimmed_rows.pop(0)
   trimmed_rows = [tr - initial_trimmed_rows for tr in trimmed_rows]

   order_trimmed = find_power_function_b(trimmed_rows, cpu_time)
   vprint(m_config["cli"]["trim_verb"], 
          f"Computation order by trimmed rows: n ** {order_trimmed}", 1)
   
   # if steps don't fit trimmed rows
   if steps[-1] != trimmed_rows[-1]:
      # calculate steps
      initial_step = steps.pop(0)
      steps = [st - initial_step for st in steps]
      
      order_steps = find_power_function_b(steps, cpu_time)
      vprint(m_config["cli"]["trim_verb"], 
             f"Computation order by steps: n ** {order_steps}", 1)

###################################################################
#   
if __name__ == "__main__":

   with open("etc/m_config.yaml", "r") as file:
         m_config = yaml.safe_load(file)
   
   initial_list = list(range(20))

   reorder_proc = globals()[f'reorder_{m_config["model"]["proc"]}']
   r_list = reorder_proc(initial_list, 20)


   #r_list = reorder_astride(initial_list, 12)
   #r_list = reorder_normal(initial_list, 20)
   #r_list = reorder_uniform(initial_list, 10)
   #r_list = reorder_delta0(initial_list, 5)
   #r_list = reorder_delta1(initial_list, 12)
   print(r_list)
   print(f"of length {len(r_list)}")
   
