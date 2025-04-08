from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from households import views as households_views
from trading import views as trading_views

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),

    # Landing page (index)
    path('', TemplateView.as_view(template_name='index.html'), name='index'),

    # User authentication (login, signup, logout)
    path('users/', include('users.urls')),

    # Main dashboard (protected view after login)
    path('main/', households_views.main_view, name='main'),

    # Report page (supports both /main/report/ and /main/report.html)
    path('main/report/', TemplateView.as_view(template_name='report.html'), name='report'),
    path('main/report.html', TemplateView.as_view(template_name='report.html'), name='report_html'),

    # Energy summary JSON endpoint (used in graphs/analytics)
    path('main/energy-summary/', trading_views.energy_summary, name='energy_summary'),

    # Household-related operations
    path('household_data/<str:household_id>/', households_views.household_data, name='household_data'),
    path('add-household/', households_views.add_household, name='add_household'),
    path('search_households/', households_views.search_households, name='search_households'),
    path('energy_graphs_view/<str:household_id>/', households_views.energy_graphs_view, name='energy_graphs_view'),
    path('list_households/', households_views.list_households, name='list_households'),
]
