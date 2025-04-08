from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from pymongo import MongoClient
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from flask import Flask, request, jsonify, redirect, render_template
import re
from datetime import datetime
import bcrypt
from werkzeug.security import generate_password_hash
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId
import hashlib
import datetime
# Connect to MongoDB using settings
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]
users_collection = db["users"]

@csrf_protect
def signup_view(request):
    """Process the signup form submission"""
    if request.method == 'POST':
        # Extract form data
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        email = request.POST.get('email')
        dob = request.POST.get('dob')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate form data
        if not all([firstname, lastname, email, dob, username, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, 'signup.html')
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup.html')
        
        if len(username) < 4:
            messages.error(request, "Username must be at least 4 characters.")
            return render(request, 'signup.html')
            
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, 'signup.html')
        
        # Check if email already exists
        if users_collection.find_one({'email': email}):
            messages.error(request, "Email already exists. Please use a different email or login.")
            return render(request, 'signup.html')
        
        # Check if username already exists
        if users_collection.find_one({'username': username}):
            messages.error(request, "Username already exists. Please choose a different username.")
            return render(request, 'signup.html')
        
        # Hash the password for security
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Create user document
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
            # Insert the user document
            result = users_collection.insert_one(user_data)
            
            if result.inserted_id:
                messages.success(request, "Account created successfully! You can now log in.")
                return redirect('login')
            else:
                messages.error(request, "Failed to create account. Please try again.")
                return render(request, 'signup.html')
                
        except DuplicateKeyError:
            messages.error(request, "An account with this email or username already exists.")
            return render(request, 'signup.html')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'signup.html')
    
    # If not POST, redirect to signup page
    return render(request, 'signup.html')

@csrf_protect
def login_view(request):
    """Process login form submission"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, 'login.html')
        
        # Hash the password for comparison
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Find the user
        user = users_collection.find_one({
            'email': email,
            'password': hashed_password
        })
        
        if user:
            # Update last login time
            users_collection.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.datetime.now()}}
            )
            
            # Set session data
            request.session['user_id'] = str(user['_id'])
            request.session['username'] = user['username']
            
            messages.success(request, f"Welcome back, {user['firstname']}!")
            return redirect('dashboard')  # Redirect to dashboard after login
        else:
            messages.error(request, "Invalid email or password.")
            return render(request, 'login.html')
    
    # If not POST, render login page
    return render(request, 'login.html')
    
def logout_view(request):
    logout(request)
    return redirect('login')  # Redirect to login page after logout