
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
   
   # pull config out once
   event_cols = mlib.event_column_list

   # number of events
   N    = len(df)
   logN = np.log(N)
   mlib.vprint(mlib.m_config["cli"]["trim_verb"],
          f"Class Statistical information: dataset has {int(N)} events", 1)

    
   # per-column counts (N_cv) via groupby.transform
   counts_dict = {
       c: df.groupby(c)[c].transform('size')
       for c in event_cols
   }
   counts_df = pd.DataFrame(counts_dict, index=df.index)
    
   # global counts (T_vcr) once, then map per column via a vectorized lookup
   global_counts = (
       pd.Series(df[event_cols].values.ravel())
                .value_counts()
   )
   global_dict = global_counts.to_dict()
   global_df = pd.DataFrame({
      c: df[c].map(global_dict)
      for c in event_cols
   }, index=df.index)
    
   # weighted Shannon info matrix
   info_matrix = (2 - counts_df / global_df) * (logN - np.log(counts_df))
    
   # sum across the event columns to get one EventInfo per row
   info_df = df.copy()
   info_df['EventInfo'] = info_matrix.sum(axis=1)
    
   # total information
   total_info = info_df['EventInfo'].sum()
    
   return total_info, info_df

##############################################################################

