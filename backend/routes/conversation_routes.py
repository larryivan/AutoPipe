from flask import Blueprint, request, jsonify
import os
import logging
from services.conversation_service import ConversationService
from services.ai_service import AIService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
conversation_routes = Blueprint('conversation_routes', __name__)

# Initialize services
ai_service = AIService(
    api_key=os.environ.get('OPENAI_API_KEY'),
    api_base=os.environ.get('OPENAI_API_BASE'),
    model_name=os.environ.get('OPENAI_MODEL_NAME', 'gpt-3.5-turbo'),
    temperature=0.7
)
conversation_service = ConversationService(ai_service=ai_service)

@conversation_routes.route('/conversations', methods=['GET'])
def get_all_conversations():
    """Get all conversations"""
    conversations = conversation_service.get_all_conversations()
    return jsonify(conversations)

@conversation_routes.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get a specific conversation"""
    try:
        conversation = conversation_service.get_conversation(conversation_id)
        return jsonify(conversation)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404

@conversation_routes.route('/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation"""
    data = request.json or {}
    title = data.get('title')
    mode = data.get('mode', 'chat')  # Default to chat mode
    
    conversation = conversation_service.create_conversation(title=title, mode=mode)
    return jsonify(conversation)

@conversation_routes.route('/conversations/<conversation_id>', methods=['PUT'])
def update_conversation(conversation_id):
    """Update a conversation"""
    data = request.json or {}
    title = data.get('title')
    
    if not title:
        return jsonify({"error": "Title is required"}), 400
        
    try:
        conversation = conversation_service.rename_conversation(conversation_id, title)
        return jsonify(conversation)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404

# Add new route for setting conversation mode
@conversation_routes.route('/conversations/<conversation_id>/mode', methods=['PUT'])
def set_conversation_mode(conversation_id):
    """Set the mode for a conversation"""
    data = request.json or {}
    mode = data.get('mode')
    
    if not mode or mode not in ['chat', 'agent']:
        return jsonify({"error": "Invalid mode. Must be 'chat' or 'agent'"}), 400
        
    try:
        conversation = conversation_service.set_conversation_mode(conversation_id, mode)
        return jsonify(conversation)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@conversation_routes.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation"""
    result = conversation_service.delete_conversation(conversation_id)
    
    if result:
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Conversation not found"}), 404

@conversation_routes.route('/conversations/<conversation_id>/messages', methods=['POST'])
def send_message(conversation_id):
    """Send a message in a conversation"""
    data = request.json or {}
    message_text = data.get('message')
    
    if not message_text:
        return jsonify({"error": "Message text is required"}), 400
        
    try:
        result = conversation_service.send_message(conversation_id, message_text)
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({'error': 'Failed to process message'}), 500
