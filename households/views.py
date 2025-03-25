from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
import pandas as pd
import numpy as np
from pymongo import MongoClient

client = MongoClient("mongodb+srv://vishwarprediscan:zT0K3JICskXrc44W@household.ipekb.mongodb.net/")
db = client["Smartgrid"]  # The database name
collection = db["energydata"]  # The collection name

def home(request):
    return render(request, 'index.html')

def main_view(request):
    data = collection.find_one()
    
    context = {'data': data}
    return render(request, 'main.html', context)

def household_data(request, household_id):
    latest_data = collection.find_one({"householdId": household_id}, sort=[("_id", -1)])
    if latest_data:
        latest_data['_id'] = str(latest_data['_id'])
        return JsonResponse(latest_data)
    else:
        return JsonResponse({})