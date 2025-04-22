# run.py
from src.app import create_app, db
from src.app.models import User, Subscription, BatchJob
from src.app.utils.data_processing import analyze_data
from src.app.utils.visualization import create_plots

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Subscription': Subscription,
        'BatchJob': BatchJob,
        'analyze_data': analyze_data,
        'create_plots': create_plots
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)