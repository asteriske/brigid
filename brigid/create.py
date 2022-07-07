import json
import logging
from collections import defaultdict
from threading import Thread

from flask import Flask

from brigid import frontend, mqtt, service

logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.register_blueprint(frontend.bp)

    with open('config.json','r') as f:
        config = json.load(f)

    app.mqtt_state = {"topic_states": {"temp_sensor": {}}}
    app.zones = config['zones']
    app.topics = config['topics']
    app.manual_locks = defaultdict(lambda: "OFF")

    topic_thread = Thread(target=mqtt.poll_topics, args=(app,), daemon=True)
    topic_thread.start()
    app.logger.info("Topic thread started.")

    state_machine_thread = Thread(
        target=service.state_machine, args=(app,), daemon=True
    )
    state_machine_thread.start()
    app.logger.info("State machine thread started.")

    return app
