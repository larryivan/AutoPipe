import json
import logging

# Removed OpenAI and Langchain imports

from langchain_openai import ChatOpenAI # 导入ChatOpenAI
from config import OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL_NAME, API_TIMEOUT, USE_FALLBACK_ONLY # 导入配置 (新的，直接导入)

class AIService:
    """Service for AI model interaction - Now a simplified version returning fixed responses."""
    
    def __init__(self):
        """Initialize the simplified AI service."""
        logging.info("AIService initialized in simplified mode (returns fixed responses).")
        # No LLM-specific initialization needed anymore
        if not USE_FALLBACK_ONLY:
            try:
                self.llm = ChatOpenAI(
                    model_name=OPENAI_MODEL_NAME,
                    openai_api_key=OPENAI_API_KEY,
                    openai_api_base=OPENAI_API_BASE,
                    request_timeout=API_TIMEOUT,
                    # streaming=True, # 根据需要启用
                )
                logging.info(f"AIService initialized with LLM: {OPENAI_MODEL_NAME} from {OPENAI_API_BASE}")
            except Exception as e:
                logging.error(f"Failed to initialize LLM: {e}")
                self.llm = None
        else:
            self.llm = None
            logging.info("AIService initialized in fallback mode (USE_FALLBACK_ONLY is True).")
    
    def generate_response(self, prompt: str) -> str:
        """Generate a fixed text response."""
        if self.llm:
            try:
                # Langchain 的 ChatOpenAI 需要一个消息列表
                # 这里我们简单地将 prompt 包装成一个用户消息
                from langchain_core.messages import HumanMessage
                messages = [HumanMessage(content=prompt)]
                ai_response = self.llm.invoke(messages)
                return ai_response.content
            except Exception as e:
                logging.error(f"LLM response generation failed: {e}")
                return self._fallback_text_response() # 出错时也返回备用回复
        else:
            # return "Hello" # 旧的固定回复
            return self._fallback_text_response()
    
    def generate_structured_response(self, prompt: str, max_retries: int = 3) -> str:
        """Generate a fixed structured JSON response."""
        # Since generate_response always returns "Hello",
        # direct JSON parsing of its output will fail, leading to _fallback_json_response.
        # We can simplify this to directly call _fallback_json_response or mimic the failure.
        # For clarity, we'll just directly return the fallback JSON.
        # return self._fallback_json_response() # 旧的实现
        if self.llm:
            # 对于结构化输出，通常需要更复杂的 prompt 工程和可能的输出解析器
            # 这里暂时简化，仍然使用普通 invoke，并期望模型能按指示输出JSON
            # 未来可以引入 Langchain 的 Output Parsers
            try:
                from langchain_core.messages import HumanMessage
                messages = [HumanMessage(content=prompt)]
                ai_response = self.llm.invoke(messages)
                # 假设模型直接返回了JSON字符串，尝试解析
                # 实际应用中，这里可能需要更健壮的解析和错误处理
                # json.loads(ai_response.content) # 确保它是有效的JSON
                return ai_response.content # 直接返回内容，由调用方处理
            except Exception as e:
                logging.error(f"LLM structured response generation failed: {e}")
                return self._fallback_json_response()
        else:
            return self._fallback_json_response()
    
    # _fallback_response is no longer called by generate_response, so it can be removed or left unused.
    # For a cleaner slate, we'll remove it.
    # def _fallback_response(self, prompt: str) -> str:
    #     return "Fixed fallback response when AI is disabled."

    def _fallback_json_response(self) -> str:
        """Return a fixed fallback JSON response."""
        return json.dumps({
            "message": "AI service is currently in fallback mode or encountered an error.", # 更新消息
            "status": "AI interaction disabled, returning fixed JSON response."
        }, indent=2)

    def _fallback_text_response(self) -> str:
        """Return a fixed fallback text response."""
        return "The AI service is currently in fallback mode or encountered an error. Please check the configuration." # 更新消息
