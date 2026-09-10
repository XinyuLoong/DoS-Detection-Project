
import pandas as pd
import numpy as np
import importlib
import os
import sys
import re

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import m_lib as mlib

def read_input_dataset(tm_config):
   """Read the input dataset to a dataframe:

      information needed:
      tm_config['cli']['input_dataset'] - can be:
            * a csv file name which should exist in the input dir
            * a csv file name including the absolute path, 
                                or a path relative to the input dir
      tm_config["cli"]["timestamp_column"] - the timestamp column;
            empty if no timestamp column specified
      tm_config["var"]["index_column"] - the trim-generated index column
      
      Output:
      tm_config - modified for consistency if needed
      event_column_list - event column list by excluding timestamp and -x arguments
      original_data_df - original dataset
   """
   global TPATH
   
   # default relative path of csv input files
   csv_input_rel_path = tm_config["filesystem"]["rel_input_path"]

   mlib.vprint(tm_config['cli']['trim_verb'], "== Input:", 1)
   if tm_config['cli']['input_dataset'].lower().endswith('.csv'):
      # if  csv file
      if not os.path.isabs(tm_config['cli']['input_dataset']):
         csv_file = os.path.abspath(os.path.join(TPATH, csv_input_rel_path, 
                                    tm_config['cli']['input_dataset']))
      else:
         csv_file = tm_config['cli']['input_dataset']
      if not os.path.isfile(csv_file):
         print(f"No such input file {csv_file}", file=sys.stderr)
         sys.exit(1)
      else:
         mlib.vprint(tm_config['cli']['trim_verb'], 
                     f"valid input file: {csv_file}", 1)
         original_data_df = mlib.r_read_csv(csv_file)

   else:
      print(f"No input specified. Possible options:")
      def_input_path = os.path.abspath(os.path.join(TPATH, csv_input_rel_path))
      csv_files = [f for f in os.listdir(def_input_path) if f.endswith(".csv")]
      print(csv_files)
      sys.exit(1)
      

   # at this point original_data_df contains the data
   # preparing for analysis:
   
   # add the trim-generated index column -- don't call it index
   if tm_config["var"]["index_column"] in original_data_df.columns:
      # exit if the dataset has an column with the same name already;
      # workarounds include appending digits to the index column name
      # until it becomes unique: TBD
      print((f"Dataframe has an index column "
             f"{tm_config['var']['index_column']} already."), file=sys.stderr)
      print(f"Please change the index_column value in the", file=sys.stderr)
      print(f"m_config dictionary in m_config.py. Exiting.", file=sys.stderr)
      sys.exit(1)
   # reset index and add index column
   if 'index' in original_data_df.columns:
      # add protection if the index column already exists
      original_data_df.rename(columns={'index': 'oaku327Z944z'},  inplace=True)
   original_data_df = original_data_df.reset_index(drop=True)
   original_data_df = original_data_df.reset_index()
   original_data_df.rename(columns={'index': tm_config["var"]["index_column"]}, 
                           inplace=True)
   if 'oaku327Z944z' in original_data_df.columns:
      # restore the original index column
      original_data_df.rename(columns={'oaku327Z944z': 'index'},  inplace=True)

   # check the timestamp column
   if tm_config["cli"]["timestamp_column"]:
      if tm_config["cli"]["timestamp_column"] not in original_data_df.columns:
         # check if the timestamp column is in the dataframe
         print(f"Timestamp column does not exist in the dataframe. Exiting.", 
               file=sys.stderr)
         sys.exit(1)
      if not pd.api.types.is_integer_dtype(
               original_data_df[tm_config["cli"]["timestamp_column"]]):
         # check if the timestamp column contains  integers
         print((f"Timestamp column does not contain integers. "
                f"Please use epoch timestamps. Exiting."), file=sys.stderr)
         sys.exit(1)
      # order the rows by decreasing timestamp value - newer rows on top
      original_data_df.sort_values(by=tm_config["cli"]["timestamp_column"], 
                                   ascending=False, inplace=True)
   else:
      print(f"Timestamp column not defined. Exiting.", 
               file=sys.stderr)
      sys.exit(1)


   # check if the columns to be excluded exist
   if not pd.Series(tm_config["cli"]["exclude_column"]).isin(original_data_df.columns).all():
      print(f"Not all columns marked to be excluded (-x) exist. Exiting.", 
               file=sys.stderr)
      sys.exit(1)
   
   # build event_column_list
   event_column_list = [col for col in original_data_df.columns 
           if (col != tm_config["cli"]["timestamp_column"] and 
               col != tm_config["var"]["index_column"] and
               col not in tm_config["cli"]["exclude_column"])]
   mlib.vprint(tm_config["cli"]["trim_verb"], 
               f"Event columns: {event_column_list}", 1)

   # check column names for characters which may cause problems
   invalid_char_regex = re.compile(r'[^a-zA-Z0-9_]')
   for col in original_data_df.columns:
      if invalid_char_regex.search(col):
         print(f"Error: Column name '{col}' contains invalid characters.", 
               file=sys.stderr)
         sys.exit(1)
   
   # check for duplicate column names
   if original_data_df.columns.duplicated().any():
        duplicate_cols = \
              original_data_df.columns[original_data_df.columns.duplicated()].unique()
        print(f"Error: Duplicate column names found: {duplicate_cols}")
        sys.exit(1)
   
   # general input dataset info
   initial_event_number = len(original_data_df)
   mlib.vprint(tm_config["cli"]["trim_verb"], 
               f"Initial event number: N={initial_event_number}", 1)
   # initial and final timestamp
   initial_timestamp = original_data_df[tm_config["cli"]["timestamp_column"]].min()
   final_timestamp = original_data_df[tm_config["cli"]["timestamp_column"]].max()
   mlib.vprint(tm_config["cli"]["trim_verb"], 
            (f"spawning between {initial_timestamp} and "
             f"{final_timestamp}"), 1)
               
   # extract trim by fraction
   fraction_rows_totrim = max( int(initial_event_number * 
                     tm_config["cli"]["frac_totrim"]), 0)
   if fraction_rows_totrim > tm_config["cli"]["rows_totrim"]:
      tm_config["cli"]["rows_totrim"] = fraction_rows_totrim
      mlib.vprint(tm_config["cli"]["trim_verb"], 
                  f"Rows to trim: {tm_config['cli']['rows_totrim']}", 1)

   # consistency check for trim by number of rows
   if initial_event_number < tm_config["cli"]["rows_totrim"]: 
      mlib.vprint(tm_config["cli"]["trim_verb"], 
                  (f"More rows to trim than existing in the table: "
                  f"{tm_config['cli']['rows_totrim']}"), 1)
      mlib.vprint(tm_config["cli"]["trim_verb"], 
                  f"Reducing to the size of the table: {initial_event_number}", 1)
      tm_config["cli"]["rows_totrim"] = initial_event_number

 
   return tm_config, event_column_list, original_data_df
