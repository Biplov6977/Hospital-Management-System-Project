from sqlalchemy.exc import IntegrityError
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import or_, cast, String

#30 mins ko antaral ma time slot banaune
def generate_time_slots(start_str, end_str, interval_minutes = 30):
    slots=[]
    try:
        start_time = datetime.strptime(start_str, '%H:%M').time()
        end_time =  datetime.strptime(end_str, '%H:%M').time()

        current_time = datetime.combine(date.today(), start_time)
        end_dt = datetime.combine(date.today(), end_time)

        while current_time< end_dt:
            slots.append(current_time.strftime('%H:%M'))
            current_time+=timedelta(minutes=interval_minutes)
    except Exception as e:
        print(f"Error occured while generating time slots: {e}")
        return ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"]
    
    return slots

# create app first
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-very-secret-and-random-string'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  
login_manager.login_message_category = 'danger' 

#use hunu agadi import garne
from extensions import db
from models import User, Department, Appointment, Treatment, DoctorAvailability

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



db.init_app(app)

with app.app_context():
    db.create_all()  #creates tables if they don't exist

    #checking if admin already exists
    admin_exists = User.query.filter_by(role='admin').first()
    if not admin_exists:
        admin_user = User(
            name='admin',
            email='admin@hms.gmail.com',
            password=generate_password_hash('admin123'),  #generating hashed password
            role='admin',
            created_at=datetime.utcnow()
        )
        db.session.add(admin_user)
        db.session.commit()
        print("default admin user created with email: admin@hms.gmail.com and password: admin123")
    else:
        print("admin user already exists")




@app.route("/")
def index():
    # redirect root to the registration page to avoid 404 when visiting '/'
    return redirect(url_for('register'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        if current_user.role == "doctor":
            return redirect(url_for("doctor_dashboard"))
        if current_user.role == "patient":
            return redirect(url_for("patient_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()

        if not user or not user.is_active:
            flash("Invalid email or password. Please try again.", "danger")
            return render_template("login.html")


        if not check_password_hash(user.password, password):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template("login.html")

        login_user(user)
        flash("Logged in successfully!", "success")

        if user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif user.role == "doctor":
            return redirect(url_for("doctor_dashboard"))
        else:
            return redirect(url_for("patient_dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    #login vaisakeko huda redirect by role
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        if current_user.role == "doctor":
            return redirect(url_for("doctor_dashboard"))
        if current_user.role == "patient":
            return redirect(url_for("patient_dashboard"))
        
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        age_raw = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip() or None
        contact_number = request.form.get("contact_number", "").strip() or None
        address = request.form.get("address", "").strip() or None

        age = None

        #server tira bata validate garne
        if not name or not email or not password or not confirm:
            flash("Please fill all the required fields.", "danger")
            return render_template("register.html")
        
        if len(password) < 6:
            flash("Password must be atleast 6 characters long.", "danger")
            return render_template("register.html")
        
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")
        
        age = None
        if age_raw:
            try:
                age_val = int(age_raw)
                if age_val>0:
                    age = age_val
                else:
                    flash("Age must be a positive number.", "danger")
                    return render_template("register.html")
            except ValueError:
                flash("Please enter a valid age!","danger")
                return render_template("register.html")

        
        #email ko uniqueness check garna lai
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account already exists with that email, try logging in.", "danger")
            return render_template("register.html")
        
        #ps hash gari patient user banaune
        try:
            hashed = generate_password_hash(password)
            user = User(
                name=name,
                email=email,
                password=hashed,
                role="patient",
                age=age,
                gender=gender,
                contact_number=contact_number,
                address=address,
                active=True
            )
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Now you can login.", "success")
            return redirect(url_for("login"))   
        
        except IntegrityError:
            db.session.rollback()
            flash("An account already exists with that email, try logging in.", "danger")
            return render_template("register.html")
        
        except Exception as e:
            db.session.rollback()
            flash("Unexpected error occured while creating your account, Please try again.", "danger")
            return render_template("register.html")
        
    #GET mas
    return render_template("register.html")


@app.route("/dashboard/admin")
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))

    doctor_search = request.args.get("doctor_search", "").strip()
    patient_search = request.args.get("patient_search", "").strip()

    patient_count = User.query.filter(User.role == 'patient', User.active == True).count()
    doctor_count = User.query.filter(User.role == 'doctor', User.active == True).count()
    appointment_count = Appointment.query.count()

    all_patients_query = User.query.filter_by(role='patient')
    all_doctors_query = User.query.filter_by(role='doctor')

    if patient_search:
        search_term = f"%{patient_search}%"
        all_patients_query = all_patients_query.filter(
            or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
                User.contact_number.ilike(search_term),
                cast(User.id, String).ilike(search_term)
            )
        )
    
    if doctor_search:
        search_term = f"%{doctor_search}%"
        all_doctors_query = all_doctors_query.join(Department, Department.id == User.specialization_id).filter(
            or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
                Department.name.ilike(search_term) 
            )
        )

    all_patients = all_patients_query.order_by(User.name).all()
    all_doctors = all_doctors_query.order_by(User.name).all()
    
    # get departments
    departments = Department.query.all()
    
    # sort(newest first)
    all_appointments = Appointment.query.order_by(Appointment.created_at.desc()).all()
    
    return render_template("admin_dashboard.html", 
                           departments=departments,
                           patient_count=patient_count,
                           doctor_count=doctor_count,
                           appointment_count=appointment_count,
                           all_patients=all_patients,
                           all_doctors=all_doctors,
                           doctor_search=doctor_search,
                           patient_search=patient_search,
                           all_appointments=all_appointments
                           )


@app.route("/admin/edit_doctor/<int:user_id>", methods=["GET"])
@login_required
def edit_doctor_form(user_id):
    """Show the form to edit a doctor's profile."""
    if current_user.role != 'admin':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))
        
    doctor = User.query.filter_by(id=user_id, role='doctor').first_or_404()
    departments = Department.query.all()
    
    return render_template("edit_doctor.html", doctor=doctor, departments=departments)


@app.route("/admin/edit_doctor/<int:user_id>", methods=["POST"])
@login_required
def edit_doctor_submit(user_id):
    if current_user.role != 'admin':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))
    
    doctor = User.query.filter_by(id=user_id, role='doctor').first_or_404()
    
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    specialization_id = request.form.get("specialization_id")

    if not name or not email or not specialization_id:
        flash("Name, Email, and Department are required.", "danger")
        return redirect(url_for('edit_doctor_form', user_id=user_id))

    # check if agadi dekhi vako email ma change hudaixa ki vanera
    if email != doctor.email and User.query.filter_by(email=email).first():
        flash("That email is already in use by another account.", "danger")
        return redirect(url_for('edit_doctor_form', user_id=user_id))
    
    try:
        doctor.name = name
        doctor.email = email
        doctor.specialization_id = int(specialization_id)
        db.session.commit()
        flash(f"Doctor {doctor.name}'s profile has been updated.", "success")
        return redirect(url_for('admin_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while updating: {e}", "danger")
        return redirect(url_for('edit_doctor_form', user_id=user_id))

@app.route("/admin/toggle_active/<int:user_id>", methods = ["POST"])
@login_required
def toggle_active(user_id):
    if current_user.role!='admin':
        flash("Access Unauthorized.", "danger")
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for('login'))
    
    user.is_active = not user.is_active
    db.session.commit()

    if user.is_active:
        flash(f"User {user.name} has been activated.", "success")
    else:
        flash(f"User {user.name} has been deactivated/blacklisted.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/add_department", methods=["POST"])
@login_required
def add_department():
    if current_user.role != 'admin':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip() or None

        if not name:
            flash("Department name is required.", "danger")
            return redirect(url_for('admin_dashboard'))

        existing = Department.query.filter_by(name=name).first()
        if existing:
            flash("A department with this name already exists.", "danger")
            return redirect(url_for('admin_dashboard'))
        
        try:
            new_dept = Department(name=name, description=description)
            db.session.add(new_dept)
            db.session.commit()
            flash(f"Department '{name}' added successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding department: {e}", "danger")
        
        return redirect(url_for('admin_dashboard'))


@app.route("/admin/add_doctor", methods=["POST"])
@login_required
def add_doctor():
    # Only admin can add doctors
    if current_user.role != 'admin':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        
        try:
            specialization_id = int(request.form.get("specialization_id"))
        except (ValueError, TypeError):
            flash("Please select a valid department.", "danger")
            return redirect(url_for('admin_dashboard'))

        if not name or not email or not password or not specialization_id:
            flash("All fields are required.", "danger")
            return redirect(url_for('admin_dashboard'))
        
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return redirect(url_for('admin_dashboard'))
        
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account already exists with that email.", "danger")
            return redirect(url_for('admin_dashboard'))
        
    #doctor banauna lai
        try:
            hashed = generate_password_hash(password)
            new_doctor = User(
                name=name,
                email=email,
                password=hashed,
                role="doctor",
                specialization_id=specialization_id
            )
            db.session.add(new_doctor)
            db.session.commit()
            flash(f"Doctor {name} added successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding doctor: {e}", "danger")
        
        return redirect(url_for('admin_dashboard'))


@app.route("/dashboard/doctor")
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))
    
    today = date.today().strftime("%Y-%m-%d")

    all_appointments = Appointment.query.filter_by(doctor_id = current_user.id).all()

    upcoming_appointments = []
    past_appointments = []

    for apt in all_appointments:
        if apt.status=="Booked" and apt.date>=today:
            upcoming_appointments.append(apt)
        else:
            past_appointments.append(apt)
    
    upcoming_appointments.sort(key= lambda x: (x.date, x.time))
    past_appointments.sort(key= lambda x:(x.date, x.time), reverse=True)

    availability_schedule = []
    start_date = date.today()
    
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        day_name = current_date.strftime('%A')

        avail = DoctorAvailability.query.filter_by(
            doctor_id=current_user.id,
            date=date_str
            ).first()
        
        if not avail:
            avail = DoctorAvailability(
                doctor_id=current_user.id,
                date=date_str)
            db.session.add(avail)
        
        if not avail.start_time:
            avail.start_time = "09:00"
        if not avail.end_time:
            avail.end_time = "17:00"
        if not avail.is_available:
            avail.is_available = False

        availability_schedule.append({
            'day_name': day_name,
            'avail_record': avail
        })
    
    db.session.commit()


    return render_template("doctor_dashboard.html",
                           upcoming_appointments = upcoming_appointments,
                           past_appointments = past_appointments,
                           availability_schedule = availability_schedule) 


@app.route("/dashboard/patient")
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))
    
    search_query = request.args.get("search_query", "").strip()
    doctor_query = User.query.filter_by(role = "doctor", active = True)

    if search_query:
        search_term = f"%{search_query}%"
        doctor_query = doctor_query.join(Department, User.specialization_id == Department.id).filter(
            or_(
                User.name.ilike(search_term),
                Department.name.like(search_term)
            )
        )
    
    doctors = doctor_query.order_by(User.name).all()

    today_str = date.today().strftime("%Y-%m-%d")

    all_appointments = Appointment.query.filter_by(
        patient_id=current_user.id
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    
    upcoming_appointments = []
    past_appointments = []
    
    for appt in all_appointments:
        if appt.status == "Booked" and appt.date >= today_str:
            upcoming_appointments.append(appt)
        else:
            past_appointments.append(appt)

    upcoming_appointments.reverse()

    return render_template("patient_dashboard.html",
                           doctors = doctors,
                           search_query = search_query,
                           upcoming_appointments=upcoming_appointments,
                           past_appointments=past_appointments)

@app.route("/doctor/manage_appointment/<int:appt_id>", methods = ["GET", "POST"])
@login_required
def manage_appointment(appt_id):
    if current_user.role!='doctor':
        flash("Access denied!!", "danger")
        return redirect(url_for('login'))
    
    appt = Appointment.query.filter_by(id=appt_id, doctor_id = current_user.id).first_or_404()

    treatment = Treatment.query.filter_by(appointment_id = appt_id).first()

    if request.method == "POST":
        diagnosis = request.form.get("diagnosis", "").strip()
        prescription = request.form.get("prescription", "").strip()
        notes = request.form.get("notes", "").strip() or None

        if not diagnosis or not prescription:
            flash("Diagnosis and Prescription are required to complete an appointment.", "danger")
            return render_template("manage_appointment.html", appt=appt, treatment=treatment)
        
        try:
            if treatment:
                treatment.diagnosis = diagnosis
                treatment.prescription = prescription
                treatment.notes = notes
            else:
                treatment = Treatment(
                    appointment_id = appt.id,
                    diagnosis = diagnosis,
                    prescription = prescription,
                    notes = notes)
                db.session.add(treatment)
            
            appt.status =  "Completed"

            db.session.commit()
            flash("Appointment marked as 'Completed' and treatment notes saved", "success")
            return redirect(url_for('doctor_dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f"An error occured: {e}", "danger")

    return render_template("manage_appointment.html", appt=appt, treatment=treatment)


@app.route("/doctor/cancel_appointment/<int:appt_id>", methods=["POST"])
@login_required
def cancel_appointment(appt_id):
    if current_user.role != 'doctor':
        flash("Access denied!!", "danger")
        return redirect(url_for('login'))
    appt = Appointment.query.filter_by(id=appt_id, doctor_id=current_user.id, status="Booked").first_or_404()
    
    try:
        appt.status = "Cancelled"
        db.session.commit()
        flash("Appointment has been cancelled.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {e}", "danger")
        
    return redirect(url_for('doctor_dashboard'))

@app.route("/doctor/patient_history/<int:patient_id>")
@login_required
def patient_history(patient_id):
    if current_user.role!='doctor':
        flash("Accedd denied!!", "danger")
        return redirect(url_for('login'))
    
    patient = User.query.get_or_404(patient_id)
    if patient.role != 'patient':
        return 404
    
    history = Appointment.query.filter_by(
        patient_id=patient.id,
        status="Completed"
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()

    return render_template("patient_history.html", patient=patient, history=history)

@app.route("/doctor/update_availability", methods=["POST"])
@login_required
def update_availability():
    if current_user.role != 'doctor':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))

    try:
        for avail_id in request.form.getlist("avail_id"):
            avail = DoctorAvailability.query.filter_by(
                id = int(avail_id),
                doctor_id = current_user.id
            ).first()

            if avail:
                avail.start_time = request.form.get(f"start_time_{avail_id}")
                avail.end_time = request.form.get(f"end_time_{avail_id}")

                avail.is_available = f"is_available_{avail_id}" in request.form
        
        db.session.commit()
        flash("Availability updated successfully.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {e}", "danger")

    return redirect(url_for('doctor_dashboard'))

@app.route("/patient/book_appointment/<int:doctor_id>")
@login_required
def book_appointment_form(doctor_id):
    if current_user.role != 'patient':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))
        
    doctor = User.query.filter_by(id=doctor_id, role='doctor', active=True).first_or_404()

    available_slots = []
    
    start_date = date.today()
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        day_name = current_date.strftime('%A')

        doc_avail = DoctorAvailability.query.filter_by(
            doctor_id=doctor.id,
            date=date_str,
            is_available=True
        ).first()
        
        if doc_avail:
            booked_appts = Appointment.query.filter_by(doctor_id = doctor_id,
                                                       date = date_str).all()
            booked_times = [appt.time for appt in booked_appts]
            all_possible_slots = generate_time_slots(doc_avail.start_time, doc_avail.end_time)
            
            day_slots = []
            for slot in all_possible_slots:
                if slot not in booked_times:
                    day_slots.append(slot)


            if day_slots:
                available_slots.append({
                    'date_str': date_str,
                    'day_name': day_name,
                    'slots': day_slots
                })
                
    return render_template("book_appointment.html", 
                           doctor=doctor, 
                           available_slots=available_slots)

@app.route("/patient/create_appointment", methods=["POST"])
@login_required
def create_appointment():
    if current_user.role != 'patient':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))

    doctor_id = request.form.get("doctor_id")
    appt_date = request.form.get("appt_date")
    appt_time = request.form.get("appt_time")
    
    if not doctor_id or not appt_date or not appt_time:
        flash("An error occurred. Please try booking again.", "danger")
        return redirect(url_for('patient_dashboard'))

    try:
        existing = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=appt_date,
            time=appt_time
        ).first()
        
        if existing:
            flash("Sorry, this time slot is already booked", "danger")
            return redirect(url_for('book_appointment_form', doctor_id = doctor_id))
        
        new_appt = Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_id,
            date=appt_date,
            time=appt_time,
            status="Booked"
        )
        db.session.add(new_appt)
        db.session.commit()
        
        flash("Appointment booked successfully!", "success")
        return redirect(url_for('patient_dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('book_appointment_form', doctor_id=doctor_id))

@app.route("/patient/cancel_appointment/<int:appt_id>", methods=["POST"])
@login_required
def patient_cancel_appointment(appt_id):
    if current_user.role != 'patient':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))
    
    appt = Appointment.query.filter_by(
        id=appt_id, 
        patient_id=current_user.id, 
        status="Booked"
    ).first_or_404()

    try:
        appt.status = "Cancelled"
        db.session.commit()
        flash("Your appointment has been successfully cancelled.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {e}", "danger")
        
    return redirect(url_for('patient_dashboard'))

@app.route("/patient/view_details/<int:appt_id>")
@login_required
def view_appointment_details(appt_id):
    if current_user.role != 'patient':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))
    
    appt = Appointment.query.filter_by(id=appt_id, patient_id=current_user.id).first_or_404()

    if appt.status != "Completed":
        flash("Details are only available for completed appointments.", "danger")
        return redirect(url_for('patient_dashboard'))
    
    treatment = Treatment.query.filter_by(appointment_id=appt.id).first()

    return render_template("view_appointment_details.html", appt=appt, treatment=treatment)



@app.route("/patient/edit_profile", methods=["GET"])
@login_required
def edit_profile_form():
    if current_user.role != 'patient':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))
        
    return render_template("edit_profile.html")
    

@app.route("/patient/edit_profile", methods=["POST"])
@login_required
def edit_profile_submit():
    if current_user.role != 'patient':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))

    name = request.form.get("name", "").strip()
    age_raw = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip() or None
    contact_number = request.form.get("contact_number", "").strip() or None
    address = request.form.get("address", "").strip() or None

    if not name:
        flash("Name is required.", "danger")
        return render_template("edit_profile.html")
        
    age = None
    if age_raw:
        try:
            age_val = int(age_raw)
            if age_val > 0:
                age = age_val
            else:
                flash("Age must be a positive number.", "danger")
                return render_template("edit_profile.html")
        except ValueError:
            flash("Please enter a valid age.", "danger")
            return render_template("edit_profile.html")
            
    try:
        user = User.query.get(current_user.id)
        user.name = name
        user.age = age
        user.gender = gender
        user.contact_number = contact_number
        user.address = address
        
        db.session.commit()
        flash("Your profile has been updated successfully.", "success")
        return redirect(url_for('patient_dashboard'))

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {e}", "danger")
        return render_template("edit_profile.html")

@app.route("/admin/view_details/<int:appt_id>")
@login_required
def admin_view_appointment_details(appt_id):
    if current_user.role != 'admin':
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))
    
    appt = Appointment.query.get_or_404(appt_id)

    if appt.status != "Completed":
        flash("Details only available for completed appointments.", "danger")
        return redirect(url_for('admin_dashboard'))
    treatment = Treatment.query.filter_by(appointment_id=appt.id).first()
    
    if not treatment:
        flash("No treatment details were found.", "warning")
        return redirect(url_for('admin_dashboard'))
    
    return render_template("view_appointment_details.html", appt=appt, treatment=treatment)

if __name__ == "__main__":
    app.run(debug=True)
