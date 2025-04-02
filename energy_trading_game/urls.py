from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from households import views as households_views
from trading import views as trading_views  # Import from the correct module
urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),
    # Home/Index page
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    # Main dashboard view
    path('main/', households_views.main_view, name='main'),
    # Main report page
    path('main/report.html', TemplateView.as_view(template_name='report.html'), name='report'),
    # Energy Summary JSON endpoint (imported from trading.views)
    path('main/energy-summary/', trading_views.energy_summary, name='energy_summary'),
    # Household data endpoints
    path('household_data/<str:household_id>/', households_views.household_data, name='household_data'),
    path('add-household/', households_views.add_household, name='add_household'),
    path('search_households/', households_views.search_households, name='search_households'),
    # Energy graphs view endpoint
    path('energy_graphs_view/<str:household_id>/', households_views.energy_graphs_view, name='energy_graphs_view'),
    # Optional: Debug endpoint to list all households
    path('list_households/', households_views.list_households, name='list_households'),
]
