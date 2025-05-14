import os
import subprocess
import uuid
import logging
import threading
import time
import json
import shlex
import signal
import fcntl
from typing import Dict, List, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, 'data')
FILES_DIR = os.path.join(DATA_DIR, 'files')
TERMINAL_LOGS_DIR = os.path.join(DATA_DIR, 'terminal_logs')

# 确保所有必要目录存在
for directory in [DATA_DIR, FILES_DIR, TERMINAL_LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# ANSI颜色代码
ANSI_COLORS = {
    'BLACK': '\033[30m',
    'RED': '\033[31m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'BLUE': '\033[34m',
    'MAGENTA': '\033[35m',
    'CYAN': '\033[36m',
    'WHITE': '\033[37m',
    'RESET': '\033[0m',
    'BOLD': '\033[1m'
}

class TerminalService:
    """服务用于执行终端命令并管理会话"""
    
    def __init__(self):
        self.sessions = {}  # 存储活跃终端会话
        self.active_processes = {}  # 存储活跃进程
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self._cleanup_thread.start()
    
    def create_session(self, conversation_id: str) -> Dict:
        """创建一个新的终端会话"""
        session_id = f"term-{uuid.uuid4().hex[:8]}"
        work_dir = self.get_conversation_files_dir(conversation_id)
        
        # 确保工作目录存在
        os.makedirs(work_dir, exist_ok=True)
        
        session = {
            'id': session_id,
            'conversation_id': conversation_id,
            'working_directory': work_dir,
            'created_at': time.time(),
            'last_active': time.time(),
            'commands': [],
            'environment': {
                'PATH': os.environ.get('PATH', ''),
                'TERM': 'xterm-256color',  # 支持256色
                'COLORTERM': 'truecolor',  # 支持真彩色
                'LANG': os.environ.get('LANG', 'en_US.UTF-8'),
                'HOME': os.environ.get('HOME', ''),
                'USER': os.environ.get('USER', '')
            }
        }
        
        self.sessions[session_id] = session
        
        # 添加欢迎消息和帮助提示
        welcome_message = {
            'id': f"cmd-{uuid.uuid4().hex[:8]}",
            'command': 'welcome',
            'start_time': time.time(),
            'status': 'completed',
            'output': f"{ANSI_COLORS['GREEN']}欢迎使用终端！{ANSI_COLORS['RESET']}\n"
                      f"当前工作目录: {ANSI_COLORS['BLUE']}{work_dir}{ANSI_COLORS['RESET']}\n"
                      f"提示: 使用 {ANSI_COLORS['YELLOW']}help{ANSI_COLORS['RESET']} 命令查看可用命令列表\n",
            'end_time': time.time()
        }
        session['commands'].append(welcome_message)
        
        return session
    
    def execute_command(self, session_id: str, command: str) -> Dict:
        """在指定会话中执行命令"""
        if session_id not in self.sessions:
            raise ValueError(f"终端会话 {session_id} 不存在")
        
        session = self.sessions[session_id]
        work_dir = session['working_directory']
        
        # 更新会话活跃时间
        session['last_active'] = time.time()
        
        # 创建日志文件
        log_file_path = os.path.join(TERMINAL_LOGS_DIR, f"{session_id}_{len(session['commands'])}.log")
        
        command_entry = {
            'id': f"cmd-{uuid.uuid4().hex[:8]}",
            'command': command,
            'start_time': time.time(),
            'status': 'running',
            'output': ''
        }
        
        # 添加到会话的命令历史
        session['commands'].append(command_entry)
        
        # 检查内部命令
        try:
            # 处理特殊内部命令
            if command.strip() == 'help':
                # 帮助命令
                command_entry['output'] = self._generate_help_text()
                command_entry['status'] = 'completed'
                command_entry['end_time'] = time.time()
                return command_entry
            
            elif command.strip() == 'clear':
                # 清屏命令 - 返回特殊标记让前端处理
                command_entry['output'] = "CLEAR_TERMINAL"
                command_entry['status'] = 'completed'
                command_entry['end_time'] = time.time()
                return command_entry
            
            elif command.strip().startswith('cd '):
                # 切换目录命令
                target_dir = command.strip()[3:].strip()
                
                # 处理相对路径
                if not os.path.isabs(target_dir):
                    target_dir = os.path.join(work_dir, target_dir)
                
                # 处理家目录符号 ~
                if target_dir.startswith('~'):
                    target_dir = os.path.expanduser(target_dir)
                
                # 验证目录存在
                if os.path.isdir(target_dir):
                    session['working_directory'] = target_dir
                    command_entry['output'] = f"{ANSI_COLORS['GREEN']}已切换到目录: {ANSI_COLORS['BLUE']}{target_dir}{ANSI_COLORS['RESET']}"
                    command_entry['status'] = 'completed'
                    command_entry['end_time'] = time.time()
                else:
                    command_entry['output'] = f"{ANSI_COLORS['RED']}错误: 目录 '{target_dir}' 不存在{ANSI_COLORS['RESET']}"
                    command_entry['status'] = 'failed'
                    command_entry['end_time'] = time.time()
                return command_entry
            
            elif command.strip() == 'pwd':
                # 显示当前工作目录
                command_entry['output'] = work_dir
                command_entry['status'] = 'completed'
                command_entry['end_time'] = time.time()
                return command_entry
            
            # 执行其他命令
            with open(log_file_path, 'w') as log_file:
                try:
                    # 设置环境变量
                    env = os.environ.copy()
                    for key, value in session['environment'].items():
                        env[key] = value
                    
                    # 使用shell执行命令
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        cwd=work_dir,
                        text=True,
                        bufsize=1,
                        env=env,
                        preexec_fn=os.setsid  # 创建新的进程组以便能够终止整个进程树
                    )
                    
                    # 存储活跃进程
                    process_id = f"proc-{uuid.uuid4().hex[:8]}"
                    self.active_processes[process_id] = {
                        'process': process,
                        'command_id': command_entry['id'],
                        'session_id': session_id,
                        'start_time': time.time(),
                        'process_group': os.getpgid(process.pid)
                    }
                    
                    # 设置非阻塞模式
                    fd = process.stdout.fileno()
                    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                    
                    # 设置超时时间
                    max_execution_time = 60  # 60秒超时
                    start_time = time.time()
                    
                    output_lines = []
                    
                    # 实时获取命令输出
                    while process.poll() is None:
                        # 检查超时
                        if time.time() - start_time > max_execution_time:
                            logger.info(f"命令执行超时: {command}")
                            try:
                                # 终止整个进程组
                                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                                # 等待一小段时间后再发送强制终止信号
                                time.sleep(0.5)
                                if process.poll() is None:
                                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            except:
                                logger.exception("终止进程失败")
                            break
                        
                        try:
                            # 尝试读取输出
                            chunk = process.stdout.read(4096)
                            if chunk:
                                chunk_str = chunk.decode('utf-8', errors='replace') if isinstance(chunk, bytes) else chunk
                                output_lines.append(chunk_str)
                                log_file.write(chunk_str)
                                log_file.flush()
                                # 更新命令输出以便实时查看
                                command_entry['output'] = ''.join(output_lines)
                            else:
                                time.sleep(0.1)  # 短暂休眠避免CPU占用过高
                        except Exception as e:
                            # 没有新数据可读或其他错误
                            time.sleep(0.1)
                    
                    # 读取剩余输出
                    try:
                        remaining = process.stdout.read()
                        if remaining:
                            remaining_str = remaining.decode('utf-8', errors='replace') if isinstance(remaining, bytes) else remaining
                            output_lines.append(remaining_str)
                            log_file.write(remaining_str)
                            log_file.flush()
                    except:
                        pass
                    
                    # 清理进程记录
                    if process_id in self.active_processes:
                        del self.active_processes[process_id]
                    
                    # 等待进程完成
                    return_code = process.returncode if process.returncode is not None else -1
                    
                    command_entry['output'] = ''.join(output_lines)
                    command_entry['end_time'] = time.time()
                    
                    if time.time() - start_time > max_execution_time:
                        command_entry['status'] = 'timeout'
                        command_entry['output'] += f"\n{ANSI_COLORS['RED']}命令执行超时 ({max_execution_time}秒){ANSI_COLORS['RESET']}"
                    elif return_code == 0:
                        command_entry['status'] = 'completed'
                    else:
                        command_entry['status'] = 'failed'
                        if not command_entry['output']:
                            command_entry['output'] = f"{ANSI_COLORS['RED']}命令执行失败，返回代码: {return_code}{ANSI_COLORS['RESET']}"
                    
                except Exception as e:
                    logger.exception(f"执行命令时出错: {command}")
                    command_entry['status'] = 'failed'
                    command_entry['output'] = f"{ANSI_COLORS['RED']}执行错误: {str(e)}{ANSI_COLORS['RESET']}"
                    command_entry['end_time'] = time.time()
        
        except Exception as e:
            logger.exception(f"处理命令时出错: {command}")
            command_entry['status'] = 'failed'
            command_entry['output'] = f"{ANSI_COLORS['RED']}执行错误: {str(e)}{ANSI_COLORS['RESET']}"
            command_entry['end_time'] = time.time()
        
        return command_entry
    
    def _generate_help_text(self) -> str:
        """生成帮助文本"""
        help_text = f"{ANSI_COLORS['GREEN']}可用命令:{ANSI_COLORS['RESET']}\n"
        help_text += f"  {ANSI_COLORS['YELLOW']}cd <目录>{ANSI_COLORS['RESET']} - 切换当前工作目录\n"
        help_text += f"  {ANSI_COLORS['YELLOW']}pwd{ANSI_COLORS['RESET']} - 显示当前工作目录\n"
        help_text += f"  {ANSI_COLORS['YELLOW']}ls{ANSI_COLORS['RESET']} - 列出当前目录文件\n"
        help_text += f"  {ANSI_COLORS['YELLOW']}cat <文件>{ANSI_COLORS['RESET']} - 显示文件内容\n"
        help_text += f"  {ANSI_COLORS['YELLOW']}mkdir <目录>{ANSI_COLORS['RESET']} - 创建新目录\n"
        help_text += f"  {ANSI_COLORS['YELLOW']}rm <文件>{ANSI_COLORS['RESET']} - 删除文件\n"
        help_text += f"  {ANSI_COLORS['YELLOW']}clear{ANSI_COLORS['RESET']} - 清屏\n"
        help_text += f"  {ANSI_COLORS['YELLOW']}help{ANSI_COLORS['RESET']} - 显示此帮助信息\n"
        
        help_text += f"\n{ANSI_COLORS['GREEN']}键盘快捷键:{ANSI_COLORS['RESET']}\n"
        help_text += f"  {ANSI_COLORS['YELLOW']}Enter{ANSI_COLORS['RESET']} - 执行命令\n"
        help_text += f"  {ANSI_COLORS['YELLOW']}点击命令{ANSI_COLORS['RESET']} - 复制命令到输入框\n"
        
        return help_text
    
    def get_session(self, session_id: str) -> Dict:
        """获取会话信息"""
        if session_id not in self.sessions:
            raise ValueError(f"终端会话 {session_id} 不存在")
        self.sessions[session_id]['last_active'] = time.time()  # 更新活跃时间
        return self.sessions[session_id]
    
    def get_conversation_sessions(self, conversation_id: str) -> List[Dict]:
        """获取会话列表"""
        result = [
            session for session in self.sessions.values() 
            if session['conversation_id'] == conversation_id
        ]
        # 按最新活跃时间排序
        result.sort(key=lambda s: s['last_active'], reverse=True)
        return result
    
    def terminate_session(self, session_id: str) -> bool:
        """终止会话"""
        if session_id in self.sessions:
            # 终止会话中的所有活跃进程
            for pid, proc_info in list(self.active_processes.items()):
                if proc_info['session_id'] == session_id:
                    try:
                        # 尝试终止整个进程组
                        os.killpg(proc_info['process_group'], signal.SIGTERM)
                        # 等待一小段时间后再发送强制终止信号
                        time.sleep(0.5)
                        os.killpg(proc_info['process_group'], signal.SIGKILL)
                    except:
                        # 如果进程组终止失败，尝试直接终止进程
                        try:
                            proc_info['process'].kill()
                        except:
                            pass
                    del self.active_processes[pid]
            
            del self.sessions[session_id]
            return True
        return False
    
    def get_conversation_files_dir(self, conversation_id: str) -> str:
        """获取会话文件目录"""
        conversation_files_dir = os.path.join(FILES_DIR, conversation_id)
        os.makedirs(conversation_files_dir, exist_ok=True)
        return conversation_files_dir
    
    def _cleanup_expired_sessions(self):
        """清理过期的会话 (1小时无活动)"""
        while True:
            try:
                time.sleep(300)  # 每5分钟检查一次
                current_time = time.time()
                expired_sessions = []
                
                for session_id, session in list(self.sessions.items()):
                    if current_time - session['last_active'] > 3600:  # 1小时超时
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    logger.info(f"清理过期会话: {session_id}")
                    self.terminate_session(session_id)
            except Exception as e:
                logger.error(f"清理过期会话时出错: {e}") 