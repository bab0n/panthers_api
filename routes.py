from flask_restx import Api, Resource, fields
import jwt
from .models import db, Users

rest_api = Api(version="1.0", title="Users API")
