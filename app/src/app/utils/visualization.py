import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_plots(df):
    plt.figure(figsize=(12, 6))
    sns.countplot(x='Churn', data=df)
    plt.title('Churn Distribution')
    return plot_to_base64()

def plot_to_base64():
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def generate_chart_data(data, chart_type='line'):
    """
    Generate chart data in a format suitable for Chart.js
    
    Args:
        data (list or DataFrame): Input data to visualize
        chart_type (str): Type of chart ('line', 'bar', 'pie')
        
    Returns:
        dict: Chart data in Chart.js format
    """
    if isinstance(data, pd.DataFrame):
        # Convert DataFrame to list of dictionaries
        data = data.to_dict('records')
    
    if not data:
        return {
            'labels': [],
            'datasets': []
        }
    
    # Default chart data structure
    chart_data = {
        'labels': [],
        'datasets': []
    }
    
    if chart_type == 'line':
        # For line charts, assume data has 'date' and 'value' fields
        chart_data['labels'] = [d.get('date', '') for d in data]
        chart_data['datasets'] = [{
            'label': 'Value',
            'data': [d.get('value', 0) for d in data],
            'borderColor': 'rgb(75, 192, 192)',
            'tension': 0.1
        }]
    
    elif chart_type == 'bar':
        # For bar charts, assume data has 'category' and 'value' fields
        chart_data['labels'] = [d.get('category', '') for d in data]
        chart_data['datasets'] = [{
            'label': 'Value',
            'data': [d.get('value', 0) for d in data],
            'backgroundColor': 'rgba(75, 192, 192, 0.2)',
            'borderColor': 'rgb(75, 192, 192)',
            'borderWidth': 1
        }]
    
    elif chart_type == 'pie':
        # For pie charts, assume data has 'label' and 'value' fields
        chart_data['labels'] = [d.get('label', '') for d in data]
        chart_data['datasets'] = [{
            'data': [d.get('value', 0) for d in data],
            'backgroundColor': [
                'rgba(255, 99, 132, 0.2)',
                'rgba(54, 162, 235, 0.2)',
                'rgba(255, 206, 86, 0.2)',
                'rgba(75, 192, 192, 0.2)',
                'rgba(153, 102, 255, 0.2)'
            ],
            'borderColor': [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(153, 102, 255, 1)'
            ],
            'borderWidth': 1
        }]
    
    return chart_data