import numpy as np
import datetime
import mysql.connector
import smtplib, ssl
from mysql.connector import Error
from sense_hat import SenseHat
from time import sleep


# - FUNCTIONS - #

def clamp(value, min_value, max_value):
    """
    Returns *value* clamped to the range *min_value* to *max_value* inclusive.
    """
    return min(max_value, max(min_value, value))

def scale(value, from_min, from_max, to_min=0, to_max=8):
    """
    Returns *value*, which is expected to be in the range *from_min* to
    *from_max* inclusive, scaled to the range *to_min* to *to_max* inclusive.
    If *value* is not within the expected range, the result is not guaranteed
    to be in the scaled range.
    """
    from_range = from_max - from_min
    to_range = to_max - to_min
    return (((value - from_min) / from_range) * to_range) + to_min

def render_bar(screen, origin, width, height, color):
    """
    Fills a rectangle within *screen* based at *origin* (an ``(x, y)`` tuple),
    *width* pixels wide and *height* pixels high. The rectangle will be filled
    in *color*.
    """
    # Calculate the coordinates of the boundaries
    x1, y1 = origin
    x2 = x1 + width
    y2 = y1 + height
    # Invert the Y-coords so we're drawing bottom up
    max_y, max_x = screen.shape[:2]
    y1, y2 = max_y - y2, max_y - y1
    # Draw the bar
    screen[int(y1):int(y2), int(x1):int(x2), :] = color

def display_readings(hat):
    """
    Display the temperature, pressure, and humidity readings of the HAT as red,
    green, and blue bars on the screen respectively.
    """
    # Calculate the environment values in screen coordinates
    temperature_range = (0, 40)
    pressure_range = (950, 1050)
    humidity_range = (0, 100)
    temperature = scale(clamp(hat.temperature, *temperature_range), *temperature_range)
    pressure = scale(clamp(hat.pressure, *pressure_range), *pressure_range)
    humidity = scale(clamp(hat.humidity, *humidity_range), *humidity_range)
    # Render the bars
    screen = np.zeros((8, 8, 3), dtype=np.uint8)
    render_bar(screen, (0, 0), 2, round(temperature), color=(255, 0, 0))
    render_bar(screen, (3, 0), 2, round(pressure), color=(0, 255, 0))
    render_bar(screen, (6, 0), 2, round(humidity), color=(0, 0, 255))
    hat.set_pixels([pixel for row in screen for pixel in row])

# Create connection to MySQL Server
def create_server_connection(host_name, user_name, user_password, database):
    connection = None
    while connection == None:
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
            print(err)

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
        print(err)


# - VARIABLES - #

# SenseHAT is initialised and reset
sense = SenseHat()
sense.clear()

# Read sensor limits from config file
try:
    cfgFile = open("/home/pi/fypenvironmentalmonitor/sensorConfig.txt", "r");

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
            
    display_readings(sense)
    query = build_query(date, current_time, tempStr, humidityStr, pressureStr)
    execute_query(connection, query)
    print("Sleeping for 10 seconds...")
    sleep(10)
