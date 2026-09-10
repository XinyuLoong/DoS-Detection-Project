
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
      Normalized time: tau_cr = (t_cr - t0_cv) / (tNcv_cv - t0_cv)
      Perception weights: w_cr = w0_cv N_cv ** (-0.5 tau_cr (1 - tau_cr)**alpha)
         where: w0_cv = N_cv / sum(N_cv ** (-0.5 tau_cr (1 - tau_cr)**alpha)
      Event information: i_r = sum(w_cr i_cr)
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

   # number of events
   N = float(len(df))
   mlib.vprint(mlib.m_config["cli"]["trim_verb"],
          f"Ideal Perception information: dataset has {int(N)} events", 1)

   # other general parameters
   timestamp_column = mlib.m_config['cli']['timestamp_column']
   alpha = mlib.m_config['model']['alpha']
   if alpha < 0:
      # bad attention factor
      print(f"Bad value {alpha} < 0 for the attention factor. Exiting",
            file=sys.stderr)
      sys.exit(1)
   
   # build and reorder info_df
   info_df = df.copy()
   info_df = info_df.sort_values(timestamp_column, ascending=True).reset_index(drop=True).copy()

   # count appearances of each value in the entire dataframe (T_v,cr);
   #    build a (value → global_count) mapping
   global_counts = (pd.Series(info_df[mlib.event_column_list].values.ravel())
          .value_counts()
   )
   # and get each column’s counts array by reindexing 
   col_arrays = {}
   for c in mlib.event_column_list:
      vc = info_df[c].value_counts()
      arr = vc.reindex(info_df[c].values).fillna(0).astype(int).values
      col_arrays[c] = dict(
          col_count = arr,
          global_count = global_counts.reindex(info_df[c].values).fillna(0).astype(int).values
      )

   # compute the weighted Shannon info per entry, per column
   entry_info = np.zeros((len(info_df), len(mlib.event_column_list)))
   for j,c in enumerate(mlib.event_column_list):
      N_cv   = col_arrays[c]['col_count']
      T_vcr  = col_arrays[c]['global_count']
      entry_info[:,j] = (2 - (N_cv / T_vcr)) * np.log(N / N_cv)

   # compute perception weights
   M = len(info_df); K = len(mlib.event_column_list)
   perc_weights = np.zeros((M, K), dtype=float)
   t_vals = info_df[timestamp_column].values.astype(float)

   for j, c in enumerate(mlib.event_column_list):
      # group size per row
      sz = info_df.groupby(c)[c].transform('size').astype(float)

      # per‐group min/max timestamps
      t_min = info_df.groupby(c)[timestamp_column].transform('min').astype(float)
      t_max = info_df.groupby(c)[timestamp_column].transform('max').astype(float)
      span  = t_max - t_min

      # normalized time tau, avoiding div0
      tau = np.zeros(M, dtype=float)
      mask = span > 0
      tau[mask] = (t_vals[mask] - t_min[mask]) / span[mask]

      # numerator = sz**(-0.5 * tau * (1 - tau)**alpha)
      m_exp     = -0.5 * tau * (1 - tau)**alpha
      numerator = sz.values ** m_exp

      # denom = sum of numerator within each group
      num_s = pd.Series(numerator, index=info_df.index)
      denom_s = num_s.groupby(info_df[c]).transform('sum')

      # final weights
      w = num_s * (sz / denom_s)

      perc_weights[:, j] = w.values

   # multiply entry_info × perc_weights, sum across mlib.event_column_list
   info_df['EventInfo'] = np.sum(entry_info * perc_weights, axis=1)

   return float(info_df['EventInfo'].sum()), info_df
   

##############################################################################

