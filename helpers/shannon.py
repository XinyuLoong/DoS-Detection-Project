#!/usr/bin/python3

import math
from collections import Counter
import pandas as pd
import numpy as np
import argparse
import os

def shannon_column_info(data_list, total_rows):
    # Count occurrences of each entry in the list
    counts = Counter(data_list)
    #print(counts)
    
    # check the number of rows
    if total_rows != len(data_list):
        printf(f"mismatched number of rows")
        exit(1)

    # dictionary of probability of entries
    entry_probability = [ counts[entry] / (total_rows) \
                                        for entry in data_list ]
    #print(entry_probability)    
    
    # entry weight = 1 for the ergodic model
    entry_weight = [ 1 for i in range(total_rows) ]
    
    # entry info = log(p[i])  
    entry_info = [ entry_weight[i] * abs(math.log(entry_probability[i])) \
                                        for i in range(total_rows) ]

    # print entries and weights
    print(f"    f  info")
    for i in range(total_rows):
        print(f"{data_list[i]}:  {counts[data_list[i]]}  {entry_info[i]:.6f}")
    print(f"========")
    
    # Calculate information
    information = sum(entry_info[i] for i in range(total_rows) )    
    return information

def table_info(df, time_column):
    # get the columns
    csv_columns = list(df.columns)

    # remove timestamp if specified
    if time_column in csv_columns:
        csv_columns.remove(time_column)
        print(f"== Using {time_column} as timestamp")
        # reorder by ascending timestamp
        df.sort_values(by=time_column, ascending=True, inplace=True)
        # drop the last 4 rows after reordering
        # df = df[:-4]
        # -or-
        # df = df.drop(df.tail(4).index)
        
    # get the number of rows
    num_rows = df.shape[0]

    # find  entropy and information in the columns
    total_info = 0
    for column in csv_columns:
        data = df[column].tolist()

        # print results for each column
        info = shannon_column_info(data, num_rows)
        total_info += info
        print(f"column   entropy   information")
        print(f"{column}:    {info/num_rows:.4f}      {info:.4f}        {data}")

    # print totals
    print(f"====== Table TOTAL ===========")
    print(f"entropy   information")
    print(f"{total_info/num_rows:.4f}      {total_info:.4f}")

    # return table info
    return total_info

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Table information")
    parser.add_argument('-t', type=str, help='Timestamp column')
    parser.add_argument('-f', type=str, help='Input csv file')
    args = parser.parse_args()

    # process arguments        
    time_column = ""
    if args.t:
        time_column = args.t

    csv_file = "test.csv"
    if args.f:
        csv_file = args.f
        if not os.path.isfile(csv_file):
            print(f"no such file {csv_file}")
            exit(1)
        if not csv_file.lower().endswith('.csv'):
            print(f"not a csv file {csv_file}")
            exit(1)
    print(f"== Input file: {csv_file}")

    # load the csv file
    df = pd.read_csv(csv_file)

    # calculate the total information
    table_info(df, time_column)
    
