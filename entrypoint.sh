#! /bin/bash

gunicorn -b 0.0.0.0:4999 --pid=app.pid --log-level=info brigid:app
