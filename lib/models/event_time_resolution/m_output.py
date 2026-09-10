
import pandas as pd
import numpy as np
import datetime
import argparse
import os
import sys

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import m_lib as mlib
import m_config as mc

def output_logistics(tm_config):
   """Prepares directory for the output: 
      current path + tm_config["filesystem"]["rel_output_path"] + 
      + file name from tm_config["cli"]["input_dataset"] + now timestamp +
      + tm_config["cli"]['strategy_totrim'] 
      = run_output_abs_path --> global var in mlib
      
      information needed:
      tm_config["cli"]["output_dest"] - python script to write to a database
      tm_config["cli"]["input_dataset"] - can be:
              * a csv file name which should exist in the input dir
              * a csv file name including the absolute path, 
                        or a path relative to the input dir
   """
   global TPATH
   
   mlib.vprint(tm_config["cli"]["trim_verb"], "== Output logistics:", 1)
   
   # output relative path from config
   output_rel_path = tm_config["filesystem"]["rel_output_path"]
   output_path = os.path.abspath(os.path.join(TPATH, output_rel_path))
   
   # check if the output directory exists
   if not os.path.exists(output_path):
      try:
         os.makedirs(output_path)
         mlib.vprint(tm_config["cli"]["trim_verb"], 
                     f"Directory '{output_path}' created.", 1)
      except OSError as e:
         print(f"Error: Could not create directory '{output_path}': {e}", 
               file=sys.stderr)
         sys.exit(1)  # Exit with a non-zero exit code (indicating an error)
   
   # get file part of the input command line argument
   in_path, run_input_file = os.path.split(tm_config["cli"]["input_dataset"])
   run_output_dirname, in_ext = os.path.splitext(run_input_file)
   now = datetime.datetime.now() 
   run_output_dir = run_output_dirname + "_" + tm_config["app"]["model_name"] \
                    + "_" + now.strftime("%y-%m-%d-%H-%M") + "_" + \
                    tm_config["cli"]["strategy_totrim"] + "_" + \
                    tm_config["model"]["proc"]
   mlib.vprint(tm_config["cli"]["trim_verb"], 
               f"Output directory: {run_output_dir}", 1)
      
   # create the output directory if it doesn't exist
   mlib.run_output_abs_path = os.path.join(output_path, run_output_dir)
   if not os.path.exists(mlib.run_output_abs_path):
      try:
         os.makedirs(mlib.run_output_abs_path)
         mlib.vprint(tm_config["cli"]["trim_verb"], 
                     f"Directory '{mlib.run_output_abs_path}' created.", 1)
      except OSError as e:
         print(f"Error: Could not create directory '{mlib.run_output_abs_path}': {e}", 
               file=sys.stderr)
         sys.exit(1)  # Exit with a non-zero exit code (indicating an error)
   else:
      mlib.vprint(tm_config["cli"]["trim_verb"], 
                  f"Directory '{mlib.run_output_abs_path}' already exists.", 1)
   
##############################################################################

def write_trimmed_dataset(df, rows_togo_set, tm_config):
   """Write the output dataset to a csv file;
      Input: original dataset, set of row indices to be deleted, configuration
      Write to file:
         rows are removed; trim-added index column is removed;
         csv file is written (default: run_output_abs_path/trimmed.csv) 

      information needed: 
      run_output_abs_path -> output path for profiling
      tm_config['cli']['output_dest'] - can be:
              * a csv file name which should exist in the input dir
              * a csv file name including the absolute path, 
                                or a path relative to the input dir
      tm_config["var"]["index_column"] - the trim-generated index column
   """
   global TPATH

   # general output dataset info
   rows_togo_number = len(rows_togo_set)
   mlib.vprint(tm_config["cli"]["trim_verb"], 
               f"Events to be deleted: {rows_togo_number}", 1)
   
   # check if output_dest  
   if not tm_config['cli']['output_dest']:
      # default csv output
      tm_config['cli']['output_dest'] = os.path.join(mlib.run_output_abs_path, 
                                                         "/trimmed.csv")
   
   if tm_config['cli']['output_dest'].lower().endswith('.csv'):
      # if output to a specified csv file
      out_dir = os.path.dirname(tm_config['cli']['output_dest'])
      # if output to a specified csv file
      if not out_dir:
         # if just a file name
         out_dir = mlib.run_output_abs_path
         tm_config['cli']['output_dest'] = os.path.join(out_dir, 
                  tm_config['cli']['output_dest'])
      elif not os.path.isabs(out_dir):
         # if relative path
         out_dir = os.path.join(mlib.run_output_abs_path, out_dir)
         tm_config['cli']['output_dest'] = os.path.join(mlib.run_output_abs_path,
                  tm_config['cli']['output_dest'])

      # test if the dir exists and can be written
      if not os.path.exists(out_dir):
         # create the directory if it doesn't exist
         try:
            os.makedirs(out_dir)
         except OSError as e:
            print(f"Error creating directory '{out_dir}': {e}", 
                  file=sys.stderr)
            sys.exit(1)         
      elif not os.access(out_dir, os.W_OK):
         # test if directory can be written
         print(f"No write permissions in directory '{out_dir}'.", 
               file=sys.stderr)
         sys.exit(1)

      # remove rows to go
      df = df[~df[tm_config["var"]["index_column"]].isin(rows_togo_set)]

      # remove the index column if it exists
      if tm_config["var"]["index_column"] in df:
         del df[tm_config["var"]["index_column"]]
      else:
         mlib.vprint(tm_config["cli"]["trim_verb"], (f"No trim-added "
               f"index column {tm_config['var']['index_column']} "
               f"found in trimmed_df"), 0)

      # general output dataset info
      trimmed_event_number = len(df)
      mlib.vprint(tm_config["cli"]["trim_verb"], 
                  f"Reduced event number: N={trimmed_event_number}", 1)
      # initial and final timestamp
      initial_timestamp = df[tm_config["cli"]["timestamp_column"]].min()
      final_timestamp = df[tm_config["cli"]["timestamp_column"]].max()
      mlib.vprint(tm_config["cli"]["trim_verb"], 
            (f"spawning between {initial_timestamp} and "
             f"{final_timestamp}"), 1)

      # write to csv file
      mlib.r_df_to_csv(df, tm_config['cli']['output_dest'])

   else:
      print(f"Unknown output destination specified. Exiting")
      sys.exit(1)
   
   
##############################################################################   
   
