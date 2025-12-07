#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-present Rudi Heitbaum (rudi@heitbaum.com)

import random
import configparser

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


def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", reason_code)

    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, client_id)
    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker_host, broker_port)
    return client


def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")

    client.subscribe(broker_topic)
    client.on_message = on_message


def run():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()


if __name__ == '__main__':
    run()
