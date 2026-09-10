
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
   # general parameters
   timestamp_column = mlib.m_config['cli']['timestamp_column']
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
   info_df = info_df.sort_values(by=timestamp_column, ascending=True).reset_index(drop=True)

   # time span
   data_time_span = info_df[timestamp_column].iat[-1] - info_df[timestamp_column].iat[0]

   # define a per‐group function
   def group_event_info(g):
      occ_nr = len(g)
      # if singleton, info = 1
      if occ_nr == 1:
         return pd.Series(1.0, index=g.index)

      times = g[timestamp_column].values
      # all identical?
      if times[-1] == times[0]:
         # first gets occ_nr, rest 0
         out = np.zeros(occ_nr)
         out[0] = float(occ_nr)
         return pd.Series(out, index=g.index)

      # build extended time array and scaled
      ext = np.empty(occ_nr + 2, dtype=float)
      ext[1:-1] = times
      ext[0]    = times[-1] - data_time_span
      ext[-1]   = times[0]  + data_time_span
      ext = ext * (occ_nr / 2.0 / data_time_span)

      # compute event_info_arr
      diffs1 = ext[1:-1] - ext[:-2]
      diffs2 = ext[2:]   - ext[1:-1]
      evinfo = c_alpha * diffs1 + alpha * diffs2

      return pd.Series(evinfo, index=g.index)


   # apply to each group
   info_series = (info_df
       .groupby(mlib.event_column_list, sort=False, group_keys=False)
       [ [timestamp_column] ]           # we only need the timestamp series
       .apply(group_event_info)
   )

   # assemble the final DataFrame column
   info_df['EventInfo'] = info_series

   # compute total_info
   #    original total = N
   #    subtract occ_nr for each group and add back the sqrt sum
   #    we can do that in a second pass or accumulate inside group_event_info
   # now adjust total info
   def group_delta(g):
      arr = info_series.loc[g.index].values
      return -len(g) + np.sqrt((arr**2).sum())

   delta = (info_df
       .groupby(mlib.event_column_list, sort=False, group_keys=False)
       .apply(group_delta)
       .sum()
   )
   total_info += delta

   return total_info, info_df

   
##############################################################################

