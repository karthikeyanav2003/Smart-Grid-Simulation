"""
URL configuration for energy_trading_game project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from households import views as households_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('main/', households_views.main_view, name='main'),
    path('household_data/<str:household_id>/', households_views.household_data, name='household_data'),
]