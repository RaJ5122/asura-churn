
# Customer Churn Analysis System

A comprehensive system for analyzing and predicting customer churn using machine learning and data analytics.

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Default Users](#default-users)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Features

- User authentication and authorization
- Customer data management
- Churn prediction and analysis
- Historical trend visualization
- Batch processing capabilities
- Role-based access control
- Interactive dashboards

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.8 or higher
- PostgreSQL database
- Redis (for background tasks)
- Git

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd asura
```

2. Create and activate a virtual environment:
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On Unix or MacOS
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Create a `.env` file in the root directory with the following variables:
```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://username:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
```

2. Initialize the database:
```bash
flask db upgrade
```

## Running the Application

1. Start the Redis server (required for background tasks):
```bash
# On Windows (if installed via Windows Subsystem for Linux)
redis-server

# On Unix or MacOS
redis-server
```

2. Start the Flask application:
```bash
python run.py
```

3. Access the application at `http://localhost:5000`

## Default Users

The system creates the following default users on first run:

| Role     | Email             | Password   |
|----------|-------------------|------------|
| Admin    | admin@example.com | admin123   |
| Analyst  | analyst@example.com| analyst123 |
| User     | user@example.com  | user123    |

## Project Structure

```
asura/
├── app/                    # Main application package
│   ├── src/               # Source code
│   │   ├── app/          # Application core
│   │   │   ├── models.py      # Database models
│   │   │   ├── routes.py      # Application routes
│   │   │   ├── utils/         # Utility functions
│   │   │   └── templates/     # HTML templates
│   │   └── ml/                # Machine learning models
│   ├── migrations/            # Database migrations
│   └── static/               # Static files
├── tests/                    # Test files
├── requirements.txt          # Python dependencies
├── run.py                   # Application entry point
└── .env                     # Environment variables
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
