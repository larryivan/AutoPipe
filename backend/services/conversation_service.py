import os
import json
import uuid
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data directories
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
CONVERSATIONS_DIR = os.path.join(DATA_DIR, 'conversations')

# Ensure directories exist
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)

class ConversationService:
    """Service for managing conversations and messages"""
    
    def __init__(self, ai_service=None, pipeline_service=None):
        """Initialize the conversation service"""
        self.ai_service = ai_service
        self.pipeline_service = pipeline_service
    
    def get_all_conversations(self) -> List[Dict]:
        """Get all conversations"""
        conversations = []
        
        if not os.path.exists(CONVERSATIONS_DIR):
            return conversations
            
        for filename in os.listdir(CONVERSATIONS_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(CONVERSATIONS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        conversation = json.load(f)
                        conversations.append({
                            'id': conversation.get('id', ''),
                            'title': conversation.get('title', 'Untitled Conversation'),
                            'created_at': conversation.get('created_at', ''),
                            'updated_at': conversation.get('updated_at', ''),
                            'mode': conversation.get('mode', 'chat'),
                            'message_count': len(conversation.get('messages', []))
                        })
                except Exception as e:
                    logger.error(f"Error reading conversation file {filename}: {e}")
        
        # Sort by updated_at in descending order
        return sorted(conversations, key=lambda x: x.get('updated_at', ''), reverse=True)
    
    def get_conversation(self, conversation_id: str) -> Dict:
        """Get a specific conversation"""
        filepath = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Conversation {conversation_id} not found")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def create_conversation(self, title: Optional[str] = None, mode: str = 'chat') -> Dict:
        """Create a new conversation"""
        conversation_id = f"conv{uuid.uuid4().hex[:8]}"
        
        if not title:
            title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
        timestamp = datetime.now().isoformat()
        
        # Set welcome message based on mode
        welcome_message = (
            "Welcome! How can I assist you with your bioinformatics questions today?" 
            if mode == 'chat' else
            "Welcome to Agent Mode! I'll help you plan and execute bioinformatics workflows. "
            "Please describe your analysis goal and the data you're working with."
        )
        
        conversation = {
            'id': conversation_id,
            'title': title,
            'created_at': timestamp,
            'updated_at': timestamp,
            'mode': mode,  # Add mode field
            'messages': [
                {
                    'id': f"welcome-{uuid.uuid4().hex[:8]}",
                    'text': welcome_message,
                    'sender': 'bot',
                    'timestamp': timestamp,
                    'isWelcome': True
                }
            ]
        }
        
        self._save_conversation(conversation)
        
        return conversation
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        filepath = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
        
        if not os.path.exists(filepath):
            return False
            
        os.remove(filepath)
        return True
    
    def rename_conversation(self, conversation_id: str, title: str) -> Dict:
        """Rename a conversation"""
        conversation = self.get_conversation(conversation_id)
        conversation['title'] = title
        conversation['updated_at'] = datetime.now().isoformat()
        
        self._save_conversation(conversation)
        
        return conversation
    
    def set_conversation_mode(self, conversation_id: str, mode: str) -> Dict:
        """Set the mode for a conversation (chat or agent)"""
        if mode not in ['chat', 'agent']:
            raise ValueError("Mode must be either 'chat' or 'agent'")
            
        conversation = self.get_conversation(conversation_id)
        
        # 如果模式没有改变，则不做任何处理
        if conversation.get('mode') == mode:
            return conversation
        
        # 更新模式
        conversation['mode'] = mode
        conversation['updated_at'] = datetime.now().isoformat()
        
        # 针对不同模式添加不同的系统消息
        timestamp = datetime.now().isoformat()
        
        if mode == 'chat':
            mode_message = {
                'id': f"mode-{uuid.uuid4().hex[:8]}",
                'text': "Switched to Chat Mode - You can ask any bioinformatics questions",
                'sender': 'system',
                'timestamp': timestamp,
                'isSystem': True
            }
        else:  # agent mode
            mode_message = {
                'id': f"mode-{uuid.uuid4().hex[:8]}",
                'text': "Switched to Agent Mode - You can describe your bioinformatics analysis goals, I'll create workflows to help you",
                'sender': 'system',
                'timestamp': timestamp,
                'isSystem': True
            }
        
        conversation['messages'].append(mode_message)
        
        self._save_conversation(conversation)
        
        return conversation
    
    def add_user_message(self, conversation_id: str, message_text: str) -> Dict:
        """Add a user message to the conversation"""
        conversation = self.get_conversation(conversation_id)
        
        timestamp = datetime.now().isoformat()
        message_id = f"user-{uuid.uuid4().hex[:8]}"
        
        user_message = {
            'id': message_id,
            'text': message_text,
            'sender': 'user',
            'timestamp': timestamp
        }
        
        conversation['messages'].append(user_message)
        conversation['updated_at'] = timestamp
        
        self._save_conversation(conversation)
        
        return user_message
    
    def add_bot_message(self, conversation_id: str, message_text: str, workflow_id: Optional[str] = None) -> Dict:
        """Add a bot message to the conversation"""
        conversation = self.get_conversation(conversation_id)
        
        timestamp = datetime.now().isoformat()
        message_id = f"bot-{uuid.uuid4().hex[:8]}"
        
        bot_message = {
            'id': message_id,
            'text': message_text,
            'sender': 'bot',
            'timestamp': timestamp
        }
        
        # If workflow_id is provided, attach it to the message
        if workflow_id:
            bot_message['workflow_id'] = workflow_id
        
        conversation['messages'].append(bot_message)
        conversation['updated_at'] = timestamp
        
        self._save_conversation(conversation)
        
        return bot_message
    
    def get_messages(self, conversation_id: str) -> List[Dict]:
        """Get all messages for a conversation"""
        conversation = self.get_conversation(conversation_id)
        return conversation.get('messages', [])
    
    def send_message(self, conversation_id: str, message_text: str) -> Dict:
        """Process a user message and generate a bot response"""
        # Add user message
        user_message = self.add_user_message(conversation_id, message_text)
        
        # Get conversation mode
        conversation = self.get_conversation(conversation_id)
        mode = conversation.get('mode', 'chat')
        
        # Generate bot response based on mode
        if mode == 'agent':
            return self._process_agent_mode(conversation_id, message_text, user_message)
        else:
            return self._process_chat_mode(conversation_id, message_text, user_message)
    
    def _process_chat_mode(self, conversation_id: str, message_text: str, user_message: Dict) -> Dict:
        """Process message in chat mode - just respond to questions"""
        if not self.ai_service:
            response_text = "I'm sorry, the AI service is currently unavailable."
            bot_message = self.add_bot_message(conversation_id, response_text)
            return {'user_message': user_message, 'ai_message': bot_message}
            
        # Get conversation history for context
        conversation = self.get_conversation(conversation_id)
        history = conversation.get('messages', [])[-5:]  # Get last 5 messages for context
        
        # Format history for AI model
        formatted_history = []
        for msg in history:
            if msg.get('isWelcome') or msg.get('isSystem'):
                continue
            formatted_history.append({
                'role': 'assistant' if msg.get('sender') == 'bot' else 'user',
                'content': msg.get('text', '')
            })
        
        # Use AI service to generate response
        try:
            prompt = f"""
            You are in CHAT MODE. The user is asking questions about bioinformatics.
            Your goal is to answer their questions without automatically planning or executing workflows.
            If they want to run an analysis, suggest they switch to Agent Mode.
            
            Here is the recent conversation history:
            {''.join([f"{'Bot' if msg['role'] == 'assistant' else 'User'}: {msg['content']}\\n" for msg in formatted_history])}
            
            Provide a helpful answer about bioinformatics concepts, tools, or techniques.
            """
            
            response_text = self.ai_service.generate_response(prompt)
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            response_text = "I'm sorry, I encountered an error while processing your request."
        
        # Add bot message
        bot_message = self.add_bot_message(conversation_id, response_text)
        
        return {
            'user_message': user_message,
            'ai_message': bot_message
        }
    
    def _process_agent_mode(self, conversation_id: str, message_text: str, user_message: Dict) -> Dict:
        """Process message in agent mode - plan and execute workflows"""
        if not self.ai_service or not self.pipeline_service:
            response_text = "I'm sorry, Agent Mode is unavailable due to missing services."
            bot_message = self.add_bot_message(conversation_id, response_text)
            return {'user_message': user_message, 'ai_message': bot_message}
        
        try:
            # First, analyze if we need to create a workflow
            analysis_prompt = f"""
            Analyze the following user request in AGENT MODE:
            "{message_text}"
            
            Is the user asking for a bioinformatics workflow or analysis to be performed?
            Answer with 'YES' if they want a workflow created, or 'NO' if they're just asking a question.
            """
            
            analysis_response = self.ai_service.generate_response(analysis_prompt).strip()
            
            # If user wants a workflow
            if analysis_response.upper().startswith("YES"):
                # Get available files for this conversation
                from os import listdir, path
                files_dir = self.pipeline_service.get_conversation_files_dir(conversation_id)
                
                available_files = []
                if path.exists(files_dir):
                    for filename in listdir(files_dir):
                        file_path = path.join(files_dir, filename)
                        if path.isfile(file_path):
                            file_type = filename.split('.')[-1] if '.' in filename else 'unknown'
                            available_files.append({
                                'name': filename,
                                'path': filename,
                                'type': file_type
                            })
                
                # Create a workflow
                workflow = self.pipeline_service.create_workflow(
                    conversation_id=conversation_id,
                    goal=message_text,
                    files=available_files
                )
                
                # Generate response text about the created workflow
                response_text = f"""I've created a workflow based on your request:

**{workflow.get('title', 'Analysis Workflow')}**

This workflow contains {len(workflow.get('steps', []))} steps:

{chr(10).join([f"- Step {i+1}: {step.get('title')}" for i, step in enumerate(workflow.get('steps', []))])}

You can view and execute this workflow in the pipeline manager below.
"""
                
                # Add bot message with workflow reference
                bot_message = self.add_bot_message(
                    conversation_id, 
                    response_text, 
                    workflow_id=workflow.get('id')
                )
                
            else:
                # Normal chat response for questions in agent mode
                prompt = f"""
                You are in AGENT MODE for bioinformatics analysis. The user asked:
                "{message_text}"
                
                Since this appears to be a general question rather than a workflow request,
                please answer their question. Focus on bioinformatics concepts and tools.
                """
                
                response_text = self.ai_service.generate_response(prompt)
                bot_message = self.add_bot_message(conversation_id, response_text)
            
        except Exception as e:
            logger.error(f"Error in agent mode processing: {e}")
            response_text = "I'm sorry, I encountered an error while planning your workflow."
            bot_message = self.add_bot_message(conversation_id, response_text)
        
        return {
            'user_message': user_message,
            'ai_message': bot_message
        }
    
    def _save_conversation(self, conversation: Dict) -> None:
        """Save conversation to file"""
        filepath = os.path.join(CONVERSATIONS_DIR, f"{conversation['id']}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
