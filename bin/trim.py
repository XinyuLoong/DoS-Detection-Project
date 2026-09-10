

import math
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
import trim_filter as tfilter
import trim_profile as tprofile
import trim_output as tout
import trim_model as tmodel

   
if __name__ == "__main__":

   #########################################################################
   # define command line arguments
   parser = argparse.ArgumentParser(description="Trim config")
   parser.add_argument('-v', '--trim_verb', type=int, default=0, 
                             help='verbosity level of output')
   parser.add_argument('-i', '--input_dataset', type=str, default='', 
                             help='input data, a csv file or use db for a database table')
   parser.add_argument('-x', '--exclude_column', action='append', default=[], 
                             help='column to exclude from event definition')
   parser.add_argument('-m', '--trim_model', type=str, default='', 
                             help='use specified model')
   parser.add_argument('-s', '--strategy_totrim', type=str, default='total',
                             help='trimming strategy: event, block, total')
   parser.add_argument('-n', '--rows_totrim', type=int, default=0,
                             help='number of rows to trim')
   parser.add_argument('-c', '--frac_totrim', type=float, default=0.,
                             help='fraction of rows (rounded down) to trim')
   parser.add_argument('-o', '--output_dest', type=str, default='',
                             help='output destination, a csv file or use db for a database table')
   parser.add_argument('-p', '--profile_dataset', action='store_true', 
                             help='profile the dataset before and after trimming')
   parser.add_argument('-f', '--filter_dataset', action='append', default=[],
                             help='custom filter for the dataset before trimming')
   parser.add_argument('-t', '--timestamp_column', type=str, default='',
                             help='timestamp column name')
   parser.add_argument('-e', '--save_evolution', action='store_true', 
                             help='save the information evolution and trimming history')
   parser.add_argument('-r', '--reverse_trim', action='store_true', 
                             help='reverse trimming: krim the high information rows')
   parser.add_argument('-d', '--del_dup', type=int, default=0, 
                             help='delete duplicates first: 1=rows, 2=events')
   args = parser.parse_args()
   tlib.trim_config["cli"] = vars(args)

   #########################################################################
   # code execution
   
   # get configuration and perform checks
   tc.read_trim_config(tlib.trim_config["cli"]["trim_verb"])

   # input
   original_data_df = tinput.read_input_dataset()

   # make working copy and drop excluded columns
   initial_df = original_data_df.copy()
   if tlib.trim_config["cli"]["exclude_column"]:
      initial_df.drop(columns=tlib.trim_config["cli"]["exclude_column"], inplace=True)
   
   # output logistics setup
   tout.output_logistics()
   
   # filter
   if tlib.trim_config["cli"]["filter_dataset"]:
      initial_df = tfilter.apply_filters(initial_df) 
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
      tlib.r_df_to_csv(initial_df, tlib.run_output_abs_path + '/filtered_main.csv')
                    
   # initial dataset profiling
   if tlib.trim_config["cli"]["profile_dataset"]:
      # create initial profile
      tprofile.create_profile(initial_df, "initial")
      # results in tprofile.profile_report_dict["initial"]

   # initialize trimmed dataset
   trimmed_df = initial_df.copy()
      
   # run model
   if not tlib.trim_config["cli"]["trim_model"]:
      tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                  f"No model specified. Execution finished.", 1)
      sys.exit(0)   
   if not tlib.trim_config["cli"]["rows_totrim"]:
      tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                  f"Zero rows to trim. Exexution finished.", 1)
#      sys.exit(0) 

   # run model
   trimmed_df = tmodel.run_model(initial_df)

   # trimmed dataset profiling
   if tlib.trim_config["cli"]["profile_dataset"] and \
               tlib.trim_config["cli"]["rows_totrim"]:
      # create trimmed profile
      tprofile.create_profile(trimmed_df, "trimmed")
      # results in tprofile.profile_report_dict["trimmed"] 
   
   # un-filtering might be needed: TBD

   # output
   if tlib.trim_config["cli"]["output_dest"]:
      # find the index of the rows to be deleted
      if tlib.trim_config["cli"]["reverse_trim"]:
         rows_tostay_set, rows_togo_set = \
                        tlib.find_index_diff(initial_df, trimmed_df)
      else:      
         rows_togo_set, rows_tostay_set = \
                        tlib.find_index_diff(initial_df, trimmed_df)
      
      # operate trimming
      tout.write_trimmed_dataset(original_data_df, rows_togo_set)
   
      
   
