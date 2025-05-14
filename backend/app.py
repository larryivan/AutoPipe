from flask import Flask
from flask_cors import CORS
import os

# Import routes
from routes.conversation_routes import conversation_routes
from routes.file_routes import file_routes
from routes.pipeline_routes import pipeline_routes
from routes.terminal_routes import terminal_routes
from routes.monitor_routes import monitor_routes

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Register blueprints
app.register_blueprint(conversation_routes, url_prefix='/api')
app.register_blueprint(file_routes, url_prefix='/api')
app.register_blueprint(pipeline_routes, url_prefix='/api')
app.register_blueprint(terminal_routes, url_prefix='/api')
app.register_blueprint(monitor_routes, url_prefix='/api')

# Create required directories
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CONVERSATIONS_DIR = os.path.join(DATA_DIR, 'conversations')
FILES_DIR = os.path.join(DATA_DIR, 'files')
LOGS_DIR = os.path.join(DATA_DIR, 'logs')
PLANS_DIR = os.path.join(DATA_DIR, 'plans')
TERMINAL_LOGS_DIR = os.path.join(DATA_DIR, 'terminal_logs')

for dir_path in [DATA_DIR, CONVERSATIONS_DIR, FILES_DIR, LOGS_DIR, PLANS_DIR, TERMINAL_LOGS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Default route
@app.route('/')
def index():
    return {
        'message': 'BioinfoFlow API Server',
        'status': 'running',
        'version': '1.0.0'
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)