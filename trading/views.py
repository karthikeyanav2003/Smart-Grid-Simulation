from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from pymongo import MongoClient
import pandas as pd
import hashlib


def hash_household_id(household_id):
    """
    Generate a SHA-256 hash for the given household ID for privacy.
    """
    return hashlib.sha256(str(household_id).encode()).hexdigest()


def process_energy_data():
    """
    Internal helper to fetch raw energy data, compute derived metrics,
    and return a DataFrame ready for insertion into energy_trading.
    """
    # Connect to MongoDB
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    energy_collection = db["energydata"]

    # Fetch raw data
    raw_documents = list(energy_collection.find())
    df = pd.DataFrame(raw_documents)

    # Ensure required fields exist
    required_cols = [
        "solarPower", "windPower", "powerConsumption", "voltage", "current",
        "electricityPrice", "overloadCondition", "transformerFault", "householdId"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    # Fill missing numeric values with 0 to avoid dtype conflicts
    numeric_cols = df.select_dtypes(include=['number']).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)

    # Handle datetime columns explicitly, if any
    datetime_cols = df.select_dtypes(include=['datetime64[ns]']).columns
    if not datetime_cols.empty:
        df[datetime_cols] = df[datetime_cols].fillna(pd.NaT)

    # Compute derived metrics
    df["NetPower"] = (df["solarPower"] + df["windPower"] - df["powerConsumption"]).round(2)
    df["Efficiency"] = (((df["solarPower"] + df["windPower"]) / df["powerConsumption"]) * 100).round(2)
    df["OverloadRisk"] = (df["powerConsumption"] / (df["voltage"] * df["current"])).round(2)
    df["AdjCost"] = (df["powerConsumption"] * df["electricityPrice"]).round(2)
    df["NoFault"] = ((df["overloadCondition"] == 0) & (df["transformerFault"] == 0)).astype(int)
    df["BothFaults"] = ((df["overloadCondition"] == 1) & (df["transformerFault"] == 1)).astype(int)
    df["OverloadOnly"] = ((df["overloadCondition"] == 1) & (df["transformerFault"] == 0)).astype(int)
    df["TransformerFaultOnly"] = ((df["overloadCondition"] == 0) & (df["transformerFault"] == 1)).astype(int)
    df["Role"] = df["NetPower"].apply(lambda x: "Producer" if x > 0 else "Consumer")
    df["householdId_hash"] = df["householdId"].apply(hash_household_id)
    df["Price"] = df["electricityPrice"].round(2)

    # Select fields for insertion
    fields = [
        "householdId", "householdId_hash", "NetPower", "Efficiency",
        "OverloadRisk", "AdjCost", "NoFault", "BothFaults",
        "OverloadOnly", "TransformerFaultOnly", "Price", "Role"
    ]
    return df[fields]


def energy_report(request):
    """
    View to display processed energy trading data in a template.
    Excludes hashed household IDs from display for privacy.
    Implements pagination with 5 items per page.
    """
    try:
        df_processed = process_energy_data()

        # Connect to MongoDB and update results collection
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]
        results_collection = db["energy_trading"]

        # Clear old data and insert new
        records = df_processed.to_dict(orient="records")
        results_collection.delete_many({})
        results_collection.insert_many(records)

        # Fetch for display, excluding hashed IDs
        data_to_display = list(
            results_collection.find(
                {},
                {"_id": 0, "householdId_hash": 0}
            )
        )
        
        # Set up pagination
        paginator = Paginator(data_to_display, 5)  # Show 5 rows per page
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context = {
            "data": data_to_display,
            "page_obj": page_obj,
            "paginator": paginator,
        }
        
        return render(request, "report.html", context)

    except Exception as e:
        # Render with error message
        return render(request, "report.html", {"error": f"An error occurred: {e}"})


def update_energy_trading_collection(request):
    """
    API endpoint to refresh the energy_trading MongoDB collection.
    Returns JSON with status and count of inserted records.
    """
    try:
        df_processed = process_energy_data()

        # Connect and upsert into trading collection
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]
        results_collection = db["energy_trading"]

        # Replace entire collection
        results_collection.delete_many({})
        records = df_processed.to_dict(orient="records")
        if records:
            insert_result = results_collection.insert_many(records)
            count = len(insert_result.inserted_ids)
        else:
            count = 0

        return JsonResponse({"status": "success", "inserted": count})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_POST
def select_household(request):
    """
    Handle the selection of a household from the grid participants table.
    """
    try:
        household_id = request.POST.get('household_id')
        
        if not household_id:
            return JsonResponse({"status": "error", "message": "No household ID provided"}, status=400)
        
        # Connect to MongoDB
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]
        
        # Find the selected household
        results_collection = db["energy_trading"]
        selected_household = results_collection.find_one({"householdId": household_id})
        
        if not selected_household:
            return JsonResponse({"status": "error", "message": "Household not found"}, status=404)
        
        # Store the selection in session
        request.session['selected_household_id'] = household_id
        messages.success(request, f"Household {household_id} selected successfully.")
        
        # Redirect back to the report page
        return redirect(reverse('energy_report'))
        
    except Exception as e:
        messages.error(request, f"Error selecting household: {str(e)}")
        return redirect(reverse('energy_report'))