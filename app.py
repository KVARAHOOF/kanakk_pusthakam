import os
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from config import Config
from models import db, Company, User, Income, Expense
from forms import LoginForm,  IncomeForm, ExpenseForm, RegisterForm, UserForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from io import BytesIO
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.context_processor
def inject_today():
    return {'current_date': datetime.today().strftime('%Y-%m-%d')}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_tables():
    with app.app_context():
        db.create_all()
        # create default company + admin if not exists
        if not Company.query.first():
            c = Company(name="Kanakk Pusthakam", country="Oman", currency="OMR")
            db.session.add(c)
            db.session.commit()
            # create a demo user (password: pass123) - in real use, have register flow
            if not User.query.filter_by(email='admin@example.com').first():
                u = User(email='admin@example.com', phone='0000000000',
                        password=generate_password_hash('pass123'), company_id=c.id)
                db.session.add(u)
                db.session.commit()

@app.route('/')
@login_required
def dashboard():
    comp = current_user.company
    # simple totals for dashboard
    total_income = sum(i.amount for i in comp.incomes)
    total_expense = sum(e.amount for e in comp.expenses)
    balance = comp.opening_balance +  total_income - total_expense
    recent_incomes = Income.query.filter_by(company_id=comp.id).order_by(Income.date.desc()).limit(5).all()
    recent_expenses = Expense.query.filter_by(company_id=comp.id).order_by(Expense.date.desc()).limit(5).all()
    return render_template('dashboard.html', comp=comp, total_income=total_income,
                           total_expense=total_expense, balance=balance,
                           recent_incomes=recent_incomes, recent_expenses=recent_expenses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        val = form.email_or_phone.data.strip()
        pw = form.password.data.strip()
        user = None
        # try email first
        user = User.query.filter_by(email=val).first()
        if not user:
            user = User.query.filter_by(phone=val).first()
        if user and check_password_hash(user.password, pw):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def company_settings():
    # Only admin can change opening balance
    if not current_user.is_admin():
        flash('Only admin can edit settings', 'danger')
        return redirect(url_for('dashboard'))

    company = current_user.company

    if request.method == 'POST':
        name = request.form.get('name')
        country = request.form.get('country')
        currency = request.form.get('currency')
        opening_balance = request.form.get('opening_balance')

        try:
            company.name = name
            company.country = country
            company.currency = currency
            company.opening_balance = float(opening_balance)
            db.session.commit()
            flash('Settings updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating settings: {}'.format(e), 'danger')

    return render_template('settings.html', company=company)

@app.route('/company/users')
@login_required
def company_users():
    comp_id = current_user.company_id
    users = User.query.filter_by(company_id=comp_id).all()
    return render_template('users.html', users=users)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # check duplicate email/phone
        existing = User.query.filter((User.email == form.email.data) | (User.phone == form.phone.data)).first()
        if existing:
            flash('A user with that email or phone already exists. Try logging in.', 'danger')
            return render_template('register.html', form=form)

        # create company
        comp = Company(
            name=form.company_name.data.strip(),
            country=form.country.data or None,
            currency=form.currency.data or None,
            opening_balance=0.0
        )
        db.session.add(comp)
        db.session.flush()  # get comp.id before commit

        # create admin user for this company
        hashed = generate_password_hash(form.password.data)
        user = User(
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            password=hashed,
            company_id=comp.id,
            role='admin'
        )
        db.session.add(user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('Error creating account: {}'.format(str(e)), 'danger')
            return render_template('register.html', form=form)
        flash('Company and admin user created. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/company/users/new', methods=['GET', 'POST'])
@login_required
def company_user_new():
    if request.method == 'POST':
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        role = request.form['role']

        hashed_pw = generate_password_hash(password)

        user = User(email=email, phone=phone, password=hashed_pw, role=role, company_id=current_user.company_id)
        db.session.add(user)
        db.session.commit()

        flash('User added successfully!', 'success')
        return redirect(url_for('company_users'))

    return render_template('user_form.html', title="Add User")


@app.route('/company/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def company_user_edit(user_id):
    user = User.query.get_or_404(user_id)
    if user.company_id != current_user.company_id:
        flash("Access denied!", "danger")
        return redirect(url_for('company_users'))

    if request.method == 'POST':
        user.email = request.form['email']
        user.phone = request.form['phone']
        user.role = request.form['role']
        db.session.commit()

        flash('User updated successfully!', 'success')
        return redirect(url_for('company_users'))

    return render_template('user_form.html', user=user, title="Edit User")



@app.route('/company/users/<int:user_id>/delete')
@login_required
def company_user_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.company_id != current_user.company_id:
        flash("Access denied!", "danger")
        return redirect(url_for('company_users'))

    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('company_users'))


@app.route('/income/new', methods=['GET', 'POST'])
@login_required
def income_new():
    form = IncomeForm()
    if form.validate_on_submit():
        inc = Income(
            title=form.title.data,
            amount=form.amount.data,
            date=form.date.data or datetime.utcnow().date(),
            
            notes=form.notes.data,
            company_id=current_user.company_id
        )
        db.session.add(inc)
        db.session.commit()
        flash('Income saved', 'success')
        return redirect(url_for('dashboard'))
    return render_template('income_form.html', form=form)

@app.route('/expense/new', methods=['GET', 'POST'])
@login_required
def expense_new():
    form = ExpenseForm()
    if form.validate_on_submit():
        exp = Expense(
            title=form.title.data,
            amount=form.amount.data,
            date=form.date.data or datetime.utcnow().date(),
           
            notes=form.notes.data,
            company_id=current_user.company_id
        )
        db.session.add(exp)
        db.session.commit()
        flash('Expense saved', 'success')
        return redirect(url_for('dashboard'))
    return render_template('expense_form.html', form=form)

@app.route('/reports')
@login_required
def reports():
    comp = current_user.company
    # basic report filters from query params
    start = request.args.get('start')
    end = request.args.get('end')
    incomes = Income.query.filter_by(company_id=comp.id)
    expenses = Expense.query.filter_by(company_id=comp.id)
    if start:
        incomes = incomes.filter(Income.date >= start)
        expenses = expenses.filter(Expense.date >= start)
    if end:
        incomes = incomes.filter(Income.date <= end)
        expenses = expenses.filter(Expense.date <= end)
    incomes = incomes.order_by(Income.date.desc()).all()
    expenses = expenses.order_by(Expense.date.desc()).all()
    total_income = sum(i.amount for i in incomes)
    total_expense = sum(e.amount for e in expenses)
    return render_template('reports.html', incomes=incomes, expenses=expenses,
                           total_income=total_income, total_expense=total_expense,
                           comp=comp, start=start, end=end)



@app.route('/reports/pdf')
@login_required
def reports_pdf():
    comp = current_user.company
    start = request.args.get('start')
    end = request.args.get('end')

    incomes = Income.query.filter_by(company_id=comp.id)
    expenses = Expense.query.filter_by(company_id=comp.id)
    if start:
        incomes = incomes.filter(Income.date >= start)
        expenses = expenses.filter(Expense.date >= start)
    if end:
        incomes = incomes.filter(Income.date <= end)
        expenses = expenses.filter(Expense.date <= end)

    incomes = incomes.order_by(Income.date.desc()).all()
    expenses = expenses.order_by(Expense.date.desc()).all()

    total_income = sum(i.amount for i in incomes)
    total_expense = sum(e.amount for e in expenses)
    balance = comp.opening_balance + total_income - total_expense

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=40, bottomMargin=40, leftMargin=40, rightMargin=40)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    title = Paragraph(f"<b>{comp.name}</b>", styles['Title'])
    subtitle = Paragraph(f"Financial Report ({start or 'All'} to {end or 'All'})", styles['Heading2'])
    elements += [title, subtitle, Spacer(1, 12)]

    # Summary
    summary_data = [
        ["Opening Balance", f"{comp.opening_balance:.2f}"],
        ["Total Income", f"{total_income:.2f}"],
        ["Total Expense", f"{total_expense:.2f}"],
        ["Final Balance", f"{balance:.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
    ]))
    elements += [Paragraph("<b>Summary</b>", styles['Heading3']), summary_table, Spacer(1, 20)]

    # Income Table
    elements.append(Paragraph("<b>Income</b>", styles['Heading3']))
    if incomes:
        inc_data = [["Date", "Title", "Amount"]]
        for i in incomes:
            inc_data.append([i.date.strftime("%Y-%m-%d"), i.title, f"{i.amount:.2f}"])
        inc_table = Table(inc_data, colWidths=[1.5 * inch, 3 * inch, 1.5 * inch])
        inc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ]))
        elements.append(inc_table)
    else:
        elements.append(Paragraph("No income records found.", styles['Normal']))
    elements.append(Spacer(1, 15))

    # Expense Table
    elements.append(Paragraph("<b>Expense</b>", styles['Heading3']))
    if expenses:
        exp_data = [["Date", "Title", "Amount"]]
        for e in expenses:
            exp_data.append([e.date.strftime("%Y-%m-%d"), e.title, f"{e.amount:.2f}"])
        exp_table = Table(exp_data, colWidths=[1.5 * inch, 3 * inch, 1.5 * inch])
        exp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.salmon),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ]))
        elements.append(exp_table)
    else:
        elements.append(Paragraph("No expense records found.", styles['Normal']))

    # Footer
    elements.append(Spacer(1, 25))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))

    # Build PDF
    doc.build(elements)

    buffer.seek(0)
    filename = f"report_{comp.name.replace(' ', '_')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=5000, debug=False)