# esxi-getsmart
![Supported Versions](https://img.shields.io/badge/python-3.10+-blue) 

The purpose of esxi-getsmart is to retrieve S.M.A.R.T data for NVMe and SATA SSD's and HDD's from ESXi hosts.

### Overview
The overview as given in the script header:
```
###############################################################################
#                                                                             #
# 2023 Jaap de Vos                                                            #
# esxi-getsmart (https://github.com/jwdevos/esxi-getsmart)                    #
#                                                                             #
# The purpose of esxi-getsmart is to retrieve S.M.A.R.T data for              #
#  NVMe and SATA SSD's and HDD's from ESXi hosts.                             #
#  Esxi-getsmart communicates with ESXi hosts via SSH by using                #
#  the Paramiko library.                                                      #
#                                                                             #
# Esxi-getsmart uses CSV and ENV files as input, and sends its output         #
#  as a report via e-mail. Execution details are logged in a log directory.   #
#  The paths needed for the input are configured via CLI arguments.           #
#  Run esxi-getsmart with the -h argument for more information.               #
#                                                                             #
# If esxi-getsmart is of use to you, feel free to take this code and use      #
#  it as you see fit. Please let me know how you like it.                     #
#                                                                             #
###############################################################################
```

### Recommended Usage
The recommended way to use esxi-getsmart is to set up a folder structure something like this:
```
/home/user/customers/customer-1/cfg/
/home/user/customers/customer-1/logs/
/home/user/customers/customer-1/cronlogs/
```
Next, create a python venv:
```
python3 -m venv esxi-getsmart
```
Clone the esxi-getsmart repo, and put `main.py` and `requirements.txt` in the esxi-getsmart venv folder. The assumed path of the esxi-getsmart venv folder in these instructions is `/home/user/python/esxi-getsmart/`. Activate the venv and install the requirements:
```
source bin/activate
pip install -r requirements.txt
```
Next, populate the cfg folder with the CSV file, the ENV file, the report template and the run-script. Set the ROOT_PATH variable in the run-script to correspond with the folder structure that was setup before. Don't forget to make the run-script executable:
```
chmod +x /home/user/customers/customer-1/cfg/esxi-getsmart-run.sh
```
Now, edit CSV file, the ENV file, and the run-script with variables that work for you, then run the run-script to start the backup procedure. You can also adjust the report template if you wish.  
  
The run-script is also compatible with cron jobs without much hassle, mostly thanks to the explicit paths everywhere. As an example, the following crontab entry will run netbackup every Sunday at 01:00. The output of the cron job will be logged:
```
0 1 * * 0 /home/user/customers/customer-1/cfg/esxi-getsmart-run.sh >> /home/user/customers/customer-1/cronlogs/esxi-getsmart-cronlog.txt 2>&1
```

### Additional Information
- ESXi support SSH key authentication. That support has not been built into esxi-getsmart. Be aware that this has security implications. Adding SSH key authentication should be possible with some minor adjustments
- There is a lot of hard-coded logic in esxi-getsmart to get all the required pieces of information, resulting in some code duplication. This approach is not the cleanest solution, but it works
- The SATA SSD support function has not been tested yet, as I don't currently have access to an ESXi host with a SATA SSD. The aim is to test this on short notice

