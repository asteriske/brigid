#!/bin/bash
docker run -e MQTT_BROKER_ADDR='mqtt.lan' \
	   -e MQTT_BROKER_PORT='1883' \
	   -p 4999:4999 \
	   -v $(pwd)/brigid_config.json:/app/config.json \
	   registry.lan:5000/brigid/brigid:v0.93

