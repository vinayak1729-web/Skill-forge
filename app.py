
# from modules.send_signup_email import send_sign_up_email, generate_otp
# from modules.signupEmailBody import Sign_up_email_body_template


import os
import json
import random
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from dotenv import load_dotenv
import hashlib
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'surya-prabha-secret-key')

# Email configuration
email_sender = os.getenv('EMAIL_USER')
sender_password = os.getenv('EMAIL_PASS')

# Create database directory if it doesn't exist
os.makedirs('database', exist_ok=True)

# Store OTPs temporarily (in a real app, use a database)
otp_store = {}

# Email template for signup verification
def Sign_up_email_body_template(username, otp):
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Email Verification - Surya Prabha</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 20px auto;
            background-color: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        h2 {{
            color: #0056b3;
            margin-top: 0;
        }}
        p {{
            margin-bottom: 15px;
        }}
        .otp-code {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
            background-color: #e9ecef;
            padding: 10px 20px;
            border-radius: 5px;
            display: inline-block;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 14px;
            color: #777;
        }}
        .team-name {{
            font-weight: bold;
            color: #0056b3;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Verify Your Email Address</h2>
        <p>Dear {username},</p>
        <p>Thank you for signing up with Surya Prabha! To complete your registration and activate your account, please verify your email address using the One-Time Password (OTP) below.</p>
        <p>This OTP is valid for a short period for security reasons. Please enter it on the verification page to proceed.</p>

        <div class="otp-code">
            {otp}
        </div>

        <p>If you did not sign up for Surya Prabha, please ignore this email. No further action is required.</p>

        <div class="footer">
            <p>Thank you,</p>
            <p class="team-name">Team Surya Prabha</p>
            <p><small>If you have any questions, please contact our support team.</small></p>
        </div>
    </div>
</body>
</html>
"""

def generate_otp():
    """Generates a 6-digit random OTP."""
    return str(random.randint(100000, 999999))

def send_sign_up_email(recipient_email, username, sender_email, sender_password):
    """Sends a formatted HTML email with OTP for signup verification."""
    otp = generate_otp()
    subject = "Surya Prabha - Verify Your Email to Activate Your Account"
    
    # Store OTP for verification
    otp_store[recipient_email] = otp
    
    body = Sign_up_email_body_template(username, otp)
    
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    
    message.attach(MIMEText(body, "html"))
    
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.sendmail(sender_email, recipient_email, message.as_string())
        print(f"Verification email sent successfully to {username} ({recipient_email}) with OTP: {otp}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def user_exists(username=None, email=None):
    """Check if a user exists by username or email."""
    for filename in os.listdir('database'):
        if filename.endswith('.json'):
            with open(os.path.join('database', filename), 'r') as f:
                user_data = json.load(f)
                if (username and user_data.get('username') == username) or \
                   (email and user_data.get('email') == email):
                    return True
    return False

def get_user_by_identifier(identifier):
    """Get user data by username or email."""
    for filename in os.listdir('database'):
        if filename.endswith('.json'):
            with open(os.path.join('database', filename), 'r') as f:
                user_data = json.load(f)
                if user_data.get('username') == identifier or user_data.get('email') == identifier:
                    return user_data
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            
            # Check if user already exists
            if user_exists(username=username):
                return jsonify({'success': False, 'error': 'Username already exists'})
            
            if user_exists(email=email):
                return jsonify({'success': False, 'error': 'Email already exists'})
            
            # Send verification email
            if send_sign_up_email(email, username, email_sender, sender_password):
                # Store user data temporarily (will be saved after OTP verification)
                session['temp_user'] = {
                    'username': username,
                    'email': email,
                    'password': hash_password(password)
                }
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Failed to send verification email'})
        
        # For regular form submission (fallback)
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')
        
        # Check if user already exists
        if user_exists(username=username):
            return render_template('signup.html', error='Username already exists')
        
        if user_exists(email=email):
            return render_template('signup.html', error='Email already exists')
        
        # Send verification email
        if send_sign_up_email(email, username, email_sender, sender_password):
            # Store user data temporarily
            session['temp_user'] = {
                'username': username,
                'email': email,
                'password': hash_password(password)
            }
            return render_template('signup.html', success='Verification email sent. Please check your inbox.')
        else:
            return render_template('signup.html', error='Failed to send verification email')

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    if request.is_json:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
    else:
        email = request.form.get('email')
        otp = request.form.get('otp')
    
    # Check if email exists in OTP store
    if email not in otp_store:
        return jsonify({'success': False, 'error': 'No OTP found for this email'})
    
    # Verify OTP
    if otp_store[email] == otp:
        # OTP is correct, save user data
        if 'temp_user' in session:
            user_data = session['temp_user']
            
            # Save user data to file
            filename = f"database/{user_data['username']}.json"
            with open(filename, 'w') as f:
                json.dump(user_data, f)
            
            # Clean up
            del otp_store[email]
            session.pop('temp_user', None)
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'User data not found'})
    else:
        return jsonify({'success': False, 'error': 'Invalid OTP'})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('home'))
    
    if request.method == 'GET':
        return render_template('login.html')
    
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            identifier = data.get('identifier')
            password = data.get('password')
        else:
            identifier = request.form.get('identifier')
            password = request.form.get('password')
        
        # Get user data
        user_data = get_user_by_identifier(identifier)
        
        if user_data and user_data['password'] == hash_password(password):
            # Set session data
            session['username'] = user_data['username']
            session['email'] = user_data['email']
            
            if request.is_json:
                return jsonify({'success': True})
            else:
                return redirect(url_for('home'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Invalid username/email or password'})
            else:
                return render_template('login.html', error='Invalid username/email or password')

@app.route('/home')
@login_required
def home():
    return render_template('home.html', 
                          username=session.get('username'), 
                          email=session.get('email'))

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)



