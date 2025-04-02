from django.http import JsonResponse
from django.shortcuts import render
from pymongo import MongoClient
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='trading_debug.log',
    filemode='a'
)
logger = logging.getLogger(__name__)


class MongoDBConnection:
    """
    MongoDB Connection Manager (Singleton Pattern)
    """
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        try:
            # In production, use environment variables or Django settings for credentials.
            connection_params = {
                "host": os.getenv("MONGO_URI", "mongodb+srv://vishwarprediscan:zT0K3JICskXrc44W@household.ipekb.mongodb.net/"),
                "serverSelectionTimeoutMS": 15000,
                "socketTimeoutMS": 15000,
                "connectTimeoutMS": 15000,
                "retryWrites": True
            }
            self.client = MongoClient(**connection_params)
            self.db = self.client["Smartgrid"]
            self.collection = self.db["energydata"]
            self.client.server_info()  # Verify connection
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.critical(f"MongoDB Connection Error: {e}", exc_info=True)
            raise ConnectionError(f"MongoDB Connection Error: {e}")

    def get_collection(self):
        return self.collection

# Instantiate MongoDB connection
mongo_connection = MongoDBConnection()

def determine_trading_status(overload, transformer_fault, surplus_energy):
    """
    Determines trading status and role based on grid conditions and surplus energy.
    
    Args:
        overload (int): 1 if grid is overloaded, 0 otherwise.
        transformer_fault (int): 1 if there is a transformer fault, 0 otherwise.
        surplus_energy (float): Surplus energy for the household.
        
    Returns:
        tuple: (trading_status, role)
            - trading_status: "Not Allowed" if grid conditions are critical, else "Allowed".
            - role: "Producer" if surplus_energy is zero or positive, "Consumer" if negative.
    """
    if overload == 1 or transformer_fault == 1:
        logger.info("Critical grid condition detected. Trading disabled.")
        trading_status = "Not Allowed"
    else:
        trading_status = "Allowed"

    role = "Producer" if surplus_energy >= 0 else "Consumer"
    return trading_status, role

def calculate_energy_data():
    """
    Calculates energy data for each household by summing solar and wind production,
    subtracting power consumption, and determining trading status and role.
    
    Returns:
        list: A list of dictionaries containing energy data for each household.
    """
    collection = mongo_connection.get_collection()
    household_ids = collection.distinct("householdId")
    energy_results = []

    for household in household_ids:
        household_data = list(collection.find({"householdId": household}))
        if not household_data:
            logger.warning(f"No data found for household ID: {household}")
            continue

        # Retrieve grid condition flags from the first record
        overload = int(household_data[0].get("overload", 0))
        transformer_fault = int(household_data[0].get("transformerFault", 0))

        # Calculate total production from solar and wind
        total_production = sum(
            float(entry.get("solarPower", 0)) + float(entry.get("windPower", 0))
            for entry in household_data
        )
        # Calculate total power consumption
        power_consumption = sum(
            float(entry.get("Power Consumption", 0))
            for entry in household_data
        )
        
        # Surplus energy is total production minus consumption
        surplus_energy = total_production - power_consumption

        # Debug log for computed values
        logger.debug(
            f"Household {household}: total_production={total_production}, "
            f"power_consumption={power_consumption}, surplus_energy={surplus_energy}"
        )

        # Determine trading status and role
        trading_status, role = determine_trading_status(overload, transformer_fault, surplus_energy)

        energy_results.append({
            "House Hold ID": household,
            "Surplus Energy (kWh)": round(surplus_energy, 2),
            "Trading Status": trading_status,
            "Role": role
        })

    return energy_results

def energy_summary(request):
    """
    JSON endpoint to return energy data for all households.
    
    Args:
        request: Django HTTP request object.
        
    Returns:
        JsonResponse: JSON response containing energy data or error message.
    """
    try:
        energy_data = calculate_energy_data()
        return JsonResponse({"energy_data": energy_data}, safe=False)
    except Exception as e:
        logger.error(f"Error in energy_summary view: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)

def energy_report(request):
    """
    Renders the report.html template which displays the energy data in a table.
    
    Args:
        request: Django HTTP request object.
        
    Returns:
        Rendered HTML page.
    """
    try:
        energy_data = calculate_energy_data()
        return render(request, 'report.html', {"energy_data": energy_data})
    except Exception as e:
        logger.error(f"Error in energy_report view: {e}", exc_info=True)
        return render(request, 'report.html', {"error": str(e)})
