import random
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

def will_churn(customer):
    """Dummy function that randomly predicts churn based on customer characteristics"""
    # Base probability
    base_prob = 0.3
    
    # Adjust probability based on factors
    if customer.subscription_length_months < 12:
        base_prob += 0.2
    if customer.monthly_bill > 100:
        base_prob += 0.1
    if customer.total_usage_gb < 100:
        base_prob += 0.15
    if customer.age > 60:
        base_prob += 0.1
    
    # Add some randomness
    base_prob += random.uniform(-0.1, 0.1)
    base_prob = max(0, min(1, base_prob))  # Ensure between 0 and 1
    
    return random.random() < base_prob, base_prob

def identify_risk_factors(customer):
    """Identify risk factors for churn"""
    risk_factors = []
    
    if customer.subscription_length_months < 12:
        risk_factors.append({
            'factor': 'New Customer',
            'description': 'Customers with less than 12 months of subscription are more likely to churn',
            'severity': 'high'
        })
    
    if customer.monthly_bill > 100:
        risk_factors.append({
            'factor': 'High Monthly Bill',
            'description': 'Customers with high monthly bills may be more price-sensitive',
            'severity': 'medium'
        })
    
    if customer.total_usage_gb < 100:
        risk_factors.append({
            'factor': 'Low Usage',
            'description': 'Customers with low data usage may not be getting value from the service',
            'severity': 'medium'
        })
    
    if customer.age > 60:
        risk_factors.append({
            'factor': 'Senior Customer',
            'description': 'Older customers may be less tech-savvy and more likely to churn',
            'severity': 'low'
        })
    
    return risk_factors

def segment_customer(customer):
    """Segment customer based on value and risk"""
    if customer.monthly_bill > 100 and customer.total_usage_gb > 200:
        return 'High-value'
    elif customer.monthly_bill > 50 and customer.total_usage_gb > 100:
        return 'Medium-value'
    else:
        return 'Low-value'

def analyze_customer_base(customers):
    """Analyze the entire customer base for churn patterns"""
    if not customers:
        return None
    
    # Basic metrics
    total_customers = len(customers)
    churn_rate = sum(1 for c in customers if c.churn_prediction) / total_customers
    avg_monthly_bill = sum(c.monthly_bill for c in customers) / total_customers
    avg_usage = sum(c.total_usage_gb for c in customers) / total_customers
    
    # Segment distribution
    segments = defaultdict(int)
    for c in customers:
        segments[c.customer_segment] += 1
    segment_distribution = {k: v/total_customers for k, v in segments.items()}
    
    # Location analysis
    location_analysis = defaultdict(lambda: {'total': 0, 'churn': 0})
    for c in customers:
        location_analysis[c.location]['total'] += 1
        if c.churn_prediction:
            location_analysis[c.location]['churn'] += 1
    
    # Age group analysis
    age_groups = defaultdict(lambda: {'total': 0, 'churn': 0})
    for c in customers:
        age_group = (c.age // 10) * 10
        age_groups[f"{age_group}-{age_group+9}"]['total'] += 1
        if c.churn_prediction:
            age_groups[f"{age_group}-{age_group+9}"]['churn'] += 1
    
    # Gender analysis
    gender_analysis = defaultdict(lambda: {'total': 0, 'churn': 0})
    for c in customers:
        gender_analysis[c.gender]['total'] += 1
        if c.churn_prediction:
            gender_analysis[c.gender]['churn'] += 1
    
    # Subscription length analysis
    sub_length_groups = defaultdict(lambda: {'total': 0, 'churn': 0})
    for c in customers:
        group = (c.subscription_length_months // 6) * 6
        sub_length_groups[f"{group}-{group+5} months"]['total'] += 1
        if c.churn_prediction:
            sub_length_groups[f"{group}-{group+5} months"]['churn'] += 1
    
    return {
        'total_customers': total_customers,
        'churn_rate': churn_rate,
        'avg_monthly_bill': avg_monthly_bill,
        'avg_usage': avg_usage,
        'segment_distribution': segment_distribution,
        'location_analysis': location_analysis,
        'age_group_analysis': age_groups,
        'gender_analysis': gender_analysis,
        'subscription_length_analysis': sub_length_groups
    }

def predict_customer_churn(customer):
    """Predict churn for a single customer and store the analysis"""
    prediction, score = will_churn(customer)
    risk_factors = identify_risk_factors(customer)
    customer_segment = segment_customer(customer)
    
    customer.churn_score = score
    customer.churn_prediction = prediction
    customer.risk_factors = risk_factors
    customer.customer_segment = customer_segment
    customer.last_prediction_date = datetime.utcnow()
    
    # Store history
    history = CustomerHistory(
        customer_id=customer.id,
        churn_score=score,
        prediction=prediction,
        features={
            'age': customer.age,
            'gender': customer.gender,
            'location': customer.location,
            'subscription_length_months': customer.subscription_length_months,
            'monthly_bill': customer.monthly_bill,
            'total_usage_gb': customer.total_usage_gb
        },
        risk_factors=risk_factors
    )
    
    return history 