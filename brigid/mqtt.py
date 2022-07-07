import datetime
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict

import paho.mqtt.client as mqtt
from flask import current_app

logger = logging.getLogger(__name__)

MQTT_CLIENT_ID = "brigid"
MQTT_BROKER_ADDR = os.environ['MQTT_BROKER_ADDR']
MQTT_BROKER_PORT = int(os.environ['MQTT_BROKER_PORT'])


class NoMatchingTopicException(Exception):
    pass


@dataclass
class AqaraSensor:
    battery: int
    friendlyName: str
    humidity: float
    last_seen: datetime.datetime
    pressure: float
    linkquality: int
    temperature: float
    voltage: int
    value_name: str
    datatype: str = field(init=False)
    temperature_f: float = field(init=False)

    def __post_init__(self):
        self.temperature_f = round((self.temperature * 9 / 5) + 32, 2)
        self.datatype = "temp_sensor"


@dataclass
class TasmotaPower:
    state: bool
    value_name: str
    datatype: str = field(init=False)
    ts: str = field(init=False)

    def __post_init__(self):
        self.datatype = "tasmota_power_bool"
        self.ts = datetime.datetime.now().timestamp()


@dataclass
class TasmotaSensor:
    # https://tasmota.github.io/docs/devices/Sonoff-Pow/
    Time: datetime.datetime
    TotalStartTime: datetime.datetime
    Total: float
    Yesterday: float
    Today: float
    Period: float
    Power: float
    ApparentPower: float
    ReactivePower: float
    Factor: float
    Voltage: float
    Current: float
    value_name: str
    datatype: str = field(init=False)

    def __post_init__(self):
        self.datatype = "power_sensor"


@dataclass
class TasmotaState:
    Time: datetime.datetime
    Uptime: str
    UptimeSec: int
    Heap: int
    SleepMode: str
    Sleep: int
    LoadAvg: int
    MqttCount: int
    POWER: str
    value_name: str
    datatype: str = field(init=False)

    def __post_init__(self):
        self.datatype = "power_state"


def tasmota_power_toggle(app, tasmota_bool_name: str):
    """
    Flip the power state of a tasmota outlet, ignoring previous state.
    """

    topic = f"outlet/cmnd/{tasmota_bool_name}/Power"
    app.mqtt_state["client"].publish(topic=topic, payload="toggle")

    app.logger.debug("Toggling power for Tasmota %s", tasmota_bool_name)

    return "", 204


def set_tasmota_power(
    mqtt_state: Dict[Any, Any], tasmota_bool_name: str, power_state: str, app
):
    """
    Assign a specific power state to a tasmota outlet.
    """

    topic = f"outlet/cmnd/{tasmota_bool_name}/Power"
    mqtt_state["client"].publish(topic=topic, payload=power_state)

    app.logger.info("Setting power state: %s to %s", topic, power_state)
    # print(f"sending {power_state} to {topic}")

    return "", 204


def parse_tasmota_sensor_payload(msg) -> TasmotaSensor:

    parsed_dict = {}
    payload = json.loads(msg.payload)
    _, _, device_name, msg_type = msg.topic.split("/")
    parsed_dict["value_name"] = "_".join([device_name, msg_type])
    parsed_dict["Time"] = datetime.datetime.strptime(
        payload["Time"], "%Y-%m-%dT%H:%M:%S"
    )
    for k in payload["ENERGY"]:
        if k == "TotalStartTime":
            parsed_dict[k] = datetime.datetime.strptime(
                payload["ENERGY"][k], "%Y-%m-%dT%H:%M:%S"
            )
        else:
            parsed_dict[k] = payload["ENERGY"][k]

    return TasmotaSensor(**parsed_dict)


def parse_aqara_payload(msg) -> AqaraSensor:

    payload = json.loads(msg.payload)
    parsed_dict = {}

    for k in payload:
        if k == "device":
            parsed_dict["friendlyName"] = payload["device"]["friendlyName"].split("/")[
                -1
            ]
            parsed_dict["value_name"] = (
                "temp_" + payload["device"]["friendlyName"].split("/")[-1]
            )
        elif k == "last_seen":
            parsed_dict[k] = datetime.datetime.strptime(
                payload[k], "%Y-%m-%dT%H:%M:%S%z"
            )
        else:
            parsed_dict[k] = payload[k]
    return AqaraSensor(**parsed_dict)


def parse_tasmota_stat_payload(msg) -> TasmotaPower:
    _, _, device, _ = msg.topic.split("/")
    state_bool = True if msg.payload == b"ON" else False
    parsed_dict = {"state": state_bool, "value_name": device}

    return TasmotaPower(**parsed_dict)


def parse_tasmota_state_payload(msg) -> TasmotaState:

    payload = json.loads(msg.payload)
    parsed_dict = {}
    _, _, device_name, msg_type = msg.topic.split("/")
    parsed_dict["value_name"] = "_".join([device_name, msg_type])
    for k in payload:
        if k == "Time":
            parsed_dict[k] = datetime.datetime.strptime(payload[k], "%Y-%m-%dT%H:%M:%S")
        elif k != "Wifi":
            parsed_dict[k] = payload[k]
    return TasmotaState(**parsed_dict)


def class_writer(msg):

    tasmota_sensor = r"outlet\/tele\/[a-z_]+\/SENSOR"
    tasmota_stat = r"outlet\/stat\/[a-zA-Z_]+\/POWER"
    tasmota_cmd = r"outlet\/cmnd\/[a-zA-Z_]+\/Power"
    tasmota_state = r"outlet\/tele\/[a-z_]+\/STATE"
    aqara_temp = r"zigbee2mqtt\/sensors\/WSDCGQ11LM\/[a-zA-Z]+"

    if re.match(tasmota_sensor, msg.topic):
        return parse_tasmota_sensor_payload(msg)

    elif re.match(tasmota_state, msg.topic):
        return parse_tasmota_state_payload(msg)

    elif re.match(aqara_temp, msg.topic):
        return parse_aqara_payload(msg)

    elif re.match(tasmota_stat, msg.topic) or re.match(tasmota_cmd, msg.topic):
        # payload is simply a string
        return parse_tasmota_stat_payload(msg)

    return None


def on_message_factory(app) -> Callable:

    mqtt_state = app.mqtt_state

    def on_message_fn(client, userdata, message):

        app.logger.debug("NEW MQTT MESSAGE: TOPIC %s", message.topic)
        try:
            parsed_message = class_writer(message)
            if parsed_message is not None:
                if parsed_message.datatype not in mqtt_state["topic_states"]:
                    mqtt_state["topic_states"][parsed_message.datatype] = {}
                mqtt_state["topic_states"][parsed_message.datatype][
                    parsed_message.value_name
                ] = parsed_message
                mqtt_state["last_message_ts"] = datetime.datetime.now().timestamp()
            else:
                app.logger.debug("MQTT MESSAGE NOT RECOGNIZED")
        except NoMatchingTopicException:
            app.logger.error("MQTT TOPIC NOT HANDLED:, %s", message.topic)
            import traceback

            traceback.print_exc()
            print(message.topic)
            pass

    return on_message_fn


def poll_topics(app):
    """
    Set up the loop which checks the MQTT broker for new messages.
    """

    mqtt_state = app.mqtt_state

    mqtt_state["client"] = mqtt.Client(MQTT_CLIENT_ID, clean_session=True)
    mqtt_state["client"].connect(host=MQTT_BROKER_ADDR, port=MQTT_BROKER_PORT)

    for topic in app.topics:
        mqtt_state["client"].subscribe(topic)

    mqtt_state["client"].on_message = on_message_factory(app)

    mqtt_state["client"].loop_start()

    while True:
        mqtt_state["mqtt_heartbeat"] = datetime.datetime.now()
        mqtt_state["mqtt_heartbeat_ts"] = datetime.datetime.now().timestamp()

        app.logger.debug("MQTT HEARTBEAT %s", mqtt_state["mqtt_heartbeat"])
        time.sleep(5)

    mqtt_state["client"].loop.stop()  # how did you get here?
