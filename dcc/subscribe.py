#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-present Rudi Heitbaum (rudi@heitbaum.com)

import array
import asyncio
import configparser
import random
import signal
import sys
import time
import threading

from enum import IntEnum

from dcc_ex_py.DCCEX import DCCEX
from dcc_ex_py.Helpers import ActiveState, Direction, Track, TurnoutState
from dcc_ex_py.Sensors import Sensor
from dcc_ex_py.Turnouts import Turnout
from dcc_ex_py.TrainEngines import TrainEngine
from dcc_ex_py.asyncsensor.AsyncSensor import AsyncSensor

from paho.mqtt import client as mqtt_client

config = configparser.ConfigParser()
config.read('config.ini')

# get the configurations for the mqtt broker
broker_host = config['BROKER']['host']
broker_port = int(config['BROKER']['port'])
broker_topic = config['BROKER']['topic']

# get the configurations for the dccex csb-1
dccex_host = config['DCCEX']['host']
dccex_port = int(config['DCCEX']['port'])

# Generate a Client ID with the subscribe prefix.
client_id = f'subscribe-{random.randint(0, 100)}'
# username = 'emqx'
# password = 'public'

#print(f"Database Host: {db_host}")
#print(f"Database Port: {db_port}")
#print(f"Database User: {db_user}")
#print(f"Database Password: {db_password}")

print(f"Broker IP:    {broker_host}")
print(f"Broker Port:  {broker_port}")
print(f"Broker Topic: {broker_topic}")

# Init DCCEX everything
running: bool = True
dccex_command: DCCEX = DCCEX(dccex_host, dccex_port)

points = [
    dccex_command.turnouts.get_turnout(10),
    dccex_command.turnouts.get_turnout(11),
    dccex_command.turnouts.get_turnout(12),
    dccex_command.turnouts.get_turnout(13),
    dccex_command.turnouts.get_turnout(14),
    dccex_command.turnouts.get_turnout(15),
    dccex_command.turnouts.get_turnout(16),
    dccex_command.turnouts.get_turnout(17),
    dccex_command.turnouts.get_turnout(18),
    dccex_command.turnouts.get_turnout(19),
    dccex_command.turnouts.get_turnout(20),
    dccex_command.turnouts.get_turnout(21),
    dccex_command.turnouts.get_turnout(22),
    dccex_command.turnouts.get_turnout(23),
    dccex_command.turnouts.get_turnout(24),
    dccex_command.turnouts.get_turnout(25)
]

# Callback function when the client connects to the MQTT broker
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    if reason_code == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", reason_code)
    client.subscribe(broker_topic) # Subscribe to a topic upon connection

def on_connect_fail(client, userdata):
    print("Connection failed:", userdata)

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    print("Disconnected:", reason_code, userdata)

def on_log(client, userdata, level, buf):
    print("log:", buf)

# Callback function when a message is received
def on_message(client, userdata, msg):
    #print(f"Received message: {msg.topic} - {msg.payload.decode()}")
    #print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
    # Split the topic string into a list of its components
    topic_parts = msg.topic.split('/')
    # Use the match statement to handle different topic structures
    match topic_parts:
        # Match a specific path: "trains/track/turnout"
        case ['trains', 'track', 'turnout', turnout_id]:
            #print(f"Turnout {turnout_id}: {msg.payload.decode()}")
            array_id = int(turnout_id) - 10
            match int(msg.payload.decode()):
                case 0:
                    points[array_id].set_state(TurnoutState.CLOSED)
                case 1:
                    points[array_id].set_state(TurnoutState.THROWN)

# Create an MQTT client instance
client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, client_id)

# Assign callback functions
client.on_connect = on_connect
client.on_connect_fail = on_connect_fail
client.on_message = on_message
client.on_disconnect=on_disconnect
client.on_log = on_log
client.enable_logger()
client.reconnect_delay_set(5, 30)

# Connect to the MQTT broker
ret = client.connect(broker_host, broker_port, 60)
print("Connect Attempt:", ret)

# Start the MQTT loop in a background thread
# This handles network traffic, message processing, and automatic re-connections
client.loop_start()

async def turnout_fix() -> None:
    """Toggles all of the turnouts into the right state"""
    print("Applying turnout check.")
    await asyncio.sleep(0.5)
    points[0].set_state(TurnoutState.THROWN)
    points[1].set_state(TurnoutState.THROWN)
    await asyncio.sleep(1)
    points[0].set_state(TurnoutState.CLOSED)
    points[1].set_state(TurnoutState.CLOSED)
    await asyncio.sleep(1)
    print("Turnout check complete.")

async def manage_tracks() -> None:
    dccex_command.track_power.power_select_track(ActiveState.ON, Track.MAIN)
    print("Track power on.")
    await asyncio.sleep(1)
    async with asyncio.TaskGroup() as tg:
        #task1 = tg.create_task(startup_sequence())
        task2 = tg.create_task(turnout_fix())

if __name__ == '__main__':
    # Main program loop - performs other tasks concurrently
    try:
        asyncio.run(manage_tracks())
        while True:
            #message = "Hello from main thread!"
            #print(f"{message}")
            #client.publish(broker_topic, message) # Publish messages from the main thread
            #print(f"Published: {message}")
            time.sleep(5) # Simulate other work
    except KeyboardInterrupt:
        print("Exiting...")
        client.loop_stop() # Stop the background thread
        client.disconnect()
