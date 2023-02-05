#!/bin/bash

# Setting the root path for the customer
ROOT_PATH="ROOT_PATH="/home/user/customers/customer-1/"

# Setting the paths to the required directories based on the root path
LOG_PATH=$ROOT_PATH"logs/"
CSV_PATH=$ROOT_PATH"cfg/.csv.example"
ENV_PATH=$ROOT_PATH"cfg/.env.example"
REP_PATH=$ROOT_PATH"cfg/esxi-report.j2"

# Activating the python venv that contains the netbackup script
source /home/user/python/esxi-getsmart/bin/activate

# Running the netbackup script, while supplying the path variables via CLI arguments
python /home/user/python/esxi-getsmart/main.py -l $LOG_PATH -c $CSV_PATH -e $ENV_PATH -r $REP_PATH
