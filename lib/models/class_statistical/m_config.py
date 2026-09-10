import argparse
import os
import sys
import yaml

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

# import local modules
import m_lib as mlib

# global variables
default_config_file = os.path.abspath(os.path.join(TPATH, 
                         "etc/m_config.yaml"))

def load_config(filepath, verb):
   """Loads configuration from a YAML file."""
   
   try:
      with open(filepath, "r") as file:
         config = yaml.safe_load(file)
         mlib.vprint(verb, f"Reading configuration file: {filepath}", 1)
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

def read_m_config(verb):
   """Appends the yaml config to m_config global dict.
   Performs consistency tests on the configuration.
   """
   global default_config_file
   mlib.m_config.update(load_config(default_config_file, 1))

   # sanity checks
   # print config
   mlib.vprint(verb, f"== Configuration:", 1)
   mlib.vprint(verb, mlib.m_config, 1)

   # basic configuration sections exist
   for sect in  ['app', 'filesystem', 'var']:
      if sect not in mlib.m_config:
         print(f"Section {sect} found not in the configuration file. Exiting", 
               file=sys.stderr)
         sys.exit(1)

   # index column is not empty
   if not mlib.m_config["var"]["index_column"]:
      print(f"index column has empty name. Exiting", file=sys.stderr)
      sys.exit(1)
   # check also for allowed characters: TBD

