###############################################################################
#                                                                             #
# 2023 Jaap de Vos                                                            #
# esxi-getsmart (https://github.com/jwdevos/esxi-getsmart                     #
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


###############################################################################
# Imports                                                                     #
###############################################################################
import argparse
import csv
import jinja2
import logging
import os
import paramiko
import re
import smtplib
import sys
from datetime import datetime
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pprint import pprint


###############################################################################
# Global variables                                                            #
###############################################################################
# Storing a default username to be used when the ENV file doesn't supply one
default_esxi_user = "root"

# Storing the supported device types to retrieve S.M.A.R.T. data from.
#  This list will be used for input validation later on
drive_types = [
    'NVME',
    'SATA',
    'DISK'
]


###############################################################################
# Main                                                                        #
###############################################################################
def main():
    # Grabbing the current time for later processing
    start_time = datetime.now()
    print("########## Starting netbackup at " + get_date() + "-" + get_time() + " ##########")

    # Reading the arguments that the script needs to run with,
    #  to determine the LOG, BCK, CSV, ENV and REP paths
    args = read_args()
    print("########## Log path: " + args.log + " ##########")
    print("########## CSV path: " + args.csv + " ##########")
    print("########## ENV path: " + args.env + " ##########")
    print("########## REP path: " + args.rep + " ##########")

    # Configuring the logging module
    logfile =  args.log + get_date() + '-esxitools-log.txt'
    logging.basicConfig(level=logging.INFO, filename=logfile, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("########## Starting netbackup at " + get_date() + "-" + get_time() + " ##########")

    # Loading the env vars
    load_dotenv_file(args.env)
    logging.info("########## Loaded ENV file for organization " + os.getenv('ORG') + " ##########")

    # Dictionary that will hold data for each server specified in the input CSV
    servers = {}

    # Reading the input CSV and doing stuff for each entry
    csv_content = load_csv_file(args.csv)
    logging.info("########## Loaded the CSV file ##########")
    logging.info("")
    for row in csv_content:
        logging.info("########## Starting CSV iteration for " + row[0] + " drive " + row[3] + " ##########")

        # Setting esxi_user to the default user, optionally overriding this
        #  depending on the ENV file
        esxi_user = default_esxi_user
        if os.getenv('ESXI_USER') is not esxi_user:
            esxi_user = os.getenv('ESXI_USER')

        # Validating drive type input
        if row[2] not in drive_types:
            logging.info("########## Unsupported drive type ##########")
            print("########## Unsupported drive type ##########")

        # Storing the command status for the ESXi SSH command. If succesful, this gets changed later
        command_status = 'Not OK'

        # Creating a dictionary with S.M.A.R.T. data for this drive
        smart_data = {}
        smart_data['Drive Type'] = row[2]
        smart_data['Drive Name'] = row[3]
        smart_data['Health Status'] = 'OK'

        # Retrieving the S.M.A.R.T. data. The command and properties depend on the drive type
        match row[2]:
            case 'NVME':
                # Setting the NVME command
                command = "esxcli nvme device log smart get -A " + row[3]

                # Running the command and storing the output and command status
                output = esxi_command(row[1], esxi_user, os.getenv('ESXI_PASS'), command)
                command_status = output[1]

                # Parsing the output line by line, stripping, splitting and converting
                #  until all required properties are selected. The properties get stored
                #  in the smart_data dictionary for the specified drive
                for line in output[0]:
                    line = line.strip().split(':')
                    if line[0] == 'NVM Subsystem Reliability Degradation':
                        smart_data[line[0]] = line[1].strip()
                    if line[0] == 'Volatile Memory Backup Device Failure':
                        smart_data[line[0]] = line[1].strip()
                    if line[0] == 'Composite Temperature':
                        temp = int(round(float(line[1].split()[0]) - 273.15))
                        smart_data['Drive Temperature (Celcius)'] = temp
                    if line[0] == 'Available Spare':
                        pct = int(line[1].split('%')[0].strip())
                        smart_data[line[0] + ' (%)'] = pct
                    if line[0] == 'Available Spare Threshold':
                        pct = int(line[1].split('%')[0].strip())
                        smart_data[line[0] + ' (%)'] = pct
                    if line[0] == 'Percentage Used':
                        pct = int(line[1].split('%')[0].strip())
                        smart_data[line[0] + ' (%)'] = pct
                    if line[0] == 'Unsafe Shutdowns':
                        amount = int(line[1].strip()[2:], 16)
                        smart_data[line[0]] = amount
                    if line[0] == 'Media Errors':
                        amount = int(line[1].strip()[2:], 16)
                        smart_data[line[0]] = amount
                    if line[0] == 'Number of Error Info Log Entries':
                        amount = int(line[1].strip()[2:], 16)
                        smart_data[line[0]] = amount
                if smart_data['Available Spare (%)'] <= smart_data['Available Spare Threshold (%)']:
                    smart_data['Health Status'] = 'Not OK'

            case 'SATA':
                # Setting the SATA command
                command = "esxcli storage core device smart get -d " + row[3]

                # Running the command and storing the output and command status
                output = esxi_command(row[1], esxi_user, os.getenv('ESXI_PASS'), command)
                command_status = output[1]

                # Parsing the output line by line, stripping, splitting and converting
                #  until all required properties are selected. The properties get stored
                #  in the smart_data dictionary for the specified drive
                for line in output[0]:
                    if 'Health Status' in line:
                        health_status = line.strip('Health Status').split()[0]
                        smart_data['Health Status'] = health_status
                    if 'Drive Temperature' in line:
                        temp = line.strip('Drive Temperature').split()[3]
                        smart_data['Drive Temperature (Celcius)'] = temp
                    if 'Media Wearout Indicator' in line:
                        count = line.strip('Media Wearout Indicator').split()[3]
                        smart_data['Media Wearout Indicator'] = count
                    if 'Reallocated Sector Count' in line:
                        count = line.strip('Reallocated Sector Count').split()[3]
                        smart_data['Reallocated Sector Count'] = count
                    if 'Write Sectors TOT Count' in line:
                        count = line.strip('Write Sectors TOT Count').split()[3]
                        smart_data['Write Sectors TOT Count'] = count
                    if 'Read Sectors TOT Count' in line:
                        count = line.strip('Read Sectors TOT Count').split()[3]
                        smart_data['Read Sectors TOT Count'] = count
                    if 'Initial Bad Block Count' in line:
                        count = line.strip('Initial Bad Block Count').split()[3]
                        smart_data['Initial Bad Block Count'] = count
                    if 'Program Fail Count' in line:
                        count = line.strip('Program Fail Count').split()[3]
                        smart_data['Program Fail Count'] = count
                    if 'Erase Fail Count' in line:
                        count = line.strip('Erase Fail Count').split()[3]
                        smart_data['Erase Fail Count'] = count
                    if 'Uncorrectable Error Count' in line:
                        count = line.strip('Uncorrectable Error Count').split()[3]
                        smart_data['Uncorrectable Error Count'] = count
                    if 'Pending Sector Reallocation Count' in line:
                        count = line.strip('Pending Sector Reallocation Count').split()[3]
                        smart_data['Pending Sector Reallocation Count'] = count

            case 'DISK':
                # Setting the DISK command
                command = "esxcli storage core device smart get -d " + row[3]

                # Running the command and storing the output and command status
                output = esxi_command(row[1], esxi_user, os.getenv('ESXI_PASS'), command)
                command_status = output[1]

                # Parsing the output line by line, stripping, splitting and converting
                #  until all required properties are selected. The properties get stored
                #  in the smart_data dictionary for the specified drive
                for line in output[0]:
                    if 'Health Status' in line:
                        health_status = line.strip('Health Status').split()[0]
                        smart_data['Health Status'] = health_status
                    if 'Drive Temperature' in line:
                        temp = line.strip('Drive Temperature').split()[3]
                        smart_data['Drive Temperature (Celcius)'] = temp
                    if 'Read Error Count' in line:
                        count = line.strip('Read Error Count').split()[3]
                        smart_data['Read Error Count'] = count
                    if 'Reallocated Sector Count' in line:
                        count = line.strip('Reallocated Sector Count').split()[3]
                        smart_data['Reallocated Sector Count'] = count
                    if 'Sector Reallocation Event Count' in line:
                        count = line.strip('Sector Reallocation Event Count').split()[3]
                        smart_data['Sector Reallocation Event Count'] = count
                    if 'Pending Sector Reallocation Count' in line:
                        count = line.strip('Pending Sector Reallocation Count').split()[3]
                        smart_data['Pending Sector Reallocation Count'] = count
                    if 'Uncorrectable Sector Count' in line:
                        count = line.strip('Uncorrectable Sector Count').split()[3]
                        smart_data['Uncorrectable Sector Count'] = count

        # Creating a key value for the specified server. If this server is not already in the servers
        #  dictionary, it gets added
        server_key = row[0] + ' (' + row[1] + ')'
        if server_key not in servers:
            server = {server_key: []}
            servers[server_key] = []

        # If the SSH command ran successfully, the data for this device gets added to the servers
        #  dictionary under the corresponding server
        if command_status == 'OK':
            servers[server_key].append(smart_data)
        else:
            logging.info("########## Command for " + row[0] + ", drive " + row[3] + " unsuccessful ##########")
            break

        logging.info("########## Command for " + row[0] + ", drive " + row[3] + " successful ##########")

    # Creating a dictionary with the variables that the status report needs
    report_vars = {}
    report_vars['org'] = os.getenv('ORG')
    report_vars['date'] = get_date()
    report_vars['servers'] = servers
    #pprint(report_vars)

    # Rendering the status report
    logging.info("########## Starting with rendering the report ##########")
    report = render_report(report_vars, args.rep)
    #print(report)

    # E-Mail the status report if USE_SMTP is set to 'yes' in the env vars
    if os.getenv('USE_SMTP') == 'yes':
        # Creating a dictionary with the variables that the report mailer needs
        mail_vars = {}
        mail_vars['smtp_host'] = os.getenv('SMTP_HOST')
        mail_vars['smtp_port'] = os.getenv('SMTP_PORT')
        mail_vars['smtp_user'] = os.getenv('SMTP_USER')
        mail_vars['smtp_pass'] = os.getenv('SMTP_PASS')
        mail_vars['from'] = os.getenv('SMTP_FROM')
        mail_vars['to'] = os.getenv('SMTP_TO')
        mail_vars['subject'] = 'ESXI getsmart report for ' + os.getenv('ORG') + ' at ' + get_date()
        mail_vars['body'] = report

        # E-Mailing the status report
        logging.info("########## Sending the report ##########")
        send_mail(mail_vars)

    # Logging the end of the script execution
    logging.info("########## Finished esxitools at " + get_date() + "-" + get_time() + "##########")
    print("########## Finished esxitools at " + get_date() + "-" + get_time() + "##########")

    # Printing the script execution time
    end_time = datetime.now()
    logging.info(f"########## Total execution time: {end_time - start_time} ##########")
    print(f"########## Total execution time: {end_time - start_time} ##########")


###############################################################################
# Functions                                                                   #
###############################################################################
# Function that runs a command on an ESXI host and returns the output
def esxi_command(host, user, password, command):
    try:
        # Start with storing negative command status and and empty output list
        command_status = 'Not OK'
        output = []

        # Setting up the Paramiko SSH client, allowing missing host keys
        #  and initiating te connection
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=password)

        # Running the specified command on the target client, storing the output
        stdin, stdout, stderr = client.exec_command(command)

        # The output will get lost upon closing the connection, so the data
        #  needs to be stored in a new variable
        for line in stdout.readlines():
            output.append(line)

        # If this stage is reached, command status becomes positive, and
        #  the status and output will be returned
        command_status = 'OK'
        return output, command_status

    except Exception as e:
        logging.error(e)
        print(e)

    finally:
        # Making sure the SSH connection to the target client always gets closed
        if client:
            client.close()


# Function that returns a formatted date
def get_date():
    return str(datetime.now().date()).replace('-', '')


# Function that returns a formatted time
def get_time():
    return str(datetime.now().time()).replace(':', '')[:6]


# Function that reads the CLI arguments and returns them as a dictionary
def read_args():
    # Defining variables with help messages to support the CLI argument function
    help_log = "(Required) Provide a log path, like '/home/user/logs/'"
    help_csv = "(Required) Provide a CSV file path, like '/home/user/.csv'"
    help_env = "(Required) Provide a ENV file path, like '/home/user/.env'"
    help_rep = "(Required) Provide a report file path, like '/home/user/report.j2'"

    # Creating the parser object to read and store CLI arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log', help=help_log)
    parser.add_argument('-c', '--csv', help=help_csv)
    parser.add_argument('-e', '--env', help=help_env)
    parser.add_argument('-r', '--rep', help=help_env)
    args = parser.parse_args()

    # Checking if all required arguments are set
    if args.log is None or args.csv is None or args.env is None or args.rep is None:
        e = "Please provide all required arguments. Use '-h' for more information"
        logging.error(e)
        exit(e)

    return args


# Function that reads a CSV file when given a path, and returns the contents
#  as an array without the first (header) line of the CSV
def load_csv_file(csv_path):
    # check if file exists
    if os.path.isfile(csv_path):
        csv_content = []
        with open(csv_path) as csv_file:
            for line in csv.reader(csv_file, delimiter=';'):
                csv_content.append(line)
        csv_content.pop(0)
        return csv_content
    else:
        e = "########## Something wrong with csv_path ##########"
        logging.error(e)
        exit(e)


# Function that reads a .env file when given a path, and makes the
#  variables in the .env file available for use
def load_dotenv_file(env_path):
    # check if file exists
    if os.path.isfile(env_path):
        load_dotenv(env_path)
    else:
        e = "########## Something wrong with env_path ##########"
        logging.error(e)
        exit(e)


# Function that renders the report
def render_report(report_vars, template_path):
    try:
        # Supplying the path to the Jinja2 report input file and reading the file
        report_template_file = template_path
        with open(report_template_file) as f:
            report_template = f.read()

        # Creating a Jinja2 object with the template file
        template = jinja2.Template(report_template)

        # Rendering the report by combining the template with the variables,
        #  then returning the rendered report
        report = template.render(report_vars)
        return report

    except Exception as e:
        logging.error(e)
        print(e)


# Function that e-mails the report
def send_mail(mail_vars):
    try:
        # Creating the e-mail object with HTML Support
        mail = MIMEMultipart('alternative')
        mail['Subject'] = mail_vars['subject']
        mail['From'] = mail_vars['from']
        mail['To'] = mail_vars['to']

        # Creating the body of the message (a plain-text version and an HTML version)
        text = "Please enable HTML e-mail support to view this message."
        html = mail_vars['body']

        # Setting the MIME types of both parts - text/plain and text/html
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        # Attaching parts to the e-mail object
        # The last part of a multipart message (the HTML part) is preferred (RFC 2046)
        mail.attach(part1)
        mail.attach(part2)

        # Sending the e-mail object via SMTP
        mailserver = smtplib.SMTP(mail_vars['smtp_host'], mail_vars['smtp_port'])
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.login(mail_vars['smtp_user'], mail_vars['smtp_pass'])
        mailserver.sendmail(mail_vars['from'], mail_vars['to'], mail.as_string())
        mailserver.quit()

    except Exception as e:
        logging.error(e)
        print(e)


# Making sure main() gets executed when script is called
if __name__ == '__main__':
    main()
