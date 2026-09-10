
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
# check the number of rows to trim

def event_nr_check(info_df, nr):

   if nr < 1:
      print((f"strat_total: wrong number of rows to be trimmed {nr}.  "
                f"Exiting"), file=sys.stderr)
      sys.exit(1)

   if nr > len(info_df):
      print((f"strat_total: too many rows to be trimmed {nr} "
                f"out of {len(info_df)}. Exiting"), file=sys.stderr)
      sys.exit(1)

####################################################################
# total strategy

def strat_total(info_df, nr):
   """Pick nr rows to trim for the total strategy.
      Returns the number and index list of trimmed rows.
   """

   # consistency checks
   if mlib.m_config['cli']['strategy'] != 'total':
      print((f"strat_total: wrong strategy {mlib.m_config['cli']['strategy']}.  "
                f"Exiting"), file=sys.stderr)
      sys.exit(1)   
   event_nr_check(info_df, nr)
   total_max_info = mlib.m_config['total']['max_info']
      
   # sort by increasing info and decreasing timestamp
   info_df.sort_values(by=['EventInfo', mlib.m_config['cli']['timestamp_column']], 
                         ascending=[True, False], inplace=True)
   
   # find the low threshold info
   thr_info = info_df['EventInfo'].iloc[nr - 1] + 1.0 / len(info_df)
   # impose model limit
   if info_df['EventInfo'].iloc[nr - 1] > total_max_info:
      one_count = (info_df['EventInfo'] <= total_max_info).sum()
      print((f"strat_total: Only max {one_count} events can be efficiently "
             f"trimmed using the total strategy. Use the block strategy to "
             f"trim {nr} events. Exiting."), file=sys.stderr)
      sys.exit(1)

   # Separate the low info group
   df_info_low = info_df[info_df['EventInfo'] <= thr_info]

   # select the indexes to trim
   idx_list = df_info_low[mlib.m_config['var']['index_column']].tolist()
   mlib.vprint(mlib.m_config["cli"]["trim_verb"],
        f"Total Strategy: picking {nr} rows out of a {len(idx_list)} group", 1)
   reorder_proc = getattr(globals()['mlib'], 
                          f'reorder_{mlib.m_config["model"]["proc"]}')
   idx_totrim = reorder_proc(idx_list, nr)

   return nr, idx_totrim

####################################################################
# block split by slice

def block_slice(info_df):

   # trimming event pick procedure function
   reorder_proc = getattr(globals()['mlib'], 
                          f'reorder_{mlib.m_config["model"]["proc"]}')

   # splitting factor
   slice_factor = 1. + mlib.m_config['block']['tolerance']

   # find the low threshold info: max(1/N,
   #        info_df['EventInfo'].iloc[0] * mlib.m_config['block']['tolerance'])
   thr_info_min = 1.0 / len(info_df)
   thr_info = info_df['EventInfo'].iloc[0]
   if thr_info < thr_info_min:
      thr_info = thr_info_min
   else:
      thr_info *= slice_factor

   # Separate the low info group
   df_info_low = info_df[info_df['EventInfo'] <= thr_info]
   low_info_count = len(df_info_low)
   mlib.vprint(mlib.m_config["cli"]["trim_verb"],
        (f"Block Strategy slicing: Low threshold info = {thr_info} "
         f"with {low_info_count} out of {len(info_df)} events"), 1)

   # if not all events are in the low cluster
   if low_info_count < len(info_df): 

      # what is the maximum number of appearances of unique events in the low cluster
      repeat_count_low = df_info_low.groupby(mlib.event_column_list).size().min()
      mlib.vprint(mlib.m_config["cli"]["trim_verb"],
                 (f"Block Strategy slicing: Min low info event repeating "
                  f"count = {repeat_count_low}"), 1)

      # find the next threshold info
      next_thr_info = info_df['EventInfo'].iloc[low_info_count] * slice_factor

      # Separate the next info group
      df_info_next = info_df[info_df['EventInfo']
                          .between(thr_info, next_thr_info, inclusive='neither')]
      mlib.vprint(mlib.m_config["cli"]["trim_verb"],
        (f"Block Strategy slicing: Next lower threshold info = {next_thr_info} "
         f"with {len(df_info_next)} events"), 1)

      # what is the max number of appearances of unique events in the next cluster
      repeat_count_next = df_info_next.groupby(mlib.event_column_list).size().max()
      mlib.vprint(mlib.m_config["cli"]["trim_verb"],
        (f"Block Strategy slicing: Max next lower info event repeating count = "
         f"{repeat_count_next}"), 1)

      # list of repeating events indexes
      index_groups = [list(group[mlib.m_config['var']['index_column']]) \
                     for _, group in df_info_low.groupby(mlib.event_column_list)]

      # add excess appearances to idx_list
      idx_list = []
      for group in index_groups:
         # how many events to trim from the group
         if len(group) > repeat_count_next:
            excess_len_group = len(group) - repeat_count_next
         elif thr_info < mlib.m_config['block']['tolerance']:
            excess_len_group = max(1, len(group) - 2)
         else:
            excess_len_group = max(1, int((len(group) - 2) / 2))
         
         mlib.vprint(mlib.m_config["cli"]["trim_verb"],
            (f"Block Strategy slicing: Adding {excess_len_group} events for "
             f"trimming from a group of size {len(group)}"), 3)
         # get the list of events to be trimmed
         if excess_len_group > 0:
            idx_list = idx_list + reorder_proc(group, excess_len_group)

   else:
      # select the indexes to trim
      idx_list = df_info_low[mlib.m_config['var']['index_column']].tolist()

   return idx_list

####################################################################
# block split by clustering

def block_cluster(info_df):

   # trimming event pick procedure function
   reorder_proc = getattr(globals()['mlib'], 
                          f'reorder_{mlib.m_config["model"]["proc"]}')


   # clustering TBD


   return [1] 

####################################################################
# block strategy

def strat_block(info_df, nr):
   """Pick nr rows to trim for the block strategy.
      Returns the number and index list of trimmed rows.
   """

   # consistency checks
   if mlib.m_config['cli']['strategy'] != 'block':
      print((f"strat_block: wrong strategy {mlib.m_config['cli']['strategy']}.  "
                f"Exiting"), file=sys.stderr)
      sys.exit(1)   
   event_nr_check(info_df, nr)

   # sort by increasing info and decreasing timestamp
   info_df.sort_values(by=['EventInfo', mlib.m_config['cli']['timestamp_column']], 
                         ascending=[True, False], inplace=True)

   # trimming event pick procedure function
   reorder_proc = getattr(globals()['mlib'], 
                          f'reorder_{mlib.m_config["model"]["proc"]}')

   # use the configured splitting method   
   split_method = globals()[f"block_{mlib.m_config['block']['split']}"]
   
   # get the index list for the block
   idx_list = split_method(info_df)
   
   # how many events can be trimmed in this block
   nb = len(idx_list)
   
   if nb >= nr:   
      # pick only nr events, part of the block
      mlib.vprint(mlib.m_config["cli"]["trim_verb"],
           (f"Block Strategy: picking {nr} events out of a {nb} block "
           f"using the {mlib.m_config["model"]["proc"]} procedure"), 1)
      return nr, reorder_proc(idx_list, nr)

   else:
      # trim the entire block
      mlib.vprint(mlib.m_config["cli"]["trim_verb"],
           f"Block Strategy: trim the entire block of {nb} events", 1)
      return nb, idx_list
   
   
####################################################################
# event strategy

def strat_event(info_df, nr):
   """Pick nr rows to trim for the event strategy.
      Returns the number and index list of trimmed rows.
   """

   # consistency checks
   if mlib.m_config['cli']['strategy'] != 'event':
      print((f"strat_event: wrong strategy {mlib.m_config['cli']['strategy']}.  "
                f"Exiting"), file=sys.stderr)
      sys.exit(1)   
   event_nr_check(info_df, nr)

   # sort by increasing info and decreasing timestamp
   info_df.sort_values(by=['EventInfo', mlib.m_config['cli']['timestamp_column']], 
                         ascending=[True, False], inplace=True)
   
   # find the low threshold info
   thr_info = info_df['EventInfo'].iloc[0] + 1.0 / len(info_df)
   
   # Separate the low info group
   df_info_low = info_df[info_df['EventInfo'] <= thr_info]

   # select the indexes to trim
   idx_list = df_info_low[mlib.m_config['var']['index_column']].tolist()
   reorder_proc = getattr(globals()['mlib'], 
                          f'reorder_{mlib.m_config["model"]["proc"]}')
   idx_totrim = reorder_proc(idx_list, 1)

   return 1, idx_totrim

