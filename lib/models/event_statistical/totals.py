
import psutil
import time
import pandas as pd
import numpy as np
import os
import sys
import yaml
import argparse
import datetime

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import m_lib as mlib
import m_config as mc
import m_info as minfo
import m_strat as mstrat
import m_input as minput
import m_output as moutput
import main_m_config as mmc

##############################################################################

def model_trim(df, event_column_list, timestamp_column, fake_timestamp=False,
               rows_totrim=1, save_evolution=True, strategy='total', verb=1,
               run_output_abs_path = '', idx_column='i_Dx', time_unit='s', 
               del_dup = 0):
   """Removes the oldest rows_totrim rows from the input dataframe ordered
      by descending timestamp_column values.
   """

   global TPATH

   ###############################
   # configure the model

   # set event column list
   mlib.event_column_list = event_column_list   

   # load configuration file
   mc.read_m_config(verb)
   
   # set verbosity level
   mlib.m_config["cli"] = {'trim_verb': verb}
   
   # check timestamp
   if timestamp_column:
      mlib.m_config['cli']['timestamp_column'] = timestamp_column
      mlib.m_config['cli']['fake_timestamp'] = fake_timestamp
   else:
      print(f"timestamp column undefined. Exiting", file=sys.stderr)
      sys.exit(1)

   # check output dir
   if run_output_abs_path:
      mlib.run_output_abs_path = run_output_abs_path

   # check the model name
   t_model_name = os.path.basename(os.path.dirname(__file__))
   if mlib.m_config["app"]["model_name"] != t_model_name:
      print(f"Model name {t_model_name} mismatch in config file. Exiting", 
            file=sys.stderr)
      sys.exit(1)

   # reset the trim-added index column name
   if mlib.m_config["var"]["index_column"] != idx_column:
      mlib.m_config["var"]["index_column"] = idx_column

   # reset time unit
   if mlib.m_config["var"]["time_unit"] != time_unit:
      mlib.m_config["var"]["time_unit"] = time_unit

   # check strategy
   if not strategy in mlib.m_config['trimming']['trim_strategy_list']:
      print((f"Strategy {strategy} not in the known list " 
             f"{mlib.m_config['trimming']['trim_strategy_list']}. Exiting"), 
             file=sys.stderr)
      sys.exit(1)
   else:
      mlib.m_config['cli']['strategy'] = strategy
   
   # set the rest of the options
   mlib.m_config['cli']['rows_totrim'] = rows_totrim
   mlib.m_config['cli']['save_evolution'] = save_evolution
   mlib.m_config['cli']['del_dup'] = del_dup

   mlib.vprint(mlib.m_config["cli"]["trim_verb"], 
               f"Event Statistical Model: trims by timestamp", 1)

   ############################
   # initial setup
   
   # start time
   start_time = time.process_time()
   start_time0 = start_time
   mlib.vprint(mlib.m_config["cli"]["trim_verb"], (f"Model start time: "
                  f"{start_time:.3f} sec"), 1)
   # start RSS
   process = psutil.Process(os.getpid())
   memory_info = process.memory_info()
   mlib.vprint(mlib.m_config["cli"]["trim_verb"], (f"Model start RSS: "
                  f"{memory_info.rss / (1024 ** 2):.2f} MB"), 1)

   # make sure that the order is right
   df.sort_values(by=timestamp_column, ascending=False, inplace=True)

   # total number of events
   N = len(df)

   # initialize  trimming   
   nr = rows_totrim
   trim_step = 0 
   strat_funct = getattr(globals()['mstrat'], f'strat_{strategy}')
   reorder_proc = getattr(globals()['mlib'], 
                          f'reorder_{mlib.m_config["model"]["proc"]}')
   
   # calculate initial information
   total_info, info_df = minfo.model_info(df)
   mlib.vprint(mlib.m_config["cli"]["trim_verb"], 
               f"Event Statistical Model: initial information = {total_info}", 1)
   
   # work on a copy
   #initial_info_df = info_df.copy()
   n0 = N
   nt = 0

   # initial information data
   if mlib.m_config['cli']['save_evolution']:
      mlib.vprint(mlib.m_config["cli"]["trim_verb"], 
               (f"Event Statistical Model: Saving evolution = "
               f"{mlib.m_config['cli']['save_evolution']}"), 1)
   
      # save/plot initial event information density
      mlib.plot_info_density(info_df, 'initial')
   
      # initialize information evolution
      dtypes = {
          'Step': pd.Series(dtype=int),
          'StepTrimmedEvents': pd.Series(dtype=int),
          'TotalRemainingEvents': pd.Series(dtype=int),
          'TotalRemainingEvents': pd.Series(dtype=int),
          'TotalInfo': pd.Series(dtype=float),
          'TrimmedInfo': pd.Series(dtype=float),
          'CPUtime0': pd.Series(dtype=float)
          }
      info_evol_df = pd.DataFrame(dtypes) 

      # initialize trimming evolution
      dtypes = {
          mlib.m_config['var']['index_column']: pd.Series(dtype=int),
          'EventInfo': pd.Series(dtype=float),
          'Step': pd.Series(dtype=int)
          }
      event_evol_df = pd.DataFrame(dtypes)
                                                                             
   ############################
   # duplicate rows trimming
   if mlib.m_config['cli']['del_dup'] > 0:

      # get duplicate list
      if mlib.m_config['cli']['del_dup'] == 1:
         dup_columns = event_column_list + [timestamp_column]
         dup = "row"
      else:
         dup_columns = event_column_list
         dup = "event"
      dup_idx_list = mlib.find_dup_rows(df, dup_columns)
      if nr < len(dup_idx_list):
         idx_totrim = reorder_proc(dup_idx_list, nr)
      else:
         idx_totrim = dup_idx_list
     
      # how many rows will be trimmed
      ns = len(idx_totrim)
      nt += ns
      n0 -= ns
      
      # remove ns rows
      s_mask = ~df[idx_column].isin(idx_totrim)
      df = df[s_mask]
      
      # split the information
      trimmed_event_df = info_df[[idx_column, 'EventInfo']].copy()
      s_mask = trimmed_event_df[idx_column].isin(idx_totrim)
      trimmed_event_df = trimmed_event_df[s_mask]
      trimmed_info = trimmed_event_df['EventInfo'].sum()
      trimmed_event_df['Step'] = trim_step

      mlib.vprint(mlib.m_config["cli"]["trim_verb"], (f"step {trim_step} "
                  f"clean duplicate {dup}s: initial info = {total_info} in {N} events, "
                  f"{len(dup_idx_list)} duplicate {dup}s found, "
                  f"{ns} trimmed {dup}s with info = {trimmed_info}"), 1)

      if mlib.m_config['cli']['save_evolution']:
         # store the information evolution
         new_row = {'Step': trim_step,
                    'StepTrimmedEvents': ns, 
                    'TotalTrimmedEvents': nt,
                    'TotalRemainingEvents': n0,
                    'TotalInfo': total_info,
                    'TrimmedInfo': trimmed_info,
                    'CPUtime0': start_time
                    }
         info_evol_df = pd.concat([info_evol_df, pd.DataFrame([new_row])], ignore_index=True)
         start_time = time.process_time()

         # store the event trimming evolution
         event_evol_df = pd.concat([event_evol_df, trimmed_event_df], ignore_index=True)

      # calculate information after the trimming step
      total_info, info_df = minfo.model_info(df)

      # reduce the number of rows to trim
      nr -= ns

   ############################                 
   # model trimming
   while nr:
      trim_step += 1
      initial_event_no = len(df)
            
      # how many rows and what index values to trim
      # according to strategy and procedure
      ns, idx_totrim = strat_funct(info_df, nr)
      nt += ns
      n0 -= ns

      # remove ns rows
      s_mask = ~df[idx_column].isin(idx_totrim)
      df = df[s_mask]

      # split the information
      trimmed_event_df = info_df[[idx_column, 'EventInfo']].copy()
      s_mask = trimmed_event_df[idx_column].isin(idx_totrim)
      trimmed_event_df = trimmed_event_df[s_mask]
      trimmed_info = trimmed_event_df['EventInfo'].sum()
      trimmed_event_df['Step'] = trim_step

      mlib.vprint(mlib.m_config["cli"]["trim_verb"], (f"step {trim_step}: "
                  f"initial info = {total_info} in {initial_event_no} events, "
                  f"{ns} trimmed events with info = {trimmed_info}"), 2)

      if mlib.m_config['cli']['save_evolution']:
         # store the information evolution
         new_row = {'Step': trim_step,
                    'StepTrimmedEvents': ns, 
                    'TotalTrimmedEvents': nt,
                    'TotalRemainingEvents': n0,
                    'TotalInfo': total_info,
                    'TrimmedInfo': trimmed_info,
                    'CPUtime0': start_time
                    }
         info_evol_df = pd.concat([info_evol_df, pd.DataFrame([new_row])], ignore_index=True)
         start_time = time.process_time()
      
         # store the event trimming evolution
         event_evol_df = pd.concat([event_evol_df, trimmed_event_df], ignore_index=True)
      
      # calculate information after the trimming step
      total_info, info_df = minfo.model_info(df)
      
      # reduce the number of rows to trim
      if ns <= nr:
         nr -= ns     
      else:
         print((f"model_trim for model {t_model_name} strategy {strategy} "
                f"procedure {mlib.m_config['model']['proc']} "
                f"trim more rows {ns} than requested {nr}"), file=sys.stderr)
         sys.exit(1)
         
   ###########################
   # final touchups
   mlib.vprint(mlib.m_config["cli"]["trim_verb"], 
                 f"Event Statistical Model: information after trimming = {total_info}", 1)

   if mlib.m_config['cli']['save_evolution']:
      # final status: fake row, nothing trimmed, just to store final information
      new_row = {'Step': trim_step+1, 
                 'StepTrimmedEvents': 0,
                 'TotalTrimmedEvents': nt, 
                 'TotalRemainingEvents': n0,
                 'TotalInfo': total_info,
                 'TrimmedInfo': 0,
                 'CPUtime0': start_time
                 }
      info_evol_df = pd.concat([info_evol_df, pd.DataFrame([new_row])], ignore_index=True)
   
      # save/plot trimmed event information density
      mlib.plot_info_density(info_df, 'trimmed')
   
      # save/plot total information evolution
      mlib.plot_info_evol(info_evol_df)
   
      # save the event trimming evolution dataframe
      mlib.r_df_to_csv(event_evol_df, run_output_abs_path + '/info_event_trim_evol.csv')
   
      # draw initial vs trimmed information density diagram from initial_info_df,info_df TBD

   # end time
   end_time = time.process_time()
   mlib.vprint(mlib.m_config["cli"]["trim_verb"], (f"Model end time: "
                  f"{end_time:.3f} sec"), 1)
   # spent time
   spent_time = end_time - start_time0
   mlib.vprint(mlib.m_config["cli"]["trim_verb"], (f"Model CPU computation time: "
                  f"{spent_time:.3f} sec"), 1)

   # end RSS
   memory_info = process.memory_info()
   mlib.vprint(mlib.m_config["cli"]["trim_verb"], (f"Model end RSS: "
                  f"{memory_info.rss / (1024 ** 2):.2f} MB"), 1)

   return df

##############################################################################

if __name__ == "__main__":

   # define command line arguments
   parser = argparse.ArgumentParser(description="Model config")
   parser.add_argument('-v', '--trim_verb', type=int, default=0, 
                             help='verbosity level of output')
   parser.add_argument('-i', '--input_dataset', type=str, default='', 
                             help='input data, a csv file or use db for a database table')
   parser.add_argument('-x', '--exclude_column', action='append', default=[], 
                             help='column to exclude from event definition')
   parser.add_argument('-l', '--trim_list_csv', type=str, default='info_step_trim_evol.csv',
                             help='block trim evolution file: event, block, total')
   parser.add_argument('-t', '--timestamp_column', type=str, default='',
                             help='timestamp column name')
   parser.add_argument('-e', '--save_evolution', action='store_true', 
                             help='save the information evolution and trimming history')
   parser.add_argument('-d', '--del_dup', type=int, default=0, 
                             help='delete duplicates first: 1=rows, 2=events')
   args = parser.parse_args()
   tm_config = {}
   tm_config["cli"] = vars(args)

   # get configuration and perform checks
   tm_config = mmc.read_m_config(tm_config["cli"]["trim_verb"], tm_config)

   # input
   tm_config, tm_event_column_list, original_data_df = minput.read_input_dataset(tm_config)

   # make working copy and drop excluded columns
   df = original_data_df.copy()
   if tm_config["cli"]["exclude_column"]:
      df.drop(columns=tm_config["cli"]["exclude_column"], inplace=True)

   # output logistics setup
   moutput.output_logistics(tm_config)

   # run the model      
   trimmed_df = model_trim(df, 
               tm_event_column_list,
               tm_config["cli"]['timestamp_column'], 
               fake_timestamp = False,
               rows_totrim = tm_config["cli"]['rows_totrim'],
               save_evolution = tm_config["cli"]['save_evolution'],
               strategy = tm_config["cli"]['strategy_totrim'],
               verb = tm_config["cli"]['trim_verb'],
               run_output_abs_path = mlib.run_output_abs_path, 
               idx_column = tm_config["var"]['index_column'],
               time_unit = tm_config["var"]['time_unit'],
               del_dup = tm_config["cli"]['del_dup'])

   # output
   if tm_config["cli"]["output_dest"]:
      # find the index of the rows to be deleted
      rows_togo_set, rows_tostay_set = \
                        mlib.find_index_diff(df, trimmed_df)

      # operate trimming
      moutput.write_trimmed_dataset(original_data_df, rows_togo_set, tm_config)
   
   