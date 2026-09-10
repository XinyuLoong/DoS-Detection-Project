
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
   info_df = info_df.sort_values(by=timestamp_column, ascending=True).reset_index(drop=True)

   # count appearances of each value in the entire dataframe (T_v,cr)
   global_counts = pd.Series(info_df[mlib.event_column_list].values.ravel()).value_counts()

   # create the new dataframe for weighted Shannon information
   entry_info_df = pd.DataFrame()
   entry_info_df[mlib.m_config['var']['index_column']] = info_df[mlib.m_config['var']['index_column']]

   # process each column
   for col in mlib.event_column_list:
      # count appearances of each value in this column (N_cv)
      column_counts = info_df[col].value_counts()
    
      # map c_ij and n_ij
      N_cv = info_df[col].map(column_counts)
      T_vcr = info_df[col].map(global_counts)
    
      # calculate the weighted Shannon information
      entry_info_df[col] = (2 - (N_cv / T_vcr)) * np.log(N / N_cv)

   # create the new dataframe for perception weights
   perc_w_df = pd.DataFrame()
   perc_w_df[mlib.m_config['var']['index_column']] = info_df[mlib.m_config['var']['index_column']]

   # define the perception per‐group function
   def group_entry_w(g):
      occ_nr = float(len(g))
      times = g[timestamp_column].values
      # singleton or all identical
      if times[-1] == times[0]:
         # all  1
         return pd.Series(1.0, index=g.index)

      # normalized time tau
      t_span =  float(times[-1] - times[0])
      tau = (times - times[0]) / t_span

      # calculate w0
      m_exp = -0.5 * tau * (1 - tau)**alpha
      w0 = occ_nr / np.sum(occ_nr**m_exp)

      # calculate weights
      w = w0 * occ_nr**(-0.5 * tau * (1 - tau)**alpha)

      return pd.Series(w, index=g.index)

   # process each column
   for col in mlib.event_column_list:
      w_series = (info_df
          .groupby(col, sort=False, group_keys=False)
          [ [timestamp_column] ]           # we only need the timestamp series
          .apply(group_entry_w)
      )

      # add the class weight values for the column
      perc_w_df[col] = w_series

   # add the perception weights to entry_info_df
   d1 = entry_info_df.set_index(mlib.m_config['var']['index_column'])[mlib.event_column_list]
   d2 = perc_w_df.set_index(mlib.m_config['var']['index_column'])[mlib.event_column_list]
   entry_info_df.loc[:, mlib.event_column_list] = d1.multiply(d2).reset_index(drop=True).values
   
   # calculate event info by summing the entry info values
   entry_info_df['EventInfo'] = entry_info_df[mlib.event_column_list].sum(axis=1)
   
   # add the EventInfo column to info_df
   info_df = info_df.merge(entry_info_df[[mlib.m_config['var']['index_column'], 'EventInfo']], 
                           on=mlib.m_config['var']['index_column'], how='left')
   
   # total information
   total_info = info_df['EventInfo'].sum()
   
   return total_info, info_df

##############################################################################

