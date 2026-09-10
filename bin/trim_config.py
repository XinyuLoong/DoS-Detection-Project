import argparse
import os
import sys
import yaml

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

# import local modules
import trim_lib as tlib

# global variables
default_config_file = os.path.abspath(os.path.join(TPATH, 
                         "../etc/trim_config.yaml"))

def load_config(filepath, verb):
   """Loads configuration from a YAML file."""
   
   try:
      with open(filepath, "r") as file:
         config = yaml.safe_load(file)
         tlib.vprint(verb, f"Reading configuration file: {filepath}", 1)
      return config
   except FileNotFoundError:
      print(f"Error: Configuration file '{filepath}' not found.", 
              file=sys.stderr)
      #return None
      sys.exit(1)
   except yaml.YAMLError as e:
      print(f"Error: Failed to parse YAML file: {e}", file=sys.stderr)
      #return None
      sys.exit(1)

def read_trim_config(verb):
   """Appends the yaml config to trim_config global dict.
   Performs consistency tests on the configuration.
   """
   global TPATH
   global default_config_file
   tlib.trim_config.update(load_config(default_config_file, 1))

   # sanity checks
   # configuration is not empty
   if not tlib.trim_config:
      print("Empty config file {default_config_file}", file=sys.stderr)
      sys.exit(1) 
   else:
      tlib.vprint(verb, f"== Configuration:", 1)
      tlib.vprint(verb, tlib.trim_config, 1)

   # basic configuration sections exist
   for sect in  ['app', 'filesystem', 'var']:
      if sect not in tlib.trim_config:
         print(f"Section {sect} found not in the configuration file. Exiting", 
               file=sys.stderr)
         sys.exit(1)

   # index column is not empty
   if not tlib.trim_config["var"]["index_column"]:
      print(f"index column has empty name. Exiting", file=sys.stderr)
      sys.exit(1)
   # check also for allowed characters: TBD

   if "cli" in tlib.trim_config:
      # check strategy
      if "strategy_totrim" in tlib.trim_config["cli"]:
         if tlib.trim_config["cli"]["strategy_totrim"] not in \
                  tlib.trim_config["trimming"]["trim_strategy_list"]:
            print((f"Unknown strategy {tlib.trim_config['cli']['strategy_totrim']}"
                  f" specified."), file=sys.stderr)
            print((f"Valid strategies: "
                  f"{tlib.trim_config['trimming']['trim_strategy_list']}"), 
                  file=sys.stderr)
            print(f"Exiting", file=sys.stderr)
            sys.exit(1)
         if tlib.trim_config["cli"]["strategy_totrim"]:
            tlib.vprint(tlib.trim_config["cli"]["trim_verb"], (f"Strategy to "
                  f"trim: {tlib.trim_config['cli']['strategy_totrim']}"), 1)

      # check filters
      if "filter_dataset" in tlib.trim_config["cli"]:
         if not all(item in tlib.trim_config["filter"]["filter_list"] 
                for item in tlib.trim_config["cli"]["filter_dataset"]):
            print((f"Not all filters in "
                   f"{tlib.trim_config['cli']['filter_dataset']} "
                   f"are recognized"), file=sys.stderr)
            print((f"Available filters: "
                   f"{tlib.trim_config['filter']['filter_list']}"), file=sys.stderr)
            print(f"Exiting", file=sys.stderr)
            sys.exit(1)

      # check model
      if "trim_model" in tlib.trim_config["cli"]:
         if tlib.trim_config["cli"]["trim_model"]:
            if tlib.trim_config["cli"]["trim_model"] not in \
                      tlib.trim_config["model"]["model_list"]:
               print((f"Unknown model {tlib.trim_config['cli']['trim_model']}"
                      f" specified."), file=sys.stderr)
               print(f"Existing models: {tlib.trim_config['model']['model_list']}",
                      file=sys.stderr)
               print(f"Exiting", file=sys.stderr)
               sys.exit(1)
            else:
               tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                     f"Trimming model: {tlib.trim_config['cli']['trim_model']}", 1)

            # build the module path and load it to tlib.model_mod_abs_path
            tlib.model_mod_abs_path = os.path.abspath(os.path.join(TPATH, 
                  tlib.trim_config['filesystem']['model_path'], 
                  tlib.trim_config['cli']['trim_model']))
            tlib.vprint(tlib.trim_config["cli"]["trim_verb"], 
                     f"Trimming model directory: {tlib.model_mod_abs_path}", 1)
                  
            # check if the module file exists
            model_module_py = os.path.join(tlib.model_mod_abs_path, 't_model.py')
            if not os.path.isfile(model_module_py):
               print(f"No model module {model_module_py}", file=sys.stderr)
               sys.exit(1)

      # set database module absoulute path
      if tlib.trim_config["cli"]["output_dest"] == 'db' or \
               tlib.trim_config["cli"]["input_dataset"] == 'db':   
         
         # build the module path and load it to tlib.db_mod_abs_path
         tlib.db_mod_abs_path = os.path.abspath(os.path.join(TPATH, 
               tlib.trim_config['filesystem']['db_path'], 
               tlib.trim_config['var']['db_engine']))
         
         # check if the module file exists
         db_module_py = os.path.join(tlib.db_mod_abs_path, 'db_trim.py')
         if not os.path.isfile(db_module_py):
            print(f"No db interaction module {db_module_py}", file=sys.stderr)
            sys.exit(1)

      # check rows to trim
      if "rows_totrim" in tlib.trim_config["cli"]:
         if tlib.trim_config["cli"]["rows_totrim"] < 0:
            tlib.trim_config["cli"]["rows_totrim"] = 0
   
         
if __name__ == "__main__":
   read_trim_config(1)
   

