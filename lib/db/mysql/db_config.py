
import argparse
import os
import sys
import yaml

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

# import local modules
import db_lib as dblib

# global variables
default_config_file = os.path.abspath(os.path.join(TPATH, 
                         "etc/db_config.yaml"))
                         
def load_config(filepath, verb):
   """Loads configuration from a YAML file."""
   
   try:
      with open(filepath, "r") as file:
         config = yaml.safe_load(file)
         dblib.vprint(verb, f"Reading configuration file: {filepath}", 1)
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

def read_db_config(verb):
   """Appends the yaml config to db_config global dict.
   Performs consistency tests on the configuration.
   """
   global default_config_file
   dblib.db_config.update(load_config(default_config_file, 1))

   # sanity checks
   # print config
   dblib.vprint(verb, f"== Configuration:", 1)
   dblib.vprint(verb, dblib.db_config, 1)

   # basic configuration sections exist
   for sect in  ['app', 'filesystem']:
      if sect not in dblib.db_config:
         print(f"Section {sect} found not in the configuration file. Exiting", 
               file=sys.stderr)
         sys.exit(1)

   # check db output
   if dblib.db_config["backup"]["data_backup"]:

      # check if value in list
      if dblib.db_config["backup"]["data_backup"] not in \
                  dblib.db_config["backup"]["data_backup_list"]:
         print((f"Data backup method {dblib.db_config["backup"]["data_backup"]} "
                f"not listed in {dblib.db_config["backup"]["data_backup_list"]}. Exiting"), 
                file=sys.stderr)
         sys.exit(1)
      
      # check for overflow table
      if dblib.db_config["backup"]["data_backup"] == 'table' and \
              (not dblib.db_config["backup"]["bkp_table"]):
         print(f"Data backup set to table but no overflow table was specified. Exiting", 
                  file=sys.stderr)
         sys.exit(1)
      
      # check for dump file name
      if dblib.db_config["backup"]["data_backup"] == 'dump' and \
              (not dblib.db_config["backup"]["bkp_dumpfile"]):
         print(f"Data backup set to dump but no dump file was specified. Exiting", 
                  file=sys.stderr)
         sys.exit(1)
         
      # check for backup csv file name
      if dblib.db_config["backup"]["data_backup"] == 'csv' and \
              (not dblib.db_config["backup"]["bkp_csvbkpfile"]):
         print(f"Data backup set to csv but no csv file was specified. Exiting", 
                  file=sys.stderr)
         sys.exit(1)
         
         
