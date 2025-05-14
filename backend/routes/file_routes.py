from flask import Blueprint, request, jsonify, send_file
import os
import logging
from werkzeug.utils import secure_filename
from services.file_service import FileService
import mimetypes
import time

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

@file_routes.route('/files/download', methods=['POST'])
def download_file():
    """使用aria2c下载文件"""
    data = request.json
    url = data.get('url')
    conversation_id = data.get('conversation_id')
    filename = data.get('filename')
    path = data.get('path', '')
    
    if not url or not conversation_id:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        download_info = file_service.download_file(url, conversation_id, filename, path)
        return jsonify(download_info)
    except Exception as e:
        logger.error(f"下载文件错误: {e}")
        return jsonify({'error': str(e)}), 500

@file_routes.route('/files/download/status', methods=['GET'])
def get_download_status():
    """获取下载状态"""
    download_id = request.args.get('download_id')
    conversation_id = request.args.get('conversation_id')
    
    if not download_id and not conversation_id:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        status = file_service.get_download_status(download_id, conversation_id)
        return jsonify(status)
    except Exception as e:
        logger.error(f"获取下载状态错误: {e}")
        return jsonify({'error': str(e)}), 500

@file_routes.route('/files/download/cancel', methods=['POST'])
def cancel_download():
    """取消下载"""
    data = request.json
    download_id = data.get('download_id')
    
    if not download_id:
        return jsonify({'error': '缺少下载ID参数'}), 400
    
    try:
        success = file_service.cancel_download(download_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': '找不到指定的下载任务'}), 404
    except Exception as e:
        logger.error(f"取消下载错误: {e}")
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

@file_routes.route('/files/rename', methods=['POST'])
def rename_file():
    """重命名文件或目录"""
    data = request.json
    old_path = data.get('old_path')
    new_name = data.get('new_name')
    conversation_id = data.get('conversation_id')
    
    if not old_path or not new_name or not conversation_id:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        renamed_file = file_service.rename_file(old_path, new_name, conversation_id)
        return jsonify(renamed_file)
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        return jsonify({'error': '文件未找到'}), 404
    except ValueError as e:
        logger.error(f"重命名错误: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"重命名文件错误: {e}")
        return jsonify({'error': str(e)}), 500

@file_routes.route('/files/download_file/<path:file_path>', methods=['GET'])
def download_direct_file(file_path):
    """下载文件（直接下载，而不是通过aria2c）"""
    conversation_id = request.args.get('conversation_id')
    
    if not conversation_id:
        return jsonify({'error': 'Missing conversation_id parameter'}), 400
    
    try:
        file_full_path = file_service.get_file_for_download(file_path, conversation_id)
        filename = os.path.basename(file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_full_path):
            return jsonify({'error': '文件未找到'}), 404
            
        # 发送文件
        return send_file(
            file_full_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetypes.guess_type(file_full_path)[0] or 'application/octet-stream'
        )
    except FileNotFoundError:
        return jsonify({'error': '文件未找到'}), 404
    except Exception as e:
        logger.error(f"下载文件错误: {e}")
        return jsonify({'error': str(e)}), 500

@file_routes.route('/files/download_batch', methods=['POST'])
def download_batch_files():
    """下载多个文件或文件夹的ZIP压缩包"""
    data = request.json
    file_paths = data.get('file_paths')
    conversation_id = data.get('conversation_id')

    if not conversation_id or not file_paths:
        return jsonify({'error': 'Missing conversation_id or file_paths parameter'}), 400
    
    if not isinstance(file_paths, list) or len(file_paths) == 0:
        return jsonify({'error': 'file_paths must be a non-empty list'}), 400

    try:
        logger.info(f"Attempting to create zip for conversation {conversation_id} with files: {file_paths}")
        zip_stream = file_service.create_zip_for_files(file_paths, conversation_id)
        
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        zip_filename = f"batch_download_{conversation_id}_{timestamp}.zip"
        logger.info(f"Zip created, serving as {zip_filename}")
        
        return send_file(
            zip_stream,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
    except FileNotFoundError as e:
        logger.error(f"File not found during zip creation: {e}")
        return jsonify({'error': 'One or more files not found for batch download'}), 404
    except ValueError as e:
        logger.error(f"Value error during zip creation: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error during batch download: {e}")
        return jsonify({'error': 'An unexpected error occurred during batch download'}), 500