
import pandas as pd
import numpy as np
import importlib
import os
import sys

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import trim_lib as tlib
import trim_config as tc


##############################################################################

def run_model(df):
   tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
               f"run model: {tlib.trim_config['cli']['trim_model']}", 1)

   # import the right module
   sys.path.insert(0, tlib.model_mod_abs_path)
   trimmodel = importlib.import_module("t_model")

   df = trimmodel.model_trim(df, 
               tlib.event_column_list,
               tlib.trim_config["cli"]["timestamp_column"],
               fake_timestamp = tlib.trim_config["cli"]["fake_timestamp"],
               rows_totrim = tlib.trim_config["cli"]["rows_totrim"],
               save_evolution = tlib.trim_config["cli"]["save_evolution"],
               strategy = tlib.trim_config["cli"]["strategy_totrim"],
               verb = tlib.trim_config["cli"]["trim_verb"],
               run_output_abs_path = tlib.run_output_abs_path, 
               idx_column = tlib.trim_config["var"]["index_column"],
               time_unit = tlib.trim_config["var"]["time_unit"],
               del_dup = tlib.trim_config["cli"]["del_dup"])
   
   return df

if __name__ == "__main__":
   model_trim(df)
