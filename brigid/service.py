import datetime
import time
from collections import defaultdict
from enum import IntEnum
from typing import Dict

from brigid import mqtt

class OutletState(IntEnum):
    TOO_COLD = 1
    IN_RANGE = 2
    TOO_HOT = 3


def apply_target_states(directives: Dict, app, state, manual_locks):
    """
    """

    for sensor, sensor_state in directives.items():

        app.logger.debug("DIRECTIVE: set %s to %s", sensor, sensor_state)
        app.logger.debug("DIRECTIVE: min for  %s to %s", sensor, min(sensor_state))

        if manual_locks[sensor] == "OFF":

            if min(sensor_state) == OutletState.TOO_HOT:
                app.logger.info(
                    "PUBLISH: Power on, sensor lock is %s", manual_locks[sensor]
                )
                mqtt.set_tasmota_power(state, sensor, "ON", app)

            elif min(sensor_state) in (OutletState.IN_RANGE, OutletState.TOO_COLD):

                app.logger.info(
                    "PUBLISH: Power off, sensor lock is %s", manual_locks[sensor]
                )
                mqtt.set_tasmota_power(state, sensor, "OFF", app)
        else:
            app.logger.debug("Can't take action, manual lock on")


def state_machine(app):

    state = app.mqtt_state
    zones = app.zones
    manual_locks = app.manual_locks
    while True:

        # Each outlet can only have one state - whatever we decide we have to reconcile
        # into a single, coherent set of instructions.

        # We'll do this by collapsing all sensor readings per outlet into a vector -
        # - if any is too cold, turn off
        # - if all zones between hot and cold, turn off
        # - if any zone is too hot, turn on

        # Too cold dominates too hot.
        try:
            temp_states = state["topic_states"]["temp_sensor"]

        except KeyError:
            app.logger.warning("Key error assigning temp_states in state machine")
            time.sleep(5)
            continue

        if len(temp_states.items()) == 0:
            app.logger.warning(
                "No temp states in state machine - are the topic states populated?"
            )
            time.sleep(5)
            continue

        tasmota_directives = defaultdict(list)

        for zone in zones:

            zone_power_control = zones[zone]["tasmota_power_bool"]
            zone_temp_sensors = zones[zone]["temp_sensor"]
            zone_target_temp = int(zones[zone]["target_temp"])
            zone_floor_temp = int(zones[zone]["floor_temp"])

            zone_temp_readings = []
            try:
                zone_temp_readings += [
                    temp_states[sensor].temperature_f for sensor in zone_temp_sensors
                ]
            except KeyError:
                app.logger.warning("No state observed for zone %s", zone)
                continue

            app.logger.debug(
                "Zone %s: zone_temp_readings: %s", zone, str(zone_temp_readings)
            )
            app.logger.debug("Zone %s: target_temp: %s", zone, str(zone_target_temp))
            if any(
                [temp_reading > zone_target_temp for temp_reading in zone_temp_readings]
            ):
                for outlet in zone_power_control:
                    tasmota_directives[outlet] += [OutletState.TOO_HOT]

            if any(
                [temp_reading < zone_floor_temp for temp_reading in zone_temp_readings]
            ):
                for outlet in zone_power_control:
                    tasmota_directives[outlet] += [OutletState.TOO_COLD]

            if any(
                [
                    (temp_reading >= zone_floor_temp)
                    and (temp_reading <= zone_target_temp)
                    for temp_reading in zone_temp_readings
                ]
            ):
                for outlet in zone_power_control:
                    tasmota_directives[outlet] += [OutletState.IN_RANGE]

        app.logger.info(
            "Zone %s: tasmota directives: %s", zone, str(tasmota_directives)
        )

        apply_target_states(tasmota_directives, app, state, manual_locks)

        state["state_machine_heartbeat_ts"] = datetime.datetime.now().timestamp()

        app.logger.debug(
            "STATE MACHINE HEARTBEAT %s", state["state_machine_heartbeat_ts"]
        )

        time.sleep(5)
