from flask import Blueprint, request, jsonify
import os
import logging
from services.pipeline_service import PipelineService
from services.file_service import FileService
from services.chat_service import AIService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
pipeline_routes = Blueprint('pipeline_routes', __name__)

# Initialize services
file_service = FileService()
ai_service = AIService()
pipeline_service = PipelineService(llm_service=ai_service)

@pipeline_routes.route('/workflows', methods=['GET'])
def get_workflows():
    """Get all workflows for a conversation"""
    conversation_id = request.args.get('conversation_id')
    
    if conversation_id:
        workflows = pipeline_service.list_workflows(conversation_id)
    else:
        workflows = pipeline_service.list_workflows()
    
    return jsonify(workflows)

@pipeline_routes.route('/workflows/<workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    """Get a specific workflow"""
    workflow = pipeline_service.get_workflow(workflow_id)
    
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404
    
    return jsonify(workflow)

@pipeline_routes.route('/workflows/<workflow_id>', methods=['PUT'])
def update_workflow(workflow_id):
    """Update a workflow"""
    data = request.json
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    try:
        updated_workflow = pipeline_service.update_workflow(workflow_id, data)
        return jsonify(updated_workflow)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error updating workflow: {e}")
        return jsonify({'error': str(e)}), 500

@pipeline_routes.route('/workflows', methods=['POST'])
def create_workflow():
    """Create a new workflow"""
    data = request.json
    conversation_id = data.get('conversation_id')
    goal = data.get('goal')
    
    if not conversation_id or not goal:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        # Get files for this conversation
        files = file_service.get_all_files(conversation_id)
        
        # Create workflow
        workflow = pipeline_service.create_workflow(conversation_id, goal, files)
        
        return jsonify(workflow)
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        return jsonify({'error': str(e)}), 500

@pipeline_routes.route('/workflows/<workflow_id>/steps/<step_id>/execute', methods=['POST'])
def execute_step(workflow_id, step_id):
    """Execute a specific step in a workflow"""
    data = request.json
    conversation_id = data.get('conversation_id')
    
    if not conversation_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        result = pipeline_service.execute_step(workflow_id, step_id, conversation_id)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error executing step: {e}")
        return jsonify({'error': str(e)}), 500

@pipeline_routes.route('/pipelines/plan', methods=['POST'])
def plan_pipeline():
    """Plan a new pipeline"""
    data = request.json
    conversation_id = data.get('conversation_id')
    goal = data.get('goal')
    
    if not conversation_id or not goal:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        # Get files for this conversation
        files = file_service.get_all_files(conversation_id)
        
        # Plan pipeline
        pipeline = pipeline_service.plan_pipeline(conversation_id, goal, files)
        
        return jsonify(pipeline)
    except Exception as e:
        logger.error(f"Error planning pipeline: {e}")
        return jsonify({'error': str(e)}), 500
