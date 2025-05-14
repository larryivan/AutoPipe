import os
import shutil
import json
import mimetypes
from typing import Dict, List, Any, Optional
import logging
import uuid
import subprocess
import threading
import time
import zipfile
import io
import signal  # Add signal module for process control

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data directories
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
FILES_DIR = os.path.join(DATA_DIR, 'files')
DOWNLOADS_DIR = os.path.join(DATA_DIR, 'downloads')  # 下载目录

# Ensure directories exist
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)  # 确保下载目录存在

class FileService:
    """Service for managing files and directories"""
    
    def __init__(self):
        """Initialize the file service"""
        self.downloads = {}  # 存储下载任务信息
        self.download_status = {}  # 存储下载状态
        self._download_lock = threading.Lock()  # 线程锁，保护下载状态字典
        
        # 启动下载状态监控线程
        self._monitor_thread = threading.Thread(target=self._monitor_downloads, daemon=True)
        self._monitor_thread.start()
    
    def get_conversation_files_dir(self, conversation_id: str) -> str:
        """Get the directory for conversation files"""
        conversation_files_dir = os.path.join(FILES_DIR, conversation_id)
        os.makedirs(conversation_files_dir, exist_ok=True)
        return conversation_files_dir
    
    def get_conversation_downloads_dir(self, conversation_id: str) -> str:
        """获取会话下载目录"""
        conversation_downloads_dir = os.path.join(DOWNLOADS_DIR, conversation_id)
        os.makedirs(conversation_downloads_dir, exist_ok=True)
        return conversation_downloads_dir
    
    def get_all_files(self, conversation_id: str, path: str = "") -> List[Dict]:
        """Get all files and directories for a conversation"""
        base_dir = self.get_conversation_files_dir(conversation_id)
        
        if path:
            target_dir = os.path.join(base_dir, path)
            if not os.path.exists(target_dir) or not target_dir.startswith(base_dir):
                return []
        else:
            target_dir = base_dir
        
        if not os.path.exists(target_dir):
            return []
            
        result = []
        
        try:
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                relative_path = os.path.relpath(item_path, base_dir)
                
                # Skip hidden files and directories
                if item.startswith('.'):
                    continue
                
                if os.path.isdir(item_path):
                    # Handle directory
                    children = self._get_directory_children(item_path, base_dir)
                    result.append({
                        'id': f"dir-{uuid.uuid4().hex[:8]}",
                        'name': item,
                        'path': relative_path,
                        'type': 'folder',
                        'children': children
                    })
                else:
                    # Handle file
                    file_type = self._get_file_type(item)
                    result.append({
                        'id': f"file-{uuid.uuid4().hex[:8]}",
                        'name': item,
                        'path': relative_path,
                        'type': file_type,
                        'size': os.path.getsize(item_path)
                    })
        except Exception as e:
            logger.error(f"Error getting files: {e}")
            return []
        
        return sorted(result, key=lambda x: (x['type'] != 'folder', x['name']))
    
    def _get_directory_children(self, directory_path: str, base_dir: str, max_depth: int = 1, current_depth: int = 0) -> List[Dict]:
        """Get children of a directory up to a certain depth"""
        if current_depth >= max_depth:
            return []
            
        result = []
        
        try:
            for item in os.listdir(directory_path):
                if item.startswith('.'):
                    continue
                    
                item_path = os.path.join(directory_path, item)
                relative_path = os.path.relpath(item_path, base_dir)
                
                if os.path.isdir(item_path):
                    children = [] if current_depth >= max_depth - 1 else self._get_directory_children(
                        item_path, base_dir, max_depth, current_depth + 1
                    )
                    result.append({
                        'id': f"dir-{uuid.uuid4().hex[:8]}",
                        'name': item,
                        'path': relative_path,
                        'type': 'folder',
                        'children': children
                    })
                else:
                    file_type = self._get_file_type(item)
                    result.append({
                        'id': f"file-{uuid.uuid4().hex[:8]}",
                        'name': item,
                        'path': relative_path,
                        'type': file_type
                    })
        except Exception as e:
            logger.error(f"Error getting directory children: {e}")
        
        return sorted(result, key=lambda x: (x['type'] != 'folder', x['name']))
    
    def _get_file_type(self, filename: str) -> str:
        """Determine file type based on extension"""
        lower_name = filename.lower()
        
        # Bioinformatics file types
        if lower_name.endswith(('.fastq', '.fq', '.fastq.gz', '.fq.gz')):
            return 'fastq'
        elif lower_name.endswith(('.fasta', '.fa', '.fna', '.faa', '.fasta.gz', '.fa.gz')):
            return 'fasta'
        elif lower_name.endswith(('.sam', '.bam', '.cram')):
            return 'alignment'
        elif lower_name.endswith(('.vcf', '.vcf.gz', '.bcf')):
            return 'variant'
        elif lower_name.endswith(('.gtf', '.gff', '.gff3')):
            return 'annotation'
        elif lower_name.endswith(('.bed', '.bedgraph', '.bigwig', '.bw')):
            return 'genomic'
        
        # Programming languages
        elif lower_name.endswith('.py'):
            return 'python'
        elif lower_name.endswith(('.r', '.rmd')):
            return 'r'
        elif lower_name.endswith('.sh'):
            return 'shell'
        elif lower_name.endswith(('.pl', '.pm')):
            return 'perl'
        
        # Documents & Data
        elif lower_name.endswith(('.txt', '.md', '.log')):
            return 'text'
        elif lower_name.endswith(('.csv', '.tsv')):
            return 'tabular'
        elif lower_name.endswith('.json'):
            return 'json'
        elif lower_name.endswith('.xml'):
            return 'xml'
        elif lower_name.endswith('.pdf'):
            return 'pdf'
        
        # Default
        return 'file'
    
    def search_files(self, query: str, conversation_id: str) -> List[Dict]:
        """Search for files by name"""
        all_files = self.get_all_files(conversation_id)
        query = query.lower()
        
        result = []
        self._search_files_recursive(all_files, query, result)
        
        return result
    
    def _search_files_recursive(self, files: List[Dict], query: str, result: List[Dict]) -> None:
        """Recursively search through files and directories"""
        for file in files:
            if query in file['name'].lower():
                result.append(file)
            
            if file['type'] == 'folder' and 'children' in file:
                self._search_files_recursive(file['children'], query, result)
    
    def create_file(self, name: str, content: str, conversation_id: str, path: str = "") -> Dict:
        """Create a new file"""
        base_dir = self.get_conversation_files_dir(conversation_id)
        
        if path:
            target_dir = os.path.join(base_dir, path)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
        else:
            target_dir = base_dir
        
        file_path = os.path.join(target_dir, name)
        
        # Prevent path traversal attacks
        if not os.path.abspath(file_path).startswith(os.path.abspath(base_dir)):
            raise ValueError("Invalid file path")
        
        # Write file content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'id': f"file-{uuid.uuid4().hex[:8]}",
            'name': name,
            'path': os.path.relpath(file_path, base_dir),
            'type': self._get_file_type(name),
            'size': os.path.getsize(file_path)
        }
    
    def create_directory(self, name: str, conversation_id: str, path: str = "") -> Dict:
        """Create a new directory"""
        base_dir = self.get_conversation_files_dir(conversation_id)
        
        if path:
            parent_dir = os.path.join(base_dir, path)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
        else:
            parent_dir = base_dir
        
        dir_path = os.path.join(parent_dir, name)
        
        # Prevent path traversal attacks
        if not os.path.abspath(dir_path).startswith(os.path.abspath(base_dir)):
            raise ValueError("Invalid directory path")
        
        os.makedirs(dir_path, exist_ok=True)
        
        return {
            'id': f"dir-{uuid.uuid4().hex[:8]}",
            'name': name,
            'path': os.path.relpath(dir_path, base_dir),
            'type': 'folder',
            'children': []
        }
    
    def get_file_content(self, file_path: str, conversation_id: str) -> Dict:
        """Get the content of a file"""
        base_dir = self.get_conversation_files_dir(conversation_id)
        full_path = os.path.join(base_dir, file_path)
        
        # Prevent path traversal attacks
        if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
            raise ValueError("Invalid file path")
        
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check if it's a binary file
        mime_type, _ = mimetypes.guess_type(full_path)
        is_binary = mime_type and not mime_type.startswith(('text/', 'application/json'))
        
        if is_binary:
            return {
                'name': os.path.basename(full_path),
                'path': file_path,
                'type': self._get_file_type(full_path),
                'size': os.path.getsize(full_path),
                'content': "[Binary file content not displayed]",
                'is_binary': True
            }
        
        # Read text file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # If UTF-8 fails, try with Latin-1 encoding
            with open(full_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        return {
            'name': os.path.basename(full_path),
            'path': file_path,
            'type': self._get_file_type(full_path),
            'size': os.path.getsize(full_path),
            'content': content,
            'is_binary': False
        }
    
    def update_file_content(self, file_path: str, content: str, conversation_id: str) -> Dict:
        """Update the content of a file"""
        base_dir = self.get_conversation_files_dir(conversation_id)
        full_path = os.path.join(base_dir, file_path)
        
        # Prevent path traversal attacks
        if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
            raise ValueError("Invalid file path")
        
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Write updated content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'name': os.path.basename(full_path),
            'path': file_path,
            'type': self._get_file_type(full_path),
            'size': os.path.getsize(full_path)
        }
    
    def delete_file(self, file_path: str, conversation_id: str) -> bool:
        """Delete a file or directory"""
        base_dir = self.get_conversation_files_dir(conversation_id)
        full_path = os.path.join(base_dir, file_path)
        
        # Prevent path traversal attacks
        if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
            raise ValueError("Invalid file path")
        
        if not os.path.exists(full_path):
            return False
        
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
            
        return True
    
    def rename_file(self, old_path: str, new_name: str, conversation_id: str) -> Dict:
        """重命名文件或目录"""
        base_dir = self.get_conversation_files_dir(conversation_id)
        full_old_path = os.path.join(base_dir, old_path)
        
        # 防止路径遍历攻击
        if not os.path.abspath(full_old_path).startswith(os.path.abspath(base_dir)):
            raise ValueError("无效的文件路径")
        
        if not os.path.exists(full_old_path):
            raise FileNotFoundError(f"文件不存在: {old_path}")
        
        # 获取目录和文件名
        old_dir = os.path.dirname(full_old_path)
        full_new_path = os.path.join(old_dir, new_name)
        
        # 检查目标文件是否已存在
        if os.path.exists(full_new_path):
            raise ValueError(f"已存在同名文件或目录: {new_name}")
        
        # 执行重命名
        os.rename(full_old_path, full_new_path)
        
        # 计算相对路径
        new_path = os.path.join(os.path.dirname(old_path), new_name) if os.path.dirname(old_path) else new_name
        
        # 返回文件信息
        return {
            'id': f"{'dir' if os.path.isdir(full_new_path) else 'file'}-{uuid.uuid4().hex[:8]}",
            'name': new_name,
            'path': new_path,
            'type': 'folder' if os.path.isdir(full_new_path) else self._get_file_type(new_name),
            'size': None if os.path.isdir(full_new_path) else os.path.getsize(full_new_path)
        }
    
    def get_file_for_download(self, file_path: str, conversation_id: str) -> str:
        """获取文件的完整路径用于下载"""
        base_dir = self.get_conversation_files_dir(conversation_id)
        full_path = os.path.join(base_dir, file_path)
        
        # 防止路径遍历攻击
        if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
            raise ValueError("无效的文件路径")
        
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        return full_path
    
    def create_zip_for_files(self, file_paths: List[str], conversation_id: str) -> io.BytesIO:
        """为指定的文件路径列表创建一个临时的ZIP文件流"""
        base_dir = self.get_conversation_files_dir(conversation_id)
        memory_file = io.BytesIO()

        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in file_paths:
                full_path = os.path.join(base_dir, file_path)
                # 安全性检查：确保文件在会话目录内且存在
                if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
                    logger.warning(f"Skipping invalid path for zipping: {file_path}")
                    continue
                if not os.path.exists(full_path):
                    logger.warning(f"Skipping non-existent file for zipping: {file_path}")
                    continue
                
                if os.path.isfile(full_path):
                    # arcname 参数用于指定文件在zip包中的路径，这里使用相对路径
                    zf.write(full_path, arcname=file_path)
                elif os.path.isdir(full_path):
                    # 如果是目录，则递归添加目录内容
                    for root, _, files in os.walk(full_path):
                        for file in files:
                            actual_file_path = os.path.join(root, file)
                            # 计算在zip中的相对路径
                            zip_path = os.path.relpath(actual_file_path, base_dir)
                            zf.write(actual_file_path, arcname=zip_path)
        
        memory_file.seek(0)
        return memory_file

    def upload_file(self, file_obj, filename: str, conversation_id: str, path: str = "") -> Dict:
        """Upload a file"""
        base_dir = self.get_conversation_files_dir(conversation_id)
        
        if path:
            target_dir = os.path.join(base_dir, path)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
        else:
            target_dir = base_dir
        
        file_path = os.path.join(target_dir, filename)
        
        # Prevent path traversal attacks
        if not os.path.abspath(file_path).startswith(os.path.abspath(base_dir)):
            raise ValueError("Invalid file path")
        
        file_obj.save(file_path)
        
        return {
            'id': f"file-{uuid.uuid4().hex[:8]}",
            'name': filename,
            'path': os.path.relpath(file_path, base_dir),
            'type': self._get_file_type(filename),
            'size': os.path.getsize(file_path)
        }
    
    def download_file(self, url: str, conversation_id: str, filename: str = None, path: str = "") -> Dict:
        """使用aria2c下载文件"""
        # 获取下载目录
        downloads_dir = self.get_conversation_downloads_dir(conversation_id)
        
        if path:
            target_dir = os.path.join(downloads_dir, path)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
        else:
            target_dir = downloads_dir
            
        # 如果没有指定文件名，从URL提取
        if not filename:
            filename = url.split('/')[-1]
            if not filename:
                filename = f"download_{uuid.uuid4().hex[:8]}"
        
        # 生成下载ID和状态记录
        download_id = f"dl-{uuid.uuid4().hex[:8]}"
        
        # 使用aria2c下载文件
        try:
            # 创建aria2c命令
            cmd = [
                "aria2c", url,
                "--dir", target_dir,
                "--out", filename,
                "--file-allocation=none",
                "--max-connection-per-server=5",
                "--max-tries=5",
                "--retry-wait=5",
                "--connect-timeout=60"
            ]
            
            # 记录下载信息
            download_info = {
                'id': download_id,
                'url': url,
                'filename': filename,
                'path': os.path.join(path, filename) if path else filename,
                'target_dir': target_dir,
                'target_path': os.path.join(target_dir, filename),
                'conversation_id': conversation_id,
                'status': 'downloading',
                'progress': 0,
                'start_time': time.time(),
                'process': None
            }
            
            # 启动下载进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            download_info['process'] = process
            
            # 保存下载信息
            with self._download_lock:
                self.downloads[download_id] = download_info
                self.download_status[download_id] = {
                    'id': download_id,
                    'url': url,
                    'filename': filename,
                    'status': 'downloading',
                    'progress': 0,
                    'path': download_info['path'],
                    'conversation_id': conversation_id,
                    'size': 1024 * 1024,  # 初始化为1MB，后续会更新
                    'downloaded_size': 0,
                    'speed': 0,
                    'eta': 0,
                    'start_time': int(time.time() * 1000)
                }
            
            return self.download_status[download_id]
            
        except Exception as e:
            logger.error(f"下载文件错误: {e}")
            raise ValueError(f"下载文件失败: {str(e)}")
    
    def get_download_status(self, download_id: str = None, conversation_id: str = None) -> List[Dict]:
        """获取下载状态"""
        with self._download_lock:
            # 如果提供了下载ID，返回特定下载的状态
            if download_id:
                status = self.download_status.get(download_id)
                return [status] if status else []
            
            # 如果提供了会话ID，返回该会话的所有下载状态
            if conversation_id:
                return [
                    status for status in self.download_status.values()
                    if status['conversation_id'] == conversation_id
                ]
            
            # 否则返回所有下载状态
            return list(self.download_status.values())
    
    def cancel_download(self, download_id: str) -> bool:
        """取消下载任务"""
        with self._download_lock:
            if download_id not in self.downloads:
                return False
            
            download_info = self.downloads[download_id]
            process = download_info.get('process')
            
            # 终止进程
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            
            # 更新状态
            download_info['status'] = 'cancelled'
            if download_id in self.download_status:
                self.download_status[download_id]['status'] = 'cancelled'
            
            return True
    
    def pause_download(self, download_id: str) -> bool:
        """暂停下载任务"""
        with self._download_lock:
            if download_id not in self.downloads:
                logger.warning(f"暂停失败: 下载ID {download_id} 不存在")
                return False
            
            download_info = self.downloads[download_id]
            process = download_info.get('process')
            
            # 如果进程正在运行，发送暂停信号
            if process and process.poll() is None:
                try:
                    if os.name == 'posix':  # Unix-like systems
                        os.kill(process.pid, signal.SIGSTOP)
                    else:
                        # Windows doesn't support SIGSTOP, so we store current progress
                        # and will implement a restart-from-scratch approach
                        process.terminate()
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                    
                    # 更新状态
                    download_info['status'] = 'paused'
                    download_info['paused_at'] = time.time()
                    download_info['paused_size'] = download_info.get('downloaded_size', 0)
                    
                    if download_id in self.download_status:
                        self.download_status[download_id]['status'] = 'paused'
                    
                    logger.info(f"下载 {download_id} 已暂停，当前大小: {download_info.get('downloaded_size', 0)} 字节")
                    return True
                except Exception as e:
                    logger.error(f"暂停下载时出错: {e}")
                    return False
            else:
                logger.warning(f"无法暂停下载 {download_id}: 进程已不存在或已完成")
                return False
    
    def resume_download(self, download_id: str) -> bool:
        """恢复已暂停的下载任务"""
        with self._download_lock:
            if download_id not in self.downloads:
                logger.warning(f"恢复失败: 下载ID {download_id} 不存在")
                return False
            
            download_info = self.downloads[download_id]
            
            if download_info['status'] != 'paused':
                logger.warning(f"下载 {download_id} 状态为 {download_info['status']}，不是 'paused'，无法恢复")
                return False
            
            try:
                # 根据操作系统选择恢复方法
                if os.name == 'posix' and download_info.get('process') and download_info['process'].poll() is None:
                    # Unix系统: 发送继续信号
                    os.kill(download_info['process'].pid, signal.SIGCONT)
                    logger.info(f"已发送SIGCONT信号恢复下载 {download_id}")
                else:
                    # Windows或进程已不存在: 重新创建下载任务
                    url = download_info['url']
                    filename = download_info['filename']
                    target_dir = download_info['target_dir']
                    conversation_id = download_info['conversation_id']
                    
                    # 获取相对路径
                    path = os.path.dirname(download_info['path']) if '/' in download_info['path'] else ''
                    
                    # 创建aria2c命令，尝试断点续传
                    cmd = [
                        "aria2c", url,
                        "--dir", target_dir,
                        "--out", filename,
                        "--file-allocation=none",
                        "--max-connection-per-server=5",
                        "--max-tries=5",
                        "--retry-wait=5",
                        "--connect-timeout=60",
                        "--continue=true"  # 启用断点续传
                    ]
                    
                    # 启动新进程
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    # 更新下载信息
                    download_info['process'] = process
                    logger.info(f"已重新启动下载进程 {download_id}")
                
                # 更新状态
                download_info['status'] = 'downloading'
                download_info['resumed_at'] = time.time()
                
                if download_id in self.download_status:
                    self.download_status[download_id]['status'] = 'downloading'
                
                return True
            except Exception as e:
                logger.error(f"恢复下载时出错: {e}")
                return False

    def _monitor_downloads(self):
        """监控下载进度和状态"""
        while True:
            try:
                # 获取当前所有下载的副本
                with self._download_lock:
                    downloads = self.downloads.copy()
                
                for download_id, download_info in downloads.items():
                    # 跳过已完成、失败或取消的下载
                    if download_info['status'] in ['completed', 'failed', 'cancelled']:
                        continue
                    
                    # 跳过已暂停的下载
                    if download_info['status'] == 'paused':
                        continue
                    
                    process = download_info.get('process')
                    
                    # 如果进程不存在，标记为失败
                    if not process:
                        with self._download_lock:
                            download_info['status'] = 'failed'
                            if download_id in self.download_status:
                                self.download_status[download_id]['status'] = 'failed'
                        continue
                    
                    # 检查进程是否已结束
                    if process.poll() is not None:
                        # 进程已结束，检查是否成功
                        if process.returncode == 0:
                            # 下载成功，移动文件到会话目录
                            target_path = download_info['target_path']
                            if os.path.exists(target_path):
                                # 获取文件大小
                                file_size = os.path.getsize(target_path)
                                
                                # 成功下载，更新状态
                                with self._download_lock:
                                    download_info['status'] = 'completed'
                                    download_info['progress'] = 100
                                    download_info['size'] = file_size
                                    download_info['downloaded_size'] = file_size
                                    download_info['speed'] = 0  # 下载完成，速度为0
                                    download_info['eta'] = 0    # 下载完成，剩余时间为0
                                    
                                    if download_id in self.download_status:
                                        self.download_status[download_id]['status'] = 'completed'
                                        self.download_status[download_id]['progress'] = 100
                                        self.download_status[download_id]['size'] = file_size
                                        self.download_status[download_id]['downloaded_size'] = file_size
                                        self.download_status[download_id]['speed'] = 0
                                        self.download_status[download_id]['eta'] = 0
                                
                                # 移动到用户文件目录
                                dest_path = os.path.join(
                                    self.get_conversation_files_dir(download_info['conversation_id']),
                                    os.path.basename(target_path)
                                )
                                try:
                                    shutil.copy2(target_path, dest_path)
                                except Exception as e:
                                    logger.error(f"移动下载文件错误: {e}")
                            else:
                                # 文件不存在，下载失败
                                with self._download_lock:
                                    download_info['status'] = 'failed'
                                    if download_id in self.download_status:
                                        self.download_status[download_id]['status'] = 'failed'
                        else:
                            # 下载失败
                            with self._download_lock:
                                download_info['status'] = 'failed'
                                if download_id in self.download_status:
                                    self.download_status[download_id]['status'] = 'failed'
                    else:
                        # 进程仍在运行，检查进度
                        target_path = download_info['target_path']
                        if os.path.exists(target_path):
                            try:
                                # 获取文件大小作为进度指示
                                current_size = os.path.getsize(target_path)
                                
                                # 获取文件总大小 (如果未知)
                                if 'size' not in download_info or download_info.get('size', 0) <= 0:
                                    try:
                                        # 读取一行aria2c输出，尝试获取文件总大小
                                        output = process.stdout.readline().strip() if process.stdout else ""
                                        if output and "Total Length:" in output:
                                            size_part = output.split("Total Length:")[1].strip()
                                            if "(" in size_part:
                                                size_bytes = size_part.split("(")[1].split(")")[0].strip()
                                                if "bytes" in size_bytes:
                                                    try:
                                                        total_size = int(size_bytes.replace("bytes", "").strip())
                                                        download_info['size'] = total_size
                                                        if download_id in self.download_status:
                                                            self.download_status[download_id]['size'] = total_size
                                                    except ValueError:
                                                        pass
                                    except Exception as e:
                                        logger.debug(f"读取aria2c输出时出错: {e}")
                                
                                # 计算下载速度
                                now = time.time()
                                last_check_time = download_info.get('last_check_time', now - 2)
                                last_size = download_info.get('last_size', 0)
                                
                                time_diff = max(now - last_check_time, 0.1)  # 避免除以零
                                size_diff = max(current_size - last_size, 0)  # 避免负值
                                
                                # 计算平滑的速度 (使用指数移动平均)
                                old_speed = download_info.get('speed', 0)
                                new_instantaneous_speed = size_diff / time_diff
                                alpha = 0.3  # 平滑因子
                                speed = alpha * new_instantaneous_speed + (1 - alpha) * old_speed
                                
                                # 避免速度为0
                                if speed < 100 and new_instantaneous_speed > 0:
                                    speed = new_instantaneous_speed
                                
                                # 更新最后检查时间和大小
                                download_info['last_check_time'] = now
                                download_info['last_size'] = current_size
                                
                                # 计算ETA (预计剩余时间)
                                eta = 0
                                if speed > 100:  # 确保至少有一些有意义的速度
                                    total_size = download_info.get('size', 0)
                                    if total_size > current_size:
                                        remaining_bytes = total_size - current_size
                                        eta = remaining_bytes / speed  # 秒
                                
                                # 确保进度百分比有意义
                                total_size = download_info.get('size', 0)
                                if total_size > 0:
                                    progress = min(int((current_size / total_size) * 100), 99)
                                else:
                                    # 如果不知道总大小，使用估算值
                                    progress = min(max(1, int(current_size / (1024 * 1024))), 99)  # 每MB大约1%进度
                                
                                logger.debug(f"下载 {download_id}: 大小={current_size}/{total_size}, 速度={speed:.2f} B/s, ETA={eta:.2f}s, 进度={progress}%")
                                
                                # 更新进度和其他信息
                                with self._download_lock:
                                    download_info['progress'] = progress
                                    download_info['downloaded_size'] = current_size
                                    download_info['speed'] = speed
                                    download_info['eta'] = eta
                                    
                                    if download_id in self.download_status:
                                        self.download_status[download_id]['progress'] = progress
                                        self.download_status[download_id]['downloaded_size'] = current_size
                                        self.download_status[download_id]['speed'] = speed
                                        self.download_status[download_id]['eta'] = eta
                            except Exception as e:
                                logger.error(f"获取下载进度错误: {e}")
                
            except Exception as e:
                logger.error(f"监控下载错误: {e}")
            
            # 降低检查频率以减少CPU使用率
            time.sleep(1)