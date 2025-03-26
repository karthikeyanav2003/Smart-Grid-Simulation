from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from households import views as households_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('main/', households_views.main_view, name='main'),
    path('household_data/<str:household_id>/', households_views.household_data, name='household_data'),
    path('add-household/', households_views.add_household, name='add_household'),  # New URL for form submission
]
