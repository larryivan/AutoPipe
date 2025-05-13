import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// 对话相关API
export const conversationsApi = {
  // 获取所有对话
  getAll: () => apiClient.get('/conversations'),
  
  // 创建新对话
  create: (title) => apiClient.post('/conversations', { title }),
  
  // 获取单个对话
  get: (conversationId) => apiClient.get(`/conversations/${conversationId}`),
  
  // 删除对话
  delete: (conversationId) => apiClient.delete(`/conversations/${conversationId}`),
  
  // 重命名对话
  rename: (conversationId, title) => apiClient.put(`/conversations/${conversationId}/rename`, { title }),
  
  // 获取对话的所有消息
  getMessages: (conversationId) => apiClient.get(`/conversations/${conversationId}/messages`),
  
  // 发送消息
  sendMessage: (conversationId, message) => apiClient.post(`/conversations/${conversationId}/messages`, { message }),
  
  // 设置对话模式
  setMode: (conversationId, mode) => apiClient.put(`/conversations/${conversationId}/mode`, { mode }),
};

// 文件相关API
export const filesApi = {
  // 获取所有文件
  getAll: (conversationId) => apiClient.get(`/files?conversation_id=${conversationId}`),
  
  // 搜索文件
  search: (query, conversationId) => apiClient.get('/files/search', {
    params: { 
      q: query,
      conversation_id: conversationId
    }
  }),
  
  // 创建新文件
  create: (name, content, conversationId, path = '') => apiClient.post('/files', { 
    name, 
    content, 
    conversation_id: conversationId,
    path
  }),
  
  // 上传文件
  upload: (file, conversationId, path = '') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('conversation_id', conversationId);
    if (path) formData.append('path', path);
    
    return apiClient.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  // 获取文件内容
  getContent: (filePath, conversationId) => apiClient.get('/files/content', { 
    params: { path: filePath, conversation_id: conversationId }
  }),
  
  // 更新文件内容
  updateContent: (filePath, content, conversationId) => apiClient.put('/files/content', {
    path: filePath,
    content,
    conversation_id: conversationId
  }),
  
  // 删除文件
  delete: (filePath, conversationId) => apiClient.delete('/files', {
    params: { 
      path: filePath,
      conversation_id: conversationId
    }
  }),
  
  // 创建目录
  createDirectory: (name, conversationId, path = '') => apiClient.post('/files/directory', { 
    name, 
    conversation_id: conversationId,
    path
  }),
};

// 工作流相关API
export const workflowsApi = {
  // 获取所有工作流
  getAll: (conversationId) => apiClient.get('/workflows', { 
    params: { conversation_id: conversationId }
  }),
  
  // 获取单个工作流
  get: (workflowId) => apiClient.get(`/workflows/${workflowId}`),
  
  // 创建新工作流
  create: (conversationId, goal) => apiClient.post('/workflows', { 
    conversation_id: conversationId,
    goal
  }),
  
  // 执行工作流步骤
  executeStep: (workflowId, stepId, conversationId) => 
    apiClient.post(`/workflows/${workflowId}/steps/${stepId}/execute`, {
      conversation_id: conversationId
    }),
};