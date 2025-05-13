import os
import uuid
import json
import random
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import shutil

# 导入配置
try:
    from dotenv import load_dotenv
    load_dotenv()  # 加载.env文件中的环境变量
except ImportError:
    pass  # dotenv不可用，使用默认环境变量

# 导入应用配置
from config import (
    USE_FALLBACK_ONLY, 
    DEBUG, 
    OPENAI_API_KEY, 
    OPENAI_API_BASE, 
    OPENAI_MODEL_NAME,
    API_TIMEOUT
)

# 添加Langchain相关导入
LANGCHAIN_AVAILABLE = False # This is an initial declaration, its value is updated below.
if not USE_FALLBACK_ONLY:
    try:
        # from langchain_community.llms import OpenAI  # 旧的导入
        from langchain_openai import ChatOpenAI         # 新的导入，使用Chat模型接口
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.runnables import RunnablePassthrough
        LANGCHAIN_AVAILABLE = True
    except ImportError as e:
        # More specific logging if imports fail.
        logging.warning(f"Langchain modules could not be imported: {e}. Langchain features will be unavailable.")
        pass  # Langchain不可用

import logging

# 设置日志
logging.basicConfig(level=logging.INFO if DEBUG else logging.WARNING)
logger = logging.getLogger(__name__)

# 记录配置状态
if USE_FALLBACK_ONLY:
    logger.warning("AI processing is disabled via USE_FALLBACK_ONLY=True. No AI responses will be generated.")
elif LANGCHAIN_AVAILABLE:
    logger.info("Langchain is available. LLM will be used for generating responses.")
else:
    logger.warning("Langchain is unavailable. AI responses cannot be generated.")

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 数据存储路径
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CONVERSATIONS_DIR = os.path.join(DATA_DIR, 'conversations')
FILES_DIR = os.path.join(DATA_DIR, 'files')

# 确保数据目录存在
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)

# 获取对话专属文件目录
def get_conversation_files_dir(conversation_id):
    conversation_files_dir = os.path.join(FILES_DIR, conversation_id)
    os.makedirs(conversation_files_dir, exist_ok=True)
    return conversation_files_dir

# 获取对话历史记录
def get_conversation_history(conversation_id, max_messages=10):
    file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        conversation = json.load(f)
    
    # 只获取最近的几条消息
    messages = conversation.get('messages', [])[-max_messages:]
    
    # 格式化为简单的对话历史
    history = []
    for msg in messages:
        if msg.get('isWelcome'):
            continue
        history.append({
            'role': 'assistant' if msg.get('sender') == 'bot' else 'user',
            'content': msg.get('text', '')
        })
    
    return history

# 使用Langchain构建AI助手
def create_langchain_chain():
    try:
        # 确认API密钥是否已设置
        if not OPENAI_API_KEY:
            logger.warning("未设置API密钥(OPENAI_API_KEY)，无法使用LLM")
            return None
            
        # API选择器 - 根据API_BASE判断使用哪种提供商
        api_type = "openai"  # 默认为OpenAI
        
        # 检查是否使用Azure OpenAI
        if "azure" in OPENAI_API_BASE.lower():
            api_type = "azure"
            logger.info("检测到Azure OpenAI API")
            # 此处可添加Azure特定配置
            
        # 检查是否使用其他本地API (如LocalAI)
        elif "localhost" in OPENAI_API_BASE.lower() or "127.0.0.1" in OPENAI_API_BASE:
            api_type = "local"
            logger.info("检测到本地API服务")
        
        # 创建基本LLM配置
        llm_config = {
            "temperature": 0.7,
            "openai_api_key": OPENAI_API_KEY,
            "openai_api_base": OPENAI_API_BASE,
            "model_name": OPENAI_MODEL_NAME,
            "request_timeout": API_TIMEOUT
        }
        
        # 根据API类型调整配置
        if api_type == "azure":
            # Azure需要额外的配置参数
            azure_deployment = os.environ.get("AZURE_DEPLOYMENT", OPENAI_MODEL_NAME)
            llm_config.update({
                "deployment_name": azure_deployment,
                "openai_api_type": "azure",
                "openai_api_version": os.environ.get("AZURE_API_VERSION", "2023-05-15")
            })
            logger.info(f"使用Azure部署: {azure_deployment}")
        
        # 创建LLM实例
        # llm = OpenAI(**llm_config)  # 旧的实例化
        llm = ChatOpenAI(**llm_config) # 新的实例化
        
        logger.info(f"已连接 {api_type} API, 模型: {OPENAI_MODEL_NAME}")
        
        # 创建提示模板
        template = """你是AutoPipe智能助手，一个友好、专业的AI助手。
        
历史对话:
{history}

用户问题: {question}

请用中文回答上述问题。你的回答应该友好、专业，并且尽量简洁明了。
如果问题涉及到文件管理，请告诉用户AutoPipe提供了文件管理功能，每个对话都有自己独立的文件空间。
如果问题涉及到编程，尽量提供有帮助的代码示例。
如果你不知道答案，请诚实地说你不知道，而不是编造信息。

你的回答:"""
        
        prompt = PromptTemplate.from_template(template)
        
        # 构建链
        chain = (
            {"history": lambda x: format_history(x["history"]), "question": lambda x: x["question"]}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        return chain
    except Exception as e:
        logger.error(f"创建Langchain链失败: {str(e)}")
        return None

# 格式化对话历史为字符串
def format_history(history):
    if not history:
        return "没有历史对话"
    
    formatted = []
    for msg in history:
        role = "AI" if msg["role"] == "assistant" else "用户"
        formatted.append(f"{role}: {msg['content']}")
    
    return "\n".join(formatted)

# 使用Langchain生成回复
def generate_ai_response_with_langchain(conversation_id, message):
    try:
        # 获取对话历史
        history = get_conversation_history(conversation_id)
        
        # 创建Langchain链
        chain = create_langchain_chain()
        
        if chain:
            # 生成回复
            response = chain.invoke({"history": history, "question": message})
            return response
        else:
            # 如果创建链失败
            logger.warning("Langchain chain creation failed. Cannot generate AI response.")
            return None
    except Exception as e:
        logger.error(f"Langchain failed to generate response: {str(e)}")
        return None

# 主AI回复函数（入口点）
def generate_ai_response(conversation_id, message):
    """使用Langchain生成AI回复。如果配置或环境问题导致无法使用，则返回错误信息。"""
    if USE_FALLBACK_ONLY:
        logger.warning(f"AI processing is disabled (USE_FALLBACK_ONLY=True). Not generating response for: {message[:30]}...")
        return "AI processing is currently disabled by configuration."
    
    if not LANGCHAIN_AVAILABLE:
        logger.warning(f"Langchain is unavailable. Cannot generate AI response for: {message[:30]}...")
        return "Language model components are not available. Please check server setup."
    
    # 尝试使用Langchain
    logger.info(f"Attempting to generate AI response using Langchain for: {message[:30]}...")
    response = generate_ai_response_with_langchain(conversation_id, message)
    
    if response is None:
        # This means generate_ai_response_with_langchain encountered an issue or chain creation failed
        logger.error(f"Failed to get response from Langchain for: {message[:30]}...")
        return "Error generating AI response. The language model may be unavailable or encountered an issue."
        
    return response

# 对话管理API
@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    conversations = []
    if os.path.exists(CONVERSATIONS_DIR):
        for filename in os.listdir(CONVERSATIONS_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(CONVERSATIONS_DIR, filename), 'r', encoding='utf-8') as f:
                    conversation = json.load(f)
                    conversations.append(conversation)
    
    # 按创建时间排序，最新的在前面
    conversations.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(conversations)

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    data = request.json
    title = data.get('title', f'新对话 {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    
    conversation_id = f"conv{uuid.uuid4().hex[:8]}"
    created_at = datetime.now().isoformat()
    
    # 创建一个新对话
    conversation = {
        'id': conversation_id,
        'title': title,
        'created_at': created_at,
        'messages': [
            {
                'id': str(uuid.uuid4()),
                'text': '欢迎使用AutoPipe聊天助手',
                'sender': 'bot',
                'isWelcome': True,
                'timestamp': created_at
            }
        ]
    }
    
    # 保存对话到文件
    with open(os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json'), 'w', encoding='utf-8') as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)
    
    # 为新对话创建专属文件目录
    conversation_files_dir = get_conversation_files_dir(conversation_id)
    
    return jsonify(conversation)

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
    if not os.path.exists(file_path):
        return jsonify({'error': '对话不存在'}), 404
    
    with open(file_path, 'r', encoding='utf-8') as f:
        conversation = json.load(f)
    
    return jsonify(conversation)

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
    if not os.path.exists(file_path):
        return jsonify({'error': '对话不存在'}), 404
    
    os.remove(file_path)
    return jsonify({'success': True, 'message': '对话已删除'})

@app.route('/api/conversations/<conversation_id>/rename', methods=['PUT'])
def rename_conversation(conversation_id):
    data = request.json
    new_title = data.get('title')
    
    if not new_title:
        return jsonify({'error': '标题不能为空'}), 400
    
    file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
    if not os.path.exists(file_path):
        return jsonify({'error': '对话不存在'}), 404
    
    with open(file_path, 'r', encoding='utf-8') as f:
        conversation = json.load(f)
    
    conversation['title'] = new_title
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)
    
    return jsonify(conversation)

# 消息管理API
@app.route('/api/conversations/<conversation_id>/messages', methods=['GET'])
def get_messages(conversation_id):
    file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
    if not os.path.exists(file_path):
        return jsonify({'error': '对话不存在'}), 404
    
    with open(file_path, 'r', encoding='utf-8') as f:
        conversation = json.load(f)
    
    return jsonify(conversation['messages'])

@app.route('/api/conversations/<conversation_id>/messages', methods=['POST'])
def send_message(conversation_id):
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message.strip():
        return jsonify({'error': '消息不能为空'}), 400
    
    file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
    if not os.path.exists(file_path):
        return jsonify({'error': '对话不存在'}), 404
    
    with open(file_path, 'r', encoding='utf-8') as f:
        conversation = json.load(f)
    
    # 添加用户消息
    message_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    user_message_obj = {
        'id': message_id,
        'text': user_message,
        'sender': 'user',
        'timestamp': timestamp
    }
    
    conversation['messages'].append(user_message_obj)
    
    # 生成AI回复
    ai_response = generate_ai_response(conversation_id, user_message)
    
    ai_message_id = str(uuid.uuid4())
    ai_message_obj = {
        'id': ai_message_id,
        'text': ai_response,
        'sender': 'bot',
        'timestamp': datetime.now().isoformat()
    }
    
    conversation['messages'].append(ai_message_obj)
    
    # 保存更新后的对话
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)
    
    return jsonify({
        'user_message': user_message_obj,
        'ai_message': ai_message_obj
    })

# 文件管理API
@app.route('/api/files', methods=['GET'])
def list_files():
    conversation_id = request.args.get('conversation_id')
    if not conversation_id:
        return jsonify({'error': '缺少对话ID参数'}), 400
    
    conversation_files_dir = get_conversation_files_dir(conversation_id)
    files = []
    
    def traverse_directory(directory, parent_path=""):
        items = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            relative_path = os.path.join(parent_path, item)
            
            if os.path.isdir(item_path):
                # 处理文件夹
                folder = {
                    'id': str(uuid.uuid4().hex[:8]),
                    'name': item,
                    'type': 'folder',
                    'path': relative_path,
                    'lastModified': datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat(),
                    'children': traverse_directory(item_path, relative_path)
                }
                items.append(folder)
            else:
                # 处理文件
                _, ext = os.path.splitext(item)
                file_type = ext[1:] if ext else 'unknown'
                
                file_info = {
                    'id': str(uuid.uuid4().hex[:8]),
                    'name': item,
                    'type': file_type,
                    'path': relative_path,
                    'size': os.path.getsize(item_path),
                    'lastModified': datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat()
                }
                items.append(file_info)
        
        return items
    
    if os.path.exists(conversation_files_dir):
        files = traverse_directory(conversation_files_dir)
    
    return jsonify(files)

@app.route('/api/files/search', methods=['GET'])
def search_files():
    query = request.args.get('query', '').lower()
    conversation_id = request.args.get('conversation_id')
    
    if not query:
        return jsonify([])
    
    if not conversation_id:
        return jsonify({'error': '缺少对话ID参数'}), 400
    
    conversation_files_dir = get_conversation_files_dir(conversation_id)
    results = []
    
    def search_in_directory(directory, parent_path=""):
        items = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            relative_path = os.path.join(parent_path, item)
            
            # 检查名称是否匹配查询
            if query in item.lower():
                if os.path.isdir(item_path):
                    folder = {
                        'id': str(uuid.uuid4().hex[:8]),
                        'name': item,
                        'type': 'folder',
                        'path': relative_path,
                        'lastModified': datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat()
                    }
                    items.append(folder)
                else:
                    _, ext = os.path.splitext(item)
                    file_type = ext[1:] if ext else 'unknown'
                    
                    file_info = {
                        'id': str(uuid.uuid4().hex[:8]),
                        'name': item,
                        'type': file_type,
                        'path': relative_path,
                        'size': os.path.getsize(item_path),
                        'lastModified': datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat()
                    }
                    items.append(file_info)
            
            # 递归搜索子目录
            if os.path.isdir(item_path):
                child_results = search_in_directory(item_path, relative_path)
                items.extend(child_results)
        
        return items
    
    if os.path.exists(conversation_files_dir):
        results = search_in_directory(conversation_files_dir)
    
    return jsonify(results)

@app.route('/api/files', methods=['POST'])
def create_file():
    data = request.json
    file_name = data.get('name', '')
    file_content = data.get('content', '')
    file_path = data.get('path', '')
    conversation_id = data.get('conversation_id')
    
    if not file_name:
        return jsonify({'error': '文件名不能为空'}), 400
    
    if not conversation_id:
        return jsonify({'error': '缺少对话ID参数'}), 400
    
    conversation_files_dir = get_conversation_files_dir(conversation_id)
    full_dir_path = conversation_files_dir
    
    if file_path:
        full_dir_path = os.path.join(conversation_files_dir, file_path)
        os.makedirs(full_dir_path, exist_ok=True)
    
    full_file_path = os.path.join(full_dir_path, file_name)
    
    # 检查文件是否已存在
    if os.path.exists(full_file_path):
        return jsonify({'error': '文件已存在'}), 409
    
    with open(full_file_path, 'w', encoding='utf-8') as f:
        f.write(file_content)
    
    _, ext = os.path.splitext(file_name)
    file_type = ext[1:] if ext else 'unknown'
    
    file_info = {
        'id': str(uuid.uuid4().hex[:8]),
        'name': file_name,
        'type': file_type,
        'path': os.path.join(file_path, file_name) if file_path else file_name,
        'size': os.path.getsize(full_file_path),
        'lastModified': datetime.fromtimestamp(os.path.getmtime(full_file_path)).isoformat()
    }
    
    return jsonify(file_info)

@app.route('/api/files/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名不能为空'}), 400
    
    file_path = request.form.get('path', '')
    conversation_id = request.form.get('conversation_id')
    
    if not conversation_id:
        return jsonify({'error': '缺少对话ID参数'}), 400
    
    conversation_files_dir = get_conversation_files_dir(conversation_id)
    full_dir_path = conversation_files_dir
    
    if file_path:
        full_dir_path = os.path.join(conversation_files_dir, file_path)
        os.makedirs(full_dir_path, exist_ok=True)
    
    full_file_path = os.path.join(full_dir_path, file.filename)
    
    # 检查文件是否已存在
    if os.path.exists(full_file_path):
        return jsonify({'error': '文件已存在'}), 409
    
    file.save(full_file_path)
    
    _, ext = os.path.splitext(file.filename)
    file_type = ext[1:] if ext else 'unknown'
    
    file_info = {
        'id': str(uuid.uuid4().hex[:8]),
        'name': file.filename,
        'type': file_type,
        'path': os.path.join(file_path, file.filename) if file_path else file.filename,
        'size': os.path.getsize(full_file_path),
        'lastModified': datetime.fromtimestamp(os.path.getmtime(full_file_path)).isoformat()
    }
    
    return jsonify(file_info)

@app.route('/api/files/<path:file_path>', methods=['GET'])
def get_file_content(file_path):
    conversation_id = request.args.get('conversation_id')
    
    if not conversation_id:
        return jsonify({'error': '缺少对话ID参数'}), 400
    
    conversation_files_dir = get_conversation_files_dir(conversation_id)
    full_path = os.path.join(conversation_files_dir, file_path)
    
    if not os.path.exists(full_path):
        return jsonify({'error': '文件不存在'}), 404
    
    if os.path.isdir(full_path):
        return jsonify({'error': '不能获取文件夹内容'}), 400
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'content': content,
            'path': file_path,
            'name': os.path.basename(file_path)
        })
    except UnicodeDecodeError:
        # 如果不是文本文件，返回错误
        return jsonify({'error': '不支持的文件类型'}), 415

@app.route('/api/files/<path:file_path>', methods=['PUT'])
def update_file(file_path):
    data = request.json
    content = data.get('content', '')
    conversation_id = data.get('conversation_id')
    
    if not conversation_id:
        return jsonify({'error': '缺少对话ID参数'}), 400
    
    conversation_files_dir = get_conversation_files_dir(conversation_id)
    full_path = os.path.join(conversation_files_dir, file_path)
    
    if not os.path.exists(full_path):
        return jsonify({'error': '文件不存在'}), 404
    
    if os.path.isdir(full_path):
        return jsonify({'error': '不能更新文件夹'}), 400
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return jsonify({
        'success': True,
        'message': '文件已更新',
        'path': file_path,
        'lastModified': datetime.fromtimestamp(os.path.getmtime(full_path)).isoformat()
    })

@app.route('/api/files/<path:file_path>', methods=['DELETE'])
def delete_file(file_path):
    conversation_id = request.args.get('conversation_id')
    
    if not conversation_id:
        return jsonify({'error': '缺少对话ID参数'}), 400
    
    conversation_files_dir = get_conversation_files_dir(conversation_id)
    full_path = os.path.join(conversation_files_dir, file_path)
    
    if not os.path.exists(full_path):
        return jsonify({'error': '文件不存在'}), 404
    
    if os.path.isdir(full_path):
        shutil.rmtree(full_path)
        return jsonify({'success': True, 'message': '文件夹已删除'})
    else:
        os.remove(full_path)
        return jsonify({'success': True, 'message': '文件已删除'})

@app.route('/api/files/mkdir', methods=['POST'])
def create_directory():
    data = request.json
    folder_name = data.get('name', '')
    folder_path = data.get('path', '')
    conversation_id = data.get('conversation_id')
    
    if not folder_name:
        return jsonify({'error': '文件夹名不能为空'}), 400
    
    if not conversation_id:
        return jsonify({'error': '缺少对话ID参数'}), 400
    
    conversation_files_dir = get_conversation_files_dir(conversation_id)
    full_parent_path = conversation_files_dir
    
    if folder_path:
        full_parent_path = os.path.join(conversation_files_dir, folder_path)
        if not os.path.exists(full_parent_path):
            return jsonify({'error': '父文件夹不存在'}), 404
    
    full_folder_path = os.path.join(full_parent_path, folder_name)
    
    # 检查文件夹是否已存在
    if os.path.exists(full_folder_path):
        return jsonify({'error': '文件夹已存在'}), 409
    
    os.makedirs(full_folder_path)
    
    folder_info = {
        'id': str(uuid.uuid4().hex[:8]),
        'name': folder_name,
        'type': 'folder',
        'path': os.path.join(folder_path, folder_name) if folder_path else folder_name,
        'lastModified': datetime.fromtimestamp(os.path.getmtime(full_folder_path)).isoformat(),
        'children': []
    }
    
    return jsonify(folder_info)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
