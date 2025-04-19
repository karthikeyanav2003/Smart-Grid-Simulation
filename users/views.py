import os
import logging
import hashlib
import datetime
from bson import ObjectId
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# --- Logging setup ---
LOG_DIR = r'logs'
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
# ---------------------

# Connect to MongoDB using settings
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]
users_collection = db["users"]

@csrf_protect
def signup_view(request):
    if request.method == 'POST':
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        email = request.POST.get('email')
        dob = request.POST.get('dob')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        logger.info("Signup attempt: username=%s, email=%s", username, email)

        if not all([firstname, lastname, email, dob, username, password, confirm_password]):
            logger.error("Signup failed: missing fields for email=%s", email)
            messages.error(request, "All fields are required.")
            return render(request, 'signup.html')

        if password != confirm_password:
            logger.error("Signup failed: passwords do not match for username=%s", username)
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup.html')

        if len(username) < 4:
            logger.error("Signup failed: username too short (%s)", username)
            messages.error(request, "Username must be at least 4 characters.")
            return render(request, 'signup.html')

        if len(password) < 8:
            logger.error("Signup failed: password too short for username=%s", username)
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, 'signup.html')

        if users_collection.find_one({'email': email}):
            logger.error("Signup failed: email already exists (%s)", email)
            messages.error(request, "Email already exists. Please use a different email or login.")
            return render(request, 'signup.html')

        if users_collection.find_one({'username': username}):
            logger.error("Signup failed: username already exists (%s)", username)
            messages.error(request, "Username already exists. Please choose a different username.")
            return render(request, 'signup.html')

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user_data = {
            'firstname': firstname,
            'lastname': lastname,
            'email': email,
            'dob': dob,
            'username': username,
            'password': hashed_password,
            'created_at': datetime.datetime.now(),
            'last_login': None
        }

        try:
            result = users_collection.insert_one(user_data)
            if result.inserted_id:
                logger.info("User created: username=%s, id=%s", username, result.inserted_id)
                messages.success(request, "Account created successfully! You can now log in.")
                return redirect('login')
            else:
                logger.error("Insert reported no inserted_id for username=%s", username)
                messages.error(request, "Failed to create account. Please try again.")
                return render(request, 'signup.html')
        except DuplicateKeyError:
            logger.exception("DuplicateKeyError during signup for username=%s", username)
            messages.error(request, "An account with this email or username already exists.")
            return render(request, 'signup.html')
        except Exception as e:
            logger.exception("Unexpected error during signup for username=%s: %s", username, e)
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'signup.html')

    return render(request, 'signup.html')


@csrf_protect
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        logger.info("Login attempt: username=%s", username)

        if not username or not password:
            logger.error("Login failed: missing credentials")
            messages.error(request, "Username and password are required.")
            return render(request, 'login.html')

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = users_collection.find_one({
            'username': username,
            'password': hashed_password
        })

        if user:
            users_collection.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.datetime.now()}}
            )
            request.session['user_id'] = str(user['_id'])
            request.session['username'] = user['username']
            logger.info("Login successful: username=%s, id=%s", username, user['_id'])
            messages.success(request, f"Welcome back, {user['firstname']}!")
            return redirect('main')
        else:
            logger.error("Login failed: invalid credentials for username=%s", username)
            messages.error(request, "Invalid username or password.")
            return render(request, 'login.html')

    return render(request, 'login.html')


def logout_view(request):
    username = request.session.get('username')
    logout(request)
    logger.info("Logout: username=%s", username)
    messages.success(request, "You have been successfully logged out.")
    return redirect('login')


def is_authenticated(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return False
    try:
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        return user is not None
    except Exception as e:
        logger.exception("Authentication check error for session user_id=%s: %s", user_id, e)
        return False


def login_required(view_func):
    def wrapped_view(request, *args, **kwargs):
        if not is_authenticated(request):
            messages.warning(request, "Please log in to access this page.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapped_view


@login_required
def main_view(request):
    """
    Display the main dashboard after login.
    Accessible only to authenticated users.
    """
    username = request.session.get('username')
    user = users_collection.find_one({'username': username})

    if not user:
        logger.error("Main view: user not found in DB for username=%s", username)
        messages.error(request, "User not found. Please log in again.")
        return redirect('login')

    logger.info("Rendering main view for username=%s", username)
    context = {
        'firstname': user.get('firstname', ''),
        'lastname': user.get('lastname', ''),
        'username': user['username'],
        'email': user['email'],
        'last_login': user.get('last_login'),
        'dob': user.get('dob'),
    }
    return render(request, 'main.html', context)
