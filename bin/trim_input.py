
import pandas as pd
import numpy as np
import importlib
import os
import sys
import re

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import trim_lib as tlib
import trim_config as tc

def read_input_dataset():
   """Read the input dataset to a dataframe:

      information needed:
      trim_config['cli']['input_dataset'] - can be:
            * a csv file name which should exist in the input dir
            * a csv file name including the absolute path, 
                                or a path relative to the input dir
            * 'db' - use database module to read from db table
      trim_config["cli"]["timestamp_column"] - the timestamp column;
            empty if no timestamp column specified
      trim_config["var"]["index_column"] - the trim-generated index column
      
      If no timestamp column is specified in the CLI arguments,
            it is set to the trim generated index column
   """
   global TPATH
   
   # default relative path of csv input files
   csv_input_rel_path = tlib.trim_config["filesystem"]["rel_input_path"]

   tlib.vprint(tlib.trim_config['cli']['trim_verb'], "== Input:", 1)
   if tlib.trim_config['cli']['input_dataset'].lower().endswith('.csv'):
      # if  csv file
      if not os.path.isabs(tlib.trim_config['cli']['input_dataset']):
         csv_file = os.path.abspath(os.path.join(TPATH, csv_input_rel_path, 
                                    tlib.trim_config['cli']['input_dataset']))
      else:
         csv_file = tlib.trim_config['cli']['input_dataset']
      if not os.path.isfile(csv_file):
         print(f"No such input file {csv_file}", file=sys.stderr)
         sys.exit(1)
      else:
         tlib.vprint(tlib.trim_config['cli']['trim_verb'], 
                     f"valid input file: {csv_file}", 1)
         original_data_df = tlib.r_read_csv(csv_file)
      if original_data_df.empty:
         print(f"Empty input dataframe. Exiting", file=sys.stderr)
         sys.exit(1)

   # otherwise, assume database
   elif tlib.trim_config['cli']['input_dataset'].lower() == 'db':

      # import the right module
      sys.path.insert(0, tlib.db_mod_abs_path)
      tdb = importlib.import_module("db_trim")

      # read data from the db table
      original_data_df = tdb.read_db_table(tlib.trim_config)

   else:
      print(f"No input specified. Possible options:", file=sys.stderr)
      def_input_path = os.path.abspath(os.path.join(TPATH, csv_input_rel_path))
      csv_files = [f for f in os.listdir(def_input_path) if f.endswith(".csv")]
      print(csv_files, file=sys.stderr)
      sys.exit(1)
      

   # at this point original_data_df contains the data
   # preparing for analysis:
   
   # add the trim-generated index column -- don't call it index
   if tlib.trim_config["var"]["index_column"] in original_data_df.columns:
      # exit if the dataset has an column with the same name already;
      # workarounds include appending digits to the index column name
      # until it becomes unique: TBD
      print((f"Dataframe has an index column "
             f"{tlib.trim_config['var']['index_column']} already."), file=sys.stderr)
      print(f"Please change the index_column value in the", file=sys.stderr)
      print(f"trim_config dictionary in trim_config.py. Exiting.", file=sys.stderr)
      sys.exit(1)
   # reset index and add index column
   if 'index' in original_data_df.columns:
      # add protection if the index column already exists
      original_data_df.rename(columns={'index': 'oaku327Z944z'},  inplace=True)
   original_data_df = original_data_df.reset_index(drop=True)
   original_data_df = original_data_df.reset_index()
   original_data_df.rename(columns={'index': tlib.trim_config["var"]["index_column"]}, 
                           inplace=True)
   if 'oaku327Z944z' in original_data_df.columns:
      # restore the original index column
      original_data_df.rename(columns={'oaku327Z944z': 'index'},  inplace=True)

   # check the timestamp column
   if tlib.trim_config["cli"]["timestamp_column"]:
      if tlib.trim_config["cli"]["timestamp_column"] not in original_data_df.columns:
         # check if the timestamp column is in the dataframe
         print(f"Timestamp column does not exist in the dataframe. Exiting.", 
               file=sys.stderr)
         sys.exit(1)
      if not pd.api.types.is_integer_dtype(
               original_data_df[tlib.trim_config["cli"]["timestamp_column"]]):
         # check if the timestamp column contains  integers
         print((f"Timestamp column does not contain integers. "
                f"Please use epoch timestamps. Exiting."), file=sys.stderr)
         sys.exit(1)
      # order the rows by decreasing timestamp value - newer rows on top
      original_data_df.sort_values(by=tlib.trim_config["cli"]["timestamp_column"], 
                                   ascending=False, inplace=True)
      # signal valid timestamp column
      tlib.trim_config["cli"]["fake_timestamp"] = False
   else:
      # if no timestamp column, consider index as timestamp
      tlib.trim_config["cli"]["timestamp_column"] = tlib.trim_config["var"]["index_column"]
      # reverse the index to fake timestamps from new to old 
      original_data_df[tlib.trim_config["var"]["index_column"]] = \
         original_data_df[tlib.trim_config["var"]["index_column"]].iloc[::-1].values 
      # signal no timestamp column
      tlib.trim_config["cli"]["fake_timestamp"] = True

   # check if the columns to be excluded exist
   if not pd.Series(tlib.trim_config["cli"]["exclude_column"]).isin(original_data_df.columns).all():
      print(f"Not all columns marked to be excluded (-x) exist. Exiting.", 
               file=sys.stderr)
      sys.exit(1)
   
   # build event_column_list
   tlib.event_column_list = [col for col in original_data_df.columns 
           if (col != tlib.trim_config["cli"]["timestamp_column"] and 
               col != tlib.trim_config["var"]["index_column"] and
               col not in tlib.trim_config["cli"]["exclude_column"])]
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
               f"Event columns: {tlib.event_column_list}", 1)

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
        print(f"Error: Duplicate column names found: {duplicate_cols}", 
              file=sys.stderr)
        sys.exit(1)
   
   # general input dataset info
   initial_event_number = len(original_data_df)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
               f"Initial event number: N = {initial_event_number}", 1)
   # initial and final timestamp
   if not tlib.trim_config["cli"]["fake_timestamp"]:
      initial_timestamp = original_data_df[tlib.trim_config["cli"]["timestamp_column"]].min()
      final_timestamp = original_data_df[tlib.trim_config["cli"]["timestamp_column"]].max()
      tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
               (f"spawning between {tlib.epoch_to_datetime(initial_timestamp)} and "
                f"{tlib.epoch_to_datetime(final_timestamp)}"), 1)
               
   # extract trim by fraction
   fraction_rows_totrim = max( int(initial_event_number * 
                     tlib.trim_config["cli"]["frac_totrim"]), 0)
   if fraction_rows_totrim > tlib.trim_config["cli"]["rows_totrim"]:
      tlib.trim_config["cli"]["rows_totrim"] = fraction_rows_totrim
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
               f"Rows to trim: {tlib.trim_config['cli']['rows_totrim']}", 1)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], (f"Remaining rows: "
        f"{initial_event_number - tlib.trim_config['cli']['rows_totrim']}"), 1)
   # consistency check for trim by number of rows
   if initial_event_number < tlib.trim_config["cli"]["rows_totrim"]: 
      print((f"More rows to trim {tlib.trim_config['cli']['rows_totrim']}"
             f"than existing in the table: {initial_event_number}. Exiting"), 
             file=sys.stderr)
      sys.exit(1)

   # remap using column name mapping: TBD
   # reverse remapping in trim_output.py: TBD               
   
   return original_data_df
