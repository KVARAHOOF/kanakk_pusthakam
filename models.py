from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(50))
    currency = db.Column(db.String(10))
    opening_balance = db.Column(db.Float, default=0.0)

    users = db.relationship('User', back_populates='company', lazy=True)
    incomes = db.relationship('Income', back_populates='company', lazy=True)
    expenses = db.relationship('Expense', back_populates='company', lazy=True)


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(32), unique=True, nullable=True)  # you can remove unique=True if you want duplicates
    password = db.Column(db.String(255), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    role = db.Column(db.String(20), default='staff')  # 'admin' or 'staff'

    company = db.relationship('Company', back_populates='users')

    def is_admin(self):
        return self.role == 'admin'



class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date)
    notes = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    company = db.relationship('Company', back_populates='incomes')


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date)
    notes = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    company = db.relationship('Company', back_populates='expenses')