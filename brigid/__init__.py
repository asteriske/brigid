import logging

from brigid import create

app = create.create_app()

gunicorn_logger = logging.getLogger('gunicorn.error')

app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)