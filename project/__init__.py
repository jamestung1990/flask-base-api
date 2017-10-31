# project/__init__.py
import os
import datetime
import logging

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from twilio.rest import Client
from celery import Celery
from flask_cors import CORS
from raven.contrib.flask import Sentry

# instantiate the extesnions
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
mail = Mail()

sentry = None
celery = None
twilio_client = None

def __make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_BACKEND'])
    # celery.app = app
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery



def create_app():
    # instantiate the app
    app = Flask(__name__, template_folder='./templates', static_folder='./static')

    # enable CORS
    CORS(app)

    # set config
    app_settings = os.getenv('APP_SETTINGS')
    app.config.from_object(app_settings)

    # configure sentry
    if not app.debug and not app.testing:
        global sentry
        sentry = Sentry(app, dsn=app.config['SENTRY_DSN'])

    # configure logging
    handler = logging.FileHandler(app.config['LOGGING_LOCATION'])
    handler.setLevel(app.config['LOGGING_LEVEL'])
    handler.setFormatter(logging.Formatter(app.config['LOGGING_FORMAT']))
    app.logger.addHandler(handler)

    # set up extensions
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # register blueprints
    from project.api.v1.auth import auth_blueprint
    from project.api.v1.users import users_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/v1')
    app.register_blueprint(users_blueprint, url_prefix='/v1')


    # register error handlers
    from project.api.common import exceptions
    from project.api.common import error_handlers
    app.register_error_handler(exceptions.InvalidUsage, error_handlers.handle_invalid_usage)
    global celery
    celery = __make_celery(app)
    global twilio_client
    twilio_client = Client(app.config['TWILIO_ACCOUNT_SID'], app.config['TWILIO_AUTH_TOKEN'])
    return app

app = create_app()
