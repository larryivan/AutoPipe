import os
import json
import uuid
import subprocess
import shutil
import time
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data directories
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
PLANS_DIR = os.path.join(DATA_DIR, 'plans')
FILES_DIR = os.path.join(DATA_DIR, 'files')
LOGS_DIR = os.path.join(DATA_DIR, 'logs')

# Ensure directories exist
os.makedirs(PLANS_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

class PipelineService:
    """Service for managing bioinformatics workflows"""
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service
    
    def get_conversation_files_dir(self, conversation_id: str) -> str:
        """Get the directory for conversation files"""
        conversation_files_dir = os.path.join(FILES_DIR, conversation_id)
        os.makedirs(conversation_files_dir, exist_ok=True)
        return conversation_files_dir
    
    def create_workflow(self, conversation_id: str, goal: str, files: List[Dict]) -> Dict:
        """Create a bioinformatics workflow based on user goals and files"""
        # Generate a unique ID for this plan
        plan_id = f"{uuid.uuid4().hex[:8]}"
        
        # Create prompt for the LLM to generate a workflow plan
        file_descriptions = "\n".join([f"- {file['name']} ({file['type']})" for file in files])
        
        prompt = f"""
        I need to create a bioinformatics workflow for the following goal:
        
        GOAL: {goal}
        
        I have the following files available:
        {file_descriptions}
        
        Create a detailed step-by-step bioinformatics workflow to achieve this goal.
        For each step, provide:
        1. A title describing the action
        2. A detailed command that can be executed in bash
        3. A description explaining what the command does and why it's necessary
        
        Format your response as a valid JSON array with the following structure:
        {{
            "title": "Overall Workflow Title",
            "steps": [
                {{
                    "id": "step1",
                    "title": "Step Title",
                    "command": "bash command to execute",
                    "description": "Detailed explanation of what this step does"
                }},
                ...
            ]
        }}
        
        Ensure that all commands correctly reference the file paths within the workflow directory. 
        Use best practices for bioinformatics workflows and include appropriate tools like FastQC, 
        BWA, STAR, Samtools, GATK, etc. as needed.
        """
        
        if self.llm_service:
            # Use the LLM service to generate the workflow
            try:
                response = self.llm_service.generate_structured_response(prompt)
                workflow = json.loads(response)
            except Exception as e:
                logger.error(f"Error generating workflow: {e}")
                # Fallback to basic workflow if LLM fails
                workflow = self._create_fallback_workflow(goal, files)
        else:
            # If no LLM service is available, create a basic fallback workflow
            workflow = self._create_fallback_workflow(goal, files)
        
        # Add metadata
        workflow['id'] = plan_id
        workflow['conversation_id'] = conversation_id
        workflow['created_at'] = time.time()
        workflow['status'] = "created"
        
        # Save the workflow plan
        self._save_workflow(plan_id, workflow)
        
        return workflow
    
    def _create_fallback_workflow(self, goal: str, files: List[Dict]) -> Dict:
        """Create a basic workflow when LLM is unavailable"""
        # Detect file types to determine workflow type
        fastq_files = [f for f in files if f['name'].endswith(('.fastq', '.fastq.gz', '.fq', '.fq.gz'))]
        
        if fastq_files:
            return {
                "title": f"Basic Analysis of {len(fastq_files)} FASTQ Files",
                "steps": [
                    {
                        "id": "step1",
                        "title": "Quality Control with FastQC",
                        "command": f"fastqc {' '.join([f['name'] for f in fastq_files])}",
                        "description": "Check the quality of raw sequencing data using FastQC"
                    },
                    {
                        "id": "step2",
                        "title": "Create Results Directory",
                        "command": "mkdir -p results",
                        "description": "Create a directory to store results"
                    }
                ]
            }
        else:
            return {
                "title": "Basic File Analysis",
                "steps": [
                    {
                        "id": "step1",
                        "title": "List Available Files",
                        "command": "ls -la *.* > file_inventory.txt",
                        "description": "Create an inventory of all available files"
                    },
                    {
                        "id": "step2",
                        "title": "Create Results Directory",
                        "command": "mkdir -p results",
                        "description": "Create a directory to store results"
                    }
                ]
            }
    
    def _save_workflow(self, plan_id: str, workflow: Dict) -> None:
        """Save workflow plan to disk"""
        plan_path = os.path.join(PLANS_DIR, f"plan_{plan_id}.json")
        with open(plan_path, 'w') as f:
            json.dump(workflow, f, indent=2)
    
    def get_workflow(self, plan_id: str) -> Optional[Dict]:
        """Retrieve a workflow plan by ID"""
        plan_path = os.path.join(PLANS_DIR, f"plan_{plan_id}.json")
        if not os.path.exists(plan_path):
            return None
            
        with open(plan_path, 'r') as f:
            return json.load(f)
    
    def list_workflows(self, conversation_id: Optional[str] = None) -> List[Dict]:
        """List all workflows, optionally filtered by conversation_id"""
        workflows = []
        
        for filename in os.listdir(PLANS_DIR):
            if filename.startswith("plan_") and filename.endswith(".json"):
                plan_path = os.path.join(PLANS_DIR, filename)
                with open(plan_path, 'r') as f:
                    workflow = json.load(f)
                    
                if conversation_id is None or workflow.get('conversation_id') == conversation_id:
                    # Include only summary information
                    workflows.append({
                        "id": workflow.get('id'),
                        "title": workflow.get('title'),
                        "conversation_id": workflow.get('conversation_id'),
                        "created_at": workflow.get('created_at'),
                        "status": workflow.get('status')
                    })
        
        return sorted(workflows, key=lambda w: w.get('created_at', 0), reverse=True)
    
    def execute_step(self, plan_id: str, step_id: str, conversation_id: str) -> Dict:
        """Execute a specific step in a workflow"""
        workflow = self.get_workflow(plan_id)
        if not workflow:
            raise ValueError(f"Workflow plan {plan_id} not found")
        
        # Find the step to execute
        target_step = None
        for step in workflow.get('steps', []):
            if step.get('id') == step_id:
                target_step = step
                break
        
        if not target_step:
            raise ValueError(f"Step {step_id} not found in workflow {plan_id}")
        
        # Prepare working directory (using conversation files directory)
        work_dir = self.get_conversation_files_dir(conversation_id)
        
        # Update step status
        target_step['status'] = 'running'
        target_step['start_time'] = time.time()
        self._save_workflow(plan_id, workflow)
        
        # Execute the command
        log_file_path = os.path.join(LOGS_DIR, f"{plan_id}_{step_id}.log")
        
        try:
            with open(log_file_path, 'w') as log_file:
                process = subprocess.Popen(
                    target_step['command'],
                    shell=True,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    cwd=work_dir
                )
                
                # Wait for process to complete (with timeout)
                try:
                    return_code = process.wait(timeout=600)  # 10-minute timeout
                    
                    if return_code == 0:
                        target_step['status'] = 'completed'
                        target_step['output'] = self._get_truncated_output(log_file_path)
                    else:
                        target_step['status'] = 'failed'
                        target_step['error'] = f"Command failed with return code {return_code}"
                        target_step['output'] = self._get_truncated_output(log_file_path)
                
                except subprocess.TimeoutExpired:
                    process.kill()
                    target_step['status'] = 'timeout'
                    target_step['error'] = "Command execution timed out after 10 minutes"
        
        except Exception as e:
            target_step['status'] = 'failed'
            target_step['error'] = str(e)
        
        # Update completion time
        target_step['end_time'] = time.time()
        
        # Check if all steps are completed to update workflow status
        all_completed = all(
            step.get('status', '') == 'completed' 
            for step in workflow.get('steps', [])
        )
        
        if all_completed:
            workflow['status'] = 'completed'
        elif any(step.get('status', '') == 'failed' for step in workflow.get('steps', [])):
            workflow['status'] = 'failed'
        else:
            workflow['status'] = 'in_progress'
        
        self._save_workflow(plan_id, workflow)
        
        return target_step
    
    def _get_truncated_output(self, log_file_path: str, max_lines: int = 1000) -> str:
        """Get the output of a command, truncated if necessary"""
        if not os.path.exists(log_file_path):
            return ""
            
        with open(log_file_path, 'r') as f:
            lines = f.readlines()
            
        if len(lines) > max_lines:
            output = "".join(lines[:max_lines//2])
            output += f"\n... [output truncated, {len(lines) - max_lines} lines omitted] ...\n"
            output += "".join(lines[-max_lines//2:])
            return output
        else:
            return "".join(lines)
