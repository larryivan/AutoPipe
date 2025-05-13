"""
AutoPipe 应用配置
"""
import os

# 是否默认使用备用回复生成器（不使用OpenAI）
# 可以通过环境变量配置，默认改为False以使用LLM
USE_FALLBACK_ONLY = os.environ.get('USE_FALLBACK_ONLY', 'False').lower() in ('true', '1', 'yes')

# OpenAI API密钥（当USE_FALLBACK_ONLY为False时需要）
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'sk-27e47833a9d14961b25c9c2a1c7a7d68')

# OpenAI兼容API的基础URL
# 允许使用自定义的OpenAI兼容API服务，如Azure OpenAI, Claude, LocalAI等
OPENAI_API_BASE = os.environ.get('OPENAI_API_BASE', 'https://dashscope.aliyuncs.com/compatible-mode/v1')

# OpenAI兼容API的模型名称
# 可设置为不同提供商支持的模型
OPENAI_MODEL_NAME = os.environ.get('OPENAI_MODEL_NAME', 'qwen-plus')

# API请求超时时间（秒）
API_TIMEOUT = int(os.environ.get('API_TIMEOUT', '30'))

# 配置调试模式
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes') 