##########################################################
# file_name: trim_profile.py
# update_date: 2026-08-03
# brief:
#    Provides the profiling entry point for TRIM. This file prepares profile
#    execution, delegates configured profile tests to profile_runner, and stores
#    the returned profile report by dataset stage.
#
# functions:
#    create_profile(df, stg):
#       Runs configured dataset profiling, stores the returned profile report
#       in profile_report_dict, and returns the report.
##########################################################

import argparse
import os
import sys

TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import trim_lib as tlib
import trim_config as tc
import trim_input as tinput
import trim_output as tout
import trim_filter as tfilter
import profile_runner as prunner


stage = ""
profile_report_dict = {}


def create_profile(df, stg):
   
   """
   brief:
      Run configured dataset profiling and store the report for the requested stage.

   paras:
      df: Input DataFrame to profile.
      stg: Dataset stage label, such as "initial".

   return:
      Profile report dictionary for the stage, or None when the stage is empty or repeated.
   """

   global stage
   global profile_report_dict

   if (not stg) or (stg == stage):
      tlib.vprint(tlib.trim_config["cli"]["trim_verb"],
                  f"No meaningful stage specified", 1)
      return None

   stage = stg
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"],
               f"================ Profiling stage: {stage}", 1)

   profile_report = prunner.run_profile_tests(df, stage)
   profile_report_dict[stage] = profile_report

   tlib.vprint(tlib.trim_config["cli"]["trim_verb"],
               f"================ Profiling {stage} dataset ended", 1)

   return profile_report


if __name__ == "__main__":

   #########################################################################
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

   #########################################################################

   # get configuration and perform checks
   tc.read_trim_config(tlib.trim_config["cli"]["trim_verb"])
   # if no input file specified, exit
   if not tlib.trim_config["cli"]["input_dataset"]:
      sys.exit(0)

   # input
   if tlib.trim_config["cli"]["input_dataset"]:
      original_data_df = tinput.read_input_dataset()

   # make working copy and drop excluded columns
   initial_df = original_data_df.copy()
   if tlib.trim_config["cli"]["exclude_column"]:
      initial_df.drop(columns=tlib.trim_config["cli"]["exclude_column"], inplace=True)

   # output logistics setup
   tout.output_logistics()

   # filter
   if tlib.trim_config["cli"]["filter_dataset"]:
      initial_df = original_data_df.copy()
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
      tlib.r_df_to_csv(initial_df, tlib.run_output_abs_path +
                        '/filtered_main.csv')

   # create initial profile
   create_profile(initial_df, "initial")
