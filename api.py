from flask import Blueprint
from flask_restx import fields, Api, Resource, reqparse
from .models import User as TgUser, getStatsDays, Statistic, Feedbacks, Sales, Tarifs
from .models import db
import datetime
import requests
from requests.adapters import HTTPAdapter
import time
from collections import Counter
import statistics


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
        args = parser.parse_args()
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
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        if user is not None:
            match args['category']:
                case 'keys':
                    user.wb_api_def = args['change_values']['def_key']
                    user.wb_api_stat = args['change_values']['stats_key']
                    db.session.commit()
                    return {'succes': True}, 200
                case 'afeeds':
                    user.star1 = args['change_values']['star1']
                    user.star2 = args['change_values']['star2']
                    user.star3 = args['change_values']['star3']
                    user.star4 = args['change_values']['star4']
                    user.star5 = args['change_values']['star5']
                    user.autofeedback = args['change_values']['activ']
                    db.session.commit()
                    return {'succes': True}, 200
        return {}, 400

    def delete(self):
        pass


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

    def modifyParser(self, parser):
        parser.add_argument('start_date', type=str, required=True)
        parser.add_argument('end_date', type=str, required=True)
        parser.add_argument('id', type=int, required=True)
        return parser

    def get_shop_rate(self, authkey):
        headers = {'Authorization': authkey}
        url = 'https://feedbacks-api.wildberries.ru/api/v1/feedbacks/count-unanswered'
        r = requests.get(url, headers=headers).json()
        print(r)
        return r['data']['valuation']

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
            .all()
        )[0]

        res = {
            'orders': len([i.finishedPrice for i in stats if not i.isCancel]),
            'buys': len([i for i in sales if i.saleID[0] == 'S']),
            'ordersMoney': round(
                sum([i.finishedPrice for i in stats if not i.isCancel]), 0
            ),
            'buysMoney': round(sum([i.forPay for i in sales if i.saleID[0] == 'S']), 0),
            'shopRate': self.get_shop_rate(user.wb_api_def),
            'topOrders': Counter([i.nmId for i in stats]).most_common(3),
            'cancels': Counter([i.nmId for i in stats if i.isCancel]).most_common(5),
            'wbPercent': round(
                sum([i.finishedPrice for i in sales if i.saleID[0] == 'S'])
                - sum([i.forPay for i in sales if i.saleID[0] == 'S']),
                0,
            ),
            'worstItem': {'art': feed.nmId, 'val': feed.valuation},
            'buysRate': round(
                (len([i for i in sales if i.saleID[0] == 'S']) / len(sales)) * 100, 2
            ),
        }
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
        for index, j in enumerate(res['cancels']):
            statstByNm = round(
                sum(
                    [
                        i.finishedPrice
                        for i in Statistic.query.filter(
                            Statistic.date.in_(period),
                            Statistic.key == user.wb_api_stat,
                            Statistic.nmId == j[0],
                            Statistic.isCancel,
                        ).all()
                    ]
                ),
                0,
            )
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
            i.srid for i in Statistic.query.filter_by(key=user.wb_api_stat).all()
        ]
        updatedArts = []
        while len(needGate) != 0:
            r = self.get_orders(needGate[0], user.wb_api_stat, 1)
            match r.status_code:
                case 200:  # успешный запрос
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
        tarifs = [i.__dict__ for i in Tarifs.query.all()]
        for i in tarifs:
            del i['_sa_instance_state']
        return {'succes': True, 'subs': tarifs}, 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True)
        parser.add_argument('tarif', type=str, required=True)
        args = parser.parse_args()
        user = TgUser.query.get(args['id'])
        tarif = Tarifs.query.get(args['tarif'])
        if user is None or tarif is None:
            return {'succes': False, 'error': 'User or tarif not found'}, 400
        if tarif.price > user.balance:
            return {'succes': False, 'error': 'Недостаточно баланса'}, 20
        user.balance -= tarif.price
        user.subscribe += tarif.days
        user.upd_date = datetime.datetime.now().isoformat()
        db.session.commit()
        return {'succes': True}, 200


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
                res = {
                    'name': f"{inf['imt_name']} {inf['vendor_code']}",
                    'sub_category': inf['subj_name'],
                    'category': inf['subj_root_name'],
                    'desc': inf['description'],
                    'options': inf['options'],
                    'variations': len(inf['colors']),
                }
                if not inf.get('compositions') is None:
                    res['components'] = inf['compositions']
                return {
                    'succes': True,
                    'res': res,
                }, 200
            case 'keyword':
                data = {}
                item_id = args['nmId']
                query = args['keyword']
                page = 1
                try:
                    while True:
                        url = f'https://search.wb.ru/exactmatch/ru/common/v4/search?TestGroup=sim_goods_rec_infra&TestID=218&appType=1&curr=rub&dest=-1257786&page={page}&query={query}&regions=80,38,83,4,64,33,68,70,30,40,86,75,69,22,1,31,66,110,48,71,114&resultset=catalog&sort=popular&spp=0&suppressSpellcheck=false'
                        response = requests.get(url=url)
                        ids = response.json()
                        ids = ids["data"]["products"]
                        for i in range(len(ids)):
                            if item_id == str(ids[i]["id"]):
                                data["pos"] = i + 1 + (page - 1) * 100
                                break
                        page += 1
                except Exception:
                    try:
                        if data["pos"] > 0:
                            return {
                                'succes': True,
                                'pos': data['pos'],
                                'pages': page,
                            }, 200
                    except Exception:
                        return {
                            'succes': False,
                            'error': 'Unfoundet',
                            'pages': page,
                        }, 200
                return {'succes': True}, 200
            case _:
                return {
                    'succes': False,
                    'error': 'Неверно указан метод',
                }, 200
