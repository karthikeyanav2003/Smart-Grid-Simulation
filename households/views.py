from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import uuid
import json
import logging
from datetime import datetime
from .utils.graph_utils import create_interactive_graphs  # Ensure this file exists in households/utils/

# Configure logging with detailed configuration; logs will be appended to household_views.log
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='household_views.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

# ------------------------------
# MongoDB Connection Management
# ------------------------------
class MongoDBConnection:
    """Robust MongoDB connection management with retry and error handling."""
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        """Establish a MongoDB connection with comprehensive error handling."""
        try:
            self.client = MongoClient(
                "mongodb+srv://vishwarprediscan:zT0K3JICskXrc44W@household.ipekb.mongodb.net/",
                serverSelectionTimeoutMS=10000,  # 10-second timeout
                socketTimeoutMS=10000
            )
            self.db = self.client["Smartgrid"]
            self.collection = self.db["energydata"]
            logger.info("Successfully established MongoDB connection")
        except Exception as e:
            logger.error(f"Critical MongoDB Connection Error: {e}")
            raise ConnectionError(f"Cannot connect to MongoDB: {e}")

    def get_collection(self):
        """Return the collection, reconnecting if necessary."""
        if not hasattr(self, 'collection'):
            self._connect()
        return self.collection

# Singleton instance of MongoDB connection.
mongo_connection = MongoDBConnection()

# ------------------------------
# Views for the Application
# ------------------------------

def home(request):
    """Render the home page (index.html)."""
    return render(request, 'index.html')

def main_view(request):
    """
    Retrieve and display the latest household energy data.
    Handles potential data retrieval errors gracefully.
    """
    try:
        collection = mongo_connection.get_collection()
        latest_data = list(collection.find().sort('_id', -1).limit(10))
        # Convert MongoDB ObjectId to string for JSON serialization.
        for item in latest_data:
            item['_id'] = str(item['_id'])
        return render(request, 'main.html', {'data_list': latest_data})
    except Exception as e:
        logger.error(f"Data retrieval error in main_view: {e}")
        return render(request, 'main.html', {
            'error': 'Unable to fetch data. Please try again later.',
            'error_details': str(e)
        })

def household_data(request, household_id):
    """
    Retrieve specific household data by household ID.
    Provides detailed error responses for various scenarios.
    """
    try:
        collection = mongo_connection.get_collection()
        latest_data = collection.find_one(
            {"householdId": household_id},
            sort=[("_id", -1)]
        )
        if latest_data:
            latest_data['_id'] = str(latest_data['_id'])
            return JsonResponse(latest_data)
        return JsonResponse({
            'error': f'No data found for household {household_id}',
            'status': 'not_found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error retrieving household data for ID {household_id}: {e}")
        return JsonResponse({
            'error': 'An unexpected error occurred while fetching household data',
            'details': str(e)
        }, status=500)

def form_view(request):
    """Render the household data submission form."""
    return render(request, 'form.html')

@csrf_exempt
@require_http_methods(["GET", "POST"])
def add_household(request):
    """
    Handle household data submission.
    Provides comprehensive validation and error handling.
    """
    if request.method == "GET":
        return render(request, 'form.html')
    
    try:
        # Flexibly handle different input formats.
        data = (
            json.loads(request.body)
            if request.content_type == 'application/json'
            else request.POST
        )
        
        # Enhanced field validation.
        required_fields = [
            'householdId', 'voltage', 'current', 'powerConsumption',
            'solarPower', 'windPower', 'gridSupply', 'overloadCondition',
            'transformerFault', 'temperature', 'humidity',
            'electricityPrice', 'predictedLoad'
        ]
        missing_fields = [field for field in required_fields if field not in data or data[field] == ""]
        if missing_fields:
            return JsonResponse({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        try:
            # Safe type conversion with error handling.
            household_data_dict = {
                "_id": str(uuid.uuid4()),
                "householdId": data.get("householdId"),
                "voltage": float(data.get("voltage")),
                "current": float(data.get("current")),
                "powerConsumption": float(data.get("powerConsumption")),
                "solarPower": float(data.get("solarPower")),
                "windPower": float(data.get("windPower")),
                "gridSupply": float(data.get("gridSupply")),
                "overloadCondition": int(data.get("overloadCondition")),
                "transformerFault": int(data.get("transformerFault")),
                "temperature": float(data.get("temperature")),
                "humidity": float(data.get("humidity")),
                "electricityPrice": float(data.get("electricityPrice")),
                "predictedLoad": float(data.get("predictedLoad")),
                "timestamp": datetime.utcnow()
            }
        except ValueError as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid data format: {e}',
                'problematic_fields': [field for field, value in data.items() if not _is_valid_numeric(value)]
            }, status=400)
        
        # Insert data into MongoDB.
        collection = mongo_connection.get_collection()
        collection.insert_one(household_data_dict)
        logger.info(f"Household data inserted successfully. ID: {household_data_dict['_id']}")
        return JsonResponse({
            'status': 'success',
            'message': 'Household data added successfully',
            'household_id': household_data_dict['_id']
        }, status=201)
    
    except Exception as e:
        logger.error(f"Unexpected error in add_household: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected system error occurred',
            'error_details': str(e)
        }, status=500)

def _is_valid_numeric(value):
    """
    Utility function to validate if a value can be converted to a numeric type.
    Helps identify problematic fields during data validation.
    """
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

# ------------------------------
# NEW: Search Households View
# ------------------------------
def search_households(request):
    """
    Search for household documents in MongoDB by householdId (case-insensitive).
    Returns a JSON list of matching household IDs.
    """
    try:
        query = request.GET.get('query', '')
        collection = mongo_connection.get_collection()
        # Perform a case-insensitive regex search on the "householdId" field.
        cursor = collection.find({"householdId": {"$regex": query, "$options": "i"}})
        matching_ids = [doc["householdId"] for doc in cursor]
        logger.info(f"search_households found {len(matching_ids)} matches for query: '{query}'")
        return JsonResponse(matching_ids, safe=False)
    except Exception as e:
        logger.error(f"Error in search_households: {e}")
        return JsonResponse({"error": "An unexpected error occurred during search.", "details": str(e)}, status=500)

# ------------------------------
# NEW: Energy Graphs View
# ------------------------------
def energy_graphs_view(request, household_id):
    """
    Retrieve the latest energy data for a household,
    create interactive Plotly graphs using the provided utility,
    and return the configurations as JSON.
    """
    try:
        collection = mongo_connection.get_collection()
        data = collection.find_one({"householdId": household_id}, sort=[("_id", -1)])
        if data:
            data['_id'] = str(data['_id'])
            graphs = create_interactive_graphs(data)
            return JsonResponse(graphs)
        else:
            return JsonResponse({'error': f'No data found for household {household_id}'}, status=404)
    except Exception as e:
        logger.error(f"Error in energy_graphs_view for household_id {household_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)
