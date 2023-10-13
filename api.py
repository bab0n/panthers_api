from flask import Blueprint
from flask_restx import fields, Api, Resource, reqparse
from .models import User as TgUser
from .models import db

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
        parser.add_argument('id', type=int, required=True)
        parser.add_argument('lol', type=int)
        args = parser.parse_args()
        print(args)
        user = TgUser.query.get(args['id'])
        if user is None:
            return {'error': 'User not found'}, 400
        t = user.__dict__
        del t['_sa_instance_state']
        return t, 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True)
        parser.add_argument('phone', type=str, required=True)
        parser.add_argument('name', type=str, required=True)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        if user is not None:
            return {'error': 'User already exist'}, 400
        new_user = TgUser(
            id=args['id'],
            state='regged',
            phone=args['phone'],
            promo=None,
            name=args['name'],
            wb_api_def=None,
            wb_api_stat=None,
            wb_api_adv=None,
            autofeedback=False,
            star1=None,
            star2=None,
            star3=None,
            star4=None,
            star5=None,
            balance=0,
            subscribe=0,
            upd_date=None,
        )
        db.session.add(new_user)
        db.session.commit()

    def put(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True)
        parser.add_argument('name', type=str, required=True)
        parser.add_argument('name', type=str, required=True)
        parser.add_argument('name', type=str, required=True)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])

    def delete(self):
        pass
