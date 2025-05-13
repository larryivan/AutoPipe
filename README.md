# BioinfoFlow: Automated Bioinformatics Workflow Platform

BioinfoFlow (formerly AutoPipe) is a comprehensive platform for automating bioinformatics workflows. It helps researchers execute complex bioinformatics analyses with just a few clicks, without needing to write complex scripts.

## Features

- **AI-Powered Workflow Generation**: Describe your bioinformatics goal in natural language, and the AI automatically creates a customized workflow
- **One-Click Execution**: Execute complex bioinformatics steps with a single click
- **File Management**: Upload, manage, and organize your bioinformatics data files
- **Interactive Chat**: Get assistance and guidance through an AI chat interface
- **Workflow Tracking**: Monitor the progress and status of your bioinformatics analyses

## Technology Stack

### Frontend
- Vue.js
- Tailwind CSS

### Backend
- Flask
- LangChain
- Bioinformatics tools integration

## 安装与运行

### 后端

1. 进入后端目录
```bash
cd backend
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 运行服务器
```bash
python main.py
```

后端服务器将在 http://localhost:5000 上运行。

### 前端

1. 进入前端目录
```bash
cd frontend
```

2. 安装依赖
```bash
npm install
```

3. 运行开发服务器
```bash
npm run dev
```

前端应用将在 http://localhost:3000 上运行。

## API接口

### 对话相关

- GET /api/conversations - 获取所有对话
- POST /api/conversations - 创建新对话
- GET /api/conversations/{conv_id} - 获取特定对话
- DELETE /api/conversations/{conv_id} - 删除对话
- PUT /api/conversations/{conv_id}/rename - 重命名对话

### 消息相关

- GET /api/conversations/{conv_id}/messages - 获取对话消息
- POST /api/conversations/{conv_id}/messages - 发送消息并获取回复

### 文件相关

- GET /api/files - 获取文件列表
- POST /api/files - 创建新文件
- POST /api/files/upload - 上传文件
- GET /api/files/{file_path} - 获取文件内容
- PUT /api/files/{file_path} - 更新文件内容
- DELETE /api/files/{file_path} - 删除文件
- POST /api/files/mkdir - 创建文件夹
- GET /api/files/search - 搜索文件 