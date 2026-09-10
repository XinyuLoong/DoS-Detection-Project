csv_file_name = 'table_to_csv.csv'

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

# the output file: output/<csv_file_name>
csv_path = os.path.abspath(os.path.join(TPATH, 
                  dblib.db_config['filesystem']['rel_output_path']))
csv_file = os.path.join(csv_path, csv_file_name)

try:
   # create directory if it doesn't exist
   os.makedirs(csv_path, exist_ok=True)
except OSError as e:
   print((f"Error: Could not create the backup "
          f"directory for {csv_file}: {e}"), file=sys.stderr)
   sys.exit(1)

# MySQL database connection details -> dblib.db_config['db_in']
cnx_args = ['host', 'port', 'user', 'password', 'database']
db_access = {key: dblib.db_config['db_in'][key] \
                  for key in cnx_args if key in dblib.db_config['db_in']}
sql_query = f"SELECT * FROM {dblib.db_config['db_in']['db_table']}"

# MySQL interaction
try:
   # Establish a MySQL connection
   cnx = pymysql.connect(**db_access, cursorclass=pymysql.cursors.DictCursor)
   cursor = cnx.cursor()

   # get the info
   cursor.execute(sql_query)

   # Fetch all rows
   rows = cursor.fetchall()

   # Commit the changes
   cnx.commit()

except pymysql.Error as err:
   print(f"Error: {err}", file=sys.stderr)
   sys.exit(1)
finally:
   if cnx:
      cursor.close()
      cnx.close()

# Save to CSV
dblib.r_df_to_csv(pd.DataFrame(rows), csv_file)

# print the result
print((f"Table {dblib.db_config['db_out']['db_table']} in "
       f"database {dblib.db_config['db_out']['database']} was saved to "
       f"csv file {csv_file}"))


