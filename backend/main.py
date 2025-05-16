import os
import uuid
import json
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
from config import DEBUG

# 服务导入
from services.chat_service import AIService
from services.conversation_service import ConversationService
from services.pipeline_service import PipelineService
# LLM相关导入和配置已移除

# 设置日志
logging.basicConfig(level=logging.INFO if DEBUG else logging.WARNING)
logger = logging.getLogger(__name__)

# LLM相关配置状态日志已移除

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化服务
ai_service = AIService()
pipeline_service = PipelineService(llm_service=ai_service)
conversation_service = ConversationService(ai_service=ai_service, pipeline_service=pipeline_service)


# 数据存储路径 (这部分可以保留，因为 ConversationService 内部也使用了类似的路径逻辑，但为了解耦，未来可以考虑统一由 ConversationService 管理)
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CONVERSATIONS_DIR = os.path.join(DATA_DIR, 'conversations')
FILES_DIR = os.path.join(DATA_DIR, 'files') # 文件相关的目录，ConversationService 不直接管理

# 确保数据目录存在 (部分目录创建可能已在 Service 中处理，但保留这里的 files 目录创建无害)
os.makedirs(CONVERSATIONS_DIR, exist_ok=True) # ConversationService 会创建
os.makedirs(FILES_DIR, exist_ok=True) # 文件相关的目录

# 获取对话专属文件目录 (这个函数主要用于文件管理API，ConversationService 不直接使用)
def get_conversation_files_dir(conversation_id):
    conversation_files_dir = os.path.join(FILES_DIR, conversation_id)
    os.makedirs(conversation_files_dir, exist_ok=True)
    return conversation_files_dir

# 获取对话历史记录 (此函数与LLM无关，保留) -> ConversationService 中已有类似功能，可以移除
# def get_conversation_history(conversation_id, max_messages=10):
#     file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
#     if not os.path.exists(file_path):
#         return []
#     
#     with open(file_path, 'r', encoding='utf-8') as f:
#         conversation = json.load(f)
#     
#     messages = conversation.get('messages', [])[-max_messages:]
#     history = []
#     for msg in messages:
#         if msg.get('isWelcome'):
#             continue
#         history.append({
#             'role': 'assistant' if msg.get('sender') == 'bot' else 'user',
#             'content': msg.get('text', '')
#         })
#     return history

# create_langchain_chain, format_history, generate_ai_response_with_langchain 已被移除

# 主AI回复函数（入口点）- 现在返回固定值 -> 此函数将被 ConversationService.send_message 替代，可以移除
# def generate_ai_response(conversation_id, message):
#     logger.info(f"generate_ai_response called for: {message[:30]}... Returning fixed response.")
#     return "Hello" # 直接返回 "Hello"

# 对话管理API
@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    # conversations = []
    # if os.path.exists(CONVERSATIONS_DIR):
    #     for filename in os.listdir(CONVERSATIONS_DIR):
    #         if filename.endswith('.json'):
    #             with open(os.path.join(CONVERSATIONS_DIR, filename), 'r', encoding='utf-8') as f:
    #                 conversation = json.load(f)
    #                 conversations.append(conversation)
    # 
    # # 按创建时间排序，最新的在前面
    # conversations.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    # return jsonify(conversations)
    try:
        conversations = conversation_service.get_all_conversations()
    return jsonify(conversations)
    except Exception as e:
        logger.error(f"Error in get_conversations: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    data = request.json
    title = data.get('title') # ConversationService 会处理默认标题
    mode = data.get('mode', 'chat') # 从请求中获取 mode
    # conversation_id = f"conv{uuid.uuid4().hex[:8]}"
    # created_at = datetime.now().isoformat()
    # 
    # # 创建一个新对话
    # conversation = {
    #     'id': conversation_id,
    #     'title': title,
    #     'created_at': created_at,
    #     'messages': [
    #         {
    #             'id': str(uuid.uuid4()),
    #             'text': '欢迎使用AutoPipe聊天助手',
    #             'sender': 'bot',
    #             'isWelcome': True,
    #             'timestamp': created_at
    #         }
    #     ]
    # }
    # 
    # # 保存对话到文件
    # with open(os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json'), 'w', encoding='utf-8') as f:
    #     json.dump(conversation, f, ensure_ascii=False, indent=2)
    # 
    # # 为新对话创建专属文件目录
    # conversation_files_dir = get_conversation_files_dir(conversation_id) # 文件目录创建与对话核心逻辑分离
    # 
    # return jsonify(conversation)
    try:
        conversation = conversation_service.create_conversation(title=title, mode=mode)
        # 为新对话创建专属文件目录 (这部分是文件管理相关的，保留在API层，与核心对话服务分离)
        get_conversation_files_dir(conversation['id'])
        return jsonify(conversation)
    except Exception as e:
        logger.error(f"Error in create_conversation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    # file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
    # if not os.path.exists(file_path):
    #     return jsonify({'error': '对话不存在'}), 404
    # 
    # with open(file_path, 'r', encoding='utf-8') as f:
    #     conversation = json.load(f)
    # 
    # return jsonify(conversation)
    try:
        conversation = conversation_service.get_conversation(conversation_id)
        return jsonify(conversation)
    except FileNotFoundError:
        return jsonify({'error': '对话不存在'}), 404
    except Exception as e:
        logger.error(f"Error in get_conversation: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    # file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
    # if not os.path.exists(file_path):
    #     return jsonify({'error': '对话不存在'}), 404
    # 
    # os.remove(file_path)
    # return jsonify({'success': True, 'message': '对话已删除'})
    try:
        if conversation_service.delete_conversation(conversation_id):
            # 删除关联的文件目录
            conv_files_dir = os.path.join(FILES_DIR, conversation_id)
            if os.path.exists(conv_files_dir):
                shutil.rmtree(conv_files_dir)
            return jsonify({'success': True, 'message': '对话已删除'})
        else:
        return jsonify({'error': '对话不存在'}), 404
    except Exception as e:
        logger.error(f"Error in delete_conversation: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations/<conversation_id>/rename', methods=['PUT'])
def rename_conversation(conversation_id):
    data = request.json
    new_title = data.get('title')
    
    if not new_title:
        return jsonify({'error': '标题不能为空'}), 400
    
    # file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
    # if not os.path.exists(file_path):
    #     return jsonify({'error': '对话不存在'}), 404
    # 
    # with open(file_path, 'r', encoding='utf-8') as f:
    #     conversation = json.load(f)
    # 
    # conversation['title'] = new_title
    # 
    # with open(file_path, 'w', encoding='utf-8') as f:
    #     json.dump(conversation, f, ensure_ascii=False, indent=2)
    # 
    # return jsonify(conversation)
    try:
        conversation = conversation_service.rename_conversation(conversation_id, new_title)
        return jsonify(conversation)
    except FileNotFoundError:
        return jsonify({'error': '对话不存在'}), 404
    except Exception as e:
        logger.error(f"Error in rename_conversation: {e}")
        return jsonify({"error": str(e)}), 500

# 消息管理API
@app.route('/api/conversations/<conversation_id>/messages', methods=['GET'])
def get_messages(conversation_id):
    # file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
    # if not os.path.exists(file_path):
    #     return jsonify({'error': '对话不存在'}), 404
    # 
    # with open(file_path, 'r', encoding='utf-8') as f:
    #     conversation = json.load(f)
    # 
    # return jsonify(conversation['messages'])
    try:
        messages = conversation_service.get_messages(conversation_id)
        return jsonify(messages)
    except FileNotFoundError:
        return jsonify({'error': '对话不存在'}), 404
    except Exception as e:
        logger.error(f"Error in get_messages: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations/<conversation_id>/messages', methods=['POST'])
def send_message(conversation_id):
    data = request.json
    user_message_text = data.get('message', '') # Renamed for clarity
    
    if not user_message_text.strip():
        return jsonify({'error': '消息不能为空'}), 400
    
    # file_path = os.path.join(CONVERSATIONS_DIR, f'{conversation_id}.json')
    # if not os.path.exists(file_path):
    #     return jsonify({'error': '对话不存在'}), 404
    # 
    # with open(file_path, 'r', encoding='utf-8') as f:
    #     conversation = json.load(f)
    # 
    # # 添加用户消息
    # message_id = str(uuid.uuid4())
    # timestamp = datetime.now().isoformat()
    # 
    # user_message_obj = {
    #     'id': message_id,
    #     'text': user_message,
    #     'sender': 'user',
    #     'timestamp': timestamp
    # }
    # 
    # conversation['messages'].append(user_message_obj)
    # 
    # # 生成AI回复
    # ai_response = generate_ai_response(conversation_id, user_message)
    # 
    # ai_message_id = str(uuid.uuid4())
    # ai_message_obj = {
    #     'id': ai_message_id,
    #     'text': ai_response,
    #     'sender': 'bot',
    #     'timestamp': datetime.now().isoformat()
    # }
    # 
    # conversation['messages'].append(ai_message_obj)
    # 
    # # 保存更新后的对话
    # with open(file_path, 'w', encoding='utf-8') as f:
    #     json.dump(conversation, f, ensure_ascii=False, indent=2)
    # 
    # return jsonify({
    #     'user_message': user_message_obj,
    #     'ai_message': ai_message_obj
    # })
    try:
        # ConversationService.send_message now handles adding user message,
        # generating AI response, and saving the conversation.
        # It returns a dict with 'user_message' and 'ai_message'
        response_data = conversation_service.send_message(conversation_id, user_message_text)
        return jsonify(response_data)
    except FileNotFoundError:
        return jsonify({'error': '对话不存在'}), 404
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>/mode', methods=['PUT'])
def set_conversation_mode_route(conversation_id):
    data = request.json
    mode = data.get('mode')

    if not mode or mode not in ['chat', 'agent']:
        return jsonify({'error': '无效的模式，必须是 "chat" 或 "agent"'}), 400

    try:
        updated_conversation = conversation_service.set_conversation_mode(conversation_id, mode)
        return jsonify(updated_conversation)
    except FileNotFoundError:
        return jsonify({'error': '对话不存在'}), 404
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Error setting conversation mode: {e}")
        return jsonify({'error': str(e)}), 500

# 文件管理API (这部分保持不变，因为它们与对话服务核心逻辑分离)
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
    app.run(debug=DEBUG, host='0.0.0.0', port=5000)
