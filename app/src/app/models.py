from datetime import datetime
from ..app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')  # user, admin, analyst
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    company_name = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    customers = db.relationship('Customer', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    location = db.Column(db.String(100))
    subscription_length_months = db.Column(db.Integer)
    monthly_bill = db.Column(db.Float)
    total_usage_gb = db.Column(db.Float)
    
    # Churn analysis fields
    churn_score = db.Column(db.Float)
    churn_prediction = db.Column(db.Boolean)
    last_prediction_date = db.Column(db.DateTime)
    risk_factors = db.Column(db.JSON)  # Store identified risk factors
    customer_segment = db.Column(db.String(50))  # High-value, Medium-value, Low-value
    activities = db.relationship('CustomerActivity', backref='customer', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CustomerActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # e.g., 'update', 'prediction', 'interaction'
    description = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    activity_metadata = db.Column(db.JSON)  # Store additional data as JSON

class CustomerHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    churn_score = db.Column(db.Float)
    prediction = db.Column(db.Boolean)
    features = db.Column(db.JSON)  # Store the features used for prediction
    risk_factors = db.Column(db.JSON)  # Store identified risk factors at this point
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChurnAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_customers = db.Column(db.Integer)
    churn_rate = db.Column(db.Float)
    avg_monthly_bill = db.Column(db.Float)
    avg_usage = db.Column(db.Float)
    segment_distribution = db.Column(db.JSON)  # Distribution of customer segments
    location_analysis = db.Column(db.JSON)  # Churn analysis by location
    age_group_analysis = db.Column(db.JSON)  # Churn analysis by age groups
    gender_analysis = db.Column(db.JSON)  # Churn analysis by gender
    subscription_length_analysis = db.Column(db.JSON)  # Churn analysis by subscription length

class ChurnTrend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    churn_rate = db.Column(db.Float, nullable=False)
    high_risk_customers = db.Column(db.Integer, nullable=False)
    avg_churn_score = db.Column(db.Float, nullable=False)
    
    # Store analysis data as JSON
    segment_analysis = db.Column(db.JSON, nullable=True)
    location_analysis = db.Column(db.JSON, nullable=True)
    future_predictions = db.Column(db.JSON, nullable=True)
    factor_importance = db.Column(db.JSON, nullable=True)
    factor_changes = db.Column(db.JSON, nullable=True)
    
    def __repr__(self):
        return f'<ChurnTrend {self.date}>'

class ChurnPrediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    prediction_date = db.Column(db.DateTime, default=datetime.utcnow)
    prediction_period = db.Column(db.String(20))  # '1m', '3m', '6m', '1y'
    predicted_churn_rate = db.Column(db.Float)
    confidence_score = db.Column(db.Float)
    segment_predictions = db.Column(db.JSON)  # Predictions for each segment
    location_predictions = db.Column(db.JSON)  # Predictions for each location
    age_group_predictions = db.Column(db.JSON)  # Predictions for each age group
    key_factors = db.Column(db.JSON)  # Key factors influencing the prediction

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    plan = db.Column(db.String(50))
    status = db.Column(db.String(20), default='active')
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    features_enabled = db.Column(db.JSON)  # Store enabled features for the subscription

class BatchJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_type = db.Column(db.String(50), nullable=False)  # 'import', 'export', 'analysis', etc.
    status = db.Column(db.String(20), nullable=False)  # 'pending', 'processing', 'completed', 'failed'
    file_path = db.Column(db.String(255))
    task_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    result_data = db.Column(db.JSON)  # Store any results or metadata

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))