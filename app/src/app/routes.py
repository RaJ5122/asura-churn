from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, abort, session
from flask_login import login_required, current_user, login_user, logout_user
from . import db, celery
from .models import User, Customer, ChurnPrediction, ChurnTrend, BatchJob, CustomerActivity
from .utils.data_processing import analyze_data, generate_insights
from .utils.ml_models import predict_churn, analyze_segments, analyze_locations, predict_future_churn, analyze_key_factors, predict_factor_changes
from .utils.visualization import generate_chart_data
from datetime import datetime, timedelta
import pandas as pd
import os
from werkzeug.utils import secure_filename
from .forms import AddCustomerForm, DynamicAnalysisForm
from flask_wtf.csrf import CSRFProtect

# Initialize CSRF protection
csrf = CSRFProtect()

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main.route('/dashboard')
@login_required
def dashboard():
    # Get customer statistics
    total_customers = Customer.query.count()
    high_risk_customers = Customer.query.filter(Customer.churn_score > 0.7).count()
    medium_risk_customers = Customer.query.filter(Customer.churn_score > 0.4, Customer.churn_score <= 0.7).count()
    low_risk_customers = Customer.query.filter(Customer.churn_score <= 0.4).count()
    
    stats = {
        'total_customers': total_customers,
        'high_risk_customers': high_risk_customers,
        'medium_risk_customers': medium_risk_customers,
        'low_risk_customers': low_risk_customers
    }
    
    # Get recent activity (last 5 customer updates)
    recent_activity = CustomerActivity.query.order_by(CustomerActivity.timestamp.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         stats=stats,
                         recent_activity=recent_activity)

@main.route('/customers')
@login_required
def customers():
    # Get all customers for the current user from database
    customers = Customer.query.filter_by(user_id=current_user.id).all()
    
    # Calculate churn scores for customers that don't have one
    for customer in customers:
        if customer.churn_score is None:
            # Calculate churn score based on customer data, using 0 as default for null age
            churn_score = predict_churn({
                'Monthly_Bill': customer.monthly_bill,
                'Total_Usage_GB': customer.total_usage_gb,
                'Subscription_Length_Months': customer.subscription_length_months,
                'Age': customer.age if customer.age is not None else 0  # Handle null age
            })
            customer.churn_score = churn_score
            
            # Create activity record
            activity = CustomerActivity(
                customer_id=customer.id,
                activity_type='prediction',
                description='Churn score calculated',
                activity_metadata={'score': churn_score}
            )
            db.session.add(activity)
    
    db.session.commit()
    
    # Check if there's an uploaded file in the session
    if 'uploaded_customers' in session:
        uploaded_customers = session['uploaded_customers']
        # Convert uploaded data to Customer objects for display
        for customer_data in uploaded_customers:
            customer = Customer(
                user_id=current_user.id,
                customer_id=customer_data.get('customer_id', ''),
                name=customer_data.get('name', ''),
                age=customer_data.get('age'),
                gender=customer_data.get('gender'),
                location=customer_data.get('location'),
                subscription_length_months=customer_data.get('subscription_length_months', 0),
                monthly_bill=customer_data.get('monthly_bill', 0),
                total_usage_gb=customer_data.get('total_usage_gb', 0)
            )
            # Calculate churn score for uploaded customer
            if customer.churn_score is None:
                customer.churn_score = predict_churn({
                    'Monthly_Bill': customer.monthly_bill,
                    'Total_Usage_GB': customer.total_usage_gb,
                    'Subscription_Length_Months': customer.subscription_length_months,
                    'Age': customer.age if customer.age is not None else 0  # Handle null age
                })
            customers.append(customer)
    
    return render_template('customers.html', customers=customers)

@main.route('/customer/<int:id>')
@login_required
def customer_detail(id):
    customer = Customer.query.get_or_404(id)
    return render_template('customer_detail.html', customer=customer)

@main.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and file.filename.endswith(('.csv', '.xlsx', '.xls')):
            # Save the file
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Create a batch job
            job = BatchJob(
                user_id=current_user.id,
                job_type='import',
                status='pending',
                file_path=filepath
            )
            db.session.add(job)
            db.session.commit()
            
            # Process the file based on Celery availability
            if current_app.config.get('USE_CELERY', False):
                try:
                    # Start the import task
                    task = import_customers.delay(job.id)
                    job.task_id = task.id
                    db.session.commit()
                    flash('File uploaded successfully. Processing started.')
                except Exception as e:
                    print(f"Warning: Celery task failed: {str(e)}")
                    import_customers(job.id)  # Run synchronously if Celery fails
                    flash('File uploaded successfully. Processing completed.')
            else:
                # Process synchronously if Celery is disabled
                import_customers(job.id)
                flash('File uploaded successfully. Processing completed.')
            
            return redirect(url_for('main.batch_jobs'))
    
    return render_template('upload.html')

@main.route('/batch-jobs')
@login_required
def batch_jobs():
    jobs = BatchJob.query.filter_by(user_id=current_user.id).order_by(
        BatchJob.created_at.desc()
    ).all()
    return render_template('batch_jobs.html', jobs=jobs)

@main.route('/trends')
@login_required
def trends():
    # Get all customers for the current user
    customers = Customer.query.filter_by(user_id=current_user.id).all()
    
    # Calculate churn scores for customers that don't have one
    for customer in customers:
        if customer.churn_score is None:
            churn_score = predict_churn({
                'Monthly_Bill': customer.monthly_bill,
                'Total_Usage_GB': customer.total_usage_gb,
                'Subscription_Length_Months': customer.subscription_length_months,
                'Age': customer.age if customer.age is not None else 0
            })
            customer.churn_score = churn_score
    
    db.session.commit()
    
    # Filter out customers without churn scores
    customers_with_scores = [c for c in customers if c.churn_score is not None]
    
    # Initialize empty analysis results
    segment_analysis = {}
    location_analysis = {}
    future_predictions = {}
    factor_importance = {}
    factor_changes = {}
    
    if customers_with_scores:
        # Perform various analyses only if we have customers with scores
        segment_analysis = analyze_segments(customers_with_scores)
        location_analysis = analyze_locations(customers_with_scores)
        future_predictions = predict_future_churn(customers_with_scores)
        factor_importance = analyze_key_factors(customers_with_scores)
        factor_changes = predict_factor_changes(customers_with_scores)
        
        # Store the analysis in the database
        churn_trend = ChurnTrend(
            user_id=current_user.id,
            date=datetime.utcnow(),
            churn_rate=sum(1 for c in customers_with_scores if c.churn_score > 0.7) / len(customers_with_scores),
            high_risk_customers=sum(1 for c in customers_with_scores if c.churn_score > 0.7),
            avg_churn_score=sum(c.churn_score for c in customers_with_scores) / len(customers_with_scores),
            segment_analysis=segment_analysis,
            location_analysis=location_analysis,
            future_predictions=future_predictions,
            factor_importance=factor_importance,
            factor_changes=factor_changes
        )
        db.session.add(churn_trend)
        db.session.commit()
    
    return render_template('trends.html',
                         segment_analysis=segment_analysis,
                         location_analysis=location_analysis,
                         future_predictions=future_predictions,
                         factor_importance=factor_importance,
                         factor_changes=factor_changes,
                         has_data=bool(customers_with_scores))

@main.route('/api/trends')
@login_required
def api_trends():
    trends = ChurnTrend.query.order_by(ChurnTrend.date).all()
    
    return jsonify({
        'dates': [t.date.strftime('%Y-%m-%d') for t in trends],
        'churn_rates': [t.churn_rate for t in trends],
        'high_risk_customers': [t.high_risk_customers for t in trends],
        'avg_churn_scores': [t.avg_churn_score for t in trends],
        'segment_trends': [t.segment_analysis for t in trends],
        'location_trends': [t.location_analysis for t in trends]
    })

@main.route('/api/predictions')
@login_required
def api_predictions():
    predictions = ChurnPrediction.query.order_by(
        ChurnPrediction.prediction_date
    ).all()
    
    return jsonify({
        'dates': [p.prediction_date.strftime('%Y-%m-%d') for p in predictions],
        'predicted_rates': [p.predicted_churn_rate for p in predictions],
        'confidence_scores': [p.confidence_score for p in predictions],
        'segment_predictions': [p.segment_predictions for p in predictions],
        'factor_changes': predictions[-1].factor_changes if predictions else {}
    })

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid email or password')
    return render_template('login.html')

@main.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        company_name = request.form.get('company_name')
        phone_number = request.form.get('phone_number')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('main.signup'))
            
        user = User(username=username, email=email, company_name=company_name, phone_number=phone_number)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('main.dashboard'))
    return render_template('signup.html')

@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route('/customer/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    form = AddCustomerForm()
    if form.validate_on_submit():
        try:
            customer = Customer(
                user_id=current_user.id,
                customer_id=form.customer_id.data,
                name=form.name.data,
                age=form.age.data,
                gender=form.gender.data,
                location=form.location.data,
                subscription_length_months=form.subscription_length_months.data,
                monthly_bill=form.monthly_bill.data,
                total_usage_gb=form.total_usage_gb.data
            )
            db.session.add(customer)
            db.session.commit()
            
            # Create activity record
            activity = CustomerActivity(
                customer_id=customer.id,
                activity_type='create',
                description='New customer added',
                activity_metadata={'source': 'manual_entry'}
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Customer added successfully', 'success')
            return redirect(url_for('main.customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding customer: {str(e)}', 'error')
    
    return render_template('add_customer.html', form=form)

@main.route('/analysis')
@login_required
def view_analysis():
    customers = Customer.query.filter_by(user_id=current_user.id).all()
    analysis = analyze_customer_base(customers)
    
    # Store the analysis
    churn_analysis = ChurnAnalysis(
        user_id=current_user.id,
        total_customers=analysis['total_customers'],
        churn_rate=analysis['churn_rate'],
        avg_monthly_bill=analysis['avg_monthly_bill'],
        avg_usage=analysis['avg_usage'],
        segment_distribution=analysis['segment_distribution'],
        location_analysis=analysis['location_analysis'],
        age_group_analysis=analysis['age_group_analysis'],
        gender_analysis=analysis['gender_analysis'],
        subscription_length_analysis=analysis['subscription_length_analysis']
    )
    db.session.add(churn_analysis)
    db.session.commit()
    
    return render_template('analysis.html', analysis=analysis)

@celery.task
def process_data(filepath, user_id):
    try:
        df = pd.read_excel(filepath)
        processed_df = analyze_data(df)
        insights = generate_insights(processed_df)
        store_results(user_id, insights)
    except Exception as e:
        handle_processing_error(user_id, str(e))

def calculate_churn_stats(customers):
    if not customers:
        return {
            'total_customers': 0,
            'churn_rate': 0,
            'avg_churn_score': 0,
            'high_risk_customers': 0
        }
    
    total_customers = len(customers)
    churn_rate = sum(1 for c in customers if c.churn_prediction) / total_customers
    avg_churn_score = sum(c.churn_score for c in customers) / total_customers
    high_risk_customers = sum(1 for c in customers if c.churn_score > 0.7)
    
    return {
        'total_customers': total_customers,
        'churn_rate': churn_rate,
        'avg_churn_score': avg_churn_score,
        'high_risk_customers': high_risk_customers
    }

def preprocess_input(data):
    # Convert categorical features to numerical
    contract_mapping = {'prepaid': 0, 'postpaid': 1}
    plan_mapping = {'basic': 0, 'premium': 1, 'enterprise': 2}
    
    processed = {
        'tenure': [data['tenure']],
        'monthly_charges': [data['monthly_charges']],
        'total_charges': [data['total_charges']],
        'contract_type': [contract_mapping.get(data['contract_type'], 0)],
        'plan_type': [plan_mapping.get(data['plan_type'], 0)]
    }
    
    return pd.DataFrame(processed)

def save_uploaded_file(file):
    # File handling logic
    pass

@main.route('/customers/upload', methods=['POST'])
@login_required
def upload_customers():
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('main.customers'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('main.customers'))
    
    # Get file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    # Check if file type is supported
    if file_ext not in ['.csv', '.xlsx', '.xls']:
        flash('Unsupported file type. Please upload a CSV or Excel file.', 'error')
        return redirect(url_for('main.customers'))
    
    try:
        # Read the file based on its type
        if file_ext == '.csv':
            df = pd.read_csv(file)
        else:  # Excel file
            df = pd.read_excel(file)
        
        # Define column name mappings for common variations
        column_mappings = {
            'customer_id': ['customer_id', 'customerid', 'id', 'customer', 'client_id', 'CustomerID'],
            'name': ['name', 'customer_name', 'full_name', 'client_name', 'Name'],
            'age': ['age', 'customer_age', 'Age'],
            'gender': ['gender', 'sex', 'Gender'],
            'location': ['location', 'city', 'region', 'area', 'Location'],
            'subscription_length_months': ['subscription_length_months', 'subscription_length', 'months_subscribed', 'tenure', 'Subscription_Length_Months'],
            'monthly_bill': ['monthly_bill', 'monthly_charges', 'bill_amount', 'monthly_payment', 'Monthly_Bill'],
            'total_usage_gb': ['total_usage_gb', 'data_usage', 'usage_gb', 'total_data', 'Total_Usage_GB']
        }
        
        # Map column names to standard names
        for standard_name, variations in column_mappings.items():
            for variation in variations:
                if variation in df.columns:
                    df = df.rename(columns={variation: standard_name})
                    break
        
        # Check for missing required columns
        required_columns = ['customer_id', 'name', 'age', 'gender', 'location', 
                          'subscription_length_months', 'monthly_bill', 'total_usage_gb']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            # Provide helpful suggestions for missing columns
            suggestions = []
            for col in missing_columns:
                possible_names = column_mappings[col]
                suggestions.append(f"{col} (possible names: {', '.join(possible_names)})")
            
            flash(f'Missing required columns. Please check your file headers. Missing: {", ".join(suggestions)}', 'error')
            return redirect(url_for('main.customers'))
        
        # Clean and validate numeric columns
        numeric_columns = ['age', 'subscription_length_months', 'monthly_bill', 'total_usage_gb']
        for col in numeric_columns:
            # Convert to numeric, replacing non-numeric values with NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # Fill NaN values with appropriate defaults
            if col == 'age':
                df[col] = df[col].fillna(df[col].median()).astype(int)
            elif col == 'subscription_length_months':
                df[col] = df[col].fillna(0).astype(int)
            elif col in ['monthly_bill', 'total_usage_gb']:
                df[col] = df[col].fillna(0.0).astype(float)

        # Clean text columns
        text_columns = ['name', 'gender', 'location']
        for col in text_columns:
            df[col] = df[col].fillna('').astype(str).str.strip()

        # Process each row and save to database
        for _, row in df.iterrows():
            try:
                customer_id = str(row.get('customer_id', '')).strip()
                if not customer_id:  # Skip rows with empty customer_id
                    continue
                    
                # Check if customer already exists
                existing_customer = Customer.query.filter_by(
                    user_id=current_user.id,
                    customer_id=customer_id
                ).first()
                
                if existing_customer:
                    # Update existing customer
                    existing_customer.name = str(row.get('name', existing_customer.name))
                    existing_customer.age = int(row.get('age', 0)) if pd.notna(row.get('age')) else existing_customer.age
                    existing_customer.gender = str(row.get('gender')) if pd.notna(row.get('gender')) else existing_customer.gender
                    existing_customer.location = str(row.get('location')) if pd.notna(row.get('location')) else existing_customer.location
                    existing_customer.subscription_length_months = int(row.get('subscription_length_months', existing_customer.subscription_length_months))
                    existing_customer.monthly_bill = float(row.get('monthly_bill', existing_customer.monthly_bill))
                    existing_customer.total_usage_gb = float(row.get('total_usage_gb', existing_customer.total_usage_gb))
                    
                    # Recalculate churn score
                    existing_customer.churn_score = predict_churn({
                        'Monthly_Bill': existing_customer.monthly_bill,
                        'Total_Usage_GB': existing_customer.total_usage_gb,
                        'Subscription_Length_Months': existing_customer.subscription_length_months,
                        'Age': existing_customer.age if existing_customer.age is not None else 0
                    })
                    
                    # Save the customer first
                    db.session.add(existing_customer)
                    db.session.flush()  # This will assign an ID to the customer
                    
                    # Create activity record for update
                    activity = CustomerActivity(
                        customer_id=existing_customer.id,
                        activity_type='update',
                        description='Customer updated from file import',
                        activity_metadata={'source': 'file_upload', 'file_type': file_ext}
                    )
                    db.session.add(activity)
                    
                else:
                    # Create new customer
                    customer = Customer(
                        user_id=current_user.id,
                        customer_id=customer_id,
                        name=str(row.get('name', '')),
                        age=int(row.get('age', 0)) if pd.notna(row.get('age')) else None,
                        gender=str(row.get('gender')) if pd.notna(row.get('gender')) else None,
                        location=str(row.get('location')) if pd.notna(row.get('location')) else None,
                        subscription_length_months=int(row.get('subscription_length_months', 0)),
                        monthly_bill=float(row.get('monthly_bill', 0)),
                        total_usage_gb=float(row.get('total_usage_gb', 0))
                    )
                    
                    # Calculate churn score
                    customer.churn_score = predict_churn({
                        'Monthly_Bill': customer.monthly_bill,
                        'Total_Usage_GB': customer.total_usage_gb,
                        'Subscription_Length_Months': customer.subscription_length_months,
                        'Age': customer.age if customer.age is not None else 0
                    })
                    
                    # Save the customer first
                    db.session.add(customer)
                    db.session.flush()  # This will assign an ID to the customer
                    
                    # Create activity record for new customer
                    activity = CustomerActivity(
                        customer_id=customer.id,
                        activity_type='import',
                        description='Customer imported from file',
                        activity_metadata={'source': 'file_upload', 'file_type': file_ext}
                    )
                    db.session.add(activity)
                
            except Exception as e:
                print(f"Error processing row: {str(e)}")
                db.session.rollback()
                continue
        
        db.session.commit()
        flash('File uploaded and processed successfully', 'success')
        return redirect(url_for('main.customers'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing file: {str(e)}', 'error')
    
    return redirect(url_for('main.customers'))

@main.route('/customer/<int:customer_id>')
@login_required
def view_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if customer.user_id != current_user.id:
        abort(403)
    return render_template('view_customer.html', customer=customer)

@main.route('/customer/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if customer.user_id != current_user.id:
        abort(403)
    
    form = AddCustomerForm(obj=customer)
    if form.validate_on_submit():
        try:
            customer.customer_id = form.customer_id.data
            customer.name = form.name.data
            customer.age = form.age.data
            customer.gender = form.gender.data
            customer.location = form.location.data
            customer.subscription_length_months = form.subscription_length_months.data
            customer.monthly_bill = form.monthly_bill.data
            customer.total_usage_gb = form.total_usage_gb.data
            
            # Recalculate churn score
            churn_score = predict_churn({
                'Monthly_Bill': customer.monthly_bill,
                'Total_Usage_GB': customer.total_usage_gb,
                'Subscription_Length_Months': customer.subscription_length_months,
                'Age': customer.age if customer.age is not None else 0  # Handle null age
            })
            customer.churn_score = churn_score
            
            # Create activity record
            activity = CustomerActivity(
                customer_id=customer.id,
                activity_type='update',
                description='Customer details updated',
                activity_metadata={'updated_fields': list(form.data.keys())}
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Customer updated successfully', 'success')
            return redirect(url_for('main.view_customer', customer_id=customer.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'error')
    
    return render_template('edit_customer.html', form=form, customer=customer)

@main.route('/customer/<int:customer_id>/delete', methods=['POST'])
@login_required
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if customer.user_id != current_user.id:
        abort(403)
    
    try:
        # Create activity record before deletion
        activity = CustomerActivity(
            customer_id=customer.id,
            activity_type='delete',
            description='Customer deleted',
            activity_metadata={'customer_id': customer.customer_id}
        )
        db.session.add(activity)
        
        # Delete the customer
        db.session.delete(customer)
        db.session.commit()
        
        flash('Customer deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting customer: {str(e)}', 'error')
    
    return redirect(url_for('main.customers'))

@celery.task
def import_customers(job_id):
    try:
        job = BatchJob.query.get(job_id)
        if not job:
            return
        
        job.status = 'processing'
        db.session.commit()
        
        # Read and process the file based on its type
        file_ext = os.path.splitext(job.file_path)[1].lower()
        if file_ext == '.csv':
            df = pd.read_csv(job.file_path)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(job.file_path)
        else:
            job.status = 'failed'
            job.error_message = f'Unsupported file type: {file_ext}'
            job.completed_at = datetime.utcnow()
            db.session.commit()
            return
        
        # Process the data
        for _, row in df.iterrows():
            try:
                customer = Customer(
                    user_id=job.user_id,
                    customer_id=str(row['customer_id']),
                    name=str(row['name']),
                    age=int(row.get('age', 0)) if pd.notna(row.get('age')) else None,
                    gender=str(row.get('gender')) if pd.notna(row.get('gender')) else None,
                    location=str(row.get('location')) if pd.notna(row.get('location')) else None,
                    subscription_length_months=int(row['subscription_length_months']),
                    monthly_bill=float(row['monthly_bill']),
                    total_usage_gb=float(row['total_usage_gb'])
                )
                db.session.add(customer)
                
                # Create activity record
                activity = CustomerActivity(
                    customer_id=customer.id,
                    activity_type='import',
                    description='Customer imported from file',
                    activity_metadata={'source': 'batch_import', 'file_type': file_ext}
                )
                db.session.add(activity)
            except Exception as e:
                # Log the error but continue processing other rows
                print(f"Error processing row: {str(e)}")
                continue
        
        db.session.commit()
        
        # Update job status
        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.session.commit()
        
        # Clean up the temporary file
        if os.path.exists(job.file_path):
            os.remove(job.file_path)
        
    except Exception as e:
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.session.commit()
        
        # Clean up the temporary file if it exists
        if os.path.exists(job.file_path):
            os.remove(job.file_path)
        
        raise

@main.route('/dynamic-analysis', methods=['GET', 'POST'])
@login_required
def dynamic_analysis():
    form = DynamicAnalysisForm()
    
    # Get unique locations from database for the dropdown
    locations = [loc[0] for loc in db.session.query(Customer.location).distinct().filter(Customer.location.isnot(None)).all()]
    form.location.choices = [('all', 'All Locations')] + [(loc, loc) for loc in locations]
    
    if request.method == 'POST' and form.validate():
        try:
            # Get filter criteria from form
            age_range = form.age_range.data
            location = form.location.data
            gender = form.gender.data
            subscription_range = form.subscription_range.data
            usage_range = form.usage_range.data
            
            # Start with base query for current user's customers
            query = Customer.query.filter_by(user_id=current_user.id)
            
            # Apply filters
            if age_range:
                min_age, max_age = map(int, age_range.split('-'))
                query = query.filter(Customer.age.between(min_age, max_age))
            
            if location and location != 'all':
                query = query.filter(Customer.location == location)
            
            if gender and gender != 'all':
                query = query.filter(Customer.gender == gender)
            
            if subscription_range:
                min_months, max_months = map(int, subscription_range.split('-'))
                query = query.filter(Customer.subscription_length_months.between(min_months, max_months))
            
            if usage_range:
                min_gb, max_gb = map(float, usage_range.split('-'))
                query = query.filter(Customer.total_usage_gb.between(min_gb, max_gb))
            
            # Get filtered customers
            customers = query.all()
            
            if not customers:
                flash('No customers match the selected criteria', 'warning')
                return redirect(request.url)
            
            # Convert customers to list of dictionaries for analysis
            customers_data = []
            for customer in customers:
                customer_dict = {
                    'customer_id': customer.customer_id,
                    'name': customer.name,
                    'age': customer.age,
                    'gender': customer.gender.lower() if customer.gender else 'other',
                    'location': customer.location,
                    'subscription_length_months': customer.subscription_length_months,
                    'monthly_bill': customer.monthly_bill,
                    'total_usage_gb': customer.total_usage_gb,
                    'churn_score': customer.churn_score
                }
                customers_data.append(customer_dict)
            
            # Perform analysis on filtered data
            total_customers = len(customers_data)
            
            # Calculate churn rate and risk distributions
            churned_customers = sum(1 for c in customers_data if c['churn_score'] > 0.7)
            churn_rate = (churned_customers / total_customers * 100) if total_customers > 0 else 0
            
            # Calculate averages
            avg_monthly_bill = sum(c['monthly_bill'] for c in customers_data) / total_customers if total_customers > 0 else 0
            avg_usage = sum(c['total_usage_gb'] for c in customers_data) / total_customers if total_customers > 0 else 0
            
            # Calculate risk based on monthly bill comparison
            max_monthly_bill = max(c['monthly_bill'] for c in customers_data)
            bill_risk_distribution = {
                'very_high': 0,  # 0-20% of max bill
                'high': 0,       # 21-40% of max bill
                'medium': 0,     # 41-60% of max bill
                'low': 0,        # 61-80% of max bill
                'very_low': 0    # 81-100% of max bill
            }
            
            total_risk_score = 0
            for customer in customers_data:
                bill_percentage = (customer['monthly_bill'] / max_monthly_bill) * 100
                if bill_percentage <= 20:
                    bill_risk_distribution['very_high'] += 1
                    risk_score = 1.0
                elif bill_percentage <= 40:
                    bill_risk_distribution['high'] += 1
                    risk_score = 0.8
                elif bill_percentage <= 60:
                    bill_risk_distribution['medium'] += 1
                    risk_score = 0.6
                elif bill_percentage <= 80:
                    bill_risk_distribution['low'] += 1
                    risk_score = 0.4
                else:
                    bill_risk_distribution['very_low'] += 1
                    risk_score = 0.2
                
                total_risk_score += risk_score
            
            # Calculate average risk percentage
            avg_risk_percentage = (total_risk_score / total_customers) * 100 if total_customers > 0 else 0
            
            # Risk distribution
            high_risk = sum(1 for c in customers_data if c['churn_score'] > 0.7)
            medium_risk = sum(1 for c in customers_data if 0.4 <= c['churn_score'] <= 0.7)
            low_risk = sum(1 for c in customers_data if c['churn_score'] < 0.4)
            
            # Calculate distributions
            age_dist = analyze_age_distribution(customers_data)
            location_dist = analyze_location_distribution(customers_data)
            gender_dist = analyze_gender_distribution(customers_data)
            subscription_dist = analyze_subscription_distribution(customers_data)
            usage_dist = analyze_usage_distribution(customers_data)
            
            analysis = {
                'total_customers': total_customers,
                'churn_rate': churn_rate,
                'avg_monthly_bill': avg_monthly_bill,
                'avg_usage': avg_usage,
                'high_risk_customers': high_risk,
                'medium_risk_customers': medium_risk,
                'low_risk_customers': low_risk,
                'age_distribution': age_dist,
                'location_distribution': location_dist,
                'gender_distribution': gender_dist,
                'subscription_distribution': subscription_dist,
                'usage_distribution': usage_dist,
                'bill_risk_distribution': bill_risk_distribution,
                'avg_risk_percentage': avg_risk_percentage,
                'max_monthly_bill': max_monthly_bill
            }
            
            return render_template('dynamic_analysis.html', 
                                form=form,
                                analysis=analysis,
                                selected_criteria={
                                    'age_range': age_range,
                                    'location': location,
                                    'gender': gender,
                                    'subscription_range': subscription_range,
                                    'usage_range': usage_range
                                },
                                locations=locations)
            
        except Exception as e:
            current_app.logger.error(f"Error in dynamic analysis: {str(e)}")
            flash(f'Error performing analysis: {str(e)}', 'error')
            return redirect(request.url)
    
    # For GET request, show the analysis form with empty analysis
    empty_analysis = {
        'total_customers': 0,
        'churn_rate': 0.0,
        'avg_monthly_bill': 0.0,
        'avg_usage': 0.0,
        'high_risk_customers': 0,
        'medium_risk_customers': 0,
        'low_risk_customers': 0,
        'age_distribution': {
            '18-25': 0, '26-35': 0, '36-45': 0, '46-55': 0, '56+': 0
        },
        'location_distribution': {},
        'gender_distribution': {'male': 0, 'female': 0, 'other': 0},
        'subscription_distribution': {
            '0-6 months': 0, '7-12 months': 0, '13-24 months': 0, '25+ months': 0
        },
        'usage_distribution': {
            '0-50 GB': 0, '51-100 GB': 0, '101-200 GB': 0, '201+ GB': 0
        },
        'bill_risk_distribution': {
            'very_high': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'very_low': 0
        },
        'avg_risk_percentage': 0.0,
        'max_monthly_bill': 0.0
    }
    return render_template('dynamic_analysis.html', 
                         form=form,
                         analysis=empty_analysis,
                         locations=locations)

def analyze_age_distribution(customers):
    age_groups = {
        '18-25': 0,
        '26-35': 0,
        '36-45': 0,
        '46-55': 0,
        '56+': 0
    }
    
    for customer in customers:
        age = customer.get('age')
        if age is not None:
            if 18 <= age <= 25:
                age_groups['18-25'] += 1
            elif 26 <= age <= 35:
                age_groups['26-35'] += 1
            elif 36 <= age <= 45:
                age_groups['36-45'] += 1
            elif 46 <= age <= 55:
                age_groups['46-55'] += 1
            else:
                age_groups['56+'] += 1
    
    return age_groups

def analyze_location_distribution(customers):
    locations = {}
    for customer in customers:
        location = customer.get('location')
        if location:
            locations[location] = locations.get(location, 0) + 1
    return locations

def analyze_gender_distribution(customers):
    genders = {'male': 0, 'female': 0, 'other': 0}
    for customer in customers:
        gender = customer.get('gender', '').lower()
        if gender in genders:
            genders[gender] += 1
        else:
            genders['other'] += 1
    return genders

def analyze_subscription_distribution(customers):
    subscription_ranges = {
        '0-6 months': 0,
        '7-12 months': 0,
        '13-24 months': 0,
        '25+ months': 0
    }
    
    for customer in customers:
        months = customer.get('subscription_length_months', 0)
        if months <= 6:
            subscription_ranges['0-6 months'] += 1
        elif 7 <= months <= 12:
            subscription_ranges['7-12 months'] += 1
        elif 13 <= months <= 24:
            subscription_ranges['13-24 months'] += 1
        else:
            subscription_ranges['25+ months'] += 1
    
    return subscription_ranges

def analyze_usage_distribution(customers):
    usage_ranges = {
        '0-50 GB': 0,
        '51-100 GB': 0,
        '101-200 GB': 0,
        '201+ GB': 0
    }
    
    for customer in customers:
        usage = customer.get('total_usage_gb', 0)
        if usage <= 50:
            usage_ranges['0-50 GB'] += 1
        elif 51 <= usage <= 100:
            usage_ranges['51-100 GB'] += 1
        elif 101 <= usage <= 200:
            usage_ranges['101-200 GB'] += 1
        else:
            usage_ranges['201+ GB'] += 1
    
    return usage_ranges