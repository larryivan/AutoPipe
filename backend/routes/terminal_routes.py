from flask import Blueprint, request, jsonify
import logging
from services.terminal_service import TerminalService
import time
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建蓝图
terminal_routes = Blueprint('terminal_routes', __name__)

# 初始化服务
terminal_service = TerminalService()

@terminal_routes.route('/terminal/sessions', methods=['POST'])
def create_terminal_session():
    """创建新的终端会话"""
    try:
        data = request.json
        conversation_id = data.get('conversation_id')
        
        if not conversation_id:
            return jsonify({'error': '缺少conversation_id参数'}), 400
        
        session = terminal_service.create_session(conversation_id)
        return jsonify(session)
    except Exception as e:
        logger.error(f"创建终端会话错误: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f"创建终端会话失败: {str(e)}"}), 500

@terminal_routes.route('/terminal/sessions', methods=['GET'])
def get_terminal_sessions():
    """获取会话列表"""
    try:
        conversation_id = request.args.get('conversation_id')
        
        if not conversation_id:
            return jsonify({'error': '缺少conversation_id参数'}), 400
        
        sessions = terminal_service.get_conversation_sessions(conversation_id)
        return jsonify(sessions)
    except Exception as e:
        logger.error(f"获取终端会话错误: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f"获取终端会话失败: {str(e)}"}), 500

@terminal_routes.route('/terminal/sessions/<session_id>', methods=['GET'])
def get_terminal_session(session_id):
    """获取会话详情"""
    try:
        session = terminal_service.get_session(session_id)
        return jsonify(session)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"获取终端会话详情错误: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f"获取终端会话详情失败: {str(e)}"}), 500

@terminal_routes.route('/terminal/sessions/<session_id>/execute', methods=['POST'])
def execute_command(session_id):
    """执行终端命令"""
    try:
        data = request.json
        command = data.get('command')
        
        if not command:
            return jsonify({'error': '缺少command参数'}), 400
        
        result = terminal_service.execute_command(session_id, command)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"执行终端命令错误: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f"执行命令失败: {str(e)}"}), 500

@terminal_routes.route('/terminal/sessions/<session_id>/commands/<command_id>/terminate', methods=['POST'])
def terminate_command(session_id, command_id):
    """终止正在执行的命令"""
    try:
        success = False
        terminated_processes = []
        
        # 查找与命令相关的进程
        for pid, proc_info in list(terminal_service.active_processes.items()):
            if (proc_info['session_id'] == session_id and 
                proc_info['command_id'] == command_id):
                try:
                    # 终止进程组
                    import os
                    import signal
                    os.killpg(proc_info['process_group'], signal.SIGTERM)
                    # 等待一小段时间后再发送强制终止信号
                    time.sleep(0.5)
                    if proc_info['process'].poll() is None:
                        os.killpg(proc_info['process_group'], signal.SIGKILL)
                    
                    terminated_processes.append(pid)
                    success = True
                except Exception as e:
                    logger.error(f"终止命令进程错误: {str(e)}\n{traceback.format_exc()}")
                    # 尝试直接终止进程
                    try:
                        proc_info['process'].kill()
                        terminated_processes.append(pid)
                        success = True
                    except:
                        pass
        
        # 从活跃进程列表中移除已终止的进程
        for pid in terminated_processes:
            if pid in terminal_service.active_processes:
                del terminal_service.active_processes[pid]
        
        # 更新命令状态
        if success:
            session = terminal_service.get_session(session_id)
            for cmd in session['commands']:
                if cmd['id'] == command_id and cmd['status'] == 'running':
                    cmd['status'] = 'terminated'
                    cmd['output'] += "\n命令已被用户终止"
                    cmd['end_time'] = time.time()
        
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"终止命令错误: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f"终止命令失败: {str(e)}"}), 500

@terminal_routes.route('/terminal/sessions/<session_id>', methods=['DELETE'])
def terminate_session(session_id):
    """终止终端会话"""
    try:
        success = terminal_service.terminate_session(session_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': '会话不存在'}), 404
    except Exception as e:
        logger.error(f"终止终端会话错误: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f"终止会话失败: {str(e)}"}), 500 