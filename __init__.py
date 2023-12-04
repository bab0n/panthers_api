from flask import Flask
from flask_cors import CORS
from . import config
from .models import db


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    db.init_app(app)

    from .api import api_blueprint

    app.register_blueprint(api_blueprint)
    return app
