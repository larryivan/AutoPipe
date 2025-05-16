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
            {''.join([f"{'Bot' if msg['role'] == 'assistant' else 'User'}: {msg['content']}\n" for msg in formatted_history])}
            
            Provide a helpful answer about bioinformatics concepts, tools, or techniques.
            """
            
            response_text = self.ai_service.generate_response(prompt)
            if not response_text:
                logger.warning(f"AI service returned empty response for chat in conversation {conversation_id}")
                response_text = "I'm sorry, I couldn't generate a response at this moment. Please try again."
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
            # 获取当前会话的消息历史以提供上下文
            conversation = self.get_conversation(conversation_id)
            history = conversation.get('messages', [])[-5:]  # 获取最近5条消息
            
            # 格式化历史以便AI模型使用
            formatted_history = []
            for msg in history:
                if msg.get('isWelcome') or msg.get('isSystem'):
                    continue
                formatted_history.append({
                    'role': 'assistant' if msg.get('sender') == 'bot' else 'user',
                    'content': msg.get('text', '')
                })
            
            # 分析请求，判断用户意图
            analysis_prompt = f"""
            分析用户在Agent模式下的请求，基于对话历史和当前消息。
            
            当前消息: "{message_text}"
            
            历史消息:
            {''.join([f"{'Bot' if msg['role'] == 'assistant' else 'User'}: {msg['content']}\n" for msg in formatted_history[:-1]])}
            
            请确定用户的意图:
            1. CREATE - 用户想要创建新的工作流
            2. MODIFY - 用户想要修改现有工作流
            3. EXECUTE - 用户想要执行工作流或某些步骤
            4. QUESTION - 用户只是提问，不需要工作流操作
            
            只回答一个单词: CREATE, MODIFY, EXECUTE 或 QUESTION
            """
            
            intent = self.ai_service.generate_response(analysis_prompt).strip().upper()
            logger.info(f"Agent mode intent analysis: {intent}")
            
            # 获取工作目录的文件列表，以提供给AI参考
            try:
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
                
                files_context = "\n".join([f"- {f['name']} ({f['type']})" for f in available_files])
                if not files_context:
                    files_context = "No files available"
            except Exception as e:
                logger.error(f"Error getting file list: {e}")
                files_context = "Error retrieving file list"
            
            if intent == "CREATE":
                # 如果用户想创建工作流
                final_response_text = None
                workflow_id_for_message = None
                try:
                    # 获取最近的工作流列表
                    recent_workflows = self.pipeline_service.list_workflows(conversation_id)
                    workflows_context = ""
                    if recent_workflows:
                        workflows_context = "最近的工作流:\n" + "\n".join([
                            f"- {w['title']} (ID: {w['id']}, 状态: {w['status']})" 
                            for w in recent_workflows[:3]
                        ])

                    # 为 pipeline_service.create_workflow 添加日志
                    logger.info(f"Attempting to create workflow for conversation_id: {conversation_id}")
                    logger.info(f"Goal for workflow creation: '{message_text}'")
                    logger.info(f"Available files for workflow creation: {available_files}")

                    # 创建工作流
                    workflow = self.pipeline_service.create_workflow(
                        conversation_id=conversation_id,
                        goal=message_text,
                        files=available_files
                    )

                    logger.info(f"Workflow object received from pipeline_service: {workflow}")

                    if not workflow or not isinstance(workflow, dict):
                        logger.error(f"Pipeline service returned invalid workflow object: {workflow} for conversation {conversation_id} when creating a new workflow.")
                        final_response_text = "我尝试创建工作流，但内部处理工作流数据时发生错误。请重试或联系支持人员。"
                        # workflow_id_for_message 保持 None
                    else:
                        actual_steps = workflow.get('steps', [])
                        steps_section_md = ""

                        if actual_steps: # Check if the list itself is not empty
                            step_details_list = []
                            for i, step_data in enumerate(actual_steps):
                                # Ensure step_data is a dict, otherwise skip or use defaults carefully
                                if not isinstance(step_data, dict):
                                    logger.warning(f"Skipping malformed step data (not a dict) in workflow {workflow.get('id')}: {step_data}")
                                    continue # Skip malformed step data

                                step_title = step_data.get('title', '无标题')
                                step_command = step_data.get('command', '未提供命令')
                                step_desc = step_data.get('description', '无说明')

                                # Handle cases where .get might return None despite a default if key exists with None value
                                step_title = step_title if step_title is not None else '无标题'
                                step_command = step_command if step_command is not None else '未提供命令'
                                step_desc = step_desc if step_desc is not None else '无说明'
                                
                                step_text = (
                                    f"**步骤 {i+1}**: {step_title}\n"
                                    f"命令: `{step_command}`\n"
                                    f"说明: {step_desc}"
                                )
                                step_details_list.append(step_text)
                            
                            if step_details_list: # If we actually generated some step details
                                steps_section_md = "\n\n".join(step_details_list) # Join steps with double newline for separation
                        
                        # If after processing, steps_section_md is still empty (e.g. actual_steps was empty, or all steps were malformed/skipped)
                        if not steps_section_md.strip():
                            steps_section_md = "**提示**: 此工作流目前没有具体的步骤，或步骤信息不完整。"

                        title = workflow.get('title', '分析工作流')
                        workflow_id_for_message = workflow.get('id')
                        title = title if title is not None else '分析工作流' # 确保 title 不是 None
                        
                        final_response_text = f"""我已经为您创建了工作流计划:

**{title}**

以下是计划的步骤:

{steps_section_md}

您可以通过以下两种方式修改此研究方案:

1. **AI辅助修改**: 直接告诉我您希望如何调整计划，例如"请添加数据可视化步骤"或"修改步骤2的命令参数"
2. **手动编辑**: 点击下方Pipeline窗口中的"手动编辑"按钮，自行调整每个步骤

修改完成后，您可以执行任何步骤或整个工作流。
"""
                        # 下面的检查是为了防止整个final_response_text意外为空，之前步骤已处理steps_section_md为空的情况
                        if not final_response_text.strip():
                            logger.warning(f"Constructed workflow creation response was unexpectedly empty/whitespace for conversation {conversation_id}. Workflow ID: {workflow_id_for_message}.")
                            fallback_title = title if title != '分析工作流' else '' # Avoid "分析工作流 分析工作流"
                            final_response_text = f"已成功启动工作流 {fallback_title} 的创建。请在 Pipeline 面板中查看详细信息。"
                            if not workflow_id_for_message and not fallback_title: 
                                final_response_text = "已成功启动工作流创建。请在 Pipeline 面板中查看详细信息。"
                
                except Exception as e:
                    logger.error(f"Error creating workflow: {e}", exc_info=True)
                    error_message = str(e)
                    final_response_text = f"抱歉，创建工作流时出错: {error_message if error_message and error_message.strip() else '发生未知错误，无法显示具体信息。'}"
                    # workflow_id_for_message 保持 None 或其在try块中可能被赋予的值

                # 确保总是有回复文本
                if not final_response_text or not final_response_text.strip():
                    logger.error(f"Final response_text for CREATE intent was empty for conversation {conversation_id}. This indicates a severe issue in response generation.")
                    final_response_text = "我尝试处理您创建工作流的请求，但遇到了意外问题，无法生成响应。请重试。"
                    workflow_id_for_message = None # 出现严重问题时，不传递 workflow_id

                bot_message = self.add_bot_message(
                    conversation_id, 
                    final_response_text, 
                    workflow_id=workflow_id_for_message
                )
            
            elif intent == "MODIFY":
                # 用户想修改现有工作流
                try:
                    # 先获取最近的工作流列表
                    workflows = self.pipeline_service.list_workflows(conversation_id)
                    if not workflows:
                        response_text = "我没有找到任何可以修改的工作流。请先创建一个工作流。"
                        bot_message = self.add_bot_message(conversation_id, response_text)
                    else:
                        # 默认使用最新的工作流
                        current_workflow = self.pipeline_service.get_workflow(workflows[0]['id'])
                        
                        # 创建修改提示
                        modification_prompt = f"""
                        用户请求: "{message_text}"
                        
                        当前工作流:
                        标题: {current_workflow.get('title')}
                        
                        步骤:
                        {chr(10).join([f"步骤 {i+1}: {step.get('title')} - {step.get('command')}" for i, step in enumerate(current_workflow.get('steps', []))])}
                        
                        可用文件:
                        {files_context}
                        
                        分析用户的请求，并解释他们想要对工作流进行哪些修改。
                        如果需要，提供修改后的工作流步骤。
                        """
                        
                        analysis = self.ai_service.generate_response(modification_prompt)
                        
                        # 回复用户建议的修改
                        response_text = f"""关于修改工作流的建议:

{analysis}

您可以在Pipeline窗口中直接编辑工作流，或者告诉我您具体想要如何修改。
"""
                        
                        bot_message = self.add_bot_message(
                            conversation_id, 
                            response_text, 
                            workflow_id=current_workflow.get('id')
                        )
                
                except Exception as e:
                    logger.error(f"Error modifying workflow: {e}")
                    response_text = f"抱歉，处理工作流修改请求时出错: {str(e)}"
                    bot_message = self.add_bot_message(conversation_id, response_text)
            
            elif intent == "EXECUTE":
                # 用户想执行工作流或步骤
                try:
                    # 获取最近的工作流
                    workflows = self.pipeline_service.list_workflows(conversation_id)
                    if not workflows:
                        response_text = "我没有找到任何可以执行的工作流。请先创建一个工作流。"
                        bot_message = self.add_bot_message(conversation_id, response_text)
                    else:
                        current_workflow = self.pipeline_service.get_workflow(workflows[0]['id'])
                        
                        # 分析用户想执行哪个步骤
                        execution_prompt = f"""
                        用户请求: "{message_text}"
                        
                        当前工作流:
                        标题: {current_workflow.get('title')}
                        
                        步骤:
                        {chr(10).join([f"步骤 {i+1} ({step.get('id')}): {step.get('title')} - {step.get('command')}" for i, step in enumerate(current_workflow.get('steps', []))])}
                        
                        用户想要执行哪个步骤? 请提供步骤ID或步骤编号(如step1)。如果用户想要执行全部步骤，请回答"ALL"。
                        只回答步骤ID或"ALL"，不要其他解释。
                        """
                        
                        step_to_execute = self.ai_service.generate_response(execution_prompt).strip()
                        
                        if step_to_execute.upper() == "ALL":
                            # 依次执行所有步骤
                            executed_steps = []
                            failed_steps = []
                            
                            for step in current_workflow.get('steps', []):
                                try:
                                    executed_step = self.pipeline_service.execute_step(
                                        current_workflow['id'],
                                        step['id'],
                                        conversation_id
                                    )
                                    if executed_step.get('status') == 'completed':
                                        executed_steps.append(executed_step)
                                    else:
                                        failed_steps.append(executed_step)
                                        # 如果步骤失败，停止执行后续步骤
                                        break
                                except Exception as step_error:
                                    logger.error(f"Error executing step {step['id']}: {step_error}")
                                    failed_steps.append({'id': step['id'], 'error': str(step_error), 'title': step.get('title', step['id'])})
                                    break
                            
                            # 构建回复
                            if failed_steps:
                                failed_step = failed_steps[0]
                                response_text = f"""执行工作流时在步骤 "{failed_step.get('title', failed_step['id'])}" 遇到错误:

错误信息: {failed_step.get('error', '未知错误')}

已成功执行 {len(executed_steps)} 个步骤，1个步骤失败。请检查错误信息并修改工作流。
"""
                            else:
                                response_text = f"""已成功执行全部 {len(executed_steps)} 个工作流步骤。

您可以在Pipeline窗口中查看每个步骤的详细执行结果。
"""
                        else:
                            # 执行特定步骤
                            step_ids = [step['id'] for step in current_workflow.get('steps', [])]
                            step_id = None
                            # 允许用户输入步骤ID或者步骤编号(1,2,3等)
                            if step_to_execute in step_ids:
                                step_id = step_to_execute
                            else:
                                # 尝试解析步骤编号
                                try:
                                    # 去除"步骤"字样和其他非数字字符
                                    step_num_str = ''.join(c for c in step_to_execute if c.isdigit())
                                    if step_num_str:
                                        step_num = int(step_num_str)
                                        if step_num > 0 and step_num <= len(step_ids):
                                            step_id = step_ids[step_num - 1]
                                except ValueError:
                                    pass #无法解析数字，保持 step_id 为 None
                            
                            if not step_id and step_ids: # 如果没有匹配到或者解析失败，默认第一个
                                step_id = step_ids[0]
                            elif not step_ids:
                                response_text = "工作流中没有可执行的步骤。"
                                bot_message = self.add_bot_message(conversation_id, response_text)
                                # Early exit if no steps
                                return {'user_message': user_message, 'ai_message': bot_message}

                            try:
                                executed_step = self.pipeline_service.execute_step(
                                    current_workflow['id'],
                                    step_id,
                                    conversation_id
                                )
                                
                                # 找到步骤的标题
                                step_title = next((step['title'] for step in current_workflow.get('steps', []) if step['id'] == step_id), step_id)
                                
                                if executed_step.get('status') == 'completed':
                                    response_text = f"""已成功执行步骤 "{step_title}":

输出: 
```
{executed_step.get('output', '无输出')}
```

您可以在Pipeline窗口中查看详细执行结果。
"""
                                else:
                                    response_text = f"""执行步骤 "{step_title}" 失败:

错误信息: {executed_step.get('error', '未知错误')}

输出: 
```
{executed_step.get('output', '无输出')}
```

请检查错误信息并修改工作流。
"""
                            except Exception as step_error:
                                logger.error(f"Error executing step {step_id}: {step_error}")
                                response_text = f"执行步骤失败: {str(step_error)}"
                        
                        # 添加消息，附加工作流ID以便前端可以刷新状态
                        bot_message = self.add_bot_message(
                            conversation_id, 
                            response_text, 
                            workflow_id=current_workflow.get('id')
                        )
                
                except Exception as e:
                    logger.error(f"Error in workflow execution: {e}")
                    response_text = f"抱歉，执行工作流时出错: {str(e)}"
                    bot_message = self.add_bot_message(conversation_id, response_text)
            
            else:  # QUESTION or unknown intent
                # 处理一般问题
                question_prompt = f"""
                用户在Agent模式下问了一个问题: "{message_text}"
                
                工作目录中的文件:
                {files_context}
                
                请提供一个有关生物信息学领域的专业回复。如果问题与文件管理或工作流相关，可提供相关建议。
                """
                response_text = self.ai_service.generate_response(question_prompt)
                if not response_text:
                    logger.warning(f"AI service returned empty response for agent question in conversation {conversation_id}")
                    response_text = "The AI agent didn't provide a specific plan or answer. Could you try rephrasing your request or providing more details?"
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
