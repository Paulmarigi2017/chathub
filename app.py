import os
import random
import uuid
import re
import secrets
import string
from random import choice
import logging

from data import names, countries, online_stores, products
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
from langdetect import detect, LangDetectException, DetectorFactory
from string import ascii_uppercase


# This will output the hashed version of your password



app = Flask(__name__)


# Configuration
app.config['SECRET_KEY'] = 'hjhjsdahhds'  # Using the second SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Example database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Initializing extensions
socketio = SocketIO(app)

# Other variables
online_users = {}
rooms = {}

UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
file_path = os.path.join(UPLOAD_FOLDER, 'os_details.png')
admin_password = 'admin@1234'
hashed_password = generate_password_hash(admin_password)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
try:
    # Attempt to open the file or proceed with the logic if it exists
    if os.path.exists(file_path):
        # Proceed with the logic if file exists
        print('File found!')
        # Add your logic here
    else:
        # Handle the missing file scenario
        print('File not found!')

except FileNotFoundError:
    print(f'Error: The file {file_path} was not found.')


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.String(50), nullable=False)
    earnings = db.Column(db.Float, default=0.0)
    experience = db.Column(db.Text, nullable=False)
    handle_info = db.Column(db.Text, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    zipcode = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    referral_code = db.Column(db.String(50), unique=True, nullable=False)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    referral_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    phone = db.Column(db.String(20), nullable=False)
    is_online = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Integer, default=1)
    is_suspended = db.Column(db.Boolean, default=False)
    star_level = db.Column(db.String(10))
    messages_limit = db.Column(db.Integer, default=50)
    total_earnings = db.Column(db.Float, default=0.0)
    comments = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.String(15), unique=True)
    uploaded_id = db.Column(db.String(150), nullable=True)
    violation_count = db.Column(db.Integer, default=0)
    driver_license = db.Column(db.String(255))  # Stores the filename of the uploaded driver's license
    selfie = db.Column(db.String(255))  # Stores the filename of the uploaded selfieapp.config['UPLOAD_FOLDER'] = 'static/uploads'
    def __repr__(self):
        return f'<User {self.first_name} {self.last_name}>'

    @staticmethod
    def generate_user_id():
        """Generate a unique 15-character alphanumeric ID."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=15))



class UpgradeRequest(db.Model):
    __tablename__ = 'upgrade_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Corrected foreign key reference
    package = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    transaction_code = db.Column(db.String(100), nullable=False)
    screenshot_filename = db.Column(db.String(100), nullable=True)

    user = db.relationship('User', backref='upgrade_requests')  # Relationship for easier access

    def __init__(self, user_id, package, payment_method, transaction_code, screenshot_filename=None):
        self.user_id = user_id
        self.package = package
        self.payment_method = payment_method
        self.transaction_code = transaction_code
        self.screenshot_filename = screenshot_filename


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    user = db.relationship('User', backref='notifications')

    def __repr__(self):
        return f'<Notification {self.message} for User {self.user_id}>'


class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_email = db.Column(db.String(120), nullable=False)
    receiver_email = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Message {self.id} from {self.sender_email} to {self.receiver_email}>'


class WithdrawalRequest(db.Model):
    __tablename__ = 'withdrawal_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')

    user = db.relationship('User', backref='withdrawal_requests')

    def __repr__(self):
        return f'<WithdrawalRequest {self.id} - User: {self.user_id}, Amount: {self.amount}>'





# Initialize BackgroundScheduler

# Initialize BackgroundScheduler
# Define allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    # Check if the file has a valid extension
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_registration_id():
    return str(uuid.uuid4())


def get_user_rating(email):
    user = User.query.filter_by(email=email).first()  # Query user by email
    return user.star_level if user else None  # Return star level or None if not found


def generate_user_id():
    """Generates a random 15-character user ID consisting of letters and digits."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(15))

def generate_unique_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def get_online_users():
    return [{'email': user['email'], 'id': user_id} for user_id, user in online_users.items()]


def contains_personal_info(message):
    # Define regex patterns for personal information
    patterns = [
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Email
        r"\b(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b",  # Phone Number
        r"@([a-zA-Z0-9_]{1,15})",  # Social Media Handles
        r"https?://[^\s]+"  # URL
    ]
    
    for pattern in patterns:
        if re.search(pattern, message):
            print(f"Pattern matched: {pattern} in message: {message}")  # Debug log
            return True
    return False




DetectorFactory.seed = 0

def detect_non_english(text):
    try:
        # Detect the language of the text
        lang = detect(text)
        
        # Return True if the detected language is not English ('en')
        return lang != 'en'
    except LangDetectException:
        # If detection fails, assume non-English content
        return True

def get_online_users():
    # Simulate getting a list of online users from a database or session
    online_users = [
        {'email': 'user1@example.com', 'is_online': True},
        {'email': 'user2@example.com', 'is_online': True},
        {'email': 'user3@example.com', 'is_online': False},  # Not online, filter out
    ]

    # Only return the emails of users who are marked as online
    return [user['email'] for user in online_users if user.get('is_online', False)]


@app.route('/')
def index():
    app_info = {
        "name": "Chathubb",
        "description": "Welcome to Chathubb, a chatting application that connects you with online users for engaging conversations. Join us to meet new people and share your thoughts!",
        "features": [
            "Connect with users who are currently online",
            "Engage in real-time chats",
            "User-friendly interface",
            "Secure and private conversations"
        ]
    }
    return render_template('index.html', app_info=app_info)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Collect form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        reason_for_joining = request.form.get('reason_for_joining', 'Not applicable')
        chat_experience = request.form.get('chat_experience', 'Not applicable')
        handling_personal_info = request.form.get('handling_personal_info', 'Not applicable')
        gender = request.form['gender']
        country = request.form['country']
        city = request.form['city']
        zipcode = request.form['zipcode']
        address = request.form['address']
        terms_agreement = request.form.get('terms_agreement')
        password = request.form['password']

        # Handle file uploads
        driver_license_file = request.files.get('file')  # Updated to match the input name
        selfie_file = request.files.get('selfie')  # Selfie file upload is now inside the route handler

        # Check if terms agreement is checked
        if not terms_agreement:
            flash('You must agree to the terms and conditions.', 'danger')
            return redirect(url_for('register'))

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('register'))

        # Ensure uploads directory exists
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        # Initialize variables for filenames
        driver_license_filename = None
        selfie_filename = None

        # Save the driver's license file if uploaded
        if driver_license_file and allowed_file(driver_license_file.filename):
            driver_license_filename = secure_filename(driver_license_file.filename)
            driver_license_file.save(os.path.join(app.config['UPLOAD_FOLDER'], driver_license_filename))

        # Save the selfie file if uploaded
        if selfie_file and allowed_file(selfie_file.filename):
            selfie_filename = secure_filename(selfie_file.filename)
            selfie_file.save(os.path.join(app.config['UPLOAD_FOLDER'], selfie_filename))

        # Hash the password provided by the user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Create a new user instance
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password=hashed_password,
            earnings=0.0,
            reason=reason_for_joining,
            experience=chat_experience,
            handle_info=handling_personal_info,
            gender=gender,
            country=country,
            city=city,
            zipcode=zipcode,
            address=address,
            referral_code=str(uuid.uuid4()),
            referred_by_id=None,
            is_active=False,
            rating=1,
            driver_license=driver_license_filename,  # Save the driver's license filename
            selfie=selfie_filename  # Save the selfie filename
        )

        # Save user to the database
        db.session.add(new_user)
        db.session.commit()

        flash('Registration Successful. Your registration ID is ' + new_user.referral_code, 'success')
        return redirect(url_for('success'))

    return render_template('register.html')





# Define online_users as a dictionary
online_users = {}  
active_rooms = []  # List to keep track of active chatrooms





@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if user:
            # Send a reset email (implement this function to send the email)
            send_reset_email(user)
            flash('An email has been sent with instructions to reset your password.', 'success')
        else:
            flash('Email not found.', 'danger')
        
        return redirect('/forgot_password')  # Redirect back to the forgot password page

    return render_template('forgot_password.html')


# Route to handle the reset password form and logic
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Validate the token (implement your token validation logic here)
    user = validate_reset_token(token)  # Replace with your token validation function
    if user is None:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect('/login')

    if request.method == 'POST':
        new_password = request.form['password']
        user.password = new_password  # Update the user's password (ensure to hash the password)
        db.session.commit()  # Commit the changes to the database
        flash('Your password has been updated!', 'success')
        return redirect('/login')  # Redirect to login page after password update

    return render_template('reset_password.html', token=token)
        
@app.route('/test')
def start_test():
    # List of 15 test questions
    questions = [
        {
            "question": "What is the purpose of chat moderation?",
            "options": [
                "To keep the conversation civil",
                "To allow any discussion",
                "To promote offensive content"
            ]
        },
        {
            "question": "How would you respond to abusive language in a chat?",
            "options": [
                "Ignore it",
                "Report it",
                "Encourage it"
            ]
        },
        {
            "question": "What actions can you take if a user is being disruptive?",
            "options": [
                "Mute the user",
                "Ban the user",
                "Ignore the user",
                "All of the above"
            ]
        },
        {
            "question": "What would you do if someone shares inappropriate content in the chat?",
            "options": [
                "Engage with them",
                "Report and remove the content",
                "Ignore it"
            ]
        },
        {
            "question": "How would you handle a situation where a user asks for personal information?",
            "options": [
                "Provide the information",
                "Politely decline and explain why",
                "Ignore the request"
            ]
        },
        {
            "question": "Correct the following sentence: 'He go to the store yesterday.'",
            "options": []
        },
        {
            "question": "I would like to sleep with you.How do you reply to that?",

            "options": []
        },
        {
            "question": "Fill in the blank: 'She ____ (to be) a great leader.'",
            "options": []
        },
        {
            "question": "What is the past tense of the verb 'to run'?",
            "options": []
        },
        {
            "question": "Write a brief summary of your favorite book.",
            "options": []
        },
        {
            "question": "Describe a time when you had to handle a difficult user in a chat environment.",
            "options": []
        },
        {
            "question": "What steps would you take to ensure a positive chat experience for all users?",
            "options": []
        },
        {
            "question": "What do you consider to be a red flag in chat moderation?",
            "options": [
                "Users asking about chat rules",
                "Frequent complaints about a user",
                "A user who is very quiet"
            ]
        },
        {
            "question": "How do you approach resolving conflicts between users in chat?",
            "options": []
        },
        {
            "question": "What strategies would you implement to improve chat engagement?",
            "options": []
        }
    ]
    
    return render_template('test.html', questions=questions)





@app.route('/success')
def success():
    return render_template('success.html', message="Your application was successful.You will now proceed to take a test.Kindly note the test is timed and you have 20 minutes to complete it.")

@app.route('/test_notification')
def test_notification():
    return render_template('test_notification.html')



@app.route('/buy_connects', methods=['GET', 'POST'])
def buy_connects():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if user is not authenticated

    if request.method == 'POST':
        # Get form data
        package = request.form['package']
        payment_method = request.form['payment_method']
        transaction_code = request.form['transaction_code']

        # Get the current user's ID from the session
        user_id = session.get('user_id')

        # Handle the uploaded file (screenshot)
        screenshot_filename = None
        if 'screenshot' in request.files:
            screenshot = request.files['screenshot']
            if screenshot:
                screenshot_filename = secure_filename(screenshot.filename)
                screenshot.save(os.path.join('uploads', screenshot_filename))  # Ensure the 'uploads' directory exists

        # Create a new upgrade request
        upgrade_request = UpgradeRequest(
            user_id=user_id,
            package=package,
            payment_method=payment_method,
            transaction_code=transaction_code,
            screenshot_filename=screenshot_filename
        )
        db.session.add(upgrade_request)
        db.session.commit()

        flash(f'Upgrade request for {package} received. Payment method: {payment_method}, Transaction code: {transaction_code}', 'success')
        return redirect(url_for('home'))  # Redirect to the homepage or a confirmation page

    # For GET requests, render the buy connects form
    return render_template('buy_connects.html')  # Ensure you have a template for this



def generate_unique_code(length=4):
    while True:
        code = "".join(random.choice(ascii_uppercase) for _ in range(length))
        if code not in rooms:
            return code

def is_language_allowed(message, allowed_language="en"):
    try:
        return detect(message) == allowed_language
    except LangDetectException:
        return False



@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Query the database for the user
        user = User.query.filter_by(email=email).first()

        # Check if user exists and password matches
        if user and check_password_hash(user.password, password) and user.is_admin:
            session['admin_user_id'] = user.id  # Store the user ID in the session
            session['admin_email'] = user.email  # Store the email in the session
            session['is_admin'] = True  # Set a flag to indicate admin is logged in
            flash('Login successful!', 'success')
            return redirect(url_for('admin_panel'))  # Redirect to the admin panel
        else:
            flash('Invalid email or password. Please try again.', 'error')

    return render_template('admin_login.html')




rooms = {}  # Global variable to hold room information




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if the user exists
        user = User.query.filter_by(email=email).first()

        if user:
            if user.is_suspended:
                flash('Your account has been suspended. Please contact support.', 'danger')
                return redirect(url_for('login'))

            star_level = user.star_level  # Make sure to retrieve the star level

            # Check if star_level is None or an invalid type
            if star_level is None or not isinstance(star_level, str):
                flash('This account is not yet ative.', 'warning')
                return redirect(url_for('login'))

            # Check if star_level is a valid string and process it
            if star_level.endswith('star'):
                numeric_star_level = int(star_level[0])  # Assuming the first character is the star level
            else:
                numeric_star_level = int(star_level)

            if check_password_hash(user.password, password):
                # Login successful, set the user in the session
                session['user_id'] = user.id
                session['user_name'] = choice(names)  # Generate random name
                session['user_country'] = choice(countries)  # Generate random country
                flash('Login successful!', 'success')
                return redirect(url_for('home'))  # Redirect to the dashboard or home page
            else:
                flash('Invalid password. Please try again.', 'danger')
        else:
            flash('This account does not exist.', 'danger')  # Message for non-existent account
        
        return redirect(url_for('login'))

    return render_template('login.html')






@app.route("/home", methods=["POST", "GET"])
def home():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect('/login')  # Redirect to login if not authenticated

    current_user = User.query.get(session['user_id'])  # Retrieve user by ID from session
    if not current_user:
        return redirect('/login')

    star_level = current_user.star_level  # Retrieve star level from the current user

    # Star level check for room creation
    if star_level is None or not isinstance(star_level, str):
        flash('This account is not active yet.', 'warning')
        return redirect(url_for('login'))

    # Process star_level correctly
    try:
        numeric_star_level = int(star_level[0]) if star_level.endswith('star') else int(star_level)
    except ValueError:
        flash('Invalid star level format.', 'danger')
        return redirect(url_for('login'))

    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")  # Get code from form
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        # Validate name
        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name, rooms=rooms, star_level=star_level)
        
        # Validate room code when joining
        if join and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name, rooms=rooms, star_level=star_level)

        # Room creation: only allow users with star level 4 or higher
        if create:
            if numeric_star_level < 4:
                return render_template("home.html", error="You need to be at least a 4-star level to create a room.", code=code, name=name, rooms=rooms, star_level=star_level)
            
            room = generate_unique_code()  # Generate unique room code
            rooms[room] = {"members": 0, "messages": [], "message_count": 0, "owner": name}
            flash(f'Room created successfully! Room code: {room}', 'success')

        # Join or access the room if a valid code is provided
        if code:
            if code not in rooms:  # Check if the room exists
                return render_template("home.html", error="Room does not exist.", code=code, name=name, rooms=rooms, star_level=star_level)

            # Check room capacity
            if rooms[code]["members"] >= 2:
                return render_template("home.html", error="Room is full.", code=code, name=name, rooms=rooms, star_level=star_level)

            # Join the room
            rooms[code]["members"] += 1
            session["room"] = code  # Store room code in session
            session["name"] = name
            return redirect(url_for("room"))

    # GET method: Pass star_level and room info to the template
    return render_template("home.html", rooms=rooms, star_level=star_level)



@app.route("/room")
def room():
    room = session.get("room")
    if not room or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])


@app.route('/join', methods=['POST'])
def join():
    if 'user_id' not in session:
        return redirect('/login')  # Redirect to login if not authenticated

    code = request.form.get('code')  # Get the room code from the form
    name = request.form.get('name')  # Get the user's name

    if not code:
        flash('Please enter a room code.', 'danger')
        return redirect(url_for('home'))

    if code not in rooms:
        flash('Room does not exist.', 'danger')
        return redirect(url_for('home'))

    # Check room capacity
    if rooms[code]["members"] >= 2:
        flash('Room is full.', 'danger')
        return redirect(url_for('home'))

    # Join the room
    rooms[code]["members"] += 1  # Increment member count
    session["room"] = code  # Store the room in the session
    session["name"] = name  # Store the user's name
    return redirect(url_for('room'))  # Redirect to the room



# Define message limits based on star levels
MESSAGE_LIMITS = {
    '1star': (50, 1),
    '2star': (100, 2),
    '3star': (200, 3),
    '4star': (400, 4),
    '5star': (800, 5),
    '6star': (float('inf'), 6)
}


@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return

    # Get message details and user's name
    message_text = data["message"]
    name = data["name"]

    # Retrieve the current user from the session
    current_user = User.query.get(session['user_id'])

    # Get the star level and determine the message limit
    star_level = current_user.star_level
    message_limit, numeric_star_level = MESSAGE_LIMITS.get(star_level, (50, 1))  # Default to 50 if unknown
    user_message_count = current_user.messages_limit  # Track the message limit stored in the database

    if user_message_count >= message_limit:
        # Send system message informing the user they've hit their message limit
        send({
            "name": "System",
            "message": f"You have reached the message limit for your star level ({numeric_star_level} star)."
        }, to=room)
        return

    # Increment the user's message count and update the database
    current_user.messages_limit += 1

    # Process the message if the limit hasn't been reached
    if not is_language_allowed(message_text):
        # Handle language violations
        current_user.violation_count += 1
        if current_user.violation_count in [300, 600, 900]:
            notify_admin(current_user)

        db.session.commit()
        send({
            "name": "System",
            "message": f"Non-English language detected, {name}. Please send messages in English."
        }, to=room)
        return

    # Increment the room's message count and process payments
    rooms[room]["message_count"] += 1
    room_owner = rooms[room]["owner"]

    # Payment logic: owner gets 0.02 per message, joiner gets 0.005
    if name == room_owner:
        current_user.total_earnings += 0.02
    else:
        current_user.total_earnings += 0.005

    # Commit changes to the database (message count and earnings)
    db.session.commit()

    # Send the message to the room
    content = {"name": name, "message": message_text}
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{name} said: {message_text}")

    # Display product advertisement every 5 messages
    if rooms[room]["message_count"] % 5 == 0:
        product = random.choice(products)
        online_store = random.choice(online_stores)
        ad_message = {
            "name": "System",
            "message": f"AD: Check out the amazing {product['name']} for just ${product['price']}! {product['catchphrase']} Available at {online_store}."
        }
        send(ad_message, to=room)
        print(f"Advertisement sent to {room}: {ad_message['message']}")


    




@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if room not in rooms:
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")


@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    if room in rooms:
        leave_room(room)
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
        send({"name": name, "message": "has left the room"}, to=room)
        print(f"{name} has left the room {room}")










@app.route('/admin/manage_users', methods=['GET', 'POST'])
def manage_users():
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))

    search_query = request.form.get('search_query')
    
    # Base query for active users
    users_query = User.query.filter_by(is_active=True)

    if search_query:
        # Filter by first name, last name, or email
        users_query = users_query.filter(
            (User.first_name.ilike(f'%{search_query}%')) |
            (User.last_name.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )
    
    # Execute the query and fetch the results
    users = users_query.all()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')
        reason = request.form.get('reason', "")  # Get the reason from the prompt

        user = User.query.get(user_id)
        if not user:
            flash(f'User with ID {user_id} not found.', 'danger')
            return redirect(url_for('manage_users'))

        # Handle different actions
        if action == 'suspend':
            user.is_suspended = True
            flash(f'User {user.first_name} {user.last_name} suspended.', 'success')
        
        elif action == 'unsuspend':
            user.is_suspended = False
            flash(f'User {user.first_name} {user.last_name} unsuspended.', 'success')
        
        elif action == 'downgrade':
            new_star_level = request.form.get('new_star_level')
            if new_star_level:
                user.star_level = new_star_level
                flash(f'User {user.first_name} {user.last_name} downgraded to {new_star_level}-star.', 'success')
            else:
                flash('No star level provided for downgrade.', 'danger')

        elif action == 'fine':
            fine_amount = request.form.get('fine_amount', type=float)
            if fine_amount and fine_amount > 0:
                if user.total_earnings >= fine_amount:
                    user.total_earnings -= fine_amount
                    flash(f'User {user.first_name} {user.last_name} fined ${fine_amount:.2f}.', 'success')
                else:
                    flash('Fine amount exceeds user earnings.', 'danger')
            else:
                flash('Invalid fine amount.', 'danger')

        elif action == 'upgrade':
            new_star_level = request.form.get('new_star_level')
            if new_star_level in ['1', '2', '3', '4', '5', '6']:  # Validate the new star level
                user.star_level = new_star_level
                # Set the corresponding message limit if necessary
                if new_star_level == '1':
                    user.messages_limit = 50
                elif new_star_level == '2':
                    user.messages_limit = 100
                elif new_star_level == '3':
                    user.messages_limit = 200
                elif new_star_level == '4':
                    user.messages_limit = 400
                elif new_star_level == '5':
                    user.messages_limit = 800
                elif new_star_level == '6':
                    user.messages_limit = float('inf')  # Infinite messages for level 6
                flash(f'User {user.first_name} {user.last_name} upgraded to {new_star_level}-star.', 'success')
            else:
                flash('Invalid star level provided for upgrade.', 'danger')

        # Store the reason in the database
        user.reason = reason  # Store the reason for the action

        # Commit changes
        db.session.commit()
        return redirect(url_for('manage_users'))

    return render_template('manage_users.html', users=users)









@app.route('/reset_limits', methods=['POST'])  # Use POST to avoid CSRF issues
def reset_limits():
    # Ensure the user is logged in as admin
    if 'admin_user_id' not in session:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_login'))  # Redirect to admin login if not logged in

    users = User.query.all()
    for user in users:
        # Reset each user's messages limit to the initial value based on star level
        user.messages_limit = 0  # Reset message limit for all users
        user.last_reset = datetime.utcnow()  # Update last reset timestamp

    db.session.commit()  # Commit all changes to the database
    flash('Message limits have been reset to zero for all users.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/view_earnings')
def view_earnings():
    user_id = session.get('user_id')  # Get the user ID from the session
    user = User.query.get(user_id)     # Retrieve the user from the database
    if user:
        return render_template('earnings.html', earnings=user.total_earnings)
    else:
        return redirect(url_for('login'))



@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if user is not authenticated

    user_id = session.get('user_id')  # Get the current user's ID

    if request.method == 'POST':
        amount = float(request.form.get('amount'))  # Get the withdrawal amount from the form

        # Ensure we're in the app context for database access
        with app.app_context():
            user = User.query.get(user_id)  # Get the user from the database

            if user:
                # Check if the user has enough balance to withdraw
                if user.earnings < amount:
                    flash('Insufficient balance for this withdrawal.', 'error')
                    return redirect(url_for('withdraw'))

                # Check if the amount is less than the minimum allowed
                if amount < 180:
                    flash('The minimum withdrawal amount is $180.', 'error')
                    return redirect(url_for('withdraw'))

                # Create a new withdrawal request
                withdrawal_request = WithdrawalRequest(
                    user_id=user_id,
                    amount=amount,
                    timestamp=datetime.utcnow(),
                    status='Pending'  # Initial status
                )
                db.session.add(withdrawal_request)

                # Optionally, deduct the amount from user earnings
                # user.earnings -= amount  # Uncomment if you want to deduct immediately
                db.session.commit()

                # Create a notification for the admin
                admin_notification = Notification(
                    message=f'User {user.username} requested a withdrawal of ${amount}.',
                )
                db.session.add(admin_notification)
                db.session.commit()

                flash('Withdrawal request submitted successfully. It is pending admin approval.', 'success')
                return redirect(url_for('withdraw'))  # Redirect to the withdrawal page

    return render_template('withdraw.html')  # Render the withdrawal template



@app.route('/admin/withdrawals', methods=['GET', 'POST'])
def manage_withdrawals():
    # Ensure the user is logged in as admin
    if 'admin_user_id' not in session:  # Check if admin user ID is in session
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_login'))  # Redirect to admin login if not logged in

    # Fetch all withdrawal requests
    withdrawal_requests = WithdrawalRequest.query.all()

    if request.method == 'POST':
        request_id = request.form.get('request_id')
        action = request.form.get('action')  # 'approve' or 'reject'

        # Ensure we're in the app context for database access
        with app.app_context():
            withdrawal_request = WithdrawalRequest.query.get(request_id)
            if withdrawal_request:
                user = User.query.get(withdrawal_request.user_id)

                if action == 'approve':
                    # Check if the user has enough earnings
                    if user.earnings >= withdrawal_request.amount:
                        # Deduct the amount from user's earnings
                        user.earnings -= withdrawal_request.amount
                        withdrawal_request.status = 'Approved'  # Update withdrawal request status
                        flash(f'Withdrawal request for ${withdrawal_request.amount} approved.', 'success')
                    else:
                        flash('Insufficient funds for this withdrawal.', 'danger')

                elif action == 'reject':
                    withdrawal_request.status = 'Rejected'  # Update withdrawal request status
                    flash('Withdrawal request rejected.', 'warning')

                db.session.commit()  # Commit changes to the database

        return redirect(url_for('manage_withdrawals'))

    return render_template('admin/manage_withdrawals.html', withdrawal_requests=withdrawal_requests)




@app.route('/admin/view_upgrade_requests', methods=['GET', 'POST'])
def view_upgrade_requests():
    if 'admin_user_id' not in session or session.get('is_admin') != True:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_login'))

    requests = UpgradeRequest.query.all()  # Retrieve all upgrade requests

    if request.method == 'POST':
        request_id = request.form['request_id']
        upgrade_request = UpgradeRequest.query.get(request_id)

        if upgrade_request:
            user = User.query.get(upgrade_request.user_id)
            action = request.form['action']

            # Approve or deny logic
            if action == 'approve':
                # Logic to approve the request
                star_levels = {
                    '1star': (50, 1),
                    '2star': (100, 2),
                    '3star': (200, 3),
                    '4star': (400, 4),
                    '5star': (800, 5),
                    '6star': (float('inf'), 6)
                }

                if upgrade_request.package in star_levels:
                    user.messages_limit, user.star_level = star_levels[upgrade_request.package]
                    flash(f'User {user.first_name} {user.last_name} has been upgraded to {upgrade_request.package}.', 'success')

                    # Check who referred the user
                    referrer = User.query.get(user.referred_by_id) if user.referred_by_id else None
                    if referrer:
                        referrer.referral_count += 1  # Increment the referral count
                        db.session.commit()  # Commit the change

                        # Notify admin if the referral count reaches 10
                        if referrer.referral_count == 10:
                            notification_message = f'User {referrer.first_name} {referrer.last_name} has reached 10 referrals!'
                            notification = Notification(message=notification_message)
                            db.session.add(notification)
                            db.session.commit()

                    db.session.delete(upgrade_request)  # Delete the processed request
                    db.session.commit()
                else:
                    flash('Invalid package selected for upgrade.', 'danger')

            elif action == 'deny':
                # Logic to deny the request (you can add additional handling here)
                db.session.delete(upgrade_request)  # Optionally delete or keep the request
                db.session.commit()
                flash('Upgrade request denied.', 'danger')

        return redirect(url_for('view_upgrade_requests'))

    return render_template('admin/view_upgrade_requests.html', upgrade_requests=requests)





@app.route('/admin/view_user/<int:user_id>', methods=['GET'])
def view_user(user_id):
    # user_id from the URL parameter is already available, so we don't need to get it again from request.args
    user = User.query.get(user_id)
    
    if user:
        return render_template('admin/view_user.html', user=user)
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('manage_users'))



@app.route('/admin_/notifications')
def admin_notifications():
    # Check if the user is logged in as an admin
    if 'admin_user_id' not in session or session.get('is_admin') != True:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_login'))  # Redirect to login if not admin

    notifications = Notification.query.order_by(Notification.timestamp.desc()).all()  # Get all notifications
    return render_template('admin/notifications.html', notifications=notifications)

def notify_admin(user):
    # Define thresholds
    thresholds = [300, 600, 900]
    
    # Check if the user has reached a notification threshold
    if user.violation_count in thresholds:
        message = f'User {user.first_name} {user.last_name} has reached {user.violation_count} violations!'

        # Create a new notification and save it to the database
        notification = Notification(message=message)
        db.session.add(notification)

        try:
            db.session.commit()  # Commit the notification to the database
            print(f"Notification saved: {message}")  # For logging purposes
        except Exception as e:
            print(f"Failed to save notification: {e}")  # Handle any errors




@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/user_details/<int:user_id>')
def user_details(user_id):
    # Assume you have a function to get a user by their ID
    user = get_user_by_id(user_id)  # Retrieve user data from the database
    if not user:
        return redirect(url_for('manage_registrations'))  # Redirect if user not found

    return render_template('user_detail.html', user=user)



@app.route('/admin/manage_registrations', methods=['GET', 'POST'])
def manage_registrations():
    if 'admin_user_id' not in session or session.get('is_admin') != True:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_login'))

    registrations = User.query.filter_by(is_active=False).all()

    if request.method == 'POST':
        action = request.form['action']
        user_id = request.form['user_id']
        user = User.query.get(user_id)

        if user:
            if action == 'approve':
                user.is_active = True
                user.star_level = 1
                user.messages_limit = 50
                flash(f'User {user.first_name} {user.last_name} has been approved!', 'success')

            elif action == 'reject':
                db.session.delete(user)
                flash(f'User {user.first_name} {user.last_name} has been rejected.', 'warning')

            db.session.commit()
        else:
            flash('User not found.', 'danger')

        return redirect(url_for('manage_registrations'))

    return render_template('admin/manage_registrations.html', registrations=registrations)


@app.route('/view_user_details', methods=['GET'])
def view_user_details():
    user_id = request.args.get('user_id')
    user = User.query.get(user_id)
    if user:
        return render_template('user_details.html', user=user)
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('manage_registrations'))


@app.route('/advertisers_login', methods=['GET', 'POST'])
def advertisers_login():
    if request.method == 'POST':
        # Simulate credential validation
        username = request.form['username']
        password = request.form['password']

        # Replace this with your actual validation logic
        if username != "valid_user" or password != "valid_password":
            flash('Invalid credentials. Please try again.', 'error')
            return redirect(url_for('advertisers_login'))  # Redirect to the same route

    return render_template('advertisers_login.html')  # Render the login form




@app.route('/referral')
def referral():
    # Attempt to get user_id from session
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None  # Check if user is logged in

    if user is None:
        # Handle the case for non-logged-in users or adjust as needed
        flash('You must be logged in to access your referral link.', 'danger')
        return redirect(url_for('home'))

    referral_link = f"http://127.0.0.1:5000/register?referral={user.referral_code}"  # Adjust the domain as needed
    return render_template('referral.html', referral_link=referral_link)





@app.route('/admin_panel')
def admin_panel():
    # Check for the correct login flag in the session
    if 'is_admin' not in session:  # Correct session key
        flash('You need to log in first', 'danger')
        return redirect(url_for('admin_login'))  # Redirect to login if not logged in

    # Access the email from the session if needed
    admin_email = session['admin_email']
    print(f"Logged in as: {admin_email}")  # Debugging output

    return render_template('admin_panel.html')  # Render the admin panel



@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_id', None)  # Remove admin from session
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_login'))

def create_db():
    create_tables()

# Start the scheduler


@app.route('/create_initial_admin', methods=['GET', 'POST'])
def create_initial_admin():
    # Check if an admin already exists
    existing_admin = User.query.filter_by(is_admin=True).first()
    
    if existing_admin:
        flash('Admin account already exists. Please log in.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Collect form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        gender = request.form['gender']
        country = request.form['country']
        city = request.form['city']
        zipcode = request.form['zipcode']
        address = request.form['address']
        password = request.form['password']

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('create_initial_admin'))

        # Hash the password using Werkzeug
        hashed_password = generate_password_hash(password)

        # Create the initial admin
        initial_admin = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password=hashed_password,
            is_admin=True,
            reason='Not specified',
            experience='Not specified',
            handle_info='Not specified',
            gender=gender,
            country=country,
            city=city,
            zipcode=zipcode,
            is_active=True,
            address=address,
            referral_code=str(uuid.uuid4()),
            referred_by_id=None,
            rating=1
        )

        # Save the initial admin to the database
        db.session.add(initial_admin)
        db.session.commit()

        flash('Initial admin account created. You can now register other admins.', 'success')
        return redirect(url_for('login'))

    return render_template('create_initial_admin.html')

    return render_template('create_initial_admin.html')

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/cookie_policy')
def cookie_policy():
    return render_template('cookie_policy.html')


@app.route('/logout')
def logout():
    session.clear()  # Clear the session to log out the user
    return redirect(url_for('login'))  # Redirect back to the login page


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the tables
    app.run(debug=True)