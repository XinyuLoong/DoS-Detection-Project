
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
   
   # number of events
   N = float(len(df))
   mlib.vprint(mlib.m_config["cli"]["trim_verb"],
          f"Class Statistical information: dataset has {int(N)} events", 1)

   # count appearances of each value in the entire dataframe (T_v,cr)
   global_counts = pd.Series(df[mlib.event_column_list].values.ravel()).value_counts()

   # create the new dataframe for weighted Shannon information
   entry_info_df = pd.DataFrame()
   entry_info_df[mlib.m_config['var']['index_column']] = df[mlib.m_config['var']['index_column']]

   # process each column
   for col in mlib.event_column_list:
      # count appearances of each value in this column (N_cv)
      column_counts = df[col].value_counts()
    
      # map c_ij and n_ij
      N_cv = df[col].map(column_counts)
      T_vcr = df[col].map(global_counts)
    
      # calculate the weighted Shannon information
      entry_info_df[col] = (2 - (N_cv / T_vcr)) * np.log(N / N_cv)

   # calculate event info by summing the entry info values
   entry_info_df['EventInfo'] = entry_info_df[mlib.event_column_list].sum(axis=1)
   
   # build info_df
   info_df = df.copy()
   info_df = info_df.merge(entry_info_df[[mlib.m_config['var']['index_column'], 'EventInfo']], 
                           on=mlib.m_config['var']['index_column'], how='left')
   
   # total information
   total_info = info_df['EventInfo'].sum()
   
   return total_info, info_df

##############################################################################

