from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):  # Пользователь и его настройки
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    state = db.Column(db.Text, nullable=True)
    phone = db.Column(db.Text, nullable=True)
    promo = db.Column(db.Text, nullable=True)
    name = db.Column(db.Text, nullable=True)
    wb_api_def = db.Column(db.Text, nullable=True)
    wb_api_stat = db.Column(db.Text, nullable=True)
    wb_api_adv = db.Column(db.Text, nullable=True)
    autofeedback = db.Column(db.Boolean, nullable=True)
    star1 = db.Column(db.Text, nullable=True)
    star2 = db.Column(db.Text, nullable=True)
    star3 = db.Column(db.Text, nullable=True)
    star4 = db.Column(db.Text, nullable=True)
    star5 = db.Column(db.Text, nullable=True)
    balance = db.Column(db.Integer, nullable=True)
    subscribe = db.Column(db.Integer, nullable=True)
    upd_date = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'User | ID: {self.id} NAME: {self.name}'


class Payment(db.Model):  # Пополнения баланса
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    tg_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.Text, nullable=True)
    payment_id = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Integer, nullable=True)
    link = db.Column(db.Text, nullable=True)
    date = db.Column(db.Text, nullable=True)


class getStatsDays(db.Model):
    date = db.Column(db.Text, primary_key=True)
    key = db.Column(db.Text, nullable=True)
    get_date = db.Column(db.Text, nullable=True)


class Statistic(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    key = db.Column(db.Text, nullable=True)
    date = db.Column(db.Text, nullable=True)
    lastChangeDate = db.Column(db.Text, nullable=True)
    warehouseName = db.Column(db.Text, nullable=True)
    countryName = db.Column(db.Text, nullable=True)
    oblastOkrugName = db.Column(db.Text, nullable=True)
    regionName = db.Column(db.Text, nullable=True)
    supplierArticle = db.Column(db.Text, nullable=True)
    nmId = db.Column(db.Integer, nullable=True)
    barcode = db.Column(db.Text, nullable=True)
    category = db.Column(db.Text, nullable=True)
    subject = db.Column(db.Text, nullable=True)
    brand = db.Column(db.Text, nullable=True)
    techSize = db.Column(db.Text, nullable=True)
    incomeID = db.Column(db.Integer, nullable=True)
    isSupply = db.Column(db.Boolean, nullable=True)
    isRealization = db.Column(db.Boolean, nullable=True)
    totalPrice = db.Column(db.Float, nullable=True)
    discountPercent = db.Column(db.Integer, nullable=True)
    spp = db.Column(db.Float, nullable=True)
    finishedPrice = db.Column(db.Float, nullable=True)
    priceWithDisc = db.Column(db.Integer, nullable=True)
    isCancel = db.Column(db.Boolean, nullable=True)
    cancelDate = db.Column(db.Text, nullable=True)
    orderType = db.Column(db.Text, nullable=True)
    sticker = db.Column(db.Text, nullable=True)
    gNumber = db.Column(db.Text, nullable=True)
    srid = db.Column(db.Text, nullable=True)


class Sales(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    key = db.Column(db.Text, nullable=True)
    date = db.Column(db.Text, nullable=True)
    lastChangeDate = db.Column(db.Text, nullable=True)
    warehouseName = db.Column(db.Text, nullable=True)
    countryName = db.Column(db.Text, nullable=True)
    oblastOkrugName = db.Column(db.Text, nullable=True)
    regionName = db.Column(db.Text, nullable=True)
    supplierArticle = db.Column(db.Text, nullable=True)
    nmId = db.Column(db.Integer, nullable=True)
    barcode = db.Column(db.Text, nullable=True)
    category = db.Column(db.Text, nullable=True)
    subject = db.Column(db.Text, nullable=True)
    brand = db.Column(db.Text, nullable=True)
    techSize = db.Column(db.Text, nullable=True)
    incomeID = db.Column(db.Integer, nullable=True)
    isSupply = db.Column(db.Boolean, nullable=True)
    isRealization = db.Column(db.Boolean, nullable=True)
    totalPrice = db.Column(db.Float, nullable=True)
    discountPercent = db.Column(db.Integer, nullable=True)
    spp = db.Column(db.Float, nullable=True)
    forPay = db.Column(db.Float, nullable=True)
    finishedPrice = db.Column(db.Float, nullable=True)
    priceWithDisc = db.Column(db.Float, nullable=True)
    saleID = db.Column(db.Text, nullable=True)
    orderType = db.Column(db.Text, nullable=True)
    sticker = db.Column(db.Text, nullable=True)
    gNumber = db.Column(db.Text, nullable=True)
    srid = db.Column(db.Text, nullable=True)


class Feedbacks(db.Model):
    nmId = db.Column(db.Integer, primary_key=True)
    valuation = db.Column(db.Text, nullable=True)
    feedbacksCount = db.Column(db.Integer, nullable=True)


class Tarifs(db.Model):
    title = db.Column(db.Text, primary_key=True)
    describe = db.Column(db.Text, nullable=True)
    days = db.Column(db.Integer, nullable=True)
    days_text = db.Column(db.Text, nullable=True)
    price = db.Column(db.Integer, nullable=True)
