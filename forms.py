from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, TextAreaField, DateField, SelectField
from wtforms.validators import DataRequired, Optional, Email
import pycountry

# --- Login Form ---
class LoginForm(FlaskForm):
    email_or_phone = StringField('Email or Phone', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# prepare country and currency choices (simple)
countries = [(c.name, c.name) for c in pycountry.countries]
currencies = [(c.alpha_3, f"{c.alpha_3} - {c.name}") for c in pycountry.currencies]

class RegisterForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired()])
    country = SelectField('Country', choices=countries, validators=[Optional()])
    currency = SelectField('Currency', choices=currencies, validators=[Optional()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Create Account')

class UserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional()])
    password = PasswordField('Password (leave blank to keep existing)', validators=[Optional()])
    role = SelectField('Role', choices=[('admin', 'Admin'), ('staff', 'Staff')], validators=[DataRequired()])
    submit = SubmitField('Save')

# --- Income Form ---
class IncomeForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    date = DateField('Date', validators=[Optional()])
    category = StringField('Category', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save')

# --- Expense Form ---
class ExpenseForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    date = DateField('Date', validators=[Optional()])
    category = StringField('Category', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save')