import datetime
from dataclasses import dataclass, field
from typing import List

from flask import Blueprint, current_app, make_response, render_template

from brigid import mqtt
from brigid.templates import *

bp = Blueprint('control', __name__)

@bp.route('/states', methods=('GET',))
def foo():
    # return "Hello foo"ower_states
    print("THIS IS CURRENT_STATE")
    print(current_app.zones)
    print(current_app.mqtt_state)
    return render_template('states_template.html', mqtt_state=current_app.mqtt_state['topic_states'], zones=current_app.zones, manual_locks = current_app.manual_locks)

# @bp.before_app_request
# def populate_g_state():

#     print(current_app.mqtt_state)

@bp.route('/manual_lock/<tasmota_id>/<state>', methods=('GET',))
def set_manual_lock(tasmota_id, state):
    current_app.manual_locks[tasmota_id] = state
    return '',204

@bp.route('/toggle_power/<tasmota_id>', methods=('GET',))
def power_toggle(tasmota_id):

    mqtt.tasmota_power_toggle(current_app, tasmota_id)

    return '',204

@bp.route('/health', methods=('GET',))
def health_check_endpoint():

    #if mqtt heartbeat is recent
    print(current_app.mqtt_state['mqtt_heartbeat_ts'])
    #if last message wasn't too long ago
    print(current_app.mqtt_state['last_message_ts'])
    #if state machine heartbeat is recent
    print(current_app.mqtt_state['state_machine_heartbeat_ts'])

    current_ts = datetime.datetime.now().timestamp()
    seconds_since_mqtt_heartbeat = current_ts - current_app.mqtt_state['mqtt_heartbeat_ts']
    seconds_since_last_message_ts = current_ts - current_app.mqtt_state['last_message_ts']
    seconds_since_state_machine_heartbeat = current_ts - current_app.mqtt_state['state_machine_heartbeat_ts']

    stats = {'mqtt_heartbeat':current_app.mqtt_state['mqtt_heartbeat_ts'],
     'seconds_since_mqtt_heartbeat': seconds_since_mqtt_heartbeat,
     'last_message_ts':current_app.mqtt_state['last_message_ts'],
     'seconds_since_last_message_ts':seconds_since_last_message_ts,
     'state_machine_heartbeat':current_app.mqtt_state['state_machine_heartbeat_ts'],
     'seconds_since_state_machine_heartbeat':seconds_since_state_machine_heartbeat
    }

    healthy = max([
        seconds_since_mqtt_heartbeat, 
        seconds_since_last_message_ts, 
        seconds_since_state_machine_heartbeat
    ]) < 600

    if healthy:
        return make_response(stats,200,{}) 
    else:
        return make_response(stats,500,{}) 


@bp.route('/set_zone_target_temp/<zone_name>/<target_temp>', methods=('GET',))
def set_target_temp(zone_name: str, target_temp:int):
    print(f"target zone {zone_name} should now be set to {target_temp}")
    current_app.zones[zone_name]['target_temp'] = target_temp

    return '',204

# @bp.route('/buttons',methods=('GET',))
# def mybuttons():
#     return render_template('ctrldiv2.html')
#     # return flask.url_for('static',filename='ctrldiv.html')

# @bp.route('/', methods=('GET',))
# def control_frontend():

#     topic_states = current_app.mqtt_state['topic_states']

#     temp_items = [d[1] for d in topic_states['temp_sensor'].items()]
#     # sort by name so they present in the same order
#     temp_items.sort(key= lambda x: x.friendlyName)
#     print("FULL STATE")
#     print(current_app.mqtt_state)
#     print("TEMP_ITEMS")
#     print(temp_items)

#     return render_template('control_interface.html', mqtt_state=temp_items)

@dataclass
class FillIn():
    power_state: str = field(init=False)
    power_state_bool: bool
    name: str
    zone_name: str
    default_temp: int
    target_temp: int
    power_state_name: str
    current_temp: float
    humidity: float
    last_update: str

    def __post_init__(self):
        self.power_state = 'checked' if self.power_state_bool else ''

def state_to_fillins(app_instance) -> List[FillIn]:

    topic_states = app_instance.mqtt_state['topic_states']
    zones = app_instance.zones

    # build template fill-in object
    fill_in = []
    for zone_name in sorted(zones):

        power_state_name = zones[zone_name]['tasmota_power_bool'][0]
        temp_sensor_name = zones[zone_name]['temp_sensor'][0]

        instance_fillin = FillIn(
            power_state_bool=topic_states['tasmota_power_bool'][power_state_name].state,
            name=zones[zone_name]['name'],
            zone_name=zone_name,
            target_temp=zones[zone_name]['target_temp'],
            default_temp=zones[zone_name]['default_temp'],
            power_state_name = zones[zone_name]['tasmota_power_bool'][0],
            current_temp=topic_states['temp_sensor'][temp_sensor_name].temperature_f,
            humidity=topic_states['temp_sensor'][temp_sensor_name].humidity,
            last_update=str(topic_states['temp_sensor'][temp_sensor_name].last_seen.isoformat())
        )
        fill_in.append(instance_fillin)

    # print(fill_in)
    return fill_in


@bp.route('/', methods=('GET',))
def zone_frontend():

    # fill_in = state_to_fillins(current_app)
    # topic_states = current_app.mqtt_state['topic_states']
    # zones = current_app.zones

    # # build template fill-in object
    # fill_in = []
    # for zone in sorted(zones):

    #     power_state_name = zones[zone]['tasmota_power_bool'][0]

    #     instance_fillin = FillIn(
    #         power_state_bool=topic_states['tasmota_power_bool'][power_state_name].state,
    #         name=zones[zone]['name'],
    #         default_temp=zones[zone]['default_temp'],
    #         power_state_name = zones[zone]['tasmota_power_bool'][0]
    #     )
    #     fill_in.append(instance_fillin)



    return render_template('zones_interface.html', states=state_to_fillins(current_app))

# @bp.route('/power_states', methods=('GET',))
# def power_states_frontend():

#     topic_states = current_app.mqtt_state['topic_states']

#     temp_items = [d[1] for d in topic_states['tasmota_power_bool'].items()]

#     return render_template('foo_template.html',mqtt_state=temp_items)