csv_file_name = 'history_scram-sf.csv'

import pandas as pd
import os
import sys
import pymysql

# get the current path and insert it into python 
TPATH = os.path.dirname(__file__)
sys.path.insert(0, TPATH)

import db_lib as dblib
import db_config as dbc

# read configuration
dbc.read_db_config(1)

# the input file: input/<csv_file_name>
csv_file = os.path.abspath(os.path.join(TPATH, 
                           dblib.db_config['filesystem']['rel_input_path'],
                           csv_file_name))

# Read the CSV file into a pandas DataFrame
df = dblib.r_read_csv(csv_file)

# if any primary keys
primary_keys = []
#primary_keys = ['scope', 'a', 'source', 'field', 'value', 'updated', 'signature']
#primary_keys = ['scope', 'source', 'field', 'value', 'updated', 'signature']
#primary_keys = ['scope', 'source', 'field', 'value', 'signature']

# MySQL database connection details -> dblib.db_config['db_in']
cnx_args = ['host', 'port', 'user', 'password', 'database']
db_access = {key: dblib.db_config['db_in'][key] \
                  for key in cnx_args if key in dblib.db_config['db_in']}

# MySQL interaction
try:
   # Establish a MySQL connection
   cnx = pymysql.connect(**db_access, cursorclass=pymysql.cursors.DictCursor)
   cursor = cnx.cursor()

   # check if table exists
   if dblib.table_exists(cursor, dblib.db_config['db_in']['database'], 
                                 dblib.db_config['db_in']['db_table']):
      print(f"Table {dblib.db_config['db_in']['db_table']} already exists. Exiting",
            file=sys.stderr)
      sys.exit(1)

   # create the table
   dblib.create_table(cursor, df, dblib.db_config['db_in']['db_table'], 
                      primary_keys)

   # Prepare the REPLACE statement
   placeholders = ', '.join(['%s'] * len(df.columns))
   insert_sql = (f"REPLACE INTO {dblib.db_config['db_in']['db_table']} "
                 f"({', '.join(df.columns)}) VALUES ({placeholders})")
   print(f"insert:")
   print(insert_sql)

   # Insert data from the DataFrame into the table
   for row in df.itertuples(index=False):
      cursor.execute(insert_sql, tuple(row))

   # Commit the changes
   cnx.commit()
   print((f"Data from csv file {csv_file} was successfully loaded into the "
          f"database {dblib.db_config['db_in']['database']}, "
          f"table {dblib.db_config['db_in']['db_table']}."))

except pymysql.Error as err:
   print(f"Error: {err}", file=sys.stderr)
   sys.exit(1)
finally:
   if cnx:
      cursor.close()
      cnx.close()

