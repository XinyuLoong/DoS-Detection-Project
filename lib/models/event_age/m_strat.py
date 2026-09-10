
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
      
   # sort by increasing info and decreasing timestamp
   info_df.sort_values(by=['EventInfo', mlib.m_config['cli']['timestamp_column']], 
                         ascending=[True, False], inplace=True)
   
   # find the low threshold info -- maybe use an adaptive factor or clustering
   thr_info = info_df['EventInfo'].iloc[nr - 1] + 1.0 / len(info_df)
      
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

   # trimming event pick procedure function
   reorder_proc = getattr(globals()['mlib'], 
                          f'reorder_{mlib.m_config["model"]["proc"]}')

   # sort by increasing info and decreasing timestamp
   info_df.sort_values(by=['EventInfo', mlib.m_config['cli']['timestamp_column']], 
                         ascending=[True, False], inplace=True)
   
   # find the low threshold info -- maybe use an adaptive factor or clustering
   thr_info = info_df['EventInfo'].iloc[0] * 1.01
   
   # Separate the low info group
   df_info_low = info_df[info_df['EventInfo'] <= thr_info]
   low_info_count = len(df_info_low)
   mlib.vprint(mlib.m_config["cli"]["trim_verb"],
        (f"Block Strategy: Low threshold info = {thr_info} "
         f"with {low_info_count} out of {len(info_df)} events"), 1)
   
   # if not all events are in the low cluster
   if low_info_count < len(info_df): 

      # what is the maximum number of appearances of unique events in the low cluster
      repeat_count_low = df_info_low.groupby(mlib.event_column_list).size().max()
      mlib.vprint(mlib.m_config["cli"]["trim_verb"],
         f"Block Strategy: Max low info event repeating count = {repeat_count_low}", 1)

      # find the next threshold info -- maybe use an adaptive factor or clustering
      next_thr_info = info_df['EventInfo'].iloc[low_info_count] * 1.01

      # Separate the next info group
      df_info_next = info_df[info_df['EventInfo']
                          .between(thr_info, next_thr_info, inclusive='neither')]
      mlib.vprint(mlib.m_config["cli"]["trim_verb"],
        (f"Block Strategy: Next lower threshold info = {next_thr_info} "
         f"with {len(df_info_next)} events"), 1)

   
      # what is the max number of appearances of unique events in the next cluster
      repeat_count_next = df_info_next.groupby(mlib.event_column_list).size().max()
      mlib.vprint(mlib.m_config["cli"]["trim_verb"],
        (f"Block Strategy: Max next lower info event repeating count = "
         f"{repeat_count_next}"), 1)
   
   
      # model information function consistency check
      if repeat_count_low <= repeat_count_next:
         print((f"strat_group: low information event group has {repeat_count_low} "
                f"max repeating entries;"), file=sys.stderr)
         print((f"strat_group: next information event group has {repeat_count_next} "
                f"max repeating entries;"), file=sys.stderr)
         print((f"strat_group: something must be wrong with the information function. "
                f"Exiting."), file=sys.stderr)
         sys.exit(1)
      
      # list of repeating events indexes
      index_groups = [list(group[mlib.m_config['var']['index_column']]) \
                     for _, group in df_info_low.groupby(mlib.event_column_list)]

      # add excess appearances to idx_list
      idx_list = []
      for group in index_groups:
         excess_len_group = len(group) - repeat_count_next
         mlib.vprint(mlib.m_config["cli"]["trim_verb"],
            (f"Block Strategy: Adding {excess_len_group} events for trimming "
             f"from a group of size {len(group)}"), 3)
         if excess_len_group > 0:
            idx_list = idx_list + reorder_proc(group, excess_len_group)

   else:
      # select the indexes to trim
      idx_list = df_info_low[mlib.m_config['var']['index_column']].tolist()
   
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
   
   # find the low threshold info -- maybe use an adaptive factor or clustering
   thr_info = info_df['EventInfo'].iloc[0] + 1.0 / len(info_df)
   
   # Separate the low info group
   df_info_low = info_df[info_df['EventInfo'] <= thr_info]

   # select the indexes to trim
   idx_list = df_info_low[mlib.m_config['var']['index_column']].tolist()
   reorder_proc = getattr(globals()['mlib'], 
                          f'reorder_{mlib.m_config["model"]["proc"]}')
   idx_totrim = reorder_proc(idx_list, 1)

   return 1, idx_totrim

