
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
      Return dataframe containing the information of each event 
      and the total information.
   """
   
   # event information
   #info_df = pd.DataFrame(
   #          {mlib.m_config['var']['index_column']: 
   #                         df[mlib.m_config['var']['index_column']],
   #          'EventInfo': 1})
   info_df = df.copy()
   info_df['EventInfo'] = 1.0

   # total information
   total_info = info_df['EventInfo'].sum()
   
   return total_info, info_df
   