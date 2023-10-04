from flask import Blueprint
from flask_restx import fields, Api, Resource, reqparse
from .models import User as TgUser

api_blueprint = Blueprint('api', __name__, url_prefix='/api/v1')

api = Api(
    api_blueprint,
    version='1.0',
    title='REST API for patnhers eth bot',
    description='This is rest api for communicate with tg bot Patners',
)

user_model = api.model(
    'User',
    {
        'id': fields.Integer,
        'state': fields.String,
        'phone': fields.String,
        'promo': fields.String,
        'name': fields.String,
        'wb_api_def': fields.String,
        'wb_api_stat': fields.String,
        'wb_api_adv': fields.String,
        'autofeedback': fields.Boolean,
        'star1': fields.String,
        'star2': fields.String,
        'star3': fields.String,
        'star4': fields.String,
        'star5': fields.String,
        'balance': fields.Integer,
        'subscribe': fields.Integer,
        'upd_date': fields.String,
    },
)
ns = api.namespace('user')
api.add_namespace(ns)


@ns.route('/')
class User(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        print(user)
        return {}, 200

    def post(self):
        pass

    def put(self):
        pass

    def delete(self):
        pass
