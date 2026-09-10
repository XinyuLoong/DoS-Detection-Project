
import pandas as pd
import numpy as np
import datetime
import argparse
import importlib
import os
import sys

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import trim_lib as tlib
import trim_config as tc

def output_logistics():
   """Prepares directory for the output: 
      current path + trim_config["filesystem"]["rel_output_path"] + 
      + file name from trim_config["cli"]["input_dataset"] + now timestamp =
      = run_output_abs_path --> global var in tlib
   """
   global TPATH
   
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], "== Output logistics:", 1)
   
   # output relative path from config
   output_rel_path = tlib.trim_config["filesystem"]["rel_output_path"]
   output_path = os.path.abspath(os.path.join(TPATH, output_rel_path))
   
   # check if the output directory exists
   if not os.path.exists(output_path):
      try:
         os.makedirs(output_path)
         tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                     f"Directory '{output_path}' created.", 1)
      except OSError as e:
         print(f"Error: Could not create directory '{output_path}': {e}", 
               file=sys.stderr)
         sys.exit(1)  # Exit with a non-zero exit code (indicating an error)
   
   # get file part of the input command line argument
   in_path, run_input_file = os.path.split(tlib.trim_config["cli"]["input_dataset"])
   run_output_dirname, in_ext = os.path.splitext(run_input_file)
   now = datetime.datetime.now() 
   run_output_dir = run_output_dirname + "_" + tlib.trim_config["cli"]["trim_model"] \
                    + "_" + now.strftime("%y-%m-%d-%H-%M") + "_" + \
                    tlib.trim_config["cli"]["strategy_totrim"] 
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
               f"Output directory: {run_output_dir}", 1)
      
   # create the output directory if it doesn't exist
   tlib.run_output_abs_path = os.path.join(output_path, run_output_dir)
   if not os.path.exists(tlib.run_output_abs_path):
      try:
         os.makedirs(tlib.run_output_abs_path)
         tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                     f"Directory '{tlib.run_output_abs_path}' created.", 1)
      except OSError as e:
         print(f"Error: Could not create directory '{tlib.run_output_abs_path}': {e}", 
               file=sys.stderr)
         sys.exit(1)  # Exit with a non-zero exit code (indicating an error)
   else:
      tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                  f"Directory '{tlib.run_output_abs_path}' already exists.", 1)
   
##############################################################################

def write_trimmed_dataset(df, rows_togo_set):
   """Write the output dataset to a csv file or to a database;
      Input: original dataset, set of row indices to be deleted
      Write to file:
         rows are removed; trim-added index column is removed;
         csv file is written relative to run_output_abs_path if no abs path is specified
      Apply to database:
         existing table is backed-up according to database module configuration;
         rows are identified by index and removed one by one

      information needed: 
      run_output_abs_path -> output path for profiling
      trim_config['cli']['output_dest'] - can be:
              * a csv file name which should exist in the input dir
              * a csv file name including the absolute path, 
                                or a path relative to the input dir
              * 'db' - use database module config to delete from db table
      trim_config["var"]["index_column"] - the trim-generated index column
   """
   global TPATH

   # general output dataset info
   rows_togo_number = len(rows_togo_set)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
               f"Events to be deleted: {rows_togo_number}", 1)
   
   # check if output_dest  
   if not tlib.trim_config['cli']['output_dest']:
      # default csv output
      #tlib.trim_config['cli']['output_dest'] = tlib.run_output_abs_path + "/trimmed.csv"
      return
   
   if tlib.trim_config['cli']['output_dest'].lower().endswith('.csv'):
      # if output to a specified csv file
      out_dir = os.path.dirname(tlib.trim_config['cli']['output_dest'])
      # get the absolute path file name
      if not out_dir:
         # if just a file name
         out_dir = tlib.run_output_abs_path
         tlib.trim_config['cli']['output_dest'] = os.path.join(out_dir,
                  tlib.trim_config['cli']['output_dest'])
      elif not os.path.isabs(out_dir):
         # if relative path
         out_dir = os.path.join(tlib.run_output_abs_path, out_dir)
         tlib.trim_config['cli']['output_dest'] = os.path.join(tlib.run_output_abs_path, 
                  tlib.trim_config['cli']['output_dest'])

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
      df = df[~df[tlib.trim_config["var"]["index_column"]].isin(rows_togo_set)]

      # remove the index column if it exists
      if tlib.trim_config["var"]["index_column"] in df:
         del df[tlib.trim_config["var"]["index_column"]]
      else:
         tlib.vprint(tlib.trim_config["cli"]["trim_verb"], (f"No trim-added "
               f"index column {tlib.trim_config['var']['index_column']} "
               f"found in trimmed_df"), 0)

      # general output dataset info
      trimmed_event_number = len(df)
      tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                  f"Reduced event number: N={trimmed_event_number}", 1)
      # initial and final timestamp
      if not tlib.trim_config["cli"]["fake_timestamp"]:
         initial_timestamp = df[tlib.trim_config["cli"]["timestamp_column"]].min()
         final_timestamp = df[tlib.trim_config["cli"]["timestamp_column"]].max()
         tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
               (f"spawning between {tlib.epoch_to_datetime(initial_timestamp)} and "
                f"{tlib.epoch_to_datetime(final_timestamp)}"), 1)

      # write to csv file
      tlib.r_df_to_csv(df, tlib.trim_config['cli']['output_dest'])

   # if database output 
   elif tlib.trim_config['cli']['output_dest'].lower() == 'db':

      # select rows to go
      df = df[df[tlib.trim_config["var"]["index_column"]].isin(rows_togo_set)]

      # remove the index column if it exists
      if tlib.trim_config["var"]["index_column"] in df:
         del df[tlib.trim_config["var"]["index_column"]]
      else:
         tlib.vprint(tlib.trim_config["cli"]["trim_verb"], (f"No trim-added "
               f"index column {tlib.trim_config['var']['index_column']} "
               f"found in trimmed_df"), 0)
      
      # general output dataset info
      event_number_totrim = len(df)
      tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                  f"Trimming {event_number_totrim} events from database", 1)

      # import the right module
      sys.path.insert(0, tlib.db_mod_abs_path)
      tdb = importlib.import_module("db_trim")
      
      # database code (backup + drop) TBD
      tdb.trim_db_table(tlib.trim_config, df)

      sys.exit(0)
   else:
      print(f"Unknown output destination specified. Exiting")
      sys.exit(1)
   
   
##############################################################################   
   
if __name__ == "__main__":
   #########################################################################
   # define command line arguments
   parser = argparse.ArgumentParser(description="Trim dataset")
   parser.add_argument('-v', '--trim_verb', type=int, 
               help='verbosity level of output', default=0)
   parser.add_argument('-i', '--input_dataset', type=str, 
               help='input data, a csv file or use db for a database table', default='')
   parser.add_argument('-o', '--output_dest', type=str, default='',
               help='output destination, a csv file or use db for a database table')
   args = parser.parse_args()
   tlib.trim_config["cli"] = vars(args)

   #########################################################################
      
   # get configuration and perform checks
   tc.read_trim_config(tlib.trim_config["cli"]["trim_verb"])
   # if no input file specified, exit
   if not tlib.trim_config["cli"]["input_dataset"]:
      sys.exit(0)

   # default relative path of csv input files
   csv_input_rel_path = tlib.trim_config["filesystem"]["rel_input_path"]

   # read a csv file
   if tlib.trim_config['cli']['input_dataset'].lower().endswith('.csv'):
      if not os.path.isabs(tlib.trim_config['cli']['input_dataset']):
         csv_file = os.path.abspath(os.path.join(TPATH, csv_input_rel_path, 
                                    tlib.trim_config['cli']['input_dataset']))
      else:
         csv_file = tlib.trim_config['cli']['input_dataset']
      if not os.path.isfile(csv_file):
         print(f"no such input file {csv_file}", file=sys.stderr)
         sys.exit(1)
      else:
         tlib.vprint(tlib.trim_config['cli']['trim_verb'], 
                     f"valid input file: {csv_file}", 1)
         input_df = tlib.r_read_csv(csv_file)
   
   # write it somewhere else without the index column
   output_logistics()
   rows_togo_set = {}
   write_trimmed_dataset(input_df, rows_togo_set)


