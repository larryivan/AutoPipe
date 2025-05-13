from flask import Blueprint, request, jsonify, send_file
import os
import logging
from werkzeug.utils import secure_filename
from services.file_service import FileService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
file_routes = Blueprint('file_routes', __name__)

# Initialize services
file_service = FileService()

@file_routes.route('/files', methods=['GET'])
def get_files():
    """Get all files for a conversation"""
    conversation_id = request.args.get('conversation_id')
    path = request.args.get('path', '')
    
    if not conversation_id:
        return jsonify({'error': 'Missing conversation_id parameter'}), 400
    
    files = file_service.get_all_files(conversation_id, path)
    return jsonify(files)

@file_routes.route('/files/search', methods=['GET'])
def search_files():
    """Search for files by name"""
    query = request.args.get('query', '')
    conversation_id = request.args.get('conversation_id')
    
    if not conversation_id:
        return jsonify({'error': 'Missing conversation_id parameter'}), 400
    
    files = file_service.search_files(query, conversation_id)
    return jsonify(files)

@file_routes.route('/files', methods=['POST'])
def create_file():
    """Create a new file"""
    data = request.json
    name = data.get('name')
    content = data.get('content', '')
    conversation_id = data.get('conversation_id')
    path = data.get('path', '')
    
    if not name or not conversation_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        file = file_service.create_file(name, content, conversation_id, path)
        return jsonify(file)
    except Exception as e:
        logger.error(f"Error creating file: {e}")
        return jsonify({'error': str(e)}), 500

@file_routes.route('/files/mkdir', methods=['POST'])
def create_directory():
    """Create a new directory"""
    data = request.json
    name = data.get('name')
    conversation_id = data.get('conversation_id')
    path = data.get('path', '')
    
    if not name or not conversation_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        directory = file_service.create_directory(name, conversation_id, path)
        return jsonify(directory)
    except Exception as e:
        logger.error(f"Error creating directory: {e}")
        return jsonify({'error': str(e)}), 500

@file_routes.route('/files/upload', methods=['POST'])
def upload_file():
    """Upload a file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    conversation_id = request.form.get('conversation_id')
    path = request.form.get('path', '')
    
    if not file or not conversation_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        filename = secure_filename(file.filename)
        uploaded_file = file_service.upload_file(file, filename, conversation_id, path)
        return jsonify(uploaded_file)
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({'error': str(e)}), 500

@file_routes.route('/files/<path:file_path>', methods=['GET'])
def get_file_content(file_path):
    """Get file content"""
    conversation_id = request.args.get('conversation_id')
    
    if not conversation_id:
        return jsonify({'error': 'Missing conversation_id parameter'}), 400
    
    try:
        file_info = file_service.get_file_content(file_path, conversation_id)
        return jsonify(file_info)
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error getting file content: {e}")
        return jsonify({'error': str(e)}), 500

@file_routes.route('/files/<path:file_path>', methods=['PUT'])
def update_file_content(file_path):
    """Update file content"""
    data = request.json
    content = data.get('content')
    conversation_id = data.get('conversation_id')
    
    if content is None or not conversation_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        updated_file = file_service.update_file_content(file_path, content, conversation_id)
        return jsonify(updated_file)
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error updating file content: {e}")
        return jsonify({'error': str(e)}), 500

@file_routes.route('/files/<path:file_path>', methods=['DELETE'])
def delete_file(file_path):
    """Delete a file"""
    conversation_id = request.args.get('conversation_id')
    
    if not conversation_id:
        return jsonify({'error': 'Missing conversation_id parameter'}), 400
    
    try:
        success = file_service.delete_file(file_path, conversation_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return jsonify({'error': str(e)}), 500