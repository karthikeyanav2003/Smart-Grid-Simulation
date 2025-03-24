from django.shortcuts import render
from django.conf import settings
import pandas as pd
import numpy as np


def home(request):
    return render(request, 'index.html')

def main_view(request):
    return render(request, 'main.html')
