from app.src.app import create_app
from app.src.app.utils.seed import seed_database
from app.src.app import db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Create database tables
        db.create_all()
        # Seed the database with default users if none exist
        seed_database()
    app.run(debug=True) 