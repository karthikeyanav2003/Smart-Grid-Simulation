from django.db import models
from djongo import models as djongo_models

class HouseholdData(models.Model):
    """
    Model representing household energy data for MongoDB
    
    This model defines the structure for storing household energy-related information
    with various fields capturing different aspects of energy consumption and environmental conditions.
    """
    # Unique identifier for the household
    household_id = models.CharField(
        max_length=100, 
        primary_key=True, 
        unique=True,
        verbose_name="Unique Household Identifier"
    )
    
    # Electrical measurements
    voltage = models.FloatField(
        verbose_name="Electrical Voltage",
        help_text="Voltage measurement in Volts",
        null=False
    )
    
    current = models.FloatField(
        verbose_name="Electrical Current",
        help_text="Current measurement in Amperes",
        null=False
    )
    
    power_consumption = models.FloatField(
        verbose_name="Total Power Consumption",
        help_text="Power consumption in kilowatts (kW)",
        null=False
    )
    
    # Renewable energy sources
    solar_power = models.FloatField(
        verbose_name="Solar Power Generation",
        help_text="Solar power generation in kilowatts (kW)",
        default=0.0
    )
    
    wind_power = models.FloatField(
        verbose_name="Wind Power Generation",
        help_text="Wind power generation in kilowatts (kW)",
        default=0.0
    )
    
    grid_supply = models.FloatField(
        verbose_name="Grid Power Supply",
        help_text="Power supplied from the electrical grid in kilowatts (kW)",
        null=False
    )
    
    # Status indicators
    overload_condition = models.BooleanField(
        verbose_name="Overload Status",
        help_text="Indicates whether the system is experiencing an overload",
        default=False
    )
    
    transformer_fault = models.BooleanField(
        verbose_name="Transformer Fault",
        help_text="Indicates the presence of a transformer fault",
        default=False
    )
    
    # Environmental conditions
    temperature = models.FloatField(
        verbose_name="Ambient Temperature",
        help_text="Temperature in degrees Celsius",
        null=False
    )
    
    humidity = models.FloatField(
        verbose_name="Humidity Level",
        help_text="Humidity percentage",
        null=False
    )
    
    # Economic metrics
    electricity_price = models.FloatField(
        verbose_name="Electricity Price",
        help_text="Price of electricity per kilowatt-hour",
        null=False
    )
    
    predicted_load = models.FloatField(
        verbose_name="Predicted Energy Load",
        help_text="Predicted energy load in kilowatts (kW)",
        null=False
    )
    
    # Timestamp for record creation
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Record Creation Timestamp"
    )
    
    class Meta:
        """
        Meta options for the HouseholdData model
        
        - db_table specifies the collection name in MongoDB
        - ordering ensures records are sorted by creation time
        """
        db_table = 'household_energy_data'
        ordering = ['-created_at']
        
        # Optional: Add a unique constraint on household_id
        constraints = [
            models.UniqueConstraint(
                fields=['household_id'], 
                name='unique_household_id'
            )
        ]
    
    def __str__(self):
        """
        String representation of the model instance
        
        Returns a human-readable representation of the household data
        """
        return f"Household {self.household_id} - Power Consumption: {self.power_consumption} kW"
    
    def save(self, *args, **kwargs):
        """
        Custom save method with optional validation
        
        Performs additional checks before saving the record
        """
        # Optional: Add custom validation logic
        self.full_clean()  # Validates model fields
        
        # Log or perform additional actions before saving
        print(f"Saving household data for ID: {self.household_id}")
        
        super().save(*args, **kwargs)