# --------------------------------------------------------------------------------------------
# Techionista Global Sailing Race simulator
#
# This python app simulates the live positions of a fleet of sailing boats racing around
# the globe. The app sends (simulated) boat telemetry to a specified EventHub every 60 seconds.
#
# You must build a working Lambda Architecture in Azure (including an EventHub) and make sure
# the boat telemetry flows through your cloud architecture correctly and appears in PowerBI.
# 
# WHAT YOU NEED TO DO:
# - Fill in the EventHub Namespace connect string and the EventHub name below
# - Run this program on your computer and keep it running
# - Make sure the boat data arrives at your EventHub and flows through the Lambda Architecture
#   into PowerBI
#
# NOTES:
# This app will send the telemetry for every boat in the race. You must ensure that this 
# information appears in PowerBI. At the very least, your dashboard should show the live
# position of each boat on a world map, and a top ranking of all boats in the race.
# For this you will need to build a complete Lambda Architecture with a hot and a cold data
# path. Use the hot path for the live boat positions and the cold path to calculate the 
# ranking. 
#
# Every few minutes one of the boats will send corrupted data to Azure. You will need to build
# a filter in the cloud to automatically filter out corrupted data so that the PowerBI 
# report always shows clean data.
# --------------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------------
# CHANGE THE TWO VARIABLES BELOW BEFORE RUNNING THE APP
# --------------------------------------------------------------------------------------------
NAMESPACE_CONNECTION_STR = 'REPLACE THIS TEXT WITH YOUR EVENTHUB NAMESPACE CONNECTION STRING'
EVENTHUB_NAME = 'REPLACE THIS TEXT WITH YOUR EVENTHUB NAME'


# --------------------------------------------------------------------------------------------
# APP CODE STARTS HERE
# --------------------------------------------------------------------------------------------

import math, random
import time
import json
from azure.eventhub import EventHubProducerClient, EventData
from azure.eventhub.exceptions import EventHubError

# Number of boats in the race
NUMBER_OF_BOATS = 10

# Speed at which simulation runs (1 = realtime, 60 = one hour every minute, 1440 = one day every minute etc)
SIMULATION_SPEED = 1

# A data record for one boat
class BoatData():
    def __init__(self, latitude, longitude, heading, speed):
        self.Latitude = latitude
        self.Longitude = longitude
        self.Heading = heading
        self.Speed = speed

# The data array for the entire fleet
FleetData = []

# Initialize the fleet
def init_fleet():
    for i in range(NUMBER_OF_BOATS):

        # put all boats just outside Cascais, Portugal, heading sout-west at 10 km/h with random spread
        boat = BoatData(
            38.6241832 + random.uniform(-0.01, 0.01) ,
            -9.3925219 + random.uniform(-0.01, 0.01), 
            225 + random.randrange(-20, 20), 
            10 + random.uniform(-5, 5))
        FleetData.append(boat)


# Send the fleet data to the EventHub 
def send_events(producer):
    batch = producer.create_batch()
    for i in range(NUMBER_OF_BOATS):
        boat_data = FleetData[i]

        # introduce random GPS corruption
        latitude = boat_data.Latitude
        longitude = boat_data.Longitude
        if (random.randrange(0, 100) == 0):
            latitude = -10000
            longitude = -10000

        # send the data record
        event_data = EventData(json.dumps({
            "boat": i,
            "latitude": latitude,
            "longitude": longitude,
            "heading": boat_data.Heading,
            "speed": boat_data.Speed
        }))
        event_data.content_type = "application/json"
        batch.add(event_data)

        # report boat info
        print ("Boat:", i, "Lat:", latitude, "Long:", longitude, "Heading:", boat_data.Heading, "Speed:", boat_data.Speed)
    
    producer.send_batch(batch)

    # report boat info
    print ("Boat:", i, "Lat:", latitude, "Long:", longitude, "Heading:", boat_data.Heading, "Speed:", boat_data.Speed)


# Update boat heading and speed
def update_boat(boat):

    # make a small adjustment to heading and speed
    boat.Heading += random.uniform(-5, 5)
    boat.Speed += random.uniform(-1, 1)

    # keep heading and speed within sane range
    if (boat.Heading < 0 or boat.Heading > 360):
        boat.Heading = 0
    if (boat.Speed < 0):
        boat.Speed = 0
    if (boat.Speed > 18):
        boat.Speed = 18

    # force boat to move south-west from Cascais
    if (boat.Latitude > 15 and (boat.Heading < 205 or boat.Heading > 245)):
        boat.Heading = 225

    # force boat to move south-east once it passes latitude 15 to move past Africa and South America
    if (boat.Latitude > -50 and boat.Latitude <= 15 and (boat.Heading < 130 or boat.Heading > 170)):
        boat.Heading = 150

    # once the boat is close to Antarctica, keep heading east towards Australia
    if (boat.Latitude > -64 and boat.Latitude <= -50 and (boat.Heading < 70 or boat.Heading > 110)):
        boat.Heading = 90


# Update the fleet
def update_fleet():
    for i in range(NUMBER_OF_BOATS):
        boat = FleetData[i]

        # adjust course and speed
        update_boat(boat)

        # calculate x and y speed components
        rad = boat.Heading * math.pi / 180
        vx = boat.Speed * math.sin(rad)
        vy = boat.Speed * math.cos(rad)

        # update ship position (rough approximation)
        boat.Longitude += (vx * SIMULATION_SPEED / (60 * 85))
        boat.Latitude += (vy * SIMULATION_SPEED / (60 * 111))


# check if the eventhub namespace connection string has been set
if NAMESPACE_CONNECTION_STR.startswith("REPLACE "):
    print ("The app cannot start because you did not set the NAMESPACE_CONNECTION_STR variable. Please check the race_simulator.py file for further instructions.")
    exit()

# check if the eventhub name has been set
if EVENTHUB_NAME.startswith("REPLACE "):
    print ("The app cannot start because you did not set the EVENTHUB_NAME variable. Please check the race_simulator.py file for further instructions.")
    exit()


# set up an eventhub producer
producer = EventHubProducerClient.from_connection_string(
    conn_str=NAMESPACE_CONNECTION_STR,
    eventhub_name=EVENTHUB_NAME
)

# initialize the fleet
init_fleet()

# send fleet telemetry to EventHub every 60 seconds
while True:
    try:
        send_events(producer)
        time.sleep(60)
        update_fleet()
    except KeyboardInterrupt:
        break

# close producer
producer.close()

