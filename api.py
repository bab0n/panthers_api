from flask import Blueprint
from flask_restx import fields, Api, Resource, reqparse
from .models import (
    User as TgUser,
    getStatsDays,
    Statistic,
    Feedbacks,
    Sales,
    Tarifs,
    Daily,
    TarifsBuys,
    Payment,
    Promocode,
)
from .models import db
import datetime
import requests
from requests.adapters import HTTPAdapter
import time
from collections import Counter
import statistics
import hashlib
from . import wb_funcs
from hashlib import sha256
from .config import TERMINAL, TINKOFF_URL, PSS, STEP, NOTIFY_URL
import os
from urllib.parse import quote as url_encode
import json
from pathlib import Path


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
        parser.add_argument(
            'pass',
            type=str,
        )
        parser.add_argument(
            'type',
            type=str,
        )
        args = parser.parse_args()
        if args.get('pass') == 'aezakmi':
            users = [i for i in TgUser.query.all()]
            if args['type'] == 'full':
                res = []
                for i in users:
                    t = i.__dict__
                    del t['_sa_instance_state']
                    res.append(t)
                return {'succes': True, 'users': res}, 200
            else:
                users = [i.id for i in users]
                return {'succes': False, 'users': users}, 200
        user = TgUser.query.get(args['id'])
        if user is None:
            return {'error': 'User not found'}, 400
        t = user.__dict__
        if user.subscribe > 0:
            t['accessLevel'] = Tarifs.query.get(user.tarif).accessLevel
        if user.promo is not None:
            t['discount'] = Promocode.query.get(user.promo).discount
        else:
            t['discount'] = 0
        t['balance'] = round(t['balance'], 0)
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
            balance=500,
            subscribe=0,
            tarif=None,
            upd_date=None,
        )
        new_daily = Daily(
            id=args['id'],
            enable=True,
            time='21:30',
            orders=True,
            sales=True,
            returns=True,
            cancels=True,
            penaltys=True,
            topOrders=True,
            topBuys=True,
        )
        db.session.add(new_daily)
        db.session.add(new_user)
        db.session.commit()
        return {}, 200

    def put(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True)
        parser.add_argument(
            'category', type=str, required=True
        )  # Указывать что именно менется (ключи/шаблоны отзывов и т.п.)
        parser.add_argument(
            'change_values', type=dict, required=True
        )  # Новые знаения в категории
        parser.add_argument(
            'pass',
            type=str,
        )  # Пароль для админ действий
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        if user is not None:
            match args['category'], args['pass']:
                case 'keys', _:
                    user.wb_api_def = args['change_values']['def_key']
                    user.wb_api_stat = args['change_values']['def_key']
                    db.session.commit()
                    return {'succes': True}, 200
                case 'afeeds', _:
                    user.star1 = args['change_values']['star1']
                    user.star2 = args['change_values']['star2']
                    user.star3 = args['change_values']['star3']
                    user.star4 = args['change_values']['star4']
                    user.star5 = args['change_values']['star5']
                    user.autofeedback = args['change_values']['activ']
                    db.session.commit()
                    return {'succes': True}, 200
                case 'status', 'aezakmi':
                    user.state = args['change_values']['status']
                    db.session.commit()
                    return {'succes': True}, 200
                case 'balance', 'aezakmi':
                    user.balance += args['change_values']['balance']
                    db.session.commit()
                    return {'succes': True}, 200
        return {'succes': False}, 400

    def delete(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True)
        parser.add_argument('pass', type=str, required=True)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        if user is None:
            return {'succes': False, 'error': 'Unknown user'}, 400
        else:
            if hashlib.sha256(str(user.id).encode('utf-8')).hexdigest() == args['pass']:
                db.session.delete(user)
                db.session.commit()
                return {'succes': True}, 200
            else:
                return {'succes': False, 'error': 'Incorrect password'}, 400


stats_ns = api.namespace('stats')
api.add_namespace(stats_ns)


@stats_ns.route('/')
class Stats(Resource):
    def checkDates(
        self, startDate: str, endDate: str
    ) -> tuple[bool, datetime.date, datetime.date, str]:
        try:
            sdate = datetime.date.fromisoformat(startDate)
            edate = datetime.date.fromisoformat(endDate)
            if sdate > edate or edate > datetime.date.today():
                return (False, sdate, edate, 'Wrong dates')
            else:
                return (True, sdate, edate, 'ok')
        except Exception:
            return (False, None, None, 'Incorrect one of dates')

    def makePeriod(
        self, startDate: datetime.date, endDate: datetime.date
    ) -> list[datetime.date]:
        period = []
        day_delta = datetime.timedelta(days=1)
        while startDate <= endDate:
            period.append(startDate.isoformat())
            startDate += day_delta
        return period

    def get_orders(
        self, datefrom: str, statisticKey: None, flag: int = 0
    ) -> requests.Response:
        headers = {'Authorization': statisticKey}
        params = {'dateFrom': datefrom, 'flag': flag}
        url = 'https://statistics-api.wildberries.ru/api/v1/supplier/orders'
        r = None
        with requests.Session() as s:
            s.mount(url, HTTPAdapter(max_retries=10))
            r = s.get(url, params=params, headers=headers, timeout=10)
        return r

    def get_buys(
        self, datefrom: str, statisticKey: None, flag: int = 0
    ) -> requests.Response:
        headers = {'Authorization': statisticKey}
        params = {'dateFrom': datefrom, 'flag': flag}
        url = 'https://statistics-api.wildberries.ru/api/v1/supplier/sales'
        r = None
        with requests.Session() as s:
            s.mount(url, HTTPAdapter(max_retries=10))
            r = s.get(url, params=params, headers=headers, timeout=10)
        return r

    def get_feedbacks(
        self,
        nmId: int,
        statisticKey: None,
    ) -> requests.Response:
        headers = {'Authorization': statisticKey}
        params = {'nmId': nmId}
        url = 'https://feedbacks-api.wb.ru/api/v1/feedbacks/products/rating/nmid'
        r = None
        with requests.Session() as s:
            s.mount(url, HTTPAdapter(max_retries=10))
            r = s.get(url, params=params, headers=headers, timeout=10)
        return r

    def getReport(self, dateFrom: str, dateTo: str, apikey: str) -> dict | None:
        url = (
            'https://statistics-api.wildberries.ru/api/v1/supplier/reportDetailByPeriod'
        )
        headers = {'Authorization': apikey}
        params = {'dateFrom': dateFrom, 'dateTo': dateTo}
        r = requests.get(
            url,
            params=params,
            headers=headers,
        )
        match r.status_code:
            case 200:
                res = {}
                for i in r.json():
                    res[i['nm_id']] = (
                        i['delivery_rub'] if i['delivery_rub'] is not None else 0
                    )
                return res
            case 429:
                time.sleep(1)
                return self.getReport(dateFrom, dateTo, apikey)
            case _:
                return None

    def getDeliviryData(
        self, datefrom: int, dateto: int, api_key: str, mode: str = 'value'
    ):
        if datefrom == dateto:
            dateto = datefrom + (60 * 60 * 24)

        def chunks(lst, chunk_size):
            for i in range(0, len(lst), chunk_size):
                yield lst[i : i + chunk_size]

        def getTasks(
            datefrom: int,
            dateto: int,
            api_key: str,
            next: int = 0,
            orderslist: list = [],
        ):
            headers = {'Authorization': api_key}
            params = {
                'dateFrom': datefrom,
                'dateTo': dateto,
                'limit': 1000,
                'next': next,
            }
            url = 'https://suppliers-api.wildberries.ru/api/v3/orders'
            r = requests.get(url, params=params, headers=headers, timeout=10)
            match r.status_code:
                case 200:
                    if mode == 'value':
                        orders = [i['id'] for i in r.json()['orders']]
                    else:
                        orders = [[i['id'], i['price']] for i in r.json()['orders']]
                    if len(orders) == 1000:
                        return getTasks(
                            datefrom,
                            dateto,
                            api_key,
                            r.json()['next'],
                            orders + orderslist,
                        )
                    else:
                        return orderslist + orders
                case 429:
                    time.sleep(1)
                    return getTasks(datefrom, dateto, api_key, next, orderslist)
                case _:
                    return None

        def getTasksStatus(orders: list[int], api_key):
            headers = {'Authorization': api_key}
            params = {"orders": orders}
            url = 'https://suppliers-api.wildberries.ru/api/v3/orders/status'
            r = requests.post(url, json=params, headers=headers, timeout=10)
            match r.status_code:
                case 200:
                    return [
                        i['id']
                        for i in r.json()['orders']
                        if i['supplierStatus'] == 'complete'
                    ]
                case 429:
                    time.sleep(1)
                    return getTasksStatus(orders)
                case _:
                    return None

        ords = getTasks(datefrom, dateto, api_key)
        if mode == 'value':
            count = 0
            for i in list(chunks(ords, 1000)):
                count += len(getTasksStatus(i, api_key))
            return count
        else:
            needet = []
            for i in list(chunks([j[0] for j in ords], 1000)):
                needet += getTasksStatus(i, api_key)
            value = 0
            for i in ords:
                if i[0] in needet:
                    value += i[1] / 100
            return value

    def modifyParser(self, parser):
        parser.add_argument('start_date', type=str, required=True)
        parser.add_argument('end_date', type=str, required=True)
        parser.add_argument('id', type=int, required=True)
        parser.add_argument('daily', type=bool)
        return parser

    def get_shop_rate(self, authkey) -> list:
        headers = {'Authorization': authkey}
        params = {'isAnswered': True, 'take': 5000, 'skip': 0}
        url = 'https://feedbacks-api.wb.ru/api/v1/feedbacks'
        r = requests.get(url, params=params, headers=headers, timeout=10)
        match r.status_code:
            case 200:
                res = r.json()
                t = [i['productValuation'] for i in res['data']['feedbacks']]
                return [round(statistics.mean(t), 1), len(t)]
            case 429:
                time.sleep(1)
                return self.get_shop_rate(authkey)
            case _:
                return None

    def get(self):
        parser = self.modifyParser(reqparse.RequestParser())
        args = parser.parse_args()
        check, sdate, edate, msg = self.checkDates(args['start_date'], args['end_date'])
        if not check:
            return {'succes': False, 'message': msg}
        user = TgUser.query.get(args['id'])
        if user is None or user.wb_api_stat is None:
            return {
                'succes': False,
                'message': 'Incorrect key for statistic',
            }, 400
        if self.get_orders(sdate.isoformat(), user.wb_api_stat).status_code == 401:
            return {
                'succes': False,
                'message': 'Incorrect key for statistic',
            }, 400
        period = self.makePeriod(sdate, edate)
        stats = [
            i
            for i in Statistic.query.filter(
                Statistic.date.in_(period), Statistic.key == user.wb_api_stat
            ).all()
        ]
        sales = [
            i
            for i in Sales.query.filter(
                Sales.date.in_(period), Sales.key == user.wb_api_stat
            ).all()
        ]
        feed = (
            Feedbacks.query.filter(
                Feedbacks.nmId.in_([j.nmId for j in stats]),
                Feedbacks.feedbacksCount > 0,
            )
            .order_by(Feedbacks.valuation)
            .first()
        )
        shopRate = self.get_shop_rate(user.wb_api_def)
        # НАДО БУДЕТ МЕНЯТЬ ПОСЛЕ ОБНОВЫ WB
        f = datetime.date(2023, 11, 1)
        last = datetime.date(2023, 11, 25)
        deliveryPrices = self.getReport(
            f.isoformat(), last.isoformat(), user.wb_api_stat
        )
        cancels = [i for i in stats if i.isCancel or i.orderType != 'Клиентский']
        res = {
            'orders': len([i.finishedPrice for i in stats if not i.isCancel]),
            'buys': len([i for i in sales if i.saleID[0] == 'S']),
            'ordersMoney': round(
                sum([i.finishedPrice for i in stats if not i.isCancel]), 0
            ),
            'buysMoney': round(sum([i.forPay for i in sales if i.saleID[0] == 'S']), 0),
            'buysTop': Counter([i.nmId for i in sales]).most_common(4),
            'shopRate': shopRate[0],
            'needRate': wb_funcs.getNeedetRate(shopRate[0], shopRate[1]),
            'topOrders': Counter([i.nmId for i in stats]).most_common(4),
            'cancels': Counter([i.nmId for i in cancels]).most_common(4),
            'cancelsValue': len(cancels),
            'cancelsMoney': round(sum(
                [i.totalPrice * (1 - (i.discountPercent / 100)) for i in cancels]
            ), 0),
            'returnsCount': len([i for i in stats if i.orderType != 'Клиентский']),
            'returnsSumm': round(sum(
                [
                    i.totalPrice * (1 - (i.discountPercent / 100))
                    for i in stats
                    if i.orderType != 'Клиентский'
                ]
            ), 0),
            'wbPercent': round(
                sum([i.finishedPrice for i in sales if i.saleID[0] == 'S'])
                - sum([i.forPay for i in sales if i.saleID[0] == 'S']),
                0,
            ),
            'worstItem': None,
            'inDelivery': round(
                self.getDeliviryData(
                    int(time.mktime(sdate.timetuple())),
                    int(time.mktime(edate.timetuple())),
                    user.wb_api_stat,
                ),
                0,
            ),
            'inDeliveryMoney': round(
                self.getDeliviryData(
                    int(time.mktime(sdate.timetuple())),
                    int(time.mktime(edate.timetuple())),
                    user.wb_api_stat,
                    mode='money',
                ),
                0,
            ),
            'deliveryCost': round(
                sum([deliveryPrices.get(i.nmId, 0) for i in stats]), 0
            ),
        }
        if feed is not None:
            res['worstItem'] = {'art': feed.nmId, 'val': feed.valuation}
        else:
            res['worstItem'] = {'art': 0, 'val': 0}
        if len(sales) > 0:
            res['buysRate'] = round(
                (len([i for i in sales if i.saleID[0] == 'S']) / len(sales)) * 100, 2
            )
        else:
            res['buysRate'] = 100
        for index, j in enumerate(res['topOrders']):
            statstByNm = round(
                sum(
                    [
                        i.finishedPrice
                        for i in Statistic.query.filter(
                            Statistic.date.in_(period),
                            Statistic.key == user.wb_api_stat,
                            Statistic.nmId == j[0],
                        ).all()
                    ]
                ),
                0,
            )
            res['topOrders'][index] = (j[0], j[1], statstByNm)
        for index, j in enumerate(res['buysTop']):
            statstByNm = round(
                sum(
                    [
                        i.finishedPrice
                        for i in Sales.query.filter(
                            Sales.date.in_(period),
                            Sales.key == user.wb_api_stat,
                            Sales.nmId == j[0],
                        ).all()
                    ]
                ),
                0,
            )
            res['buysTop'][index] = (j[0], j[1], statstByNm)
        for index, j in enumerate(res['cancels']):
            statstByNm = round(
                sum(
                    [
                        g.totalPrice * (1 - (g.discountPercent / 100))
                        for g in cancels if g.nmId == j[0]
                    ]
                ),
                0,
            )
            print(j[0], j[1], statstByNm)
            res['cancels'][index] = (j[0], j[1], statstByNm)
        return {'succes': True, 'data': res}, 200

    def post(self):
        parser = self.modifyParser(reqparse.RequestParser())
        args = parser.parse_args()
        check, sdate, edate, msg = self.checkDates(args['start_date'], args['end_date'])
        if not check:
            return {'succes': False, 'message': msg}
        user = TgUser.query.get(args['id'])
        if user is None or user.wb_api_stat is None:
            return {
                'succes': False,
                'message': 'Incorrect key for statistic',
            }, 400
        takedDates = [
            i for i in getStatsDays.query.filter_by(key=user.wb_api_stat).all()
        ]
        period = self.makePeriod(sdate, edate)
        needGate = []
        tdates = [j.date for j in takedDates]
        for i in period:
            if (
                i not in tdates
                or i in tdates
                and datetime.date.fromisoformat(i)
                >= datetime.date.fromisoformat(
                    [j.get_date for j in takedDates if j.date == i][0]
                )
            ):
                needGate.append(i)
        srids_orders = [
            i.srid for i in Statistic.query.filter_by(key=user.wb_api_stat).all()
        ]
        srids_sales = [
            i.srid for i in Sales.query.filter_by(key=user.wb_api_stat).all()
        ]
        updatedArts = []
        retrys_dates = []
        while len(needGate) != 0:
            r = self.get_orders(needGate[0], user.wb_api_stat, 1)
            match r.status_code:
                case 200:  # успешный запрос
                    if len(r.json()) < 1 and not (needGate[0] in retrys_dates):
                        retrys_dates.append(needGate[0])
                        time.sleep(3)
                        continue
                    for i in r.json():
                        if i['srid'] in srids_orders:
                            continue
                        if i['nmId'] not in updatedArts:
                            updatedArts.append(i['nmId'])
                        newStat = Statistic(
                            key=user.wb_api_stat,
                            date=i['date'][:10],
                            lastChangeDate=i['lastChangeDate'],
                            warehouseName=i['warehouseName'],
                            countryName=i['countryName'],
                            oblastOkrugName=i['oblastOkrugName'],
                            regionName=i['regionName'],
                            supplierArticle=i['supplierArticle'],
                            nmId=i['nmId'],
                            barcode=i['barcode'],
                            category=i['category'],
                            subject=i['subject'],
                            brand=i['brand'],
                            techSize=i['techSize'],
                            incomeID=i['incomeID'],
                            isSupply=i['isSupply'],
                            isRealization=i['isRealization'],
                            totalPrice=i['totalPrice'],
                            discountPercent=i['discountPercent'],
                            spp=i['spp'],
                            finishedPrice=i['finishedPrice'],
                            priceWithDisc=i['priceWithDisc'],
                            isCancel=i['isCancel'],
                            cancelDate=i['cancelDate'],
                            orderType=i['orderType'],
                            sticker=i['sticker'],
                            gNumber=i['gNumber'],
                            srid=i['srid'],
                        )
                        db.session.add(newStat)
                case 401:  # неверный ключ
                    return {
                        'succes': False,
                        'message': 'Incorrect key for statistic',
                    }, 400
                case _:  # любая другая ситуация
                    time.sleep(1)
            t = self.get_buys(needGate[0], user.wb_api_stat, 1)
            match t.status_code:
                case 200:
                    for i in t.json():
                        if i['srid'] in srids_sales:
                            continue
                        if i['nmId'] not in updatedArts:
                            updatedArts.append(i['nmId'])
                        newSale = Sales(
                            key=user.wb_api_stat,
                            date=i['date'][:10],
                            lastChangeDate=i['lastChangeDate'],
                            warehouseName=i['warehouseName'],
                            countryName=i['countryName'],
                            oblastOkrugName=i['oblastOkrugName'],
                            regionName=i['regionName'],
                            supplierArticle=i['supplierArticle'],
                            nmId=i['nmId'],
                            barcode=i['barcode'],
                            category=i['category'],
                            subject=i['subject'],
                            brand=i['brand'],
                            techSize=i['techSize'],
                            incomeID=i['incomeID'],
                            isSupply=i['isSupply'],
                            isRealization=i['isRealization'],
                            totalPrice=i['totalPrice'],
                            discountPercent=i['discountPercent'],
                            spp=i['spp'],
                            forPay=i['forPay'],
                            finishedPrice=i['finishedPrice'],
                            priceWithDisc=i['priceWithDisc'],
                            saleID=i['saleID'],
                            orderType=i['orderType'],
                            sticker=i['sticker'],
                            gNumber=i['gNumber'],
                            srid=i['srid'],
                        )
                        db.session.add(newSale)
                case _:
                    time.sleep(1)
            gettedDate = getStatsDays.query.get(needGate[0])
            if gettedDate is None:
                new_getstat = getStatsDays(
                    key=user.wb_api_stat,
                    get_date=datetime.date.today().isoformat(),
                    date=needGate[0],
                )
                db.session.add(new_getstat)
            else:
                gettedDate.get_date = datetime.date.today().isoformat()
            db.session.commit()
            needGate.pop(0)
        while len(updatedArts) != 0:
            r = self.get_feedbacks(updatedArts[0], statisticKey=user.wb_api_def)
            match r.status_code:
                case 200:
                    feedback = Feedbacks.query.get(updatedArts[0])
                    rRes = r.json()
                    if feedback is None:
                        newFeedback = Feedbacks(
                            nmId=updatedArts[0],
                            valuation=rRes['data']['valuation'],
                            feedbacksCount=rRes['data']['feedbacksCount'],
                        )
                        db.session.add(newFeedback)
                    else:
                        feedback.valuation = rRes['data']['valuation']
                        feedback.feedbacksCount = rRes['data']['feedbacksCount']
                    db.session.commit()
                case 401:
                    return {
                        'succes': False,
                        'message': 'Incorrect key',
                    }, 400
                case _:
                    time.sleep(1)
            updatedArts.pop(0)
        return {'succes': True}, 200

    def put(self):
        return {'succes': True}, 200

    def delete(self):
        return {'succes': True}, 200


subs_ns = api.namespace('subs')
api.add_namespace(subs_ns)


@subs_ns.route('/')
class Subs(Resource):
    def get(self):
        res = {'succes': True, 'subs': []}
        tarifs = [i for i in Tarifs.query.all()]
        for i in tarifs:
            res['subs'].append(
                {
                    'title': i.title,
                    'desc': i.describe,
                    'access': i.access,
                    'days': i.days.split(','),
                    'price': [int(j) for j in i.price.split(',')],
                }
            )
        return res, 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True)
        parser.add_argument('tarif', type=str, required=True)
        parser.add_argument('price', type=str, required=True)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        tarif = Tarifs.query.get(args['tarif'])
        if user is None or tarif is None:
            return {'succes': False, 'error': 'Тариф не найден'}, 400
        price = int(args['price'])
        if price not in [int(i) for i in tarif.price.split(',')]:
            return {'succes': False, 'error': 'Что с ценой?'}, 400
        if user.promo is not None:
            promo = Promocode.query.get(user.promo)
            if promo is not None:
                price -= round(price * (promo.discount / 100), 0)
                user.promo = None
        days = int(tarif.getDaysByPrice(args['price']))
        if tarif.purchases != 0:
            buys = [
                i
                for i in TarifsBuys.query.filter(
                    TarifsBuys.user_id == user.id, TarifsBuys.tarif == tarif.title
                )
            ]
            if len(buys) >= tarif.purchases:
                return {
                    'succes': False,
                    'error': 'Достигнут лимит покупки данного тарифа',
                }, 200
        if price > user.balance:
            return {'succes': False, 'error': 'Недостаточно баланса'}, 200
        user.balance -= price
        user.subscribe += days
        user.upd_date = datetime.datetime.now().isoformat()
        user.tarif = tarif.title
        new_buy = TarifsBuys(
            user_id=user.id,
            tarif=tarif.title,
            date=datetime.date.today().isoformat(),
        )
        db.session.add(new_buy)
        db.session.commit()
        return {'succes': True}, 200

    def put(self):
        parser = reqparse.RequestParser()
        parser.add_argument('pass', type=str, required=True)
        parser.add_argument('title', type=str, required=True)
        parser.add_argument('describe', type=str, required=True)
        parser.add_argument('access', type=str, required=True)
        parser.add_argument('days', type=str, required=True)
        parser.add_argument('price', type=str, required=True)
        parser.add_argument('purchases', type=int, required=True)
        parser.add_argument('accessLevel', type=int, required=True)
        args = parser.parse_args()
        tarifs = [i.title.lower() for i in Tarifs.query.all()]
        if args['title'].lower() in tarifs:
            return {'succes': False, 'error': 'Tarif now available'}, 400
        if args['pass'] == 'aezakmi':
            new_tarif = Tarifs(
                title=args['title'],
                describe=args['describe'],
                access=args['access'],
                days=args['days'],
                price=args['price'],
                purchases=args['purchases'],
                accessLevel=args['accessLevel'],
            )
            db.session.add(new_tarif)
            db.session.commit()
            return {'succes': True}, 200
        else:
            return {'succes': False}, 400

    def delete(self):
        parser = reqparse.RequestParser()
        parser.add_argument('pass', type=str, required=True)
        parser.add_argument('tarif', type=str)
        args = parser.parse_args()
        if args['pass'] == 'aezakmi':
            tarifs = [i for i in Tarifs.query.all()]
            for i in tarifs:
                print(i)
                db.session.delete(i)
            db.session.commit()
            return "Tarifs now clean", 200
        return {}, 404


cards_ns = api.namespace('card_analiz')
api.add_namespace(cards_ns)


@cards_ns.route('/')
class CardAnaliz(Resource):
    def get_info(self, id: int):
        for i in range(1, 20):
            try:
                r = requests.get(
                    f'https://basket-{"0" if i < 10 else ""}{i}.wb.ru/vol{str(id//100000)}/part{str(id//1000)}/{id}/info/ru/card.json'
                )
            except Exception:
                return None
            if r.status_code == 200:
                return r
        return None

    def get_stats(self, nmId):
        r = requests.get(
            f'https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&spp=27&nm={nmId}'
        )
        return r if r.status_code == 200 else None

    # Поиск -> Сводный отчет
    def consolidatedReport(self, ident: int):
        URL = 'https://quickosintapi.com/api/v1/'
        TOKEN = (
            'eyJhbGciOiJodHRwOi8vd3d3LnczLm9yZy8yMDAxLzA0L3htbGRzaWctbW9yZSNobWFjLXNoYTI1NiIsInR5cCI6IkpXVCJ9'
            + '.eyJzdWIiOiI1MDcwOTE2MDM4IiwianRpIjoiNjU5OTllNjc3OTUwYmU0MTY5OGYwNmNjIiwiZXhwIjoyMDIwMTg2OTQ3LCJpc3MiOiJM'
            + 'T0xhcHAiLCJhdWQiOiJMT0xzZWFyc2gifQ._SyyL57u432wNg2o0JhNoT47O8aE-ZnRs2Jqf6jtczg'
        )
        auth = 'Bearer ' + TOKEN
        head = {'Authorization': auth, 'X-ClientId': 'aezakmiBRUH223'}
        r = requests.get(f'{URL}search/agregate/{ident}', headers=head)
        return r

    def getSellerInfo(self, nmId: int) -> dict | None:
        t = self.get_stats(nmId)
        if t is None:
            return None
        t = t.json()
        if not bool(len(t['data']['products'])):
            return None
        response = requests.get(
            f'https://static-basket-01.wbbasket.ru/vol0/data/supplier-by-id/{t["data"]["products"][0]["supplierId"]}.json'
        )
        return response.json() if response.ok else None

    def deepGet(self, dictionary: dict, keys: list) -> dict | None:
        res = None
        for ind, i in enumerate(keys):
            if type(res) is list:
                try:
                    res = res[i]
                    continue
                except Exception:
                    return None
            if ind == 0:
                res = dictionary.get(i, {})
            else:
                res = res.get(i, {})
        return res

    def dataFromNalog(self, inn: str) -> dict:
        url = f'https://egrul.itsoft.ru/{inn}.json'
        return requests.get(url).json()

    def fullnameByArt(self, art: int) -> str | None:
        seller = self.getSellerInfo(art)
        if seller is None or len(seller['inn']) < 1:
            return None
        data = self.dataFromNalog(seller['inn'])
        fields = {}
        if data.get('СвИП', False):
            fields = self.deepGet(data, ['СвИП', 'СвФЛ', 'ФИОРус', '@attributes'])
        else:
            fields = self.deepGet(data, ['СвЮЛ', 'СведДолжнФЛ', 'СвФЛ', '@attributes'])
        if len(fields.keys()) < 1:
            return None
        else:
            return ' '.join(
                [
                    i
                    for i in [
                        fields.get("Фамилия"),
                        fields.get("Имя"),
                        fields.get("Отчество"),
                    ]
                    if i is not None
                ]
            )

    def takeFirst(self, mass):
        return mass[0] if len(mass) > 0 else None

    def checkFIOdata(self, fio: str) -> dict | bool:
        path = Path('fio', f'{sha256(fio.encode()).hexdigest()}.json')
        if not os.path.exists('fio'):
            os.mkdir('fio')
            return None
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                res = json.load(f)['items']
                return self.takeFirst(res)
        else:
            return False

    def saveFIOdata(self, fio: str, data: dict) -> None:
        path = Path('fio', f'{sha256(fio.encode()).hexdigest()}.json')
        with open(path, 'w') as f:
            json.dump(data, f)
        return None

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('nmId', type=int, required=True)
        parser.add_argument('method', type=str, required=True)
        parser.add_argument('keyword', type=str)
        args = parser.parse_args()
        inf = self.get_info(args['nmId'])
        if inf is None:
            return {
                'succes': False,
                'error': 'Не удалось получить информацию о товаре. Убедитесь что ввели корректный артикул или попробуйте повторить позже',
            }, 200
        inf = inf.json()
        stats = self.get_stats(inf['nm_id'])
        if stats is None:
            return {
                'succes': False,
                'error': 'Не удалось получить информацию о товаре. Повторите попытку позже',
            }, 200
        stats = stats.json()
        if len(stats['data']['products']) < 1:
            return {
                'succes': False,
                'error': 'Не удалось получить информацию о товаре. Повторите попытку позже',
            }, 200
        match args['method']:
            case 'feedbacks':
                rev = stats['data']['products'][0]['reviewRating']
                value = stats['data']['products'][0]['feedbacks']
                rate = [rev for _ in range(value)]
                counter = 0
                needet_rate = 4.9
                while statistics.mean(rate) < needet_rate:
                    if len(rate) < 500:
                        rate.append(5)
                        counter += 1
                    elif len(rate) < 1000:
                        rate.extend([5 for _ in range(4)])
                        counter += 4
                    else:
                        rate.extend([5 for _ in range(10)])
                        counter += 10
                return {
                    'succes': True,
                    'count': counter,
                    'name': stats['data']['products'][0]['name'],
                    'current_rate': rev,
                    'current_value': value,
                    'price': stats['data']['products'][0]['salePriceU'] / 100,
                    'brand': stats['data']['products'][0]['brand'],
                }, 200
            case 'card':
                value = []
                for size in stats['data']['products'][0]['sizes']:
                    for stock in size['stocks']:
                        value.append(stock['qty'])
                v = sum(value)
                res = {
                    'name': stats['data']['products'][0]['name'],
                    'brand': stats['data']['products'][0]['brand'],
                    'price': stats['data']['products'][0]['salePriceU'] / 100,
                    'rate': stats['data']['products'][0]['reviewRating'],
                    'seller': stats['data']['products'][0]['supplier'],
                    'value': v,
                    'sklad': v * (stats['data']['products'][0]['salePriceU'] / 100),
                    'SGR': None,
                    'country': None,
                }
                if not inf.get('options') is None:
                    for i in inf['options']:
                        if i['name'] == 'Свидетельство о регистрации СГР':
                            res['SGR'] = i['value']
                        if i['name'] == 'Страна производства':
                            res['country'] = i['value']
                return {
                    'succes': True,
                    'res': res,
                }, 200
            case 'keyword':
                data = {'pos': 0}
                item_id = args['nmId']
                query = args['keyword']
                page = 1
                try:
                    while True:
                        url = f'https://search.wb.ru/exactmatch/ru/common/v4/search?TestGroup=no_test&TestID=no_test&appType=1&curr=rub&dest=-1257786&page={page}&query={query}&resultset=catalog&sort=popular&spp=27&suppressSpellcheck=false'
                        response = requests.get(url=url)
                        products = response.json()
                        products = products["data"]["products"]
                        for ind, i in enumerate(products):
                            if str(item_id) == str(i["id"]):
                                data["pos"] = (ind + 1) + ((page - 1) * len(products))
                                data['page'] = page
                                data['pagePos'] = ind + 1
                                # Вызов ошибки для выхода в exception)))
                                1 / 0
                        page += 1
                except Exception:
                    pass
                data['name'] = stats['data']['products'][0]['name']
                data['brand'] = stats['data']['products'][0]['brand']
                data['price'] = stats['data']['products'][0]['salePriceU'] / 100
                data['rate'] = stats['data']['products'][0]['reviewRating']
                if data["pos"] > 0:
                    return {
                        'succes': True,
                        'pos': data['pos'],
                        'pagePos': data['pagePos'],
                        'pages': data['page'],
                        'data': data,
                    }, 200
                else:
                    return {
                        'succes': False,
                        'error': 'Unfoundet',
                        'pages': page,
                        'data': data,
                    }, 200
            case 'seller':
                seller = self.getSellerInfo(args['nmId'])
                data = self.dataFromNalog(seller['inn'])
                fio = self.fullnameByArt(args['nmId'])
                takedData = self.checkFIOdata(fio)
                if not takedData:
                    print('take new fio')
                    g = self.consolidatedReport(url_encode(f'RU|{fio}'))
                    if g.ok and len(g.json().get('items', [])) > 0:
                        self.saveFIOdata(fio, g.json())
                    else:
                        return {}, 400
                    takedData = self.checkFIOdata(fio)
                res = {
                    'type': 'ИП' if data.get('СвИП', False) else 'ООО',
                    'fio': fio,
                    'selled': None,
                    'site': None,
                    'wbReg': None,
                    'status': None,
                }
                res['ogrn'] = self.deepGet(
                    data,
                    [
                        'СвИП' if res['type'] == 'ИП' else 'СвЮЛ',
                        '@attributes',
                        'ОГРНИП' if res['type'] == 'ИП' else 'ОГРН',
                    ],
                )

                ooo_addr = self.deepGet(data, ['СвЮЛ', 'СвАдресЮЛ', 'АдресРФ'])
                adr = [
                    ooo_addr.get('Регион', {})
                    .get('@attributes', {})
                    .get('НаимРегион', ''),
                    ooo_addr.get('Город', {})
                    .get('@attributes', {})
                    .get('ТипГород', ''),
                    ooo_addr.get('Город', {})
                    .get('@attributes', {})
                    .get('НаимГород', ''),
                    ooo_addr.get('Улица', {})
                    .get('@attributes', {})
                    .get('ТипУлица', ''),
                    ooo_addr.get('Улица', {})
                    .get('@attributes', {})
                    .get('НаимУлица', ''),
                    ooo_addr.get('@attributes', {}).get('Дом', ''),
                    ooo_addr.get('@attributes', {}).get('Кварт', ''),
                ]
                res['addr'] = None if res.get('type') == 'ИП' else ', '.join(adr)
                ooo_email = self.deepGet(
                    data, ['СвИП', 'СвАдрЭлПочты', '@attributes', 'E-mail']
                )
                if isinstance(ooo_email, dict):
                    ooo_email = None
                res['email'] = ooo_email if res.get('type') == 'ИП' else None
                res2 = {
                    'nation': 'РФ',
                    'adres': takedData['adressess'],
                    'number': takedData['phones'],
                    'email': takedData['emails'],
                    'passport': takedData['passpCompiles'],
                    'penalty': [
                        i for i in takedData['namesDatabaseItems'] if 'ИП' in i
                    ],
                    'another': takedData['databaseInfo'] + takedData['infoAddInfo'],
                    'profession': self.takeFirst(takedData['professions']),
                    'password': takedData['passwords'],
                    'names': takedData['snScreenNames'],
                    'bd': self.takeFirst(takedData['borns']),
                    'social': None,
                    'car': takedData['carNs'],
                    'snils': self.takeFirst(takedData['snilses']),
                }
                return {'org': res, 'person': res2}, 200
            case _:
                return {
                    'succes': False,
                    'error': 'Неверно указан метод',
                }, 200


daily_ns = api.namespace('daily')
api.add_namespace(daily_ns)


@daily_ns.route('/')
class UserDaily(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        daily = Daily.query.get(args['id'])
        if user is None or daily is None:
            return {'error': 'User not found'}, 400
        return {
            'succes': True,
            'time': daily.time,
            'enable': daily.enable,
            'orders': daily.orders,
            'sales': daily.sales,
            'returns': daily.returns,
            'cancels': daily.cancels,
            'penaltys': daily.penaltys,
            'topOrders': daily.topOrders,
            'topBuys': daily.topBuys,
        }, 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True)
        parser.add_argument('state', type=dict, required=True)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        daily = Daily.query.get(args['id'])
        if user is None or daily is None:
            return {'error': 'User not found'}, 400
        daily.enable = args['state']['enabled']
        daily.time = args['state']['dailyTime']
        daily.orders = args['state']['orders']
        daily.sales = args['state']['buys']
        daily.returns = args['state']['returns']
        daily.cancels = args['state']['cancels']
        daily.penaltys = args['state']['pennys']
        daily.topOrders = args['state']['topOrders']
        daily.topBuys = args['state']['topBuys']
        db.session.commit()
        return {'succes': True}, 200


payments_ns = api.namespace('payments')
api.add_namespace(payments_ns)


@payments_ns.route('/')
class Payments(Resource):
    def make_token(self, params: dict):
        if params.get('Shops', False):
            params.pop('Shops')
        if params.get('Receipt', False):
            params.pop('Receipt')
        if params.get('DATA', False):
            params.pop('DATA')
        params['Password'] = PSS
        return sha256(
            (''.join(str(i) for _, i in sorted([i for i in params.items()]))).encode(
                'utf-8'
            )
        ).hexdigest()

    def createNewPayment(
        self,
        order_id: int,
        amount: int,
        data: dict = None,
        receipt: dict = None,
    ) -> requests.Response:
        params = {
            'TerminalKey': TERMINAL,
            'Amount': amount,
            'OrderId': order_id,
            'NotificationURL': NOTIFY_URL,
            'SuccessURL': 'https://panthereth.online/profile',
            'FailURL': 'https://panthereth.online/balance',
        }
        if data is not None:
            params['DATA'] = data
        if receipt is not None:
            params['Receipt'] = receipt
        params['Token'] = self.make_token(params)
        r = requests.post(
            TINKOFF_URL + "Init",
            headers={'content-type': 'application/json'},
            json=params,
        )
        return r

    def checkPaymentStatus(self, paymentId: int):
        params = {'TerminalKey': TERMINAL, 'PaymentId': paymentId}
        params['Token'] = self.make_token(params)
        r = requests.post(
            TINKOFF_URL + 'GetState',
            headers={'content-type': 'application/json'},
            json=params,
        )
        return r

    def cancelPayment(self, paymentId: int):
        params = {'TerminalKey': TERMINAL, 'PaymentId': paymentId}
        params['Token'] = self.make_token(params)
        r = requests.post(
            TINKOFF_URL + 'Cancel',
            headers={'content-type': 'application/json'},
            json=params,
        )
        return r

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        if user is None:
            return {'error': 'User not found'}, 400
        res = {'succes': True, 'pays': []}
        for i in [i for i in Payment.query.filter(Payment.tg_id == user.id).all()]:
            classes = {
                'Успешно': 'succes',
                'Ожидание': 'wait',
                'Отказ банка': 'canceled',
            }
            t = {
                'amount': i.amount / 100,
                'status': 'Успешно'
                if i.status == 'CONFIRMED'
                else 'Отказ банка'
                if i.status in ['CANCELED', 'REFOUND']
                else 'Ожидание',
                'date': i.date,
            }
            t['cls'] = classes.get(t['status'], 'wait')
            res['pays'].append(t)
        return res, 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        if user is None:
            return {'error': 'User not found'}, 400
        pays = [
            i
            for i in Payment.query.filter(
                Payment.tg_id == user.id, Payment.status == "NEW"
            ).all()
        ]
        for i in pays:
            r = self.checkPaymentStatus(i.payment_id)
            if r.status_code != 200 or not r.json()['Success']:
                continue
            res = r.json()
            if res['Status'] == 'CONFIRMED':
                user.balance += res['Amount'] / 100
            i.status = res['Status']
            db.session.commit()
        return {}, 200

    def put(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True)
        parser.add_argument('amount', type=int, required=True)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        if user is None:
            return {'error': 'User not found'}, 400
        pays = [i for i in Payment.query.all()]
        t = self.createNewPayment(len(pays) + STEP, args['amount'] * 100)
        r = t.json()
        if t.status_code == 200 and r.get('Success', False):
            new_pay = Payment(
                tg_id=user.id,
                status=r['Status'],
                payment_id=r['PaymentId'],
                amount=r['Amount'],
                link=r['PaymentURL'],
                date=datetime.date.today().strftime('%d.%m.%Y'),
            )
            db.session.add(new_pay)
            db.session.commit()
            return {'url': r['PaymentURL']}, 200
        return {'error': 'Tinkof side error'}, 400


paymentcheck_ns = api.namespace('paycheck')
api.add_namespace(paymentcheck_ns)


@paymentcheck_ns.route('/')
class PayCheck(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('PaymentId', type=int, required=True)
        parser.add_argument('Status', type=str, required=True)
        args = parser.parse_args()
        payment = Payment.query.filter(Payment.payment_id == args['PaymentId']).first()
        if payment is not None:
            if args['Status'] == 'CONFIRMED' and payment.status != 'CONFIRMED':
                user = TgUser.query.get(payment.tg_id)
                if user is not None:
                    user.balance += payment.amount / 100
            payment.status = args['Status']
            db.session.commit()
        return 'OK', 200


promo_ns = api.namespace('promo')
api.add_namespace(promo_ns)


@promo_ns.route('/')
class Promo(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('promo', type=str, required=True)
        parser.add_argument('id', type=int, required=True)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        promo = Promocode.query.get(args['promo'])
        if user is None or promo is None:
            return {'error': 'Промокод не найден'}, 400
        if user.promo == promo.text:
            return {'error': 'Вы уже использовали данный промокод'}, 400
        if promo.activs <= 0:
            return {'error': 'Превышено количество активаций промокода'}, 400
        user.promo = promo.text
        promo.activs -= 1
        db.session.commit()
        return {'succes': True}, 200

    def put(self):
        parser = reqparse.RequestParser()
        parser.add_argument('text', type=str, required=True)
        parser.add_argument('activs', type=int, required=True)
        parser.add_argument('discount', type=int, required=True)
        args = parser.parse_args()
        promo = Promocode.query.get(args['text'])
        if promo is not None:
            return {'error': 'Промокод существует'}, 400
        else:
            new_promo = Promocode(
                text=args['text'], activs=args['activs'], discount=args['discount']
            )
            db.session.add(new_promo)
            db.session.commit()
        return {}, 200
