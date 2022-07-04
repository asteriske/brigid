from flask import Flask
from brigid import frontend, mqtt, service
from threading import Thread
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.register_blueprint(frontend.bp)

    app.mqtt_state = {'topic_states':{'temp_sensor':{}}}
    app.zones = service.zones
    app.manual_locks = defaultdict(lambda: "OFF")

    topic_thread = Thread(target=mqtt.poll_topics, args=(app,),daemon=True)
    topic_thread.start()
    app.logger.info('Topic thread started.')

    state_machine_thread = Thread(target=service.state_machine, args=(app,), daemon=True)
    state_machine_thread.start()
    app.logger.info('State machine thread started.')

    return app