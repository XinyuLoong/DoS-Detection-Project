
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import math
import os
import sys


data_df = pd.read_csv("info_df_initial.csv")

timestamp_column = 'updated'
event_columns = ['scope', 'source', 'field', 'value', 'signature', timestamp_column]
index_column = 'i_Dx'
event_info_column = 'EventInfo'
mask = data_df.duplicated(subset=event_columns, keep=False)
event_dup_df = data_df[mask].copy()

event_dup_df.sort_values(by=event_columns, inplace=True)

dup_rows = len(event_dup_df)
print(f"Rows which appear more than once = {dup_rows}")

unique_combinations = event_dup_df[event_columns].drop_duplicates()
unique_dups = len(unique_combinations)
print(f"Unique values of duplicates = {unique_dups}")
print(f"Excess repeating rows = {dup_rows - unique_dups}")
print(f"Excess repeating 3+ times rows = {dup_rows - 2 * unique_dups}")

zero_info_rows = (data_df[event_info_column] < 1e-10).sum()
print(f"Zero info rows = {zero_info_rows}")

zero_info_df = data_df[data_df[event_info_column] < 1e-10].copy()
if len(zero_info_df) != zero_info_rows:
   print (f"Different results {len(zero_info_df)} and {zero_info_rows} for zero info row count")

event_dup_df.to_csv('duplicate_info_df_initial.csv', index=False)
zero_info_df.to_csv('zero_info_df_initial.csv', index=False)

