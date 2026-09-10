
import pandas as pd
import os
import sys
import yaml
import argparse
import datetime
import pymysql

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import db_lib as dblib
import db_config as dbc

def read_db_table(conf):
   """Reads a mysql table and returns a dataframe with the contents.
      The database access details are in the configuration file 
      etc/d_config.yaml
   """

   # if no configuration, read it
   if not dblib.db_config:
      dbc.read_db_config(conf['cli']['trim_verb'])

   # say what it does
   dblib.vprint(conf['cli']['trim_verb'], 
         (f"Reading from database {dblib.db_config['db_in']['database']} "
                  f"table {dblib.db_config['db_in']['db_table']}"), 1)

   # MySQL database connection details
   cnx_args = ['host', 'port', 'user', 'password', 'database']
   db_access = {key: dblib.db_config['db_in'][key] \
                  for key in cnx_args if key in dblib.db_config['db_in']}

   # MySQL interaction
   try:
      # Establish a MySQL connection
      cnx = pymysql.connect(**db_access, cursorclass=pymysql.cursors.DictCursor)
      cursor = cnx.cursor()
   
      if not dblib.table_exists(cursor, db_access['database'], 
                   dblib.db_config['db_in']['db_table']):
         print((f"read_db_table: Table {dblib.db_config['db_in']['db_table']} "
                f"does not exist. Exiting"), file=sys.stderr)
         sys.exit(1)
   
      # SELECT query
      sql_query = f"SELECT * FROM {dblib.db_config['db_in']['db_table']}"
      cursor.execute(sql_query)
      
      # Fetch all rows
      rows = cursor.fetchall()
      
      # Commit operation and close the connection
      cnx.commit()

   except pymysql.Error as e:
      print(f"read_db_table error: {e}", file=sys.stderr)
      sys.exit(1)
   finally:
      if cnx:
         cursor.close()
         cnx.close()
   
   # return the dataset      
   df = pd.DataFrame(rows)
   dblib.vprint(conf['cli']['trim_verb'], f"read_db_table: {len(df)} rows were read", 1)
   return pd.DataFrame(rows)

def trim_db_table(conf, df):
   """Trims out of a mysql table the rows of the input dataframe.
                                       (no trim-added index column)
      Backup methods in db_config[backup][data_backup]:
         '' - no backup
         csv - the entire table is saved to a csv file before trimming
         dump - the table is dumped to a sql file using mysqldump
         table - the rows to be trimmed are first added to the overflow
                 table db_config[backup][bkp_table], then deleted
                 from the original table (slow, no downtime)
      The database access details are in the configuration file 
      etc/d_config.yaml
   """
   
   # if no configuration, read it
   if not dblib.db_config:
      dbc.read_db_config(conf['cli']['trim_verb'])
   
   # say what it does
   dblib.vprint(conf['cli']['trim_verb'], 
            (f"Trimming table {dblib.db_config['db_out']['db_table']} from "
             f"database {dblib.db_config['db_out']['database']}"), 1)

   # MySQL database connection details
   cnx_args = ['host', 'port', 'user', 'password', 'database']
   db_access = {key: dblib.db_config['db_out'][key] \
                  for key in cnx_args if key in dblib.db_config['db_in']}

   # connect to database
   try:
      cnx = pymysql.connect(**db_access, cursorclass=pymysql.cursors.DictCursor)
      cursor = cnx.cursor()

      # handle backup
      if dblib.db_config['backup']['data_backup']:
         if dblib.db_config['backup']['data_backup'] == 'csv':
            dblib.csv_backup(conf['cli']['trim_verb'], cursor)
      
         elif dblib.db_config['backup']['data_backup'] == 'dump':
            dblib.dump_backup(conf['cli']['trim_verb'])         
         
         elif dblib.db_config['backup']['data_backup'] == 'table':
            dblib.table_backup(conf['cli']['trim_verb'], cursor, df)

         else:
            print((f"Unknown backup type {dblib.db_config['backup']['data_backup']} in "
                   f"etc/db_config.yaml. Possible options:"), file=sys.stderr)
            print(f"{','.join(dblib.db_config['backup']['data_backup_list'])}", 
                   file=sys.stderr)
            print(f"Exiting.", file=sys.stderr)
            sys.exit(1)

      # Trim data specified in dataframe from MySQL table
      for _, row in df.iterrows():
         # Dynamically create WHERE conditions based on column names
         where_clause = " AND ".join([f"{col} = %s" for col in df.columns])
         sql = f"DELETE FROM {dblib.db_config['db_out']['db_table']} WHERE {where_clause} LIMIT 1"
            
         # Execute query with row values
         cursor.execute(sql, tuple(row))

      # Commit the changes and close the connection
      cnx.commit()
      dblib.vprint(conf['cli']['trim_verb'], f"trim_db_table: {len(df)} rows were trimmed", 1)

   except pymysql.Error as e:
      print(f"trim_db_table error: {e}", file=sys.stderr)
      sys.exit(1)
   finally:
      if cnx:
         cursor.close()
         cnx.close()

             
##############################################################################

if __name__ == "__main__":
   """Read a dataframe from a csv file or db table.
      Trims out of a mysql table the rows of the totrim_df dataframe.
      Backs-up the data based on the method specified in the config file.
   """
   
   # define command line arguments
   parser = argparse.ArgumentParser(description="Model config")
   parser.add_argument('-v', '--trim_verb', type=int, default=0, 
                             help='verbosity level of output')
   parser.add_argument('-i', '--input_dataset', type=str, default='', 
                             help='input data, a csv file or use db for a database table')
   parser.add_argument('-t', '--timestamp_column', type=str, default='',
                             help='timestamp column name')
   parser.add_argument('-o', '--output_dest', type=str, default='',
                             help='output destination, a csv file or use db for a database table')
   parser.add_argument('-n', '--rows_totrim', type=int, default=0,
                             help='number of rows to trim')
   parser.add_argument('-c', '--frac_totrim', type=float, default=0.,
                             help='fraction of rows (rounded down) to trim')
   args = parser.parse_args()
   conf = {"cli": vars(args)}

   # if no configuration, read it
   if not dblib.db_config:
      dbc.read_db_config(conf['cli']['trim_verb'])
   
   if conf['cli']['input_dataset'] == 'db':
   
      # read the dataframe
      original_data_df = read_db_table(conf)
   
   else:
      # read file containing rows to be trimmed out
      csv_input_rel_path = dblib.db_config["filesystem"]["rel_input_path"]

      dblib.vprint(conf['cli']['trim_verb'], "== Input:", 1)
      if conf['cli']['input_dataset'].lower().endswith('.csv'):
         # if  csv file
         if not os.path.isabs(conf['cli']['input_dataset']):
            csv_file = os.path.abspath(os.path.join(TPATH, csv_input_rel_path, 
                                    conf['cli']['input_dataset']))
         else:
            csv_file = conf['cli']['input_dataset']
         if not os.path.isfile(csv_file):
            print(f"No such input file {csv_file}", file=sys.stderr)
            sys.exit(1)
         else:
            dblib.vprint(conf['cli']['trim_verb'], 
                     f"loading input file: {csv_file}", 1)
            original_data_df = dblib.r_read_csv(csv_file)
      else:
         print(f"Input is not a csv file.", file=sys.stderr)
         sys.exit(1)

   # reorder by timestamp column
   if conf["cli"]["timestamp_column"]:
      if conf["cli"]["timestamp_column"] not in original_data_df.columns:
         # check if the timestamp column is in the dataframe
         print(f"Timestamp column does not exist in the dataframe. Exiting.", 
               file=sys.stderr)
         sys.exit(1)
      if not pd.api.types.is_integer_dtype(
               original_data_df[conf["cli"]["timestamp_column"]]):
         # check if the timestamp column contains  integers
         print((f"Timestamp column does not contain integers. "
                f"Please use epoch timestamps. Exiting."), file=sys.stderr)
         sys.exit(1)
      # order the rows by decreasing timestamp value - newer rows on top
      original_data_df.sort_values(by=conf["cli"]["timestamp_column"], 
                                   ascending=False, inplace=True)
   else:
      print(f"Timestamp column not specified. Exiting.", file=sys.stderr)
      sys.exit(1)     

   # how much to trim
   initial_event_number = len(original_data_df)
   fraction_rows_totrim = max( int(initial_event_number * 
                     conf["cli"]["frac_totrim"]), 0)
   if fraction_rows_totrim > conf["cli"]["rows_totrim"]:
      conf["cli"]["rows_totrim"] = fraction_rows_totrim
      dblib.vprint(conf["cli"]["trim_verb"], 
                  f"Rows to trim: {conf['cli']['rows_totrim']}", 1)
   # consistency check for trim by number of rows
   if initial_event_number < conf["cli"]["rows_totrim"]: 
      dblib.vprint(conf["cli"]["trim_verb"], 
                  (f"More rows to trim than existing in the table: "
                  f"{conf['cli']['rows_totrim']}"), 1)
      dblib.vprint(conf["cli"]["trim_verb"], 
                  f"Reducing to the size of the table: {initial_event_number}", 1)
      conf["cli"]["rows_totrim"] = initial_event_number   
   
   # do dataframe trimming:
   totrim_df = original_data_df.copy()   
   remaining_rows = initial_event_number - conf["cli"]["rows_totrim"]
   totrim_df.drop(totrim_df.index[:remaining_rows], inplace=True)
   #print(totrim_df)

   # trim the table
   dblib.vprint(conf['cli']['trim_verb'], "== Trimming:", 1)
   if  conf["cli"]['output_dest'] == "db":
      dblib.vprint(conf['cli']['trim_verb'], (f"removing {len(totrim_df)} rows "
                   f"from the table"), 1)
      dblib.vprint(conf['cli']['trim_verb'], (f"Event number to be reduced from "
                   f"{initial_event_number} to {remaining_rows}"), 1)
      trim_db_table(conf, totrim_df)
   else:
      # save totrim_df to check.csv
      dblib.vprint(conf['cli']['trim_verb'], "save totrim_df to output/check.csv", 1)
      csv_file = os.path.abspath(os.path.join(TPATH, 
                              dblib.db_config['filesystem']['rel_output_path'], 
                              'check.csv'))
      dblib.r_df_to_csv(totrim_df, csv_file)


