from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import uuid
import json
import logging
from datetime import datetime, timedelta

# Advanced Logging Configuration
logging.basicConfig(
    level=logging.DEBUG,  # Increased to DEBUG for more comprehensive logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='smart_grid_debug.log',
    filemode='a'
)
logger = logging.getLogger(__name__)


class MongoDBConnection:
    """
    Robust MongoDB Connection Management with Enhanced Error Handling
    
    Key Features:
    - Singleton pattern
    - Dynamic connection retry
    - Comprehensive error tracking
    """
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        """
        Establish a secure and resilient MongoDB connection.
        """
        try:
            connection_params = {
                "host": "mongodb+srv://vishwarprediscan:zT0K3JICskXrc44W@household.ipekb.mongodb.net/",
                "serverSelectionTimeoutMS": 15000,  # Increased timeout
                "socketTimeoutMS": 15000,
                "connectTimeoutMS": 15000,
                "retryWrites": True
            }
            self.client = MongoClient(**connection_params)
            self.db = self.client["Smartgrid"]
            self.collection = self.db["energydata"]

            # Verify connection
            self.client.server_info()
            logger.info("Successfully established robust MongoDB connection")
        except Exception as e:
            logger.critical(f"Critical MongoDB Connection Failure: {e}", exc_info=True)
            raise ConnectionError(f"MongoDB Connection Error: {e}")

    def get_collection(self):
        """
        Retrieve MongoDB collection with automatic reconnection.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not hasattr(self, 'collection'):
                    self._connect()
                return self.collection
            except Exception as e:
                logger.warning(f"Collection retrieval attempt {attempt + 1} failed: {e}", exc_info=True)
                if attempt == max_retries - 1:
                    raise


mongo_connection = MongoDBConnection()


def energy_graphs_view(request, household_id):
    """
    Generates Chart.js data for energy graphs for the given household
    without using timestamp filtering.

    Returns JSON with:
    - temperature_humidity_bubble: Data for a bubble chart (Temperature vs. Humidity)
    - power_sources_bar: Data for a bar chart (Breakdown of energy sources: Solar, Wind, Grid)
    """
    try:
        collection = mongo_connection.get_collection()
        logger.info(f"Generating graphs for household: {household_id}")

        # Retrieve all available data for the household
        household_data = list(collection.find({"householdId": household_id}))

        if not household_data:
            existing_households = list(collection.distinct('householdId'))
            logger.warning(f"No data for {household_id}. Available: {existing_households}")
            return JsonResponse({
                'error': 'No data available',
                'available_households': existing_households
            }, status=404)

        # Prepare Bubble Chart data (Temperature vs Humidity)
        bubble_data = []
        for entry in household_data:
            bubble_data.append({
                "x": entry.get("temperature", 0),
                "y": entry.get("humidity", 0),
                "r": entry.get("powerConsumption", 0) / 10  # scaling factor for bubble size
            })

        # Prepare Bar Chart data (Energy Sources Breakdown)
        total_solar = sum(entry.get("solarPower", 0) for entry in household_data)
        total_wind = sum(entry.get("windPower", 0) for entry in household_data)
        total_grid = sum(entry.get("gridSupply", 0) for entry in household_data)
        bar_data = {
            "labels": ["Solar", "Wind", "Grid"],
            "values": [total_solar, total_wind, total_grid]
        }

        graphs_data = {
            "temperature_humidity_bubble": {
                "data": bubble_data
            },
            "power_sources_bar": {
                "data": bar_data
            }
        }

        return JsonResponse(graphs_data, safe=False)

    except Exception as e:
        logger.error(f"Graph generation error for {household_id}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'System error during graph generation',
            'details': str(e)
        }, status=500)


def list_households(request):
    """
    Debug endpoint to list all households in the system.
    """
    try:
        collection = mongo_connection.get_collection()
        households = list(collection.distinct('householdId'))
        return JsonResponse({
            'total_households': len(households),
            'households': households
        })
    except Exception as e:
        logger.error(f"Household listing error: {e}", exc_info=True)
        return JsonResponse({'error': 'Could not retrieve households'}, status=500)


def household_data(request, household_id):
    """
    Retrieve specific household data by household ID.
    Provides detailed error responses for various scenarios.
    """
    try:
        collection = mongo_connection.get_collection()
        latest_data = collection.find_one({"householdId": household_id}, sort=[("_id", -1)])
        if latest_data:
            latest_data['_id'] = str(latest_data['_id'])
            return JsonResponse(latest_data)
        logger.warning(f"No data found for household {household_id}")
        return JsonResponse({
            'error': f'No data found for household {household_id}',
            'status': 'not_found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error retrieving household data for ID {household_id}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'An unexpected error occurred while fetching household data',
            'details': str(e)
        }, status=500)


def main_view(request):
    """
    Render the main dashboard view.
    """
    return render(request, 'main.html')


def form_view(request):
    """
    Render the household data submission form.
    """
    return render(request, 'form.html')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def add_household(request):
    """
    Handle household data submission with comprehensive validation.
    Supports multiple input formats and provides robust error handling.
    """
    if request.method == "GET":
        return render(request, 'form.html')

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        required_fields = [
            'householdId', 'voltage', 'current', 'powerConsumption',
            'solarPower', 'windPower', 'gridSupply', 'overloadCondition',
            'transformerFault', 'temperature', 'humidity',
            'electricityPrice', 'predictedLoad'
        ]
        missing_fields = [field for field in required_fields if field not in data or data[field] == ""]
        if missing_fields:
            logger.debug(f"Missing fields in submission: {missing_fields}")
            return JsonResponse({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)

        try:
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
            logger.debug(f"Data conversion error: {e} | Data received: {data}")
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid data format: {e}',
                'problematic_fields': [field for field, value in data.items() if not _is_valid_numeric(value)]
            }, status=400)

        collection = mongo_connection.get_collection()
        collection.insert_one(household_data_dict)
        logger.info(f"Household data inserted successfully. ID: {household_data_dict['_id']}")
        return JsonResponse({
            'status': 'success',
            'message': 'Household data added successfully',
            'household_id': household_data_dict['_id']
        }, status=201)

    except Exception as e:
        logger.error(f"Unexpected error in add_household: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected system error occurred',
            'error_details': str(e)
        }, status=500)


def _is_valid_numeric(value):
    """
    Utility function to validate numeric convertibility.
    Helps identify problematic fields during data validation.
    """
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def search_households(request):
    """
    Search for household documents by householdId (case-insensitive).
    Returns a JSON list of matching household IDs.
    """
    try:
        query = request.GET.get('query', '')
        collection = mongo_connection.get_collection()
        cursor = collection.find({"householdId": {"$regex": query, "$options": "i"}})
        matching_ids = [doc["householdId"] for doc in cursor]
        logger.info(f"search_households found {len(matching_ids)} matches for query: '{query}'")
        return JsonResponse(matching_ids, safe=False)
    except Exception as e:
        logger.error(f"Error in search_households: {e}", exc_info=True)
        return JsonResponse({
            "error": "An unexpected error occurred during search.",
            "details": str(e)
        }, status=500)


def plotGraphs(request, household_id):
    """
    This view is called via AJAX to fetch additional graph data.
    It plots two graphs:
    - A bubble chart for Temperature vs. Humidity.
    - A bar chart for the breakdown of energy sources (Solar, Wind, Grid).
    
    Note: The canvas elements in the HTML must have IDs:
          'temperatureHumidityBubbleChart' for the bubble chart and
          'energyMixChart' for the bar chart.
    """
    try:
        collection = mongo_connection.get_collection()
        logger.info(f"Plotting additional graphs for household: {household_id}")

        household_data = list(collection.find({"householdId": household_id}))
        if not household_data:
            existing_households = list(collection.distinct('householdId'))
            logger.warning(f"No data for {household_id}. Available: {existing_households}")
            return JsonResponse({
                'error': 'No data available',
                'available_households': existing_households
            }, status=404)

        # Prepare bubble chart data: Temperature vs. Humidity.
        bubble_data = []
        for entry in household_data:
            bubble_data.append({
                "x": entry.get("temperature", 0),
                "y": entry.get("humidity", 0),
                "r": entry.get("powerConsumption", 0) / 10  # scaling factor
            })

        # Prepare bar chart data: Breakdown of energy sources.
        total_solar = sum(entry.get("solarPower", 0) for entry in household_data)
        total_wind = sum(entry.get("windPower", 0) for entry in household_data)
        total_grid = sum(entry.get("gridSupply", 0) for entry in household_data)
        bar_data = {
            "labels": ["Solar", "Wind", "Grid"],
            "values": [total_solar, total_wind, total_grid]
        }

        graphs_data = {
            "temperature_humidity_bubble": {
                "data": bubble_data
            },
            "power_sources_bar": {
                "data": bar_data
            }
        }

        return JsonResponse(graphs_data, safe=False)

    except Exception as e:
        logger.error(f"Graph plotting error for {household_id}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'System error during graph plotting',
            'details': str(e)
        }, status=500)
