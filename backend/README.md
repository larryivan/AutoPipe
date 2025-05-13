# BioinfoFlow Backend

BioinfoFlow (formerly AutoPipe) is a platform for automating bioinformatics workflows through AI-powered workflow generation and execution.

## Key Features

- **Bioinformatics Workflow Generation**: AI-powered creation of workflow steps based on user goals
- **Workflow Execution Engine**: Execute bioinformatics commands with tracking and error handling
- **Dual Operating Modes**:
  - **Agent Mode**: Automatically plans and executes workflows based on user goals
  - **Chat Mode**: Regular conversational Q&A for bioinformatics guidance
- **Intelligent Chat Interface**: Support for bioinformatics questions and analysis guidance
- **Conversation-specific File Management**: Each conversation has an isolated file workspace
- **RESTful API**: Clean API design for frontend integration

## 环境变量配置

AutoPipe支持通过环境变量或`.env`文件进行配置：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `OPENAI_API_KEY` | API密钥 | (空) |
| `OPENAI_API_BASE` | API基础URL | https://api.openai.com/v1 |
| `OPENAI_MODEL_NAME` | 模型名称 | gpt-3.5-turbo |
| `API_TIMEOUT` | API请求超时(秒) | 30 |
| `USE_FALLBACK_ONLY` | 是否只使用备用回复生成器 | False |
| `DEBUG` | 是否启用调试模式 | True |
| `AZURE_DEPLOYMENT` | Azure OpenAI部署名称 | (与OPENAI_MODEL_NAME相同) |
| `AZURE_API_VERSION` | Azure API版本 | 2023-05-15 |

## 支持的API提供商

AutoPipe支持以下API提供商：

### 1. OpenAI API

默认设置适用于OpenAI官方API。只需设置您的`OPENAI_API_KEY`：

```
OPENAI_API_KEY=sk-your-api-key
```

### 2. Azure OpenAI

通过设置Azure特定的环境变量来使用Azure OpenAI：

```
OPENAI_API_BASE=https://your-resource-name.openai.azure.com
OPENAI_API_KEY=your-azure-api-key
AZURE_DEPLOYMENT=your-deployment-name
AZURE_API_VERSION=2023-05-15
```

### 3. 本地API（LocalAI/自托管API）

支持各种兼容OpenAI API的本地或自托管服务：

```
OPENAI_API_BASE=http://localhost:8080/v1
OPENAI_API_KEY=any-key-will-work
OPENAI_MODEL_NAME=ggml-vicuna-13b-1.1-q4_2
```

支持的本地解决方案包括：
- LocalAI
- LM Studio
- Ollama
- 等其他OpenAI兼容API

## 使用简易模式

如果您没有API密钥，可以启用简易模式：

```
USE_FALLBACK_ONLY=True
```

这将使用基于关键词匹配的本地回复生成器，无需任何API调用.