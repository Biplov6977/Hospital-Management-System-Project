from extensions import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(150), nullable = False)
    email = db.Column(db.String(150),unique = True, nullable = False)
    password = db.Column(db.String(150), nullable = False)
    role = db.Column(db.String(50), nullable = False)
    created_at = db.Column(db.DateTime, default = datetime.utcnow)
    specialization_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable = True)

    doctor_appointments = db.relationship('Appointment', foreign_keys='Appointment.doctor_id', backref='doctor', lazy=True)
    patient_appointments = db.relationship('Appointment', foreign_keys='Appointment.patient_id', backref='patient', lazy=True)

    age = db.Column(db.Integer, nullable = True)
    gender = db.Column(db.String(20), nullable = True)
    contact_number = db.Column(db.String(15), nullable = True)
    address = db.Column(db.String(150), nullable = True)

    active = db.Column(db.Boolean, default = True, nullable = False)

    @property
    def is_active(self):
        return self.active
    
    @is_active.setter
    def is_active(self, value):
        self.active = value

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), unique = True, nullable = False)
    description = db.Column(db.Text, nullable = True)
    doctors = db.relationship('User', backref='department', lazy=True)


class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key = True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    date = db.Column(db.String(30), nullable = False)
    time = db.Column(db.String(30), nullable = False)
    status = db.Column(db.String(50), nullable = False, default = 'Booked')
    created_at = db.Column(db.DateTime, default = datetime.utcnow)
    treatments = db.relationship('Treatment', backref='appointment', lazy=True)

    
class Treatment(db.Model):
    __tablename__ = 'treatments'
    id = db.Column(db.Integer, primary_key = True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable = False)
    diagnosis = db.Column(db.Text, nullable = False)
    prescription = db.Column(db.Text, nullable = False)
    follow_up_date = db.Column(db.String(30), nullable = True)
    notes = db.Column(db.Text, nullable = True)
    created_at = db.Column(db.DateTime, default = datetime.utcnow)

class DoctorAvailability(db.Model):
    __tablename__ = 'doctor_availability'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False) 
    start_time = db.Column(db.String(10), nullable=True)
    end_time = db.Column(db.String(10), nullable=True)
    is_available = db.Column(db.Boolean, default=False, nullable=False)
    doctor = db.relationship('User', backref='availability')


