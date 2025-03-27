from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from households import views as households_views

urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),

    # Home page (renders index.html)
    path('', TemplateView.as_view(template_name='index.html'), name='index'),

    # Main simulation page; displays latest energy data, household list, and graphs
    path('main/', households_views.main_view, name='main'),

    # Endpoint to fetch detailed data for a specific household.
    # The household_id is passed as a URL parameter.
    path('household_data/<str:household_id>/', households_views.household_data, name='household_data'),

    # Endpoint for adding a new household record via form submission.
    path('add-household/', households_views.add_household, name='add_household'),

    # Endpoint for searching households by their ID.
    # This view should return a JSON list of matching household IDs.
    path('search_households/', households_views.search_households, name='search_households'),

    # Endpoint for generating Plotly graphs for a given household.
    # The energy_graphs_view function retrieves the latest household data,
    # creates interactive graphs, and returns them as JSON.
    path('energy_graphs_view/<str:household_id>/', households_views.energy_graphs_view, name='energy_graphs_view'),
]
