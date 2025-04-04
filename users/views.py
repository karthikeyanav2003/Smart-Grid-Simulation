from django.shortcuts import render, redirect
from django.http import JsonResponse
from pymongo import MongoClient
from django.conf import settings
import bcrypt
from django.contrib.auth import logout

# Connect to MongoDB
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]
users_collection = db["users"]

# Render Signup Page
def signup_view(request):
    return render(request, 'signup.html')

# Check if email already exists
def check_email(request):
    if request.method == "POST":
        email = request.POST.get("email")
        
        # Check in MongoDB
        if users_collection.find_one({"email": email}):
            return JsonResponse({"exists": True})
        
        return JsonResponse({"exists": False})
    
    return JsonResponse({"error": "Invalid request"}, status=400)

# Handle User Signup
def signup_submit(request):
    if request.method == "POST":
        first_name = request.POST.get("firstname")
        last_name = request.POST.get("lastname")
        email = request.POST.get("email")
        dob = request.POST.get("dob")
        username = request.POST.get("signup-username")
        password = request.POST.get("signup-password")

        # Check if email exists
        if users_collection.find_one({"email": email}):
            return JsonResponse({"success": False, "message": "Email already exists"})

        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Store in MongoDB
        users_collection.insert_one({
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "dob": dob,
            "username": username,  # Store as plain text
            "password": hashed_password   # Store hashed password
        })

        return JsonResponse({"success": True, "redirect": "/users/login/"})

    return JsonResponse({"success": False, "message": "Invalid request"})

# Handle User Login
def login_view(request):
    if request.method == "GET":
        return render(request, "login.html")  # Ensure you have a `login.html` template

    elif request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Find user in MongoDB
        user = users_collection.find_one({"email": email})

        if user and bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
            return JsonResponse({"success": True, "message": "Login successful", "redirect": "/dashboard/"})
        else:
            return JsonResponse({"success": False, "message": "Invalid email or password"})

    return JsonResponse({"error": "Invalid request"}, status=400)

# Handle User Logout
def logout_view(request):
    logout(request)
    return redirect('/')
