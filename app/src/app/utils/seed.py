from .. import db
from ..models import User

def seed_database():
    """Seed the database with initial data if no users exist."""
    if User.query.first() is None:
        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin',
            company_name='System Admin',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Create analyst user
        analyst = User(
            username='analyst',
            email='analyst@example.com',
            role='analyst',
            company_name='Data Analytics Team',
            is_active=True
        )
        analyst.set_password('analyst123')
        db.session.add(analyst)

        # Create regular user
        user = User(
            username='user',
            email='user@example.com',
            role='user',
            company_name='Demo Company',
            is_active=True
        )
        user.set_password('user123')
        db.session.add(user)

        db.session.commit()
        print("Database seeded with default users.") 