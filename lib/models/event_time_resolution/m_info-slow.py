
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from scipy.stats import norm
import math
import random
import inspect
import os
import sys

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import m_lib as mlib

####################################################################

def model_info(df):
   """Calculate information according to the model.
      Entry information: i_cr = (2 - N_cv / T_vcr) * ln(N / N_cv)
      Event information: i_r = sum(i_cr)
      Total information: i = sum(i_r)

      info_df = df + EventInfo column
      Return dataframe containing the information of each event i_r 
      and the total information i.
   """
   
   # test if there is no EventInfo column in the dataset
   if 'EventInfo' in mlib.event_column_list:
      # workaround TBD
      print(f"EventInfo column exists already. Exiting", file=sys.stderr)
      sys.exit(1)

   # general parameters
   timestamp_column = mlib.m_config['cli']['timestamp_column']
   index_column = mlib.m_config['var']['index_column']
   alpha = mlib.m_config['model']['alpha']
   c_alpha = 2. - alpha
   if alpha < 0. or alpha > 2.0:
      # bad attention factor
      print(f"Bad value 0 <= {alpha} <= 2 for the attention factor. Exiting",
            file=sys.stderr)
      sys.exit(1)
   
   # number of events
   N = len(df)
   mlib.vprint(mlib.m_config["cli"]["trim_verb"],
          f"Event Time Resolution information: dataset has {N} events", 1)

   # initialize total information
   total_info = N * 1.0

   # build and reorder info_df
   info_df = df.copy()
   info_df.sort_values(by=timestamp_column, ascending=True, inplace=True)
   
   # list of repeating events indexes
   index_groups = [list(group[index_column]) \
                     for _, group in info_df.groupby(mlib.event_column_list)]
   
   info_df['EventInfo'] = 1.0
   data_time_span =  info_df[timestamp_column].iloc[-1] - info_df[timestamp_column].iloc[0]

   for occ_list in index_groups:
      # number of occurrences N_v
      occ_nr = len(occ_list)
      if occ_nr > 1:
         # build timestamp list
         time_list = info_df[info_df[index_column]\
                     .isin(occ_list)][timestamp_column].tolist()

         # print(f"Index group with {occ_nr} entries")
         # index_group_df = info_df[info_df[index_column].isin(occ_list)][[index_column, timestamp_column]]
         # print(index_group_df)
         # print(occ_list)
         # print(time_list)

         # check for ascending timestamp list
         #if not all(earlier <= later for earlier, later in zip(time_list, time_list[1:])):
         #   print(f"Timestamps in index group are not in ascending order. Exiting.",
         #         file=sys.stderr)
         #   print(time_list, file=sys.stderr)
         #   sys.exit(1)

         if time_list[-1] == time_list[0]:
            # if all rows identical         
            # concentrate all the info in one occurrence
            info_df.loc[info_df[index_column].isin(occ_list[1:]), 'EventInfo'] = 0.0
            info_df.loc[info_df[index_column] == occ_list[0], 'EventInfo'] = 1. * occ_nr
         
         else:
            # if not all rows are identical         
            time_list = [time_list[-1] - data_time_span] + time_list + \
                        [time_list[0] + data_time_span]
            time_arr = np.array(time_list) * occ_nr / 2.0 / data_time_span

            # calculate event information
            event_info_arr = c_alpha * (time_arr[1:-1] - time_arr[:-2]) + \
                             alpha * (time_arr[2:] - time_arr[1:-1])
            
            # calculate the unique event contribution to the total information
            unique_event_info = np.sqrt(np.sum(np.square(event_info_arr)))
            total_info = total_info - occ_nr + unique_event_info

            # check the correspondence between timestamp and index
            # print("====")
            # print(occ_list)
            # print(time_list[1:-1])
            #matches = []
            #for x, y in zip(occ_list, time_list[1:-1]):
            #   # Use boolean indexing to see if there is a row with col1==x AND col2==y
            #   exists = not info_df[(info_df[index_column] == x) & (info_df[timestamp_column] == y)].empty
            #   matches.append(exists)
            #if not all(matches):
            #   print(f"Timestamps and indexes in index group are not aligned. Exiting.",
            #      file=sys.stderr)
            #   print(matches, file=sys.stderr)
            #   sys.exit(1)

            # copy event information to info_df
            info_mapping = dict(zip(occ_list, event_info_arr))
            mask = info_df[index_column].isin(occ_list)
            info_df.loc[mask, 'EventInfo'] = info_df.loc[mask, index_column].map(info_mapping)

   return total_info, info_df

##############################################################################

