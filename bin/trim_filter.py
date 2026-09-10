
import pandas as pd
import numpy as np
import argparse
import os
import sys

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import trim_lib as tlib
import trim_config as tc
import trim_input as tinput
import trim_output as tout


def filter_map_toint(df):

   # columns to remap
   columns_to_remap = tlib.event_column_list

   # concatenate the values of interest into one series
   all_values = pd.concat([df[col] for col in columns_to_remap])

   # create a pandas series of value counts
   value_counts = all_values.value_counts()
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
               f"map_toint: value_counts:", 3)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], f"{value_counts}", 3)

   # transform to dataframe adding index
   translate_counts_df = value_counts.to_frame(name='counts').reset_index()
   translate_counts_df.rename(columns={'index': 'entry'}, inplace=True)
   translate_counts_df = translate_counts_df.reset_index()
   translate_counts_df.rename(columns={'index': 'translate'}, inplace=True)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
               f"map_toint: translate_counts_df:", 3)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], translate_counts_df, 3)
   # write to csv
   tlib.r_df_to_csv(translate_counts_df, tlib.run_output_abs_path + \
                              '/filter_toint_counts.csv')

   # create translate dictionary
   if translate_counts_df['translate'].duplicated().any():
      raise ValueError("Column 'translate' must have unique values.")
   if translate_counts_df['entry'].duplicated().any():
      raise ValueError("Column 'entry' must have unique values.")
   translate_dict = pd.Series(translate_counts_df['translate'].values, 
                              index=translate_counts_df['entry']).to_dict()
   #tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
   #		"map_toint: translate_dict:", 3)
   #tlib.vprint(tlib.trim_config["cli"]["trim_verb"], translate_dict, 3)

   # remap using the replacement dictionary
   df[columns_to_remap] = df[columns_to_remap].replace(translate_dict)

   return df
   
##############################################################################

def filter_a(df):
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                  f"a: Test filter; does nothing", 1)
   if tlib.trim_config['cli']['fake_timestamp']:
      tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                  f"a: Timestamp column: None", 1)
   else:
      tlib.vprint(tlib.trim_config["cli"]["trim_verb"], (f"a: Timestamp column: "
                  f"{tlib.trim_config['cli']['timestamp_column']}"), 1)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
               f"a: Index column: {tlib.trim_config['var']['index_column']}", 1)

   return df

##############################################################################

def apply_filters(df):
   
   # what filters are defined
   defined_filters = {s: globals()[f'filter_{s}'] 
                     for s in tlib.trim_config["filter"]["filter_list"]}
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], f"== Defined filters:", 1)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], defined_filters, 1)
   
   # apply the filters in sequence
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
         f"Filters to apply: {tlib.trim_config['cli']['filter_dataset']}", 1)
   for filter in tlib.trim_config["cli"]["filter_dataset"]:
      if filter in defined_filters:
         df = defined_filters[filter](df)
      else:
         print(f"Filter {filter} not found. Exiting", file=sys.stderr)
         sys.exit(1)
         
   return df

##############################################################################

if __name__ == "__main__":

   # define command line arguments
   parser = argparse.ArgumentParser(description="Trim dataset")
   parser.add_argument('-v', '--trim_verb', type=int, 
               help='verbosity level of output', default=0)
   parser.add_argument('-i', '--input_dataset', type=str, 
               help='input data, a csv file or use db for a database table', default='')
   parser.add_argument('-x', '--exclude_column', action='append', 
               help='column to exclude from event definition', default=[])
   parser.add_argument('-o', '--output_dest', type=str, 
               help='output destination, a csv file or use db for a database table', default='')
   parser.add_argument('-f', '--filter_dataset', action='append', 
               help='custom filter for the dataset before trimming', default=[])
   parser.add_argument('-t', '--timestamp_column', type=str, 
               help='timestamp column name', default='')
   args = parser.parse_args()
   tlib.trim_config["cli"] = vars(args)

   
   # get configuration and perform checks
   tc.read_trim_config(tlib.trim_config["cli"]["trim_verb"])
   # if no input file specified, exit
   if not tlib.trim_config["cli"]["input_dataset"]:
      sys.exit(0)

   # input
   if tlib.trim_config["cli"]["input_dataset"]:
      original_data_df = tinput.read_input_dataset()
      
   # output logistics setup
   tout.output_logistics()   
   
   initial_df = original_data_df.copy()
   initial_df = apply_filters(initial_df) 
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                               f"== Filtering results:", 1)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], "original_data_df:", 1)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                                  f"{original_data_df.dtypes}", 1)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], original_data_df, 3)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], "initial_df:", 1)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                               f"{initial_df.dtypes}", 1)
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], initial_df, 3)

   # filtered dataframe is stored to run_output_abs_path/filtered_main.csv
   tlib.r_df_to_csv(initial_df, tlib.run_output_abs_path + 
                    '/filtered_main.csv')

