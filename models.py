from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# class site_user(db.Model):  # Пользователь сайта
#     pass


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


# class Order(db.Model):  # Стаитстика -> Заказы
#     pass


class Payment(db.Model):  # Пополнения баланса
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    tg_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.Text, nullable=True)
    payment_id = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Integer, nullable=True)
    link = db.Column(db.Text, nullable=True)
    date = db.Column(db.Text, nullable=True)
