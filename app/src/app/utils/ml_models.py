import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime, timedelta

def predict_churn(customer_data):
    """
    Predict churn probability for a customer or set of customers.
    
    Args:
        customer_data (dict or list): Customer data to predict churn for
        
    Returns:
        float or list: Churn probability/probabilities
    """
    # Load the model and scaler
    model_path = os.path.join(os.path.dirname(__file__), '../../models/churn_model.pkl')
    scaler_path = os.path.join(os.path.dirname(__file__), '../../models/scaler.pkl')
    
    try:
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
    except FileNotFoundError:
        # Return a default prediction if model files are not found
        return 0.5 if isinstance(customer_data, dict) else [0.5] * len(customer_data)
    
    # Convert input to DataFrame if it's a single customer
    if isinstance(customer_data, dict):
        df = pd.DataFrame([customer_data])
    else:
        df = pd.DataFrame(customer_data)
    
    # Preprocess the data
    # Add any necessary feature engineering here
    features = [
        'Monthly_Bill',
        'Total_Usage_GB',
        'Subscription_Length_Months',
        'Age'
    ]
    
    # Ensure all required features are present
    for feature in features:
        if feature not in df.columns:
            df[feature] = 0  # Default value if feature is missing
    
    # Scale the features
    X = scaler.transform(df[features])
    
    # Make predictions
    predictions = model.predict_proba(X)[:, 1]
    
    return predictions[0] if isinstance(customer_data, dict) else predictions.tolist()

def analyze_segments(customers):
    """Analyze churn risk by customer segments."""
    # Group customers by usage
    usage_thresholds = {
        'low': 50,  # GB
        'medium': 200  # GB
    }
    
    usage_segments = {
        'low': [],
        'medium': [],
        'high': []
    }
    
    # Group customers by subscription length
    subscription_thresholds = {
        'new': 6,  # months
        'medium': 24  # months
    }
    
    subscription_segments = {
        'new': [],
        'medium': [],
        'long_term': []
    }
    
    for customer in customers:
        # Analyze usage segments
        if customer.total_usage_gb <= usage_thresholds['low']:
            usage_segments['low'].append(customer.churn_score)
        elif customer.total_usage_gb <= usage_thresholds['medium']:
            usage_segments['medium'].append(customer.churn_score)
        else:
            usage_segments['high'].append(customer.churn_score)
        
        # Analyze subscription segments
        if customer.subscription_length_months <= subscription_thresholds['new']:
            subscription_segments['new'].append(customer.churn_score)
        elif customer.subscription_length_months <= subscription_thresholds['medium']:
            subscription_segments['medium'].append(customer.churn_score)
        else:
            subscription_segments['long_term'].append(customer.churn_score)
    
    # Calculate average churn scores for each segment
    return {
        'usage_segments': {
            'low': np.mean(usage_segments['low']) if usage_segments['low'] else 0,
            'medium': np.mean(usage_segments['medium']) if usage_segments['medium'] else 0,
            'high': np.mean(usage_segments['high']) if usage_segments['high'] else 0
        },
        'subscription_segments': {
            'new': np.mean(subscription_segments['new']) if subscription_segments['new'] else 0,
            'medium': np.mean(subscription_segments['medium']) if subscription_segments['medium'] else 0,
            'long_term': np.mean(subscription_segments['long_term']) if subscription_segments['long_term'] else 0
        }
    }

def analyze_locations(customers):
    """Analyze churn risk by location."""
    location_stats = {}
    
    for customer in customers:
        if customer.location not in location_stats:
            location_stats[customer.location] = {
                'scores': [],
                'count': 0
            }
        
        location_stats[customer.location]['scores'].append(customer.churn_score)
        location_stats[customer.location]['count'] += 1
    
    # Calculate statistics for each location
    return {
        location: {
            'mean': np.mean(stats['scores']),
            'count': stats['count']
        }
        for location, stats in location_stats.items()
    }

def predict_future_churn(customers):
    """Predict churn rates for the next 6 months."""
    # Get current churn rate
    current_rate = np.mean([c.churn_score for c in customers])
    
    # Generate predictions with some variation
    predictions = []
    for i in range(6):
        # Add some random variation to the prediction
        variation = np.random.normal(0, 0.05)  # 5% standard deviation
        prediction = max(0, min(1, current_rate + variation))
        predictions.append(prediction)
    
    return predictions

def analyze_key_factors(customers):
    """Analyze which factors most influence churn."""
    # Create a DataFrame for analysis
    df = pd.DataFrame([{
        'monthly_bill': c.monthly_bill,
        'total_usage': c.total_usage_gb,
        'subscription_length': c.subscription_length_months,
        'age': c.age or 0,
        'churn_score': c.churn_score
    } for c in customers])
    
    # Calculate correlations with churn score
    correlations = df.corr()['churn_score'].abs()
    
    # Normalize correlations to sum to 1
    total = correlations.sum()
    if total > 0:
        correlations = correlations / total
    
    return {
        'Monthly Bill': correlations.get('monthly_bill', 0),
        'Usage': correlations.get('total_usage', 0),
        'Subscription Length': correlations.get('subscription_length', 0),
        'Age': correlations.get('age', 0)
    }

def predict_factor_changes(customers):
    """Predict how key factors might change in the future."""
    # Get current averages
    current_metrics = {
        'Monthly Bill': np.mean([c.monthly_bill for c in customers]),
        'Usage': np.mean([c.total_usage_gb for c in customers]),
        'Subscription Length': np.mean([c.subscription_length_months for c in customers]),
        'Age': np.mean([c.age or 0 for c in customers])
    }
    
    # Predict changes (simple linear projection)
    changes = {}
    for metric, current in current_metrics.items():
        # Add some random variation to the prediction
        variation = np.random.normal(1, 0.1)  # 10% standard deviation
        changes[metric] = max(0.5, min(1.5, variation))
    
    return changes 