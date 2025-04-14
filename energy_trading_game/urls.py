from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from households import views as households_views
from trading import views as trading_views # Make sure this points to your trading app's views

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),

    # Landing page (index)
    path('', TemplateView.as_view(template_name='index.html'), name='index'),

    # User authentication (login, signup, logout)
    path('users/', include('users.urls')), # Assumes you have a 'users' app with its own urls.py

    # Main dashboard (protected view after login)
    path('main/', households_views.main_view, name='main'), # Assumes main_view is in households app

    # Report page served with calculated energy trading data (calculated on-the-fly)
    path('main/report/', trading_views.report_view, name='report'), # Correctly points to report_view
    path('main/report.html', RedirectView.as_view(url='/main/report/', permanent=True)), # Redirect is fine

    # API endpoint for energy trading data (calculated on-the-fly)
    path('api/energy-trading/data/', trading_views.energy_trading_data, name='energy_trading_data'), # Correctly points to energy_trading_data

    # *** UPDATED LINE BELOW ***
    # Optional: Endpoint to explicitly trigger update of the 'energy_trading' collection
    path('api/update-trading-data/', trading_views.update_energy_trading_collection, name='update_trading_data'),

    # Household-related operations (Assuming these are correct for your 'households' app)
    path('household_data/<str:household_id>/', households_views.household_data, name='household_data'),
    path('add-household/', households_views.add_household, name='add_household'),
    path('search_households/', households_views.search_households, name='search_households'),
    path('energy_graphs_view/<str:household_id>/', households_views.energy_graphs_view, name='energy_graphs_view'),
    path('list_households/', households_views.list_households, name='list_households'),
]