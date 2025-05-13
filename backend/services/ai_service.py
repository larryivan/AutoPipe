import os
import json
import logging
from typing import Optional, Dict, List, Any

# Try to import OpenAI's official client
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI Python package not installed. Using fallback responses.")

# Try to import LangChain components
LANGCHAIN_AVAILABLE = False
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logging.warning("LangChain packages not installed. Using fallback responses.")

class AIService:
    """Service for interacting with AI models"""
    
    def __init__(self, 
                 api_key: Optional[str] = None, 
                 api_base: Optional[str] = None,
                 model_name: str = "gpt-3.5-turbo",
                 temperature: float = 0.2,
                 timeout: int = 60):
        """Initialize the AI service"""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.api_base = api_base or os.environ.get("OPENAI_API_BASE")
        self.model_name = model_name
        self.temperature = temperature
        self.timeout = timeout
        
        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE and self.api_key:
            openai.api_key = self.api_key
            if self.api_base:
                openai.api_base = self.api_base
        
        # Initialize LangChain if available
        self.llm = None
        if LANGCHAIN_AVAILABLE and self.api_key:
            try:
                self.llm = ChatOpenAI(
                    model=self.model_name,
                    openai_api_key=self.api_key,
                    openai_api_base=self.api_base if self.api_base else None,
                    temperature=self.temperature,
                    request_timeout=self.timeout
                )
                logging.info(f"LangChain initialized with model {self.model_name}")
            except Exception as e:
                logging.error(f"Failed to initialize LangChain: {e}")
    
    def generate_response(self, prompt: str) -> str:
        """Generate a text response from the AI model"""
        # Try using LangChain first
        if self.llm:
            try:
                chain = PromptTemplate.from_template(prompt) | self.llm | StrOutputParser()
                return chain.invoke({})
            except Exception as e:
                logging.error(f"LangChain error: {e}")
        
        # Fall back to OpenAI direct API
        if OPENAI_AVAILABLE and self.api_key:
            try:
                response = openai.ChatCompletion.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    timeout=self.timeout
                )
                return response.choices[0].message.content
            except Exception as e:
                logging.error(f"OpenAI API error: {e}")
        
        # If all else fails, return a fallback response
        return self._fallback_response(prompt)
    
    def generate_structured_response(self, prompt: str, max_retries: int = 3) -> str:
        """Generate a structured JSON response from the AI model with retry logic for JSON parsing"""
        system_prompt = """
        You are an expert bioinformatics workflow planner. Your task is to create detailed, executable
        bioinformatics workflows based on the user's goals and available files. Your responses must be
        valid JSON that matches the schema provided by the user. Be thorough and precise in your command
        syntax, ensuring all commands are correct.
        """
        
        for attempt in range(max_retries):
            try:
                full_prompt = f"{system_prompt}\n\n{prompt}"
                response = self.generate_response(full_prompt)
                
                # Clean up response to extract just the JSON
                try:
                    # Try to find JSON content between triple backticks
                    import re
                    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response)
                    if json_match:
                        response = json_match.group(1)
                    else:
                        # If no triple backticks, try to find content between curly braces
                        json_match = re.search(r"(\{[\s\S]*\})", response)
                        if json_match:
                            response = json_match.group(1)
                except:
                    pass
                
                # Validate JSON
                json.loads(response)
                return response
            
            except json.JSONDecodeError as e:
                logging.warning(f"Invalid JSON response on attempt {attempt+1}: {e}")
                if attempt == max_retries - 1:
                    return self._fallback_json_response()
    
    def _fallback_response(self, prompt: str) -> str:
        """Generate a fallback response when AI services are unavailable"""
        if "workflow" in prompt.lower() or "bioinformatics" in prompt.lower():
            return """
            I've created a basic bioinformatics workflow for you:
            
            ```json
            {
                "title": "Basic FASTQ Analysis Workflow",
                "steps": [
                    {
                        "id": "step1",
                        "title": "Quality Control with FastQC",
                        "command": "fastqc input.fastq -o results/",
                        "description": "Perform quality control on the raw sequencing data"
                    },
                    {
                        "id": "step2",
                        "title": "Trim Adapters and Low-Quality Reads",
                        "command": "trimmomatic SE input.fastq results/trimmed.fastq ILLUMINACLIP:TruSeq3-SE.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36",
                        "description": "Remove adapter sequences and low-quality bases"
                    }
                ]
            }
            ```
            """
        else:
            return "I'm sorry, but I don't have enough information to provide a meaningful response right now."
    
    def _fallback_json_response(self) -> str:
        """Return a fallback JSON response when structured generation fails"""
        return json.dumps({
            "title": "Basic Analysis Workflow",
            "steps": [
                {
                    "id": "step1",
                    "title": "List All Files",
                    "command": "ls -la > file_inventory.txt",
                    "description": "Create an inventory of all files in the working directory"
                },
                {
                    "id": "step2",
                    "title": "Create Results Directory",
                    "command": "mkdir -p results",
                    "description": "Create a directory to store analysis results"
                }
            ]
        }, indent=2)
