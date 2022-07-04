#! /bin/bash

#. venv/bin/activate && gunicorn -b 0.0.0.0:5000 --pid=app.pid aircon:app
gunicorn -b 0.0.0.0:4999 --pid=app.pid aircon:app
