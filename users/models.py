from djongo import models

class User(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField()
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)  # Will store hashed password
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users'  # Collection name in MongoDB