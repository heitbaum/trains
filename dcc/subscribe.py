#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-present Rudi Heitbaum (rudi@heitbaum.com)

import configparser
import random
import time
import threading

from paho.mqtt import client as mqtt_client

config = configparser.ConfigParser()
config.read('config.ini')

broker_host = config['BROKER']['host']
broker_port = int(config['BROKER']['port'])
broker_topic = config['BROKER']['topic']

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

# Callback function when the client connects to the MQTT broker
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    if reason_code == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", reason_code)
    client.subscribe(broker_topic) # Subscribe to a topic upon connection

# Callback function when a message is received
def on_message(client, userdata, msg):
    print(f"Received message: {msg.topic} - {msg.payload.decode()}")
    print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")

# Create an MQTT client instance
client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, client_id)

# Assign callback functions
client.on_connect = on_connect
client.on_message = on_message

# Connect to the MQTT broker
client.connect(broker_host, broker_port, 60)

# Start the MQTT loop in a background thread
# This handles network traffic, message processing, and automatic re-connections
client.loop_start()

if __name__ == '__main__':
    # Main program loop - performs other tasks concurrently
    try:
        while True:
            message = "Hello from main thread!"
            client.publish(broker_topic, message) # Publish messages from the main thread
            print(f"Published: {message}")
            time.sleep(5) # Simulate other work
    except KeyboardInterrupt:
        print("Exiting...")
        client.loop_stop() # Stop the background thread
        client.disconnect()
