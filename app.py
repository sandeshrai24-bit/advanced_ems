import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'advanced_secret_98765')

# Database setup: Render provides DATABASE_URL for Postgres, defaults to SQLite locally
db_url = os.environ.get('DATABASE_URL', 'sqlite:///advanced_ems.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    department = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    salary = db.Column(db.Float, nullable=False)
    
    # Relationships
    leaves = db.relationship('LeaveRequest', backref='employee', cascade="all, delete-orphan", lazy=True)
    schedules = db.relationship('Schedule', backref='employee', cascade="all, delete-orphan", lazy=True)

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False) 
    start_date = db.Column(db.String(10), nullable=False)
    end_date = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Rejected

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    shift_date = db.Column(db.String(10), nullable=False)
    shift_time = db.Column(db.String(50), nullable=False) 

# Create tables within application context
with app.app_context():
    db.create_all()

# --- ROUTES ---

# 1. Dashboard / Employees Directory
@app.route('/')
def index():
    employees = Employee.query.all()
    return render_template('index.html', employees=employees)

@app.route('/add', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        try:
            new_emp = Employee(
                name=request.form['name'],
                email=request.form['email'],
                department=request.form['department'],
                role=request.form['role'],
                salary=float(request.form['salary'])
            )
            db.session.add(new_emp)
            db.session.commit()
            flash('Employee onboarding successful!', 'success')
            return redirect(url_for('index'))
        except Exception:
            db.session.rollback()
            flash('Error onboarding employee. Check if email is unique.', 'danger')
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    emp = Employee.query.get_or_404(id)
    if request.method == 'POST':
        try:
            emp.name = request.form['name']
            emp.email = request.form['email']
            emp.department = request.form['department']
            emp.role = request.form['role']
            emp.salary = float(request.form['salary'])
            db.session.commit()
            flash('Employee records updated!', 'success')
            return redirect(url_for('index'))
        except Exception:
            db.session.rollback()
            flash('Error modifying employee records.', 'danger')
    return render_template('edit.html', emp=emp)

@app.route('/delete/<int:id>')
def delete_employee(id):
    emp = Employee.query.get_or_404(id)
    db.session.delete(emp)
    db.session.commit()
    flash('Employee records completely purged.', 'success')
    return redirect(url_for('index'))

# 2. Payroll System
@app.route('/payroll')
def payroll():
    employees = Employee.query.all()
    payroll_data = []
    for emp in employees:
        monthly_base = emp.salary / 12
        tax_deduction = monthly_base * 0.15 # 15% flat deduction rate
        net_pay = monthly_base - tax_deduction
        payroll_data.append({
            'emp': emp,
            'gross': monthly_base,
            'tax': tax_deduction,
            'net': net_pay
        })
    return render_template('payroll.html', payroll_data=payroll_data)

# 3. Leave Management
@app.route('/leaves', methods=['GET', 'POST'])
def leaves():
    if request.method == 'POST':
        new_leave = LeaveRequest(
            employee_id=int(request.form['employee_id']),
            leave_type=request.form['leave_type'],
            start_date=request.form['start_date'],
            end_date=request.form['end_date']
        )
        db.session.add(new_leave)
        db.session.commit()
        flash('Leave request filed successfully!', 'success')
        return redirect(url_for('leaves'))
        
    leaves_list = LeaveRequest.query.all()
    employees = Employee.query.all()
    return render_template('leaves.html', leaves=leaves_list, employees=employees)

@app.route('/leaves/status/<int:id>/<string:status>')
def update_leave_status(id, status):
    req = LeaveRequest.query.get_or_404(id)
    if status in ['Approved', 'Rejected']:
        req.status = status
        db.session.commit()
        flash(f'Leave application marked as {status}!', 'info')
    return redirect(url_for('leaves'))

# 4. Scheduling
@app.route('/schedules', methods=['GET', 'POST'])
def schedules():
    if request.method == 'POST':
        new_schedule = Schedule(
            employee_id=int(request.form['employee_id']),
            shift_date=request.form['shift_date'],
            shift_time=request.form['shift_time']
        )
        db.session.add(new_schedule)
        db.session.commit()
        flash('Shift rotation timeline committed successfully!', 'success')
        return redirect(url_for('schedules'))
        
    schedules_list = Schedule.query.all()
    employees = Employee.query.all()
    return render_template('schedules.html', schedules=schedules_list, employees=employees)

if __name__ == '__main__':
    app.run(debug=True)