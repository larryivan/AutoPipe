from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    print("Starting Flask server...")
    print(f"Database path: {os.path.join(os.path.dirname(__file__), 'app', 'database', 'db.json')}")
    print(f"Projects path: {os.path.join(os.path.dirname(__file__), 'projects')}")
    print("Server running at http://localhost:5000")
    print("API endpoints:")
    print("  GET    /api/projects")
    print("  POST   /api/projects")
    print("  PUT    /api/projects/<id>")
    print("  DELETE /api/projects/<id>")
    app.run(debug=True, host='0.0.0.0', port=5000)
