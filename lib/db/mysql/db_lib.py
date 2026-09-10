
##########################################################
# print_nested_dict(dictionary, indent=0): print nested dictionary
# vprint(verb, aaa, level): verbose print
# epoch_to_datetime(epoch_time): timestamp epoch to real date
# dtype_to_sql(dtype): pandas dtypes to MySQL data types
# r_read_csv(csv_file): robust read from csv file
# r_df_to_csv(df, csv_file): robust write dataframe to csv file
# table_exists(cursor, db, table): check if table exists
# create_table(cursor, df, table, primary_keys): create table
# dump_backup(verb, dump_path=''): table backup through mysqldump
# csv_backup(verb, cursor, csv_path=''): table backup to a csv file
# table_backup(verb, cnx, cursor, df): overflow rows are moved to different table
#
##########################################################

import pandas as pd
import numpy as np
import os
import sys
import pymysql
import yaml
import inspect
import subprocess

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

# global variables
db_config = {}

import db_config as dbc
####################################################################
# print nested dictionary
def print_nested_dict(dictionary, indent=0):
    for key, value in dictionary.items():
        if isinstance(value, dict):
            print("  " * indent + f"{key}:")
            print_nested_dict(value, indent + 1)
        else:
            print("  " * indent + f"{key}: {value}")


###################################################################
# verbose print
def vprint(verb, aaa, level):
   """Verbose levels:
   quiet   -> verb <= 0  -> default
   summary -> verb = 1   -> one liners
   live    -> verb = 2   -> 1 + plots
   debug   -> verb >= 3  -> everything
   """
   #print(f"type of aaa is {type(aaa)}")
   if verb >= level: 
      if type(aaa) is dict:
         print_nested_dict(aaa, 2)   
      else:
         print(aaa)

###################################################################
# timestamp epoch to real date
def epoch_to_datetime(epoch_time):
   """Transforms epoch to real time"""
   global m_config

   return pd.to_datetime(epoch_time, unit=m_config["var"]['time_unit'])

###################################################################
# pandas dtypes to MySQL data types
def dtype_to_sql(dtype):
   """Converts pandas dtypes to MySQL data types."""
   if pd.api.types.is_integer_dtype(dtype):
      return 'INT(64)'
   elif pd.api.types.is_float_dtype(dtype):
      return 'FLOAT'
   elif pd.api.types.is_datetime64_any_dtype(dtype):
      return 'DATETIME'
   else:
      return 'VARCHAR(128)' # Default for strings and other types
      
###################################################################
# robust read from csv file
def r_read_csv(csv_file):

   caller_frame = inspect.stack()[1]  # Get the caller's frame
   # Caller's function name: caller_frame.function

   try:
      # Read the CSV file into a pandas DataFrame
      df = pd.read_csv(csv_file)
   except FileNotFoundError:
      print(f"Error from {caller_frame.function}: File '{csv_file}' not found.", 
            file=sys.stderr)
      sys.exit(1)
   except pd.errors.ParserError:
      print((f"Error from {caller_frame.function}: Could not parse CSV file "
             f"'{csv_file}'. Check file format."), file=sys.stderr)
      sys.exit(1)
   except Exception as e:
      print(f"An unexpected read error occurred from {caller_frame.function}: {e}", 
            file=sys.stderr)
      sys.exit(1)
   return df

###################################################################
# robust write dataframe to csv file
def r_df_to_csv(df, csv_file):

   caller_frame = inspect.stack()[1]  # Get the caller's frame
   # Caller's function name: caller_frame.function

   try:
      # create directory if it doesn't exist
      os.makedirs(os.path.dirname(csv_file), exist_ok=True)
   except OSError as e:
      print((f"Error from {caller_frame.function}: Could not create the directory "
             f"for {csv_file}. Exiting."), file=sys.stderr)
      sys.exit(1)

   try:
      df.to_csv(csv_file, index=False)
   except OSError as e:
      print(f"Error from {caller_frame.function}: Could not write to {csv_file}: {e}",
            file=sys.stderr)
      sys.exit(1)
   except IOError as e:
      print((f"Error from {caller_frame.function}: An I/O error occurred "
             f"while writing to {csv_file}: {e}"), file=sys.stderr)
      sys.exit(1)
   except Exception as e:
      print(f"An unexpected write error occurred from {caller_frame.function}: {e}",
            file=sys.stderr)
      sys.exit(1)

###################################################################
# check if table exists
def table_exists(cursor, db, table):
   """
   Checks if a table exists in a MySQL database.
        cursor: A PyMySQL cursor object.
        db: The name of the database.
        table: The name of the table to check.
   Returns:
        True if the table exists, False otherwise.
   """
   
   # SQL query
   sql = "SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s LIMIT 1"
   
   try:
      # Execute the query
      cursor.execute(sql, (db, table))

      # Fetch the result
      result = cursor.fetchone()

      # Return True if a result is found, False otherwise
      return result is not None

   except pymysql.MySQLError as e:
      return False

###################################################################
# create table with the structure from df and primary_keys
def create_table(cursor, df, table, keys):
   """
   Create a table if it does not exist.
        cnx: database connection PyMySQL object.
        cursor: A PyMySQL cursor object.
        df: dataframe  with the table structure.
        table: The name of the table to be created.
        primary_keys: Primary keys list.
   """
   global db_config

   # check if primary keys exist
   if keys:
      primary_keys = [item for item in keys if item in df.columns]
   else:
      primary_keys = list()
   #print(primary_keys)  
   #print(f"creating table {db_config['db_in']['db_table']}")
   
   # Create the SQL table creation query
   create_table_sql = (f"CREATE TABLE IF NOT EXISTS {table} "
      f"({', '.join([f'{col} {dtype_to_sql(dtype)}' for col, dtype in zip(df.columns, df.dtypes)])}")
   if primary_keys:
      create_table_sql = create_table_sql + f", PRIMARY KEY ({','.join(primary_keys)})"
   create_table_sql = create_table_sql + ")"

   try:
      # Execute the CREATE TABLE statement
      cursor.execute(create_table_sql)

   except pymysql.MySQLError as e:
      print(f"Error: {e}", file=sys.stderr)
      sys.exit(1)

###################################################################
# table backup through mysqldump
def dump_backup(verb, dump_path = ''):
   """
   Table to be trimmed is dumped to db_config['backup']['bkp_dumpfile'] 
   before trimming, to directory dump_path/ if absolute,
   or to TPATH/dump_path/ if dump_path is relative,
   or to TPATH/db_config['filesystem']['rel_output_path']/
   """
   global db_config
   
   caller_frame = inspect.stack()[1]  # Get the caller's frame
   # Caller's function name: caller_frame.function
   
   if not db_config['backup']['bkp_dumpfile']:
      print(f"Dump file not specified in the configuration. Exiting", 
            file=sys.stderr)
      sys.exit(1) 

   # dump file
   if not dump_path:
      dump_path = os.path.abspath(os.path.join(TPATH, 
                    db_config['filesystem']['rel_output_path']))
   elif not os.path.isabs(dump_path):
      dump_path = os.path.abspath(os.path.join(TPATH, dump_path))
   
   # dump file with absolute path
   dump_file = os.path.join(dump_path, db_config['backup']['bkp_dumpfile'])
   
   try:
      # create directory if it doesn't exist
      os.makedirs(dump_path, exist_ok=True)
   except OSError as e:
      print((f"Error from {caller_frame.function}: Could not create the dump directory "
             f"for {dump_file}. Exiting."), file=sys.stderr)
      sys.exit(1)

   # backup command
   backup_command = (f"mysqldump --no-tablespaces "
                         f"-h {db_config['db_out']['host']} "
                         f"-P {db_config['db_out']['port']} "
                         f"-u {db_config['db_out']['user']} "
                         f"-p{db_config['db_out']['password']} "
                         f"{db_config['db_out']['database']} "
                         f"{db_config['db_out']['db_table']} > {dump_file}")

   # perform backup
   try:
      # Execute the backup command - this MUST succeed before proceeding
      subprocess.run(backup_command, shell=True, check=True)
      vprint(verb, (f"Table {db_config['db_out']['db_table']} in "
             f"database {db_config['db_out']['database']} was backed-up to "
             f"dump {dump_file}"), 1)
   except subprocess.CalledProcessError as e:
      print(f"Failed to create dump: {str(e)}")
      print("Trimming aborted for data safety.", file=sys.stderr)
      sys.exit(1)
   
###################################################################
# table backup to a csv file
def csv_backup(verb, cursor, csv_path = ''):
   """
   Table to be trimmed is saved to csv db_config['backup']['bkp_csvbkpfile'] 
   before trimming, to directory csv_path/ if absolute,
   or to TPATH/csv_path/ if csv_path is relative,
   or to TPATH/db_config['filesystem']['rel_output_path']/   
   """
   global db_config
   
   caller_frame = inspect.stack()[1]  # Get the caller's frame
   # Caller's function name: caller_frame.function
   
   if not db_config['backup']['bkp_csvbkpfile']:
      print(f"CSV file not specified in the configuration. Exiting", 
            file=sys.stderr)
      sys.exit(1) 

   # csv file
   if not csv_path:
      csv_path = os.path.abspath(os.path.join(TPATH, 
                    db_config['filesystem']['rel_output_path']))
   elif not os.path.isabs(csv_path):
      csv_path = os.path.abspath(os.path.join(TPATH, csv_path))

   # csv file with absolute path
   csv_file = os.path.join(csv_path, db_config['backup']['bkp_csvbkpfile'])

   try:
      # create directory if it doesn't exist
      os.makedirs(csv_path, exist_ok=True)
   except OSError as e:
      print((f"Error from {caller_frame.function}: Could not create the backup "
             f"directory for {csv_file}: {e}. Exiting."), file=sys.stderr)
      sys.exit(1)
   
   sql_query = f"SELECT * FROM {db_config['db_out']['db_table']}"
   cursor.execute(sql_query)
        
   # Fetch all rows
   rows = cursor.fetchall()
        
   # Save to CSV
   r_df_to_csv(pd.DataFrame(rows), csv_file)
   
   # print the result
   vprint(verb, (f"Table {db_config['db_out']['db_table']} in "
             f"database {db_config['db_out']['database']} was backed-up to "
             f"csv file {csv_file}"), 1)
   
###################################################################
# overflow rows are moved to db_config['backup']['bkp_table']
def table_backup(verb, cursor, df):
   """
   Overflow rows specified by df from table {db_config['db_out']['db_table']}
   in database db_config['db_out']['database'] are saved to 
   table {db_config['backup']['bkp_table'].
   """
   global db_config
   
   caller_frame = inspect.stack()[1]  # Get the caller's frame
   # Caller's function name: caller_frame.function

   if not db_config['backup']['bkp_table']:
      print(f"Overflow table not specified in the configuration. Exiting", 
            file=sys.stderr)
      sys.exit(1) 

   # check if table exists, create it otherwise
   if not table_exists(cursor, db_config['db_out']['database'], 
                               db_config['backup']['bkp_table']):
      vprint(verb, (f"Overflow table {db_config['backup']['bkp_table']} "
             f"does not exist. Creating now."), 1)
      create_table(cursor, df, db_config['backup']['bkp_table'], list())
      
   # check if overflow table has the same columns with the dataframe
   else:
      df_columns = df.columns
      sql = f"""
          SELECT COLUMN_NAME 
          FROM INFORMATION_SCHEMA.COLUMNS 
          WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
          ORDER BY ORDINAL_POSITION
        """
      cursor.execute(sql, (db_config['db_out']['database'], 
                           db_config['backup']['bkp_table']))

      # Fetch column names
      table_columns = [row["COLUMN_NAME"] for row in cursor.fetchall()]      
      
      if sorted(df_columns) != sorted(table_columns):
         print(f"The overflow table columns: {sorted(table_columns)}",
                file=sys.stderr)
         print(f"{sorted(table_columns)}", file=sys.stderr)
         print(f"are different from the dataframe columns:",
                file=sys.stderr)
         print(f"{sorted(df_columns)}", file=sys.stderr)
         print(f"Exiting.", file=sys.stderr)
         sys.exit(1)
   
   # add the dataframe rows to the backup table
   columns = ", ".join(df.columns)
   placeholders = ", ".join(["%s"] * len(df.columns))
   sql = (f"INSERT INTO {db_config['backup']['bkp_table']} ({columns}) "
                       f"VALUES ({placeholders})")

   # Convert DataFrame rows to tuples and insert them
   cursor.executemany(sql, [tuple(row) for row in df.itertuples(index=False, 
                      name=None)])

   # print the result
   vprint(verb, (f"Overflow of {len(df)} rows "
             f"from table {db_config['db_out']['db_table']} in "
             f"database {db_config['db_out']['database']} was saved to "
             f"table {db_config['backup']['bkp_table']}"), 1)

###################################################################
#










