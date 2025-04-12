import pandas as pd
import hashlib
from pymongo import MongoClient
from django.conf import settings

# Function to hash household ID
def hash_household_id(household_id):
    return hashlib.sha256(str(household_id).encode()).hexdigest()

# Connect to MongoDB using the imported config
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]
energy_collection = db["energydata"]
results_collection = db["energy_trading"]

# Fetch documents
data = list(energy_collection.find())

# Convert to DataFrame
df = pd.DataFrame(data)

# Check the columns to ensure they are as expected
print(df.columns)

# Required fields, update based on the provided column names
required_fields = [
    "householdId", "solarPower", "windPower", "powerConsumption",
    "voltage", "current", "electricityPrice", "overloadCondition", "transformerFault"
]

# Perform calculations
df["NetPower"] = (df["solarPower"] + df["windPower"] - df["powerConsumption"]).round(2)
df["Efficiency"] = (((df["solarPower"] + df["windPower"]) / df["powerConsumption"]) * 100).round(2)
df["OverloadRisk"] = (df["powerConsumption"] / (df["voltage"] * df["current"])).round(2)
df["AdjCost"] = (df["powerConsumption"] * df["electricityPrice"]).round(2)
df["NoFault"] = ((df["overloadCondition"] == 0) & (df["transformerFault"] == 0)).astype(int)
df["BothFaults"] = ((df["overloadCondition"] == 1) & (df["transformerFault"] == 1)).astype(int)
df["Role"] = df["NetPower"].apply(lambda x: "Producer" if x > 0 else "Consumer")

# Hash the household ID
df["householdId_hash"] = df["householdId"].apply(hash_household_id)

# Prepare fields for insertion
insert_fields = [
    "householdId","householdId_hash", "NetPower", "Efficiency", "OverloadRisk",
    "AdjCost", "NoFault", "BothFaults", "Role"
]

# Convert to dict
records_to_insert = df[insert_fields].to_dict(orient="records")

# Insert into new collection
if records_to_insert:
    results_collection.delete_many({})  # optional: clear existing
    results_collection.insert_many(records_to_insert)
    print(f"{len(records_to_insert)} hashed records inserted.")
else:
    print("No valid records to insert.")
