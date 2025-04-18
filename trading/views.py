import pandas as pd
import hashlib
import numpy as np
import plotly.graph_objects as go
import networkx as nx
from pymongo import MongoClient
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse

# Configuration
GRID_BUY_PRICE = 0.13
GRID_SELL_PRICE = 0.15
SELLER_PRICE_LOW = GRID_BUY_PRICE + 0.01
SELLER_PRICE_HIGH = GRID_SELL_PRICE - 0.01
BUYER_PRICE_LOW = GRID_SELL_PRICE
BUYER_PRICE_HIGH = GRID_SELL_PRICE + 0.05

# Helper functions
def hash_household_id(household_id):
    return hashlib.sha256(str(household_id).encode()).hexdigest()

def merge(left, right, compare):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if compare(left[i], right[j]):
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

def merge_sort(arr, compare):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid], compare)
    right = merge_sort(arr[mid:], compare)
    return merge(left, right, compare)

def perform_trading(households):
    sellers = {n: d for n, d in households.items() if d['Role'] == 'seller' and d['NetPower'] > 0}
    buyers = {n: d for n, d in households.items() if d['Role'] == 'buyer' and d['NetPower'] < 0}

    compare_seller = lambda a, b: a[1]['NetPower'] > b[1]['NetPower']
    compare_buyer = lambda a, b: a[1]['NetPower'] < b[1]['NetPower']

    sorted_sellers = merge_sort(list(sellers.items()), compare_seller)
    sorted_buyers = merge_sort(list(buyers.items()), compare_buyer)

    trades = []

    # Peer-to-peer trading
    for s_name, s_data in sorted_sellers:
        for b_name, b_data in sorted_buyers:
            if s_data['remaining'] > 0 and b_data['remaining'] < 0:
                if b_data['electricityPrice'] >= s_data['electricityPrice']:
                    trade_qty = min(s_data['remaining'], -b_data['remaining'])
                    traded_price = (s_data['electricityPrice'] + b_data['electricityPrice']) / 2.0
                    
                    # Update seller
                    s_data['traded_units'] += trade_qty
                    s_data['total_price'] += trade_qty * traded_price
                    s_data['remaining'] -= trade_qty

                    # Update buyer
                    b_data['traded_units'] += trade_qty
                    b_data['total_price'] -= trade_qty * traded_price
                    b_data['remaining'] += trade_qty

                    trades.append({
                        'seller': s_name,
                        'buyer': b_name,
                        'quantity': trade_qty,
                        'price': traded_price
                    })

    # Grid trading
    for s_name, s_data in sellers.items():
        if s_data['remaining'] > 0:
            trade_qty = s_data['remaining']
            s_data['traded_units'] += trade_qty
            s_data['total_price'] += trade_qty * GRID_BUY_PRICE
            s_data['remaining'] = 0
            trades.append({
                'seller': s_name,
                'buyer': 'grid',
                'quantity': trade_qty,
                'price': GRID_BUY_PRICE
            })

    for b_name, b_data in buyers.items():
        if b_data['remaining'] < 0:
            trade_qty = -b_data['remaining']
            b_data['traded_units'] += trade_qty
            b_data['total_price'] -= trade_qty * GRID_SELL_PRICE
            b_data['remaining'] = 0
            trades.append({
                'seller': 'grid',
                'buyer': b_name,
                'quantity': trade_qty,
                'price': GRID_SELL_PRICE
            })
    
    return households, trades

def create_summary_chart(households):
    fig = go.Figure()
    names = list(households.keys())
    
    fig.add_trace(go.Bar(
        x=names,
        y=[h['traded_units'] for h in households.values()],
        name='Traded Units',
        marker_color='blue'
    ))
    
    fig.add_trace(go.Bar(
        x=names,
        y=[h['total_price'] for h in households.values()],
        name='Total Price',
        marker_color='green'
    ))
    
    fig.add_trace(go.Bar(
        x=names,
        y=[h['remaining'] for h in households.values()],
        name='Remaining',
        marker_color='orange'
    ))
    
    fig.update_layout(
        title='Energy Trading Summary',
        barmode='group',
        xaxis_title='Households',
        yaxis_title='Values'
    )
    return fig.to_html(full_html=False)

def create_network_graph(households, trades):
    G = nx.DiGraph()
    
    # Add nodes
    for name in households:
        G.add_node(name)
    G.add_node('grid')
    
    # Add edges
    for trade in trades:
        G.add_edge(trade['seller'], trade['buyer'], weight=trade['quantity'])
    
    # Create positions
    pos = nx.circular_layout(G)
    
    # Create edge traces
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')
    
    # Create node traces
    node_x = []
    node_y = []
    node_text = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        marker=dict(
            showscale=True,
            colorscale='YlGnBu',
            size=20,
            color=[],
            line_width=2))
    
    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title='Trading Network',
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
    
    return fig.to_html(full_html=False)

def energy_report(request):
    try:
        # MongoDB connection
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]
        energy_collection = db["energydata"]
        trading_collection = db["energy_trading"]
        
        # Fetch and process data
        raw_data = list(energy_collection.find())
        df = pd.DataFrame(raw_data)
        
        # Data validation
        required_fields = ['householdId', 'solarPower', 'windPower', 'powerConsumption',
                          'voltage', 'current', 'overloadCondition', 'transformerFault']
        if df.empty or not all(field in df.columns for field in required_fields):
            return HttpResponse("Missing required data fields", status=400)
        
        # Calculations
        df['NetPower'] = (df['solarPower'] + df['windPower'] - df['powerConsumption']).round(2)
        df['Role'] = np.where(df['NetPower'] > 0, 'seller', 
                            np.where(df['NetPower'] < 0, 'buyer', 'neutral'))
        df['NoFault'] = (df['overloadCondition'] == 0) & (df['transformerFault'] == 0)
        
        # Generate price based on role
        def generate_price(row):
            if row['Role'] == 'seller':
                return round(np.random.uniform(SELLER_PRICE_LOW, SELLER_PRICE_HIGH), 2)
            elif row['Role'] == 'buyer':
                return round(np.random.uniform(BUYER_PRICE_LOW, BUYER_PRICE_HIGH), 2)
            return None
        df['electricityPrice'] = df.apply(generate_price, axis=1)
        
        # Create household records
        households = {}
        for _, row in df.iterrows():
            hh_id = str(row['householdId'])
            households[hh_id] = {
                'householdId': hh_id,
                'householdId_hash': hash_household_id(hh_id),
                'NetPower': row['NetPower'],
                'electricityPrice': row['electricityPrice'],
                'Role': row['Role'],
                'NoFault': row['NoFault'],
                'traded_units': 0,
                'total_price': 0.0,
                'remaining': row['NetPower']
            }
        
        # Filter eligible participants
        eligible_households = {
            k: v for k, v in households.items() 
            if v['NoFault'] and v['Role'] in ['seller', 'buyer']
        }
        
        # Perform trading
        traded_households, trades = perform_trading(eligible_households.copy())
        
        # Store results in MongoDB
        trading_records = []
        for hh_id, data in traded_households.items():
            record = {
                'householdId': data['householdId'],
                'householdId_hash': data['householdId_hash'],
                'NetPower': data['NetPower'],
                'traded_units': data['traded_units'],
                'total_price': data['total_price'],
                'remaining': data['remaining'],
                'Role': data['Role']
            }
            trading_records.append(record)
        
        trading_collection.delete_many({})
        trading_collection.insert_many(trading_records)
        
        # Generate visualizations
        summary_div = create_summary_chart(traded_households)
        network_div = create_network_graph(traded_households, trades)
        
        # Get trading data for table
        trading_data = list(trading_collection.find({}, {'_id': 0}))
        
        # Prepare context
        context = {
            'trading_data': trading_data,
            'summary_plot': summary_div,
            'network_plot': network_div,
            'trades': trades
        }
        
        return render(request, 'report.html', context)
    
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

def update_energy_trading_collection(request):
    return HttpResponse("Trading data updated successfully")