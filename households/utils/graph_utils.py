import plotly.graph_objs as go

def create_interactive_graphs(data):
    """
    Create interactive graphs for energy trading simulation using Plotly.

    Parameters:
        data (dict): Dictionary containing household energy data

    Returns:
        dict: JSON-serializable dictionary of graph configurations
    """
    graphs = {}

    # 1. Temperature vs Humidity Bubble Chart
    bubble_trace = go.Scatter(
        x=[data['temperature']],
        y=[data['humidity']],
        mode='markers',
        marker=dict(
            size=[data['powerConsumption'] * 10],
            color=[data['powerConsumption']],
            colorscale='Viridis',
            showscale=True
        ),
        text=[f'Power Consumption: {data["powerConsumption"]} kW'],
        hoverinfo='text'
    )
    
    bubble_layout = go.Layout(
        title='Temperature vs Humidity with Power Consumption',
        xaxis={'title': 'Temperature (°C)'},
        yaxis={'title': 'Humidity (%)'},
        hovermode='closest'
    )
    
    graphs['temperature_humidity_bubble'] = {
        'data': [bubble_trace],
        'layout': bubble_layout
    }
    
    # 2. Bar Chart - Power Sources
    power_sources = ['Power Consumption', 'Solar Power', 'Wind Power', 'Grid Supply']
    power_values = [
        data.get('powerConsumption', 0),
        data.get('solarPower', 0),
        data.get('windPower', 0),
        data.get('gridSupply', 0)
    ]
    
    bar_trace = go.Bar(
        x=power_sources,
        y=power_values,
        marker_color=['red', 'yellow', 'blue', 'green'],
        text=[f'{val:.2f} kW' for val in power_values],
        textposition='auto'
    )
    
    bar_layout = go.Layout(
        title='Energy Sources Breakdown',
        xaxis={'title': 'Power Sources'},
        yaxis={'title': 'Power (kW)'}
    )
    
    graphs['power_sources_bar'] = {
        'data': [bar_trace],
        'layout': bar_layout
    }
    
    # 3. Heatmap - Grid Health Indicators
    heatmap_trace = go.Heatmap(
        z=[[int(data.get('overloadCondition', 0)), int(data.get('transformerFault', 0))]],
        x=['Overload Condition', 'Transformer Fault'],
        y=['Indicator'],
        colorscale=[[0, 'green'], [1, 'red']],
        hoverongaps=False,
        text=[[f'{int(data.get("overloadCondition", 0))}', f'{int(data.get("transformerFault", 0))}']],
        texttemplate='%{text}',
        textfont={"color": "white"}
    )
    
    heatmap_layout = go.Layout(
        title='Grid Health Indicators',
        xaxis={'title': 'Condition Type'},
        yaxis={'title': ''}
    )
    
    graphs['grid_health_heatmap'] = {
        'data': [heatmap_trace],
        'layout': heatmap_layout
    }
    
    # 4. Line Chart - Electricity Pricing vs Temperature
    line_trace = go.Scatter(
        x=[data['temperature']],
        y=[data['electricityPrice']],
        mode='markers+lines',
        marker=dict(color='purple', size=10),
        line=dict(color='purple', width=2)
    )
    
    line_layout = go.Layout(
        title='Electricity Pricing vs Temperature',
        xaxis={'title': 'Temperature (°C)'},
        yaxis={'title': 'Electricity Price ($/kWh)'}
    )
    
    graphs['electricity_price_line'] = {
        'data': [line_trace],
        'layout': line_layout
    }
    
    # 5. Scatter Plot - Power Flow Analysis (Voltage vs Current)
    scatter_trace = go.Scatter(
        x=[data['current']],
        y=[data['voltage']],
        mode='markers',
        marker=dict(
            size=15,
            color='orange',
            opacity=0.7
        ),
        text=[f'Current: {data["current"]} A\nVoltage: {data["voltage"]} V'],
        hoverinfo='text'
    )
    
    scatter_layout = go.Layout(
        title='Power Flow: Voltage vs Current',
        xaxis={'title': 'Current (A)'},
        yaxis={'title': 'Voltage (V)'}
    )
    
    graphs['power_flow_scatter'] = {
        'data': [scatter_trace],
        'layout': scatter_layout
    }
    
    return graphs
