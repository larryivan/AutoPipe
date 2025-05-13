import os
import shutil
import json
import mimetypes
from typing import Dict, List, Any, Optional
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data directories
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
FILES_DIR = os.path.join(DATA_DIR, 'files')

# Ensure directories exist
os.makedirs(FILES_DIR, exist_ok=True)

class FileService:
    """Service for managing files and directories"""
    
    def __init__(self):
        """Initialize the file service"""
        pass
    
    def get_conversation_files_dir(self, conversation_id: str) -> str:
        """Get the directory for conversation files"""
        conversation_files_dir = os.path.join(FILES_DIR, conversation_id)
        os.makedirs(conversation_files_dir, exist_ok=True)
        return conversation_files_dir
    
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