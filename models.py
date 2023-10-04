from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class site_user(db.Model):
    pass


class User(db.Model):
    pass


class Payment(db.Model):
    pass
