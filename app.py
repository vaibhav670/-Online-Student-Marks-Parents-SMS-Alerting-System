from flask import Flask, request, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client
import sqlite3

app = Flask(__name__)
app.secret_key = '41cdef6fb14cdb548585e3d17a55a66e'  # Replace with your generated secret key

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure Twilio
account_sid = 'AC171dd3f7e7c4495d1a438d1c5eaaef33'
auth_token = '223764dc6127ab0113792c38e0871e69'
twilio_number = '+14154087434'
client = Client(account_sid, auth_token)

# User model
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# User loader
@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect('school.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
    if user:
        return User(user[0], user[1], user[2])
    return None

# Function to send SMS using Twilio
def send_sms(to, message):
    try:
        message = client.messages.create(
            body=message,
            from_=twilio_number,
            to=to
        )
        print(f"Message sent with SID: {message.sid}")
        return True
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return False

# Function to fetch student information from SQLite database
def get_student_info(student_id):
    try:
        conn = sqlite3.connect('school.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, parent_contact FROM students WHERE student_id=?", (student_id,))
        student = cursor.fetchone()
        conn.close()
        if student:
            return {"name": student[0], "parent_contact": student[1]}
        else:
            return None
    except Exception as e:
        print(f"Failed to fetch student info: {e}")
        return None

# Login route (also the home page)
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('school.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
        if user and check_password_hash(user[2], password):
            user_obj = User(user[0], user[1], user[2])
            login_user(user_obj)
            return redirect(url_for('marks'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        with sqlite3.connect('school.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
        flash('Registration successful! You can now log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

# Route for handling marks submission
@app.route('/marks', methods=['GET', 'POST'])
@login_required
def marks():
    if request.method == 'POST':
        try:
            student_id = request.form['student_id']
            subject = request.form['subject']
            mark = int(request.form['mark'])
            
            # Fetch student information from database
            student = get_student_info(student_id)
            if not student:
                flash('Student not found. Please check the student ID.', 'danger')
                return redirect(url_for('marks'))
            
            # Process marks and send alert if mark is below threshold
            if mark < 50:
                message = f"Alert: Your child {student['name']} scored {mark} in {subject}."
                if send_sms(student['parent_contact'], message):
                    flash('Alert SMS sent successfully!', 'success')
                else:
                    flash('Failed to send alert SMS. Please try again later.', 'danger')
            
            # Save marks to database
            conn = sqlite3.connect('school.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO marks (student_id, subject, mark) VALUES (?, ?, ?)",
                           (student_id, subject, mark))
            conn.commit()
            conn.close()
            
            flash('Marks submitted successfully!', 'success')
            return redirect(url_for('marks'))
        except Exception as e:
            print(f"Error processing form: {e}")
            flash('An error occurred while submitting the form. Please try again.', 'danger')
            return redirect(url_for('marks'))
    
    return render_template('marks.html')

# Optionally, handle favicon requests
@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)
