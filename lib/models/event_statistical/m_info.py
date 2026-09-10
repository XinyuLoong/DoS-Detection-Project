
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
      info_df = df + EventInfo column
      Return dataframe containing the information of each event 
      and the total information.
   """
   
   # test if there is no EventInfo column in the dataset
   if 'EventInfo' in mlib.event_column_list:
      # workaround TBD
      print(f"EventInfo column exists already. Exiting", file=sys.stderr)
      sys.exit(1)
   
   # number of events
   N = float(len(df))
   
   # add a column with appearance count -- name it EventInfo
   info_df = df.copy()
   info_df['EventInfo'] = df.groupby(mlib.event_column_list)\
          .transform('count')[mlib.m_config['var']['index_column']]
   
   # EventInfo should be float
   info_df['EventInfo'] = info_df['EventInfo'].astype(float)
    
   # get the Shannon information
   info_df['EventInfo'] = np.log(N / info_df['EventInfo'])
    
   # total information
   total_info = info_df['EventInfo'].sum()
   
   return total_info, info_df

   