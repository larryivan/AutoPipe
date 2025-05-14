import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 60000, // 较长的超时时间，以便处理耗时的操作
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  // 确保axios可以处理上传进度事件
  onUploadProgress: function() { return; }
});

// 对话相关API
export const conversationsApi = {
  // 获取所有对话
  getAll: () => apiClient.get('/conversations'),
  
  // 获取单个对话
  get: (conversationId) => apiClient.get(`/conversations/${conversationId}`),
  
  // 创建新对话
  create: (params = {}) => apiClient.post('/conversations', params),
  
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
  getAll: (conversationId, path = '') => 
    apiClient.get('/files', { 
      params: { conversation_id: conversationId, path }
    }),
  
  // 搜索文件
  search: (query, conversationId) => 
    apiClient.get('/files/search', { 
      params: { query, conversation_id: conversationId }
    }),
  
  // 创建新文件
  create: (name, content, conversationId, path = '') => apiClient.post('/files', { 
    name, 
    content, 
    conversation_id: conversationId,
    path
  }),
  
  // 上传文件
  upload: (file, conversationId, path = '', onProgress) => {
    // 使用XMLHttpRequest实现更可靠的进度跟踪
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('file', file);
      formData.append('conversation_id', conversationId);
      if (path) formData.append('path', path);
      
      console.log(`使用XHR上传文件: ${file.name}, 大小: ${file.size} 字节, 到路径: ${path || '/'}`);
      
      // 设置进度事件
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && onProgress && typeof onProgress === 'function') {
          const percentCompleted = Math.round((event.loaded * 100) / event.total);
          console.log(`XHR上传进度: ${event.loaded}/${event.total} (${percentCompleted}%)`);
          onProgress(percentCompleted);
        }
      });
      
      // 设置完成事件
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (e) {
            resolve({ success: true, message: "File uploaded successfully" });
          }
        } else {
          reject(new Error(`上传文件失败: ${xhr.status} - ${xhr.statusText}`));
        }
      });
      
      // 设置错误事件
      xhr.addEventListener('error', () => {
        reject(new Error('上传过程中发生网络错误'));
      });
      
      // 设置中止事件
      xhr.addEventListener('abort', () => {
        reject(new Error('上传被用户取消'));
      });
      
      // 发送请求
      xhr.open('POST', `${API_URL}/files/upload`, true);
      xhr.send(formData);
    });
  },
  
  // 使用axios上传（备用方法）
  uploadWithAxios: (file, conversationId, path = '', onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('conversation_id', conversationId);
    if (path) formData.append('path', path);
    
    console.log(`开始上传文件(Axios): ${file.name}, 大小: ${file.size} 字节, 到路径: ${path || '/'}`);
    
    // 配置请求，包括进度回调
    const config = {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    };
    
    // 如果提供了进度回调，添加上传进度事件监听
    if (onProgress && typeof onProgress === 'function') {
      config.onUploadProgress = (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        console.log(`上传进度(Axios): ${progressEvent.loaded}/${progressEvent.total} (${percentCompleted}%)`);
        onProgress(percentCompleted);
      };
    }
    
    return apiClient.post('/files/upload', formData, config);
  },
  
  // 获取文件内容
  getContent: (filePath, conversationId) => 
    apiClient.get(`/files/${filePath}`, { 
      params: { conversation_id: conversationId }
    }),
  
  // 更新文件内容
  updateContent: (filePath, content, conversationId) => 
    apiClient.put(`/files/${filePath}`, { content, conversation_id: conversationId }),
  
  // 删除文件
  delete: (filePath, conversationId) => 
    apiClient.delete(`/files/${filePath}`, { 
      params: { conversation_id: conversationId }
    }),
  
  // 创建目录
  createDirectory: (name, conversationId, path = '') => apiClient.post('/files/mkdir', { 
    name, 
    conversation_id: conversationId,
    path
  }),
  
  // 重命名文件或文件夹
  renameFile: (oldPath, newName, conversationId) => apiClient.post('/files/rename', {
    old_path: oldPath,
    new_name: newName,
    conversation_id: conversationId
  }),
  
  // 直接下载文件 (返回blob)
  directDownload: (filePath, conversationId) => {
    return apiClient.get(`/files/download_file/${filePath}`, {
      params: { conversation_id: conversationId },
      responseType: 'blob'
    });
  },
  
  // 新增：下载文件相关API
  downloadFile: (url, conversationId, filename = null, path = '') => {
    return apiClient.post('/files/download', {
      url,
      conversation_id: conversationId,
      filename,
      path
    });
  },
  
  getDownloadStatus: (downloadId = null, conversationId = null) => {
    const params = {};
    if (downloadId) params.download_id = downloadId;
    if (conversationId) params.conversation_id = conversationId;
    
    return apiClient.get('/files/download/status', { params });
  },
  
  cancelDownload: (downloadId) => {
    return apiClient.post('/files/download/cancel', { download_id: downloadId });
  },
  
  // 新增：暂停下载
  pauseDownload: (downloadId) => {
    return apiClient.post('/files/download/pause', { download_id: downloadId });
  },
  
  // 新增：恢复下载
  resumeDownload: (downloadId) => {
    return apiClient.post('/files/download/resume', { download_id: downloadId });
  },
  
  // 新增：批量下载文件为ZIP (返回blob)
  downloadBatchAsZip: (filePaths, conversationId) => {
    console.log(`API - downloadBatchAsZip: Requesting batch download for paths:`, filePaths, `in conv: ${conversationId}`);
    return apiClient.post('/files/download_batch', {
      file_paths: filePaths,
      conversation_id: conversationId
    }, {
      responseType: 'blob' // 重要的是设置响应类型为blob
    });
  },
};

// 工作流相关API
export const workflowsApi = {
  // 获取所有工作流
  getAll: (conversationId) => apiClient.get(`/workflows?conversation_id=${conversationId}`),
  
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

// 终端API
export const terminalApi = {
  getSessions: (conversationId) => 
    apiClient.get(`/terminal/sessions?conversation_id=${conversationId}`),
  getSession: (sessionId) => 
    apiClient.get(`/terminal/sessions/${sessionId}`),
  createSession: (conversationId) => 
    apiClient.post('/terminal/sessions', { conversation_id: conversationId }),
  executeCommand: (sessionId, command) => 
    apiClient.post(`/terminal/sessions/${sessionId}/execute`, { command }),
  terminateCommand: (sessionId, commandId) =>
    apiClient.post(`/terminal/sessions/${sessionId}/commands/${commandId}/terminate`),
  terminateSession: (sessionId) => 
    apiClient.delete(`/terminal/sessions/${sessionId}`),
};

// 系统监控API
export const monitorApi = {
  getSystemInfo: () => 
    apiClient.get('/monitor/info'),
  getCurrentMetrics: () => 
    apiClient.get('/monitor/metrics'),
  getProcesses: (pythonOnly = false) => 
    apiClient.get(`/monitor/processes${pythonOnly ? '?python_only=true' : ''}`),
  getHistory: (metricType = null, points = null) => {
    let url = '/monitor/history';
    const params = new URLSearchParams();
    
    if (metricType) params.append('type', metricType);
    if (points) params.append('points', points);
    
    const queryString = params.toString();
    return apiClient.get(url + (queryString ? `?${queryString}` : ''));
  },
};

export default {
  conversationsApi,
  filesApi,
  workflowsApi,
  terminalApi,
  monitorApi,
};