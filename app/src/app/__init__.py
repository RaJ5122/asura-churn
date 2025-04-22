from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_admin import Admin
from flask_wtf.csrf import CSRFProtect
from celery import Celery
from .config import Config
import os

db = SQLAlchemy()
login = LoginManager()
migrate = Migrate()
admin = Admin(name='Churn Analytics', template_mode='bootstrap3')
csrf = CSRFProtect()
celery = None  # Initialize celery as None

def make_celery(app):
    if not app.config.get('USE_CELERY', False):
        print("Celery is disabled in configuration")
        class DummyCelery:
            def task(self, *args, **kwargs):
                def decorator(f):
                    def wrapper(*args, **kwargs):
                        print("Warning: Celery is disabled. Running task synchronously.")
                        return f(*args, **kwargs)
                    wrapper.delay = lambda *args, **kwargs: f(*args, **kwargs)  # Fix the delay method
                    return wrapper
                return decorator
        return DummyCelery()

    try:
        # Test Redis connection
        import redis
        redis_client = redis.Redis.from_url(app.config['CELERY_BROKER_URL'])
        redis_client.ping()
        
        celery = Celery(
            app.import_name,
            broker=app.config['CELERY_BROKER_URL'],
            backend=app.config['CELERY_RESULT_BACKEND']
        )
        
        # Update Celery configuration
        celery.conf.update(app.config)
        
        # Windows-specific settings
        if os.name == 'nt':  # Windows
            celery.conf.update(
                worker_pool='solo',
                worker_concurrency=1,
                task_always_eager=False
            )
        
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
        return celery
    except Exception as e:
        print(f"Warning: Celery initialization failed: {str(e)}")
        print("Falling back to synchronous processing")
        # Return a dummy Celery instance that will fail gracefully
        class DummyCelery:
            def task(self, *args, **kwargs):
                def decorator(f):
                    def wrapper(*args, **kwargs):
                        print("Warning: Celery is not available. Running task synchronously.")
                        return f(*args, **kwargs)
                    wrapper.delay = lambda *args, **kwargs: f(*args, **kwargs)  # Fix the delay method
                    return wrapper
                return decorator
        return DummyCelery()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login.init_app(app)
    migrate.init_app(app, db)
    admin.init_app(app)
    csrf.init_app(app)

    # Initialize Celery
    global celery
    celery = make_celery(app)
    app.celery = celery

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app