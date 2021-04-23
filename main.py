import datetime
import mysql.connector
import smtplib, ssl
from mysql.connector import Error
from sense_hat import SenseHat
from time import sleep


# - FUNCTIONS - #

# Create connection to MySQL Server
def create_server_connection(host_name, user_name, user_password, database):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=database,
            auth_plugin='caching_sha2_password'
        )
        print("MySQL Database connection successful")
    except Error as err:
        print(f"Error: '{err}'")

    return connection


# Build query out of passed variables
def build_query(date, time, temp, hum, pre):
    query = "INSERT INTO datalogs (Date_of_Log, Time_of_Log, Temperature, Humidity, Pressure) VALUES ("
    query = query + date + ", " + time + ", " + temp + ", " + hum + ", " + pre + ")"
    return query


# Executes the query that is passed to the function
def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query successful")
    except Error as err:
        print(f"Error: '{err}'")


# - VARIABLES - #

# SenseHAT is initialised and reset
sense = SenseHat()
sense.clear()

# Read sensor limits from config file
try:
    cfgFile = open("sensorConfig.txt", "r");

    firstLine = cfgFile.readline().split();
    tempLimit = float(firstLine[1]);
    secondLine = cfgFile.readline().split();
    pressureLimit = float(secondLine[1]);
    thirdLine = cfgFile.readline().split();
    humidityLimit = float(thirdLine[1]);

    cfgFile.close();
    limitsSet = 1;
except OSError:
    print ("Could not open/read file:", cfgFile)
    limitsSet = 0;
    templimit = 0;
    pressureLimit = 0;
    humidityLimit = 0;

# Email variables
port = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = "lffyptest@gmail.com"
receiver_email = "lffyptest@gmail.com"
password = "LF_fyp_test"
message = ""
context = ssl.create_default_context()

# Database variables
hostname = "192.168.1.128"
username = "raspberry"
pw = "password"
databaseName = "flat_logs"

connection = create_server_connection(hostname, username, pw, databaseName)

# - MAIN LOOP - #
while True:
    # Get temperature, round to 2 decimal places and cast to a string
    temp = float(sense.get_temperature())
    temp = round(temp, 2)
    tempStr = str(temp)

    # Get humidity, round to 2 decimal places and cast to a string
    humidity = float(sense.get_humidity())
    humidity = round(humidity, 2)
    humidityStr = str(humidity)

    # Get pressure, round to 2 decimal places and cast to a string
    pressure = float(sense.get_pressure())
    pressure = round(pressure, 2)
    pressureStr = str(pressure)

    # Get date as string surrounded by '' for use in query
    date = "'" + str(datetime.date.today()) + "'"
    # Get current time, format it and surround with '' for use in query
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M:%S")
    current_time = "'" + current_time + "'"

    # If temperature exceeds hard coded limit of 40 an email is sent
    if temp > tempLimit and limitsSet == 1:
        print("Temp exceeded limit, email sent")
        message = """\
        Subject: Temperature

        Temperature on Raspberry Pi has exceeded a certain limit."""

        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)

    if pressure > pressureLimit and limitsSet == 1:
        print("Pressure exceeded limit, email sent")
        message = """\
        Subject: Pressure

        Pressure on Raspberry Pi has exceeded a certain limit."""

        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)

    if humidity > humidityLimit and limitsSet == 1:
        print("Humidity exceeded limit, email sent")
        message = """\
        Subject: Humidity

        Humidity on Raspberry Pi has exceeded a certain limit."""

        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)

    query = build_query(date, current_time, tempStr, humidityStr, pressureStr)
    execute_query(connection, query)
    print("Sleeping for 10 seconds...")
    sleep(10)
