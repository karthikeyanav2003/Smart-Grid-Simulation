from django.http import JsonResponse, HttpResponseServerError
from django.conf import settings
from django.shortcuts import render
from pymongo import MongoClient
import pandas as pd
import hashlib
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

def hash_household_id(household_id):
    """Returns a SHA-256 hash of the household_id."""
    return hashlib.sha256(str(household_id).encode()).hexdigest()

def _calculate_trading_data_from_source(db, incremental=False, last_processed_time=None):
    """
    Reads raw data from 'energydata', performs calculations, and returns the processed data as a list of dictionaries.
    Supports incremental updates by processing only new or updated records based on last_processed_time.
    Handles missing columns by setting them to default values.
    
    Parameters:
    - db: MongoDB database connection
    - incremental: Boolean flag for incremental updates
    - last_processed_time: Datetime for filtering new records in incremental mode
    
    Returns:
    - Dictionary with 'data' (list of calculated records) or 'error' (error message)
    """
    try:
        source_collection = db["energydata"]
        
        # Build query for incremental updates
        query = {}
        if incremental and last_processed_time:
            query = {"last_updated": {"$gt": last_processed_time}}
        
        # Fetch data, sorted by last_updated to ensure latest records are processed last
        raw_data = list(source_collection.find(query).sort("last_updated", 1))
        if not raw_data:
            message = "No new data in 'energydata'." if incremental else "Source collection 'energydata' is empty."
            return {"data": [], "message": message}
        
        # Load into DataFrame
        df = pd.DataFrame(raw_data)
        
        # Select the latest record per household_id
        if not df.empty:
            df = df.sort_values("last_updated", ascending=True).groupby("household_id").last().reset_index()
        
        # Define required columns from energydata
        required_columns = [
            "Solar Power (kW)", "Wind Power (kW)", "Power Consumption (kW)",
            "Voltage (V)", "Current (A)", "Electricity Price (USD/kWh)",
            "Grid Supply (kW)", "Overload Condition", "Transformer Fault", "household_id"
        ]
        
        # Handle missing columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"Missing columns in 'energydata': {missing_columns}. Setting to 0.")
            for col in missing_columns:
                df[col] = 0
        
        # Ensure numeric columns are properly typed
        numeric_columns = [
            "Solar Power (kW)", "Wind Power (kW)", "Power Consumption (kW)",
            "Voltage (V)", "Current (A)", "Electricity Price (USD/kWh)",
            "Grid Supply (kW)", "Overload Condition", "Transformer Fault"
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Perform calculations
        df["Net Power (kW)"] = (df["Solar Power (kW)"] + df["Wind Power (kW)"] - df["Power Consumption (kW)"]).round(2)
        
        df["Efficiency (%)"] = df.apply(
            lambda row: round(((row["Solar Power (kW)"] + row["Wind Power (kW)"]) / row["Power Consumption (kW)"]) * 100, 2)
            if row["Power Consumption (kW)"] != 0 else 0,
            axis=1
        )
        
        df["Overload Risk"] = df.apply(
            lambda row: round(row["Power Consumption (kW)"] / (row["Voltage (V)"] * row["Current (A)"]), 2)
            if (row["Voltage (V)"] * row["Current (A)"]) != 0 else 0,
            axis=1
        )
        
        df["Adjusted Cost"] = (df["Power Consumption (kW)"] * df["Electricity Price (USD/kWh)"]).round(2)
        
        denominator = df["Solar Power (kW)"] + df["Wind Power (kW)"] + df["Grid Supply (kW)"]
        df["RenRatio"] = ((df["Solar Power (kW)"] + df["Wind Power (kW)"]) / denominator).fillna(0).round(2)
        df.loc[denominator == 0, "RenRatio"] = 0
        
        df["No Fault"] = ((df["Overload Condition"] == 0) & (df["Transformer Fault"] == 0)).astype(int)
        df["Both Faults"] = ((df["Overload Condition"] == 1) & (df["Transformer Fault"] == 1)).astype(int)
        
        # Role and Trading Status are the same concept as per the requirement
        df["Role"] = df["Net Power (kW)"].apply(lambda x: "Producer" if x > 0 else ("Consumer" if x < 0 else "Balanced"))
        df["Trading Status"] = df["Role"]  # Trading Status is synonymous with Role
        
        df["electricity price"] = df["Electricity Price (USD/kWh)"].round(2)
        df["householdId_hash"] = df["household_id"].apply(hash_household_id)
        df["last_updated"] = df.get("last_updated", pd.Series([datetime.utcnow()] * len(df), index=df.index))
        
        # Select final columns
        output_columns = [
            "household_id", "householdId_hash", "Net Power (kW)", "Efficiency (%)", "Overload Risk",
            "Adjusted Cost", "No Fault", "Both Faults", "Role", "Trading Status", "electricity price",
            "last_updated"
        ]
        calculated_data = df[output_columns].to_dict(orient="records")
        
        return {"data": calculated_data}
    
    except Exception as e:
        error_msg = f"Error during data calculation: {str(e)}"
        logger.exception(error_msg)
        return {"error": error_msg, "error_type": "calculation_error"}

def update_energy_trading_collection(request):
    """
    View to trigger calculation of data from 'energydata' and store it in 'energy_trading'.
    Supports full refresh (incremental=false) or incremental update (incremental=true) via query parameter.
    
    URL Example: /update_energy_trading/?incremental=true 

    """
    client = None
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]
        
        # Determine if incremental update is requested
        incremental = request.GET.get('incremental', 'false').lower() == 'true'
        last_processed_time = None
        if incremental:
            latest_record = db["energy_trading"].find_one(sort=[("last_updated", -1)])
            last_processed_time = latest_record.get("last_updated") if latest_record else None
        
        # Calculate data
        calculation_result = _calculate_trading_data_from_source(db, incremental=incremental, last_processed_time=last_processed_time)
        
        if "error" in calculation_result:
            return JsonResponse({"error": calculation_result["error"]}, status=500)
        
        calculated_data = calculation_result.get("data", [])
        message = calculation_result.get("message", "")
        
        # Update energy_trading collection
        target_collection = db["energy_trading"]
        if calculated_data:
            if not incremental:
                # Full refresh: Clear and insert
                target_collection.delete_many({})
                target_collection.insert_many(calculated_data)
                insert_msg = f"Inserted {len(calculated_data)} records into 'energy_trading' (full refresh)."
            else:
                # Incremental update: Upsert based on household_id
                for record in calculated_data:
                    target_collection.update_one(
                        {"household_id": record["household_id"]},
                        {"$set": record},
                        upsert=True
                    )
                insert_msg = f"Upserted {len(calculated_data)} records into 'energy_trading' (incremental update)."
        else:
            insert_msg = f"No data to insert. {message}"
        
        return JsonResponse({"message": insert_msg, "records_processed": len(calculated_data)})
    
    except Exception as e:
        error_msg = f"Error updating energy_trading collection: {str(e)}"
        logger.exception(error_msg)
        return JsonResponse({"error": error_msg}, status=500)
    finally:
        if client:
            client.close()

def energy_trading_data(request):
    """
    API endpoint to fetch data from 'energy_trading' after performing an incremental update.
    Returns JSON data excluding MongoDB '_id' field.
    
    URL Example: /api/energy-trading/data/
    """
    client = None
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]
        
        # Perform incremental update
        latest_record = db["energy_trading"].find_one(sort=[("last_updated", -1)])
        last_processed_time = latest_record.get("last_updated") if latest_record else None
        calculation_result = _calculate_trading_data_from_source(db, incremental=True, last_processed_time=last_processed_time)
        
        if "error" in calculation_result:
            return HttpResponseServerError(JsonResponse({"error": calculation_result["error"]}))
        
        calculated_data = calculation_result.get("data", [])
        target_collection = db["energy_trading"]
        if calculated_data:
            for record in calculated_data:
                target_collection.update_one(
                    {"household_id": record["household_id"]},
                    {"$set": record},
                    upsert=True
                )
            logger.info(f"Upserted {len(calculated_data)} new records into 'energy_trading'.")
        
        # Fetch all data
        trading_data = list(target_collection.find({}, {"_id": 0}))
        return JsonResponse(trading_data, safe=False)
    
    except Exception as e:
        error_msg = f"Error in energy_trading_data endpoint: {str(e)}"
        logger.exception(error_msg)
        return HttpResponseServerError(JsonResponse({"error": error_msg}))
    finally:
        if client:
            client.close()

def report_view(request):
    """
    Renders report.html with data from 'energy_trading' after an incremental update.
    Passes trading_data and optional error/message to the template.
    
    URL Example: /main/report/
    """
    client = None
    context = {}
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]
        
        # Perform incremental update
        latest_record = db["energy_trading"].find_one(sort=[("last_updated", -1)])
        last_processed_time = latest_record.get("last_updated") if latest_record else None
        calculation_result = _calculate_trading_data_from_source(db, incremental=True, last_processed_time=last_processed_time)
        
        target_collection = db["energy_trading"]
        if "error" in calculation_result:
            context["error"] = calculation_result["error"]
            context["trading_data"] = []
        else:
            calculated_data = calculation_result.get("data", [])
            if calculated_data:
                for record in calculated_data:
                    target_collection.update_one(
                        {"household_id": record["household_id"]},
                        {"$set": record},
                        upsert=True
                    )
            # Fetch data for display
            trading_data = list(target_collection.find({}, {"_id": 0}))
            context["trading_data"] = trading_data
            context["message"] = f"Displaying {len(trading_data)} calculated record(s)."
        
        return render(request, 'report.html', context)
    
    except Exception as e:
        error_msg = f"Error rendering report view: {str(e)}"
        logger.exception(error_msg)
        context["error"] = "An unexpected error occurred while generating the report."
        context["trading_data"] = []
        return render(request, 'report.html', context)
    finally:
        if client:
            client.close()