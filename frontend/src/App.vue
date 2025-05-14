<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from "vue";
import "./assets/main.css";
import { conversationsApi, filesApi, workflowsApi } from "./services/api";
import Sidebar from "./components/Sidebar.vue";
import Downloader from "./components/Downloader.vue"; // 导入下载器组件

const conversationHistory = ref([]);
const currentConversationId = ref(null);
const newMessage = ref("");

// --- Screen Size Detection ---
const isLargeScreen = ref(false);
const updateScreenSize = () => {
  isLargeScreen.value = window.innerWidth >= 1024; // Tailwind's lg breakpoint (1024px)
};

// --- Mobile Navigation State ---
const isMobileNavOpen = ref(false); // For left sidebar on mobile

// --- Resizable Sidebars State ---
const collapsedLeftSidebarWidth = 64;
const defaultOpenLeftSidebarWidth = 256;
const mobileLeftSidebarWidth = 256; // Fixed width for mobile overlay
const leftSidebarWidth = ref(defaultOpenLeftSidebarWidth);
let lastOpenLeftWidth = defaultOpenLeftSidebarWidth;
const isResizingLeft = ref(false);
const initialMouseXLeft = ref(0);
const initialLeftWidth = ref(0);
const leftSidebarResizeMin = 150;
const leftSidebarResizeMax = 500;
let rafLeftResize = null;

const collapsedRightSidebarWidth = 0;
const defaultOpenRightSidebarWidth = 288;
const mobileRightSidebarWidth = 288; // Fixed width for mobile overlay
const rightSidebarWidth = ref(collapsedRightSidebarWidth);
let lastOpenRightWidth = defaultOpenRightSidebarWidth;
const isResizingRight = ref(false);
const initialMouseXRight = ref(0);
const initialRightWidth = ref(0);
const rightSidebarResizeMin = 150;
const rightSidebarResizeMax = 600;
let rafRightResize = null;

const isLeftSidebarLogicallyOpen = computed(() => {
  if (!isLargeScreen.value) return isMobileNavOpen.value;
  return leftSidebarWidth.value > collapsedLeftSidebarWidth;
});

const isRightSidebarLogicallyOpen = computed(() => {
  // On mobile, just check if width is greater than 0 (it will be fixed overlay width or 0)
  // On desktop, use the resizable logic
  if (!isLargeScreen.value) return rightSidebarWidth.value > 0;
  return rightSidebarWidth.value > collapsedRightSidebarWidth;
});
// --- End Resizable Sidebars State ---

const projectFiles = ref([]);
const isLoading = ref(false);
const fileSearchQuery = ref("");
const fileContentToCreate = ref("");
const fileNameToCreate = ref("");
const showCreateFileModal = ref(false);
const filePathToCreate = ref("");
const selectedFile = ref(null);
const fileUploadInput = ref(null);
const currentFileContent = ref("");
const currentFileName = ref("");
const showFileContentModal = ref(false);
const currentFilePath = ref("");
const currentDirectoryPath = ref(""); // 当前文件浏览路径

const messages = computed(() => {
  if (!currentConversationId.value) return [];
  const currentConv = conversationHistory.value.find(
    (conv) => conv.id === currentConversationId.value
  );
  return currentConv ? currentConv.messages : [];
});

const messageDisplayArea = ref(null);

const scrollToBottom = async () => {
  await nextTick();
  if (messageDisplayArea.value) {
    messageDisplayArea.value.scrollTop = messageDisplayArea.value.scrollHeight;
  }
};

const loadConversations = async () => {
  try {
    isLoading.value = true;
    const response = await conversationsApi.getAll();
    conversationHistory.value = response.data;
    if (conversationHistory.value.length > 0 && !currentConversationId.value) {
      await selectConversation(conversationHistory.value[0].id);
    } else if (conversationHistory.value.length === 0) {
      await newConversation();
    }
    scrollToBottom();
  } catch (error) {
    console.error("加载对话失败:", error);
  } finally {
    isLoading.value = false;
  }
};

const selectConversation = async (convId) => {
  try {
    currentConversationId.value = convId;
    const response = await conversationsApi.get(convId);
    const index = conversationHistory.value.findIndex((conv) => conv.id === convId);
    if (index !== -1) conversationHistory.value[index] = response.data;
    await loadFiles();
    scrollToBottom();
    if (!isLargeScreen.value) isMobileNavOpen.value = false; // Close mobile nav on selection
  } catch (error) {
    console.error("加载对话详情失败:", error);
  }
};

const newConversation = async (mode = 'chat') => {
  try {
    const response = await conversationsApi.create({ mode });
    const newConv = response.data;
    conversationHistory.value.unshift(newConv);
    currentConversationId.value = newConv.id;
    scrollToBottom();
    if (!isLargeScreen.value) isMobileNavOpen.value = false; // Close mobile nav after creating new
  } catch (error) {
    console.error("创建对话失败:", error);
  }
};

const deleteConversation = async (convIdToDelete) => {
  try {
    await conversationsApi.delete(convIdToDelete);
    const index = conversationHistory.value.findIndex(
      (conv) => conv.id === convIdToDelete
    );
    if (index !== -1) {
      conversationHistory.value.splice(index, 1);
      if (currentConversationId.value === convIdToDelete) {
        if (conversationHistory.value.length > 0) {
          await selectConversation(conversationHistory.value[0].id);
        } else {
          await newConversation();
        }
      }
    }
  } catch (error) {
    console.error("删除对话失败:", error);
  }
};

const sendMessage = async () => {
  if (newMessage.value.trim() === "") return;
  if (!currentConversationId.value) await newConversation();

  const userMessageText = newMessage.value;
  newMessage.value = "";

  try {
    const currentConv = conversationHistory.value.find(
      (conv) => conv.id === currentConversationId.value
    );
    if (currentConv) {
      const tempUserId = `temp-${Date.now()}`;
      currentConv.messages.push({
        id: tempUserId,
        text: userMessageText,
        sender: "user",
        timestamp: new Date().toISOString(),
      });
      scrollToBottom();

      const response = await conversationsApi.sendMessage(
        currentConversationId.value,
        userMessageText
      );
      const { user_message, ai_message } = response.data;
      const userMsgIndex = currentConv.messages.findIndex((msg) => msg.id === tempUserId);
      if (userMsgIndex !== -1) currentConv.messages[userMsgIndex] = user_message;
      currentConv.messages.push(ai_message);
      scrollToBottom();
    }
  } catch (error) {
    console.error("发送消息失败:", error);
  }
};

const loadFiles = async () => {
  try {
    if (!currentConversationId.value) return;
    console.log("Loading files for conversation:", currentConversationId.value, "Path:", currentDirectoryPath.value);
    const response = await filesApi.getAll(currentConversationId.value, currentDirectoryPath.value);
    console.log("Files loaded:", response.data);
    projectFiles.value = response.data;
  } catch (error) {
    console.error("加载文件失败:", error);
  }
};

const searchFiles = async (query) => {
  try {
    if (!currentConversationId.value) return;
    if (!query.trim()) {
      await loadFiles();
      return;
    }
    const response = await filesApi.search(query, currentConversationId.value);
    projectFiles.value = response.data;
  } catch (error) {
    console.error("搜索文件失败:", error);
  }
};

const toggleSidebar = () => {
  // For desktop left sidebar collapse/expand
  if (!isLargeScreen.value) {
    isMobileNavOpen.value = !isMobileNavOpen.value;
    return;
  }
  if (leftSidebarWidth.value > collapsedLeftSidebarWidth) {
    lastOpenLeftWidth = leftSidebarWidth.value;
    leftSidebarWidth.value = collapsedLeftSidebarWidth;
  } else {
    leftSidebarWidth.value =
      lastOpenLeftWidth > collapsedLeftSidebarWidth
        ? lastOpenLeftWidth
        : defaultOpenLeftSidebarWidth;
  }
};

const startResizeLeft = (event) => {
  if (!isLargeScreen.value) return;
  event.preventDefault();
  isResizingLeft.value = true;
  initialMouseXLeft.value = event.clientX || event.touches[0].clientX;
  initialLeftWidth.value = leftSidebarWidth.value;
  document.addEventListener("mousemove", doResizeLeft);
  document.addEventListener("mouseup", stopResizeLeft);
  document.addEventListener("touchmove", doResizeLeft, { passive: true });
  document.addEventListener("touchend", stopResizeLeft);
  document.body.style.userSelect = "none";
  document.body.style.cursor = "col-resize"; // 明确设置拖动时的光标
};
const doResizeLeft = (event) => {
  if (!isResizingLeft.value) return;
  if (rafLeftResize) cancelAnimationFrame(rafLeftResize);
  rafLeftResize = requestAnimationFrame(() => {
    const currentX = event.clientX || (event.touches && event.touches[0].clientX);
    if (currentX === undefined) return;
    const deltaX = currentX - initialMouseXLeft.value;
    let newWidth = initialLeftWidth.value + deltaX;
    newWidth = Math.max(leftSidebarResizeMin, Math.min(newWidth, leftSidebarResizeMax));
    leftSidebarWidth.value = newWidth;
  });
};
const stopResizeLeft = () => {
  if (rafLeftResize) cancelAnimationFrame(rafLeftResize);
  rafLeftResize = null;
  isResizingLeft.value = false;
  document.removeEventListener("mousemove", doResizeLeft);
  document.removeEventListener("mouseup", stopResizeLeft);
  document.removeEventListener("touchmove", doResizeLeft);
  document.removeEventListener("touchend", stopResizeLeft);
  document.body.style.userSelect = "";
  document.body.style.cursor = ""; // 恢复光标
};

const toggleFileSidebar = () => {
  // For right sidebar
  if (!isLargeScreen.value) {
    // Toggle mobile overlay for right sidebar
    if (rightSidebarWidth.value > 0) {
      rightSidebarWidth.value = 0; // Close overlay
    } else {
      rightSidebarWidth.value = mobileRightSidebarWidth; // Open overlay
      loadFiles();
    }
    return;
  }
  // Desktop logic
  const wasOpen = rightSidebarWidth.value > collapsedRightSidebarWidth;
  if (wasOpen) {
    lastOpenRightWidth = rightSidebarWidth.value;
    rightSidebarWidth.value = collapsedRightSidebarWidth;
  } else {
    rightSidebarWidth.value =
      lastOpenRightWidth > collapsedRightSidebarWidth
        ? lastOpenRightWidth
        : defaultOpenRightSidebarWidth;
    if (
      rightSidebarWidth.value > collapsedRightSidebarWidth &&
      currentConversationId.value
    )
      loadFiles();
  }
  initialMouseXRight.value = event.clientX || event.touches[0].clientX;
  initialRightWidth.value = rightSidebarWidth.value;
  document.addEventListener("mousemove", doResizeRight);
  document.addEventListener("mouseup", stopResizeRight);
  document.addEventListener("touchmove", doResizeRight, { passive: true });
  document.addEventListener("touchend", stopResizeRight);
  document.body.style.userSelect = "none";
  document.body.style.cursor = "col-resize"; // 明确设置拖动时的光标
};

const startResizeRight = (event) => {
  if (!isLargeScreen.value) return;
  event.preventDefault();
  isResizingRight.value = true;
  initialMouseXRight.value = event.clientX || event.touches[0].clientX;
  initialRightWidth.value = rightSidebarWidth.value;
  document.addEventListener("mousemove", doResizeRight);
  document.addEventListener("mouseup", stopResizeRight);
  document.addEventListener("touchmove", doResizeRight, { passive: true });
  document.addEventListener("touchend", stopResizeRight);
  document.body.style.userSelect = "none";
  document.body.style.cursor = "col-resize"; // 明确设置拖动时的光标
};
const doResizeRight = (event) => {
  if (!isResizingRight.value) return;
  if (rafRightResize) cancelAnimationFrame(rafRightResize);
  rafRightResize = requestAnimationFrame(() => {
    const currentX = event.clientX || (event.touches && event.touches[0].clientX);
    if (currentX === undefined) return;
    const deltaX = currentX - initialMouseXRight.value;
    let newWidth = initialRightWidth.value - deltaX; //注意是减去deltaX因为是从右边拖动
    newWidth = Math.max(rightSidebarResizeMin, Math.min(newWidth, rightSidebarResizeMax));
    rightSidebarWidth.value = newWidth;
  });
};
const stopResizeRight = () => {
  if (rafRightResize) cancelAnimationFrame(rafRightResize);
  rafRightResize = null;
  isResizingRight.value = false;
  document.removeEventListener("mousemove", doResizeRight);
  document.removeEventListener("mouseup", stopResizeRight);
  document.removeEventListener("touchmove", doResizeRight);
  document.removeEventListener("touchend", stopResizeRight);
  document.body.style.userSelect = "";
  document.body.style.cursor = ""; // 恢复光标
};

let fileListRefreshInterval = null;
const startFileListRefresh = () => {
  if (fileListRefreshInterval) clearInterval(fileListRefreshInterval);
  fileListRefreshInterval = setInterval(() => {
    if (isRightSidebarLogicallyOpen.value && currentConversationId.value) loadFiles();
  }, 10000);
};
const stopFileListRefresh = () => {
  if (fileListRefreshInterval) clearInterval(fileListRefreshInterval);
  fileListRefreshInterval = null;
};

onMounted(() => {
  updateScreenSize();
  window.addEventListener("resize", updateScreenSize);
  loadConversations();
  startFileListRefresh();
  document.addEventListener("click", closeDropdownOnClickOutside);
});
onUnmounted(() => {
  window.removeEventListener("resize", updateScreenSize);
  stopFileListRefresh();
  stopDownloadStatusPolling();
  document.removeEventListener("click", closeDropdownOnClickOutside);
  document.removeEventListener("mousemove", doResizeLeft);
  document.removeEventListener("mouseup", stopResizeLeft);
  document.removeEventListener("mousemove", doResizeRight);
  document.removeEventListener("mouseup", stopResizeRight);
  if (document.body.style.userSelect === "none") document.body.style.userSelect = "";
});

const handleFileSearch = async () => {
  await searchFiles(fileSearchQuery.value);
};
const uploadFile = async (files, progressCallback = null) => {
  try {
    if (!currentConversationId.value || !files.length) return;
    
    // 使用当前路径
    const uploadPath = currentDirectoryPath.value;
    console.log("上传文件到:", uploadPath);
    
    // 对每个文件进行上传
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const uploadId = `upload-${Date.now()}-${i}`;
      
      try {
        if (progressCallback) {
          progressCallback(uploadId, 1); // 开始上传，1%进度
        }
        
        // 创建进度回调函数
        const onProgress = (percent) => {
          if (progressCallback) {
            progressCallback(uploadId, percent);
            console.log(`文件 ${file.name} 上传进度: ${percent}%`);
          }
        };
        
        // 上传文件，传递进度回调
        await filesApi.upload(file, currentConversationId.value, uploadPath, onProgress);
        
        // 上传完成
        if (progressCallback) {
          progressCallback(uploadId, 100);
        }
      } catch (error) {
        console.error(`文件 ${file.name} 上传失败:`, error);
        if (progressCallback) {
          progressCallback(uploadId, 0, `上传失败: ${error.message}`);
        }
      }
    }
    
    // 刷新文件列表
    await loadFiles();
  } catch (error) {
    console.error("上传过程中发生错误:", error);
    alert(`上传失败: ${error.message}`);
  }
};
const triggerFileUpload = () => {
  /* ... */
};
const openCreateFileModal = (isFolder = false) => {
  console.log("App - openCreateFileModal被调用, isFolder:", isFolder);
  selectedFile.value = isFolder ? 'folder' : 'file';
  fileNameToCreate.value = '';
  fileContentToCreate.value = '';
  filePathToCreate.value = currentDirectoryPath.value;
  showCreateFileModal.value = true;
};
const createFileOrFolder = async () => {
  try {
    if (!currentConversationId.value || !fileNameToCreate.value.trim()) return;
    
    if (selectedFile.value === 'folder') {
      // 创建文件夹
      await filesApi.createDirectory(fileNameToCreate.value, currentConversationId.value, filePathToCreate.value);
    } else {
      // 创建文件
      await filesApi.create(fileNameToCreate.value, fileContentToCreate.value, currentConversationId.value, filePathToCreate.value);
    }
    
    // 刷新文件列表
    await loadFiles();
    showCreateFileModal.value = false;
  } catch (error) {
    console.error("创建文件/文件夹失败:", error);
    alert(`创建失败: ${error.message}`);
  }
};
const deleteFileOrFolder = async (filePath) => {
  /* ... */
};
const openFileContent = async (filePath) => {
  console.log("App - openFileContent被调用, 文件路径:", filePath);
  try {
    if (!currentConversationId.value) return;
    
    console.log("App - 调用API获取文件内容");
    const response = await filesApi.getContent(filePath, currentConversationId.value);
    
    if (response.data.is_binary) {
      // 如果是二进制文件，提示用户不能直接查看
      alert("不能直接查看二进制文件。");
      return;
    }
    
    currentFileContent.value = response.data.content;
    currentFileName.value = response.data.name;
    currentFilePath.value = filePath;
    showFileContentModal.value = true;
  } catch (error) {
    console.error("获取文件内容失败:", error);
    alert(`无法打开文件: ${error.message}`);
  }
};
const saveFileContent = async () => {
  try {
    if (!currentConversationId.value || !currentFilePath.value) return;
    
    // 保存文件内容
    await filesApi.updateContent(currentFilePath.value, currentFileContent.value, currentConversationId.value);
    showFileContentModal.value = false;
    
    // 可选：刷新文件列表
    await loadFiles();
  } catch (error) {
    console.error("保存文件内容失败:", error);
    alert(`保存失败: ${error.message}`);
  }
};
const toggleMode = async () => {
  if (!currentConversationId.value) return;
  
  try {
    const currentConv = conversationHistory.value.find(
      (conv) => conv.id === currentConversationId.value
    );
    
    if (currentConv) {
      const newMode = currentConv.mode === 'chat' ? 'agent' : 'chat';
      const response = await conversationsApi.setMode(currentConversationId.value, newMode);
      
      // 更新本地状态
      const index = conversationHistory.value.findIndex((conv) => conv.id === currentConversationId.value);
      if (index !== -1) conversationHistory.value[index] = response.data;
    }
  } catch (error) {
    console.error("切换模式失败:", error);
  }
};
const inputModes = [
  { id: "chat", label: "Chat", icon: "chat" },
  { id: "agent", label: "Agent", icon: "agent" },
];
const handleModeChange = async (mode) => {
  if (!currentConversationId.value) return;
  
  try {
    const response = await conversationsApi.setMode(currentConversationId.value, mode);
    
    // 更新本地状态
    const index = conversationHistory.value.findIndex((conv) => conv.id === currentConversationId.value);
    if (index !== -1) conversationHistory.value[index] = response.data;
    
    showModeDropdown.value = false;
  } catch (error) {
    console.error("更改模式失败:", error);
  }
};
const showModeDropdown = ref(false);
const toggleModeDropdown = () => {
  showModeDropdown.value = !showModeDropdown.value;
};
const modeDropdownRef = ref(null);
const closeDropdownOnClickOutside = (event) => {
  if (modeDropdownRef.value && !modeDropdownRef.value.contains(event.target)) {
    showModeDropdown.value = false;
  }
};

const closeMobileSidebars = () => {
  isMobileNavOpen.value = false;
  if (!isLargeScreen.value && rightSidebarWidth.value > 0) {
    rightSidebarWidth.value = 0;
  }
};

// 下载任务相关数据和方法
const downloadTasks = ref([]);
const downloadStatusInterval = ref(null); // Added for polling

// 暂停下载
const pauseDownload = async (downloadId) => {
  try {
    console.log("暂停下载:", downloadId);
    // 目前后端可能没有实现暂停功能，所以先在前端更新状态
    const taskIndex = downloadTasks.value.findIndex(task => task.id === downloadId);
    if (taskIndex !== -1) {
      downloadTasks.value[taskIndex].status = 'paused';
    }
    
    // 如果后端有实现暂停API，可以调用这里
    // await filesApi.pauseDownload(downloadId);
    
    // 然后从服务器刷新状态
    await getDownloadStatus();
  } catch (error) {
    console.error("暂停下载失败:", error);
  }
};

// 恢复下载
const resumeDownload = async (downloadId) => {
  try {
    console.log("恢复下载:", downloadId);
    // 目前后端可能没有实现恢复功能，所以先在前端更新状态
    const taskIndex = downloadTasks.value.findIndex(task => task.id === downloadId);
    if (taskIndex !== -1) {
      downloadTasks.value[taskIndex].status = 'downloading';
    }
    
    // 如果后端有实现恢复API，可以调用这里
    // await filesApi.resumeDownload(downloadId);
    
    // 然后从服务器刷新状态
    await getDownloadStatus();
  } catch (error) {
    console.error("恢复下载失败:", error);
  }
};

// 清除已完成的下载
const clearCompletedDownloads = () => {
  console.log("App - 清除已完成的下载任务");
  
  // 过滤掉已完成、失败和取消的下载，只保留正在下载和暂停的
  const activeTasks = downloadTasks.value.filter(task => {
    return task.status === 'downloading' || task.status === 'paused';
  });
  
  console.log(`App - 清除前: ${downloadTasks.value.length} 个任务, 清除后: ${activeTasks.length} 个任务`);
  downloadTasks.value = activeTasks;
};

// 下载文件
const downloadFile = async (downloadInfo) => {
  try {
    if (!currentConversationId.value) return;
    
    const { url, filename } = downloadInfo;
    console.log("开始下载文件:", url, filename, currentConversationId.value);
    
    // 估计一个初始大小
    const initialSize = 1024 * 1024; // 默认1MB
    
    // 先添加一个临时任务到下载任务列表中以提供即时反馈
    const tempTask = {
      id: `temp-${Date.now()}`,
      url: url,
      filename: filename || url.split('/').pop() || `download_${Date.now()}`,
      status: 'downloading',
      progress: 1,
      size: initialSize,
      downloaded_size: 0,
      speed: 0,
      eta: 0,
      conversation_id: currentConversationId.value
    };
    downloadTasks.value = [...downloadTasks.value, tempTask];
    
    // 调用后端API
    const response = await filesApi.downloadFile(url, currentConversationId.value, filename);
    console.log("后端下载响应:", response.data);
    
    // 下载开始后立即刷新下载状态
    await getDownloadStatus();
    
    // 启动轮询以持续更新状态
    startDownloadStatusPolling();
  } catch (error) {
    console.error("下载文件失败:", error);
    // 添加失败状态的任务
    const failedTask = {
      id: `failed-${Date.now()}`,
      url: downloadInfo.url,
      filename: downloadInfo.filename || downloadInfo.url.split('/').pop() || `download_${Date.now()}`,
      status: 'failed',
      progress: 0,
      size: 0,
      downloaded_size: 0,
      speed: 0,
      eta: 0,
      conversation_id: currentConversationId.value
    };
    downloadTasks.value = [...downloadTasks.value.filter(t => !t.id.startsWith('temp-')), failedTask];
  }
};

// 启动下载状态轮询
const startDownloadStatusPolling = () => {
  if (downloadStatusInterval.value) {
    clearInterval(downloadStatusInterval.value);
  }
  console.log("启动下载状态轮询");
  // 首先立即获取一次
  getDownloadStatus();
  
  // 然后开始定期轮询
  downloadStatusInterval.value = setInterval(async () => {
    if (!currentConversationId.value) {
      stopDownloadStatusPolling();
      return;
    }
    await getDownloadStatus();
  }, 2000); // 每2秒轮询一次
};

const stopDownloadStatusPolling = () => {
  if (downloadStatusInterval.value) {
    console.log("停止下载状态轮询");
    clearInterval(downloadStatusInterval.value);
    downloadStatusInterval.value = null;
  }
};

// 获取下载状态
const getDownloadStatus = async () => {
  try {
    if (!currentConversationId.value) {
      stopDownloadStatusPolling();
      return;
    }
    
    console.log("获取下载状态:", currentConversationId.value);
    const response = await filesApi.getDownloadStatus(null, currentConversationId.value);
    console.log("下载状态原始响应:", response.data);
    
    if (response.data && Array.isArray(response.data)) {
      // 确保每个任务都有所需的字段
      const validatedTasks = response.data.map(task => {
        // 确保返回的数据格式正确
        const validatedTask = {
          id: task.id || `task-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
          filename: task.filename || '未知文件',
          url: task.url || '',
          status: ['downloading', 'completed', 'failed', 'cancelled', 'paused'].includes(task.status) ? task.status : 'downloading',
          progress: typeof task.progress === 'number' ? task.progress : 0,
          size: typeof task.size === 'number' ? task.size : 0,
          downloaded_size: typeof task.downloaded_size === 'number' ? task.downloaded_size : 0,
          speed: typeof task.speed === 'number' ? task.speed : 0,
          eta: typeof task.eta === 'number' ? task.eta : 0
        };
        
        console.log(`任务 ${validatedTask.id} 数据:`, {
          文件名: validatedTask.filename,
          大小: validatedTask.size,
          已下载: validatedTask.downloaded_size,
          进度: validatedTask.progress,
          速度: validatedTask.speed,
          剩余时间: validatedTask.eta
        });
        
        return validatedTask;
      });
      
      // 保留临时任务，同时更新服务器返回的任务
      const tempTasks = downloadTasks.value.filter(task => task.id.startsWith('temp-'));
      
      // 如果服务器返回了任务，说明临时任务应该被移除
      if (validatedTasks.length > 0) {
        downloadTasks.value = validatedTasks;
        console.log("已更新下载任务列表:", downloadTasks.value.length);
      } else if (tempTasks.length > 0) {
        // 只有临时任务，保留它们
        downloadTasks.value = tempTasks;
      } else {
        downloadTasks.value = [];
      }
      
      // 检查是否有活跃下载
      const activeDownloads = downloadTasks.value.some(task => task.status === 'downloading');
      
      // 如果没有活跃下载但轮询仍在进行，停止轮询
      if (!activeDownloads && downloadStatusInterval.value) {
        stopDownloadStatusPolling();
      }
    } else {
      console.warn("下载状态响应格式不正确:", response.data);
    }
  } catch (error) {
    console.error("获取下载状态失败:", error);
    // 错误后不立即停止轮询，给后端一些恢复的时间
  }
};

// 取消下载
const cancelDownload = async (downloadId) => {
  try {
    console.log("取消下载:", downloadId);
    const response = await filesApi.cancelDownload(downloadId);
    console.log("取消下载响应:", response.data);
    
    // 立即更新下载任务状态
    const taskIndex = downloadTasks.value.findIndex(task => task.id === downloadId);
    if (taskIndex !== -1) {
      downloadTasks.value[taskIndex].status = 'cancelled';
    }
    
    // 然后从服务器刷新状态
    await getDownloadStatus();
  } catch (error) {
    console.error("取消下载失败:", error);
  }
};

// 导航到指定路径
const navigateToDirectory = async (path) => {
  currentDirectoryPath.value = path;
  await loadFiles();
};

// 重命名文件
const renameFile = async ({oldPath, newName, isDirectory}) => {
  try {
    if (!currentConversationId.value) return;
    
    console.log("重命名文件:", oldPath, "为:", newName);
    const response = await filesApi.renameFile(oldPath, newName, currentConversationId.value);
    console.log("重命名响应:", response.data);
    
    // 重新加载文件列表
    await loadFiles();
  } catch (error) {
    console.error("重命名文件失败:", error);
    // 显示错误消息
    alert(`重命名失败: ${error.response?.data?.error || error.message}`);
  }
};

// 直接下载文件，接收文件路径
const directDownloadFile = async (filePath) => {
  console.log(`App - directDownloadFile: Initiating download for ${filePath}`);
  try {
    if (!currentConversationId.value) {
      console.error("App - directDownloadFile: No currentConversationId. Aborting download.");
      return;
    }
    
    console.log(`App - directDownloadFile: Attempting to download ${filePath} for conversation ${currentConversationId.value}`);
    
    const tempDownloadId = `direct-dl-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    const filename = filePath.split('/').pop() || '未知文件';

    downloadTasks.value.push({
      id: tempDownloadId,
      filename: filename,
      status: 'downloading',
      progress: 0,
      source: 'direct' 
    });
    console.log(`App - directDownloadFile: Added task ${tempDownloadId} for ${filename} to downloadTasks.`);
    
    const response = await filesApi.directDownload(filePath, currentConversationId.value);
    console.log(`App - directDownloadFile: API response received for ${filePath}. Status: ${response.status}`);
    
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    console.log(`App - directDownloadFile: Download triggered for ${filename}`);
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    const index = downloadTasks.value.findIndex(task => task.id === tempDownloadId);
    if (index !== -1) {
      downloadTasks.value[index].status = 'completed';
      downloadTasks.value[index].progress = 100;
      console.log(`App - directDownloadFile: Task ${tempDownloadId} for ${filename} marked as completed.`);
      setTimeout(() => {
        downloadTasks.value = downloadTasks.value.filter(task => task.id !== tempDownloadId);
        console.log(`App - directDownloadFile: Task ${tempDownloadId} for ${filename} removed from downloadTasks after timeout.`);
      }, 5000); 
    }
  } catch (error) {
    console.error(`App - directDownloadFile: Error downloading ${filePath}:`, error);
    alert(`下载 ${filePath.split('/').pop()} 失败: ${error.response?.data?.error || error.message}`);
    const filename = filePath.split('/').pop() || '未知文件';
    // Try to find the specific task to mark as failed
    let existingTaskIndex = downloadTasks.value.findIndex(task => task.filename === filename && task.status === 'downloading' && task.source === 'direct');
    if (existingTaskIndex !== -1) {
        downloadTasks.value[existingTaskIndex].status = 'failed';
        console.log(`App - directDownloadFile: Task for ${filename} (ID: ${downloadTasks.value[existingTaskIndex].id}) marked as failed.`);
    } else {
        // If no specific downloading task found, add a new failed entry
        const failedTaskId = `direct-dl-failed-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
        downloadTasks.value.push({
            id: failedTaskId,
            filename: filename,
            status: 'failed',
            progress: 0,
            source: 'direct'
        });
        console.log(`App - directDownloadFile: Added new failed task ${failedTaskId} for ${filename} to downloadTasks.`);
    }
  }
};

// 处理批量直接下载文件
const downloadBatchFilesAsZip = async (filePaths) => {
  console.log("App - downloadBatchFilesAsZip: Received request to download files as ZIP:", filePaths);
  if (!currentConversationId.value) {
    console.error("App - downloadBatchFilesAsZip: No currentConversationId. Aborting ZIP download.");
    alert("无法开始批量下载：缺少会话信息。");
    return;
  }
  if (!filePaths || filePaths.length === 0) {
    console.warn("App - downloadBatchFilesAsZip: No file paths provided for ZIP download.");
    alert("请至少选择一个文件进行批量下载。");
    return;
  }

  const tempDownloadId = `batch-zip-dl-${Date.now()}`;
  const zipFilename = `batch_download_${currentConversationId.value}_${new Date().toISOString().slice(0,19).replace(/[-:T]/g,"")}.zip`;

  downloadTasks.value.push({
    id: tempDownloadId,
    filename: zipFilename,
    status: 'downloading',
    progress: 0, // 对于ZIP包，进度可能较难精确跟踪，可以设置为0或一个中间值
    source: 'batch-zip'
  });
  console.log(`App - downloadBatchFilesAsZip: Added task ${tempDownloadId} for ${zipFilename} to downloadTasks.`);

  try {
    console.log(`App - downloadBatchFilesAsZip: Calling API for ZIP download. Files: ${filePaths.length}, ConvID: ${currentConversationId.value}`);
    const response = await filesApi.downloadBatchAsZip(filePaths, currentConversationId.value);
    console.log(`App - downloadBatchFilesAsZip: API response received. Status: ${response.status}`);

    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', zipFilename);
    document.body.appendChild(link);
    link.click();
    console.log(`App - downloadBatchFilesAsZip: ZIP download triggered for ${zipFilename}`);
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    const index = downloadTasks.value.findIndex(task => task.id === tempDownloadId);
    if (index !== -1) {
      downloadTasks.value[index].status = 'completed';
      downloadTasks.value[index].progress = 100;
      console.log(`App - downloadBatchFilesAsZip: Task ${tempDownloadId} for ${zipFilename} marked as completed.`);
      setTimeout(() => {
        downloadTasks.value = downloadTasks.value.filter(task => task.id !== tempDownloadId);
        console.log(`App - downloadBatchFilesAsZip: Task ${tempDownloadId} for ${zipFilename} removed from downloadTasks after timeout.`);
      }, 5000);
    }
  } catch (error) {
    console.error("App - downloadBatchFilesAsZip: Error downloading ZIP:", error);
    alert(`批量下载ZIP失败: ${error.response?.data?.error || error.message || '未知错误'}`);
    const index = downloadTasks.value.findIndex(task => task.id === tempDownloadId);
    if (index !== -1) {
      downloadTasks.value[index].status = 'failed';
      console.log(`App - downloadBatchFilesAsZip: Task ${tempDownloadId} for ${zipFilename} marked as failed.`);
    }
  }
};

// 处理下载请求 - 统一入口
const handleDownload = (param) => {
  console.log("App - handleDownload接收到参数:", param);
  
  // 如果是对象且有url属性，使用downloadFile从URL下载
  if (typeof param === 'object' && param !== null && param.url) {
    downloadFile(param);
  } 
  // 如果是字符串，使用directDownloadFile从本地下载
  else if (typeof param === 'string') {
    directDownloadFile(param);
  }
  else {
    console.error("App - handleDownload: 无效的下载参数", param);
  }
};
</script>

<template>
  <div class="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
    <!-- Backdrop for Mobile Overlays -->
    <div
      v-if="!isLargeScreen && (isMobileNavOpen || isRightSidebarLogicallyOpen)"
      @click="closeMobileSidebars"
      class="fixed inset-0 z-30 bg-black/50 lg:hidden"
    ></div>

    <!-- Left Sidebar -->
    <aside
      :style="
        isLargeScreen
          ? { width: leftSidebarWidth + 'px' }
          : { width: mobileLeftSidebarWidth + 'px' }
      "
      class="flex flex-col overflow-y-auto bg-slate-800 text-slate-100 border-r border-slate-700 transition-transform transform duration-300 ease-in-out z-40 lg:relative lg:translate-x-0 lg:flex-shrink-0 lg:z-auto"
      :class="{
        'fixed inset-y-0 left-0': !isLargeScreen,
        'translate-x-0': !isLargeScreen && isMobileNavOpen,
        '-translate-x-full': !isLargeScreen && !isMobileNavOpen,
        [isLargeScreen
          ? isResizingLeft
            ? 'duration-0'
            : 'transition-all duration-100'
          : '']: true,
        [isLargeScreen
          ? leftSidebarWidth > collapsedLeftSidebarWidth
            ? 'p-4'
            : 'p-3 items-center'
          : 'p-4']: true,
      }"
    >
      <button
        v-if="isLargeScreen"
        @click="toggleSidebar"
        class="mb-6 p-1.5 rounded-md hover:bg-slate-700 self-start text-slate-400 hover:text-slate-200"
        :class="{ 'lg:self-center': !(leftSidebarWidth > collapsedLeftSidebarWidth) }"
        aria-label="Toggle sidebar"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="w-5 h-5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
          />
        </svg>
      </button>
      <!-- Close button for mobile overlay -->
      <button
        v-if="!isLargeScreen && isMobileNavOpen"
        @click="isMobileNavOpen = false"
        class="absolute top-3 right-3 mb-6 p-1.5 rounded-md hover:bg-slate-700 self-start text-slate-400 hover:text-slate-200"
        aria-label="Close sidebar"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="w-5 h-5"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <button
        @click="newConversation"
        :class="[
          'flex items-center font-medium py-2 px-3 rounded-md transition duration-200 ease-in-out focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:ring-opacity-50 mb-6 w-full',
          (isLargeScreen ? leftSidebarWidth > collapsedLeftSidebarWidth : true)
            ? 'bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white shadow-md'
            : 'justify-center bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg p-2.5',
        ]"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="w-5 h-5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 4.5v15m7.5-7.5h-15"
          />
        </svg>
        <span
          v-if="isLargeScreen ? leftSidebarWidth > collapsedLeftSidebarWidth : true"
          class="ml-2 text-sm"
          >New Chat</span
        >
      </button>

      <template
        v-if="isLargeScreen ? leftSidebarWidth > collapsedLeftSidebarWidth : true"
      >
        <h2 class="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2">
          Recent Chats
        </h2>
        <div class="flex-1 overflow-y-auto space-y-1.5 w-full scrollbar-thin">
          <div
            v-for="conv in conversationHistory"
            :key="conv.id"
            @click="selectConversation(conv.id)"
            :class="[
              'py-2.5 px-3 rounded-lg cursor-pointer transition-all duration-150 ease-in-out flex items-center justify-between',
              currentConversationId === conv.id
                ? 'bg-emerald-600 text-white shadow-md'
                : 'hover:bg-slate-700/70 text-slate-300 hover:text-slate-100',
            ]"
            :title="conv.title"
          >
            <div class="flex items-center overflow-hidden">
              <span
                v-if="conv.mode === 'agent'"
                class="text-xs px-1.5 py-0.5 rounded-full bg-blue-600/50 text-blue-100 mr-1.5 flex-shrink-0"
                title="Agent Mode"
                >A</span
              >
              <span
                v-else
                class="text-xs px-1.5 py-0.5 rounded-full bg-emerald-600/50 text-emerald-100 mr-1.5 flex-shrink-0"
                title="Chat Mode"
                >C</span
              >
              <span class="truncate text-sm">{{ conv.title }}</span>
            </div>
            <button
              @click.stop="deleteConversation(conv.id)"
              class="p-1 hover:bg-red-500/80 hover:text-white rounded-full ml-1 flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity"
              aria-label="Delete conversation"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="w-3.5 h-3.5"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12.56 0c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                />
              </svg>
            </button>
          </div>
        </div>
      </template>
      <div
        v-else-if="isLargeScreen && !(leftSidebarWidth > collapsedLeftSidebarWidth)"
        class="flex-1"
      ></div>
      <!-- Spacer for collapsed desktop sidebar -->

      <div class="mt-auto w-full pt-4 border-t border-slate-800/70">
        <button
          :class="[
            'flex items-center py-2 px-3 rounded-md transition duration-200 ease-in-out hover:bg-slate-700 text-slate-400 hover:text-slate-200 w-full',
            !(isLargeScreen ? leftSidebarWidth > collapsedLeftSidebarWidth : true) &&
              'justify-center',
          ]"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="w-5 h-5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.646.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 1.655c.007.379.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.333.183-.583.495-.646.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.645-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.759 6.759 0 010-1.655c-.007-.379-.137-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"
            />
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          <span
            v-if="isLargeScreen ? leftSidebarWidth > collapsedLeftSidebarWidth : true"
            class="ml-2 text-sm"
            >Settings</span
          >
        </button>
      </div>
    </aside>

    <!-- Left Resizer -->
    <div
      v-if="isLargeScreen && leftSidebarWidth > collapsedLeftSidebarWidth"
      @mousedown="startResizeLeft"
      class="w-1 flex-shrink-0 cursor-col-resize bg-slate-700 hover:bg-emerald-600 transition-colors duration-150 z-20 lg:flex hidden"
      title="Resize sidebar"
    ></div>

    <!-- Main Chat Area -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <header
        class="bg-gradient-to-r from-slate-900 to-slate-800 shadow-md px-4 sm:px-5 py-3.5 border-b border-slate-800/80 backdrop-blur-sm sticky top-0 z-10 flex-shrink-0"
      >
        <div
          class="flex items-center justify-between max-w-full sm:max-w-4xl mx-auto w-full"
        >
          <div class="flex items-center space-x-2 sm:space-x-3">
            <!-- Mobile Nav Toggle -->
            <button
              @click="isMobileNavOpen = !isMobileNavOpen"
              class="p-1.5 rounded-md text-slate-400 hover:text-slate-200 lg:hidden"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="w-6 h-6"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12"
                />
              </svg>
            </button>
            <div
              class="h-8 w-8 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-md flex-shrink-0"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4 text-white"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z"
                />
                <path
                  d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z"
                />
              </svg>
            </div>
            <h1 class="text-base sm:text-lg font-semibold text-slate-100 truncate">
              {{
                currentConversationId
                  ? conversationHistory.find((c) => c.id === currentConversationId)?.title
                  : "Chat Interface"
              }}
            </h1>
            <div v-if="currentConversationId" class="ml-1 sm:ml-3">
              <button
                @click="toggleMode"
                :class="[
                  'text-xs px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-lg transition-colors duration-200 font-medium',
                  conversationHistory.find((c) => c.id === currentConversationId)
                    ?.mode === 'agent'
                    ? 'bg-sky-500/80 text-white hover:bg-sky-500'
                    : 'bg-emerald-500/80 text-white hover:bg-emerald-500',
                ]"
              >
                <span class="hidden sm:inline">{{
                  conversationHistory.find((c) => c.id === currentConversationId)
                    ?.mode === "agent"
                    ? "Agent Mode"
                    : "Chat Mode"
                }}</span>
                <span class="sm:hidden">{{
                  conversationHistory.find((c) => c.id === currentConversationId)
                    ?.mode === "agent"
                    ? "A"
                    : "C"
                }}</span>
              </button>
            </div>
          </div>
          <button
            @click="toggleFileSidebar"
            class="p-1.5 rounded-md hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM2 11a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4z"
              />
            </svg>
          </button>
        </div>
      </header>

      <div
        ref="messageDisplayArea"
        class="flex-1 overflow-y-auto py-6 px-4 sm:px-6 bg-gradient-to-b from-slate-950 to-slate-900 scrollbar-thin"
      >
        <!-- 模式指示横幅 -->
        <div
          v-if="currentConversationId"
          :class="[
            'py-2 px-4 mb-6 text-center text-sm font-medium rounded-lg border animate-fade-in max-w-md mx-auto',
            conversationHistory.find((c) => c.id === currentConversationId)?.mode === 'agent'
              ? 'bg-blue-600/30 text-blue-100 border-blue-700/50'
              : 'bg-emerald-600/30 text-emerald-100 border-emerald-700/50',
          ]"
        >
          <span v-if="conversationHistory.find((c) => c.id === currentConversationId)?.mode === 'agent'">
            <span class="font-bold">Agent Mode</span> - Describe your analysis goal, I'll create workflows
          </span>
          <span v-else>
            <span class="font-bold">Chat Mode</span> - Ask questions to get professional answers
          </span>
        </div>
        
        <div
          v-if="messages.length === 1 && messages[0].isWelcome"
          class="flex flex-col items-center justify-center h-full"
        >
          <div
            class="text-center w-full max-w-2xl mx-auto bg-slate-800/60 rounded-2xl p-6 sm:p-10 shadow-xl backdrop-blur-sm"
          >
            <div class="mb-6">
              <div
                class="mx-auto w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-full flex items-center justify-center shadow-lg shadow-emerald-600/20"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-8 w-8 sm:h-10 sm:w-10 text-white"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fill-rule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9a1 1 0 100-2 1 1 0 000 2zm7-1a1 1 0 11-2 0 1 1 0 012 0zm-.464 5.535a1 1 0 10-1.415-1.414 3 3 0 01-4.242 0 1 1 0 00-1.415 1.414 5 5 0 007.072 0z"
                    clip-rule="evenodd"
                  />
                </svg>
              </div>
            </div>
            <h2
              class="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-emerald-400 via-green-400 to-teal-400 bg-clip-text text-transparent mb-5 animate-fade-in"
            >
              Welcome!
            </h2>
            <p class="text-slate-400 text-base sm:text-lg max-w-lg mx-auto mb-8 sm:mb-10">
              I am your AI assistant for bioinformatics workflows. Describe your analysis
              goal, and I can help you design, execute, and monitor automated processes.
            </p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 max-w-xl mx-auto">
              <div
                class="bg-slate-800/70 hover:bg-slate-750/90 p-4 sm:p-6 rounded-xl cursor-pointer border border-slate-700 hover:border-emerald-500/70 transition-all duration-300 hover:shadow-lg group"
              >
                <div class="flex items-start mb-2">
                  <span
                    class="bg-emerald-500/20 p-2.5 rounded-lg mr-3 group-hover:bg-emerald-500/30 transition-all duration-300"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-5 w-5 text-emerald-500"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        d="M10 3.5a1.5 1.5 0 013 0V4a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-.5a1.5 1.5 0 000 3h.5a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-.5a1.5 1.5 0 00-3 0v.5a1 1 0 01-1 1H6a1 1 0 01-1-1v-3a1 1 0 00-1-1h-.5a1.5 1.5 0 010-3H4a1 1 0 001-1V6a1 1 0 011-1h3a1 1 0 001-1v-.5z"
                      />
                    </svg>
                  </span>
                  <p
                    class="font-medium text-slate-200 group-hover:text-white transition-colors"
                  >
                    Design a new bioinformatics workflow
                  </p>
                </div>
                <p class="text-slate-400 text-sm pl-10">
                  Start by defining your analysis steps and data inputs.
                </p>
              </div>
              <div
                class="bg-slate-800/70 hover:bg-slate-750/90 p-4 sm:p-6 rounded-xl cursor-pointer border border-slate-700 hover:border-emerald-500/70 transition-all duration-300 hover:shadow-lg group"
              >
                <div class="flex items-start mb-2">
                  <span
                    class="bg-emerald-500/20 p-2.5 rounded-lg mr-3 group-hover:bg-emerald-500/30 transition-all duration-300"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-5 w-5 text-emerald-500"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 12V4h8v12H6z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </span>
                  <p
                    class="font-medium text-slate-200 group-hover:text-white transition-colors"
                  >
                    Analyze genomic data for variants
                  </p>
                </div>
                <p class="text-slate-400 text-sm pl-10">
                  Upload your VCF files and specify analysis parameters.
                </p>
              </div>
            </div>
            <div
              class="mt-10 sm:mt-12 text-slate-500 flex items-center justify-center text-sm"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 mr-2 animate-bounce"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M10 3a1 1 0 011 1v10.586l3.293-3.293a1 1 0 011.414 1.414l-5 5a1 1 0 01-1.414 0l-5-5a1 1 0 111.414-1.414L9 14.586V4a1 1 0 011-1z"
                  clip-rule="evenodd"
                /></svg
              ><span>Enter your question below or choose a suggestion</span>
            </div>
          </div>
        </div>
        <div
          v-for="message in messages.filter((m) => !m.isWelcome)"
          :key="message.id"
          :class="[
            'flex mb-6',
            message.sender === 'user' ? 'justify-end' : 
            message.sender === 'system' ? 'justify-center' : 'justify-start',
          ]"
        >
          <div
            :class="[
              message.sender === 'user'
                ? 'max-w-md lg:max-w-lg px-4 py-3 rounded-xl shadow-md bg-gradient-to-br from-emerald-500 to-emerald-600 text-white'
                : message.sender === 'system'
                ? 'max-w-md px-4 py-2 rounded-lg bg-slate-800/80 text-slate-300 border border-slate-700/50 text-center text-sm animate-fade-in'
                : 'max-w-md lg:max-w-lg px-4 py-3 rounded-xl shadow-md bg-slate-700 text-slate-100 border border-slate-600/50',
            ]"
          >
            <p class="whitespace-pre-wrap text-sm leading-relaxed">{{ message.text }}</p>
          </div>
        </div>
      </div>

      <div
        class="bg-slate-900 p-3 sm:p-4 shadow-lg border-t border-slate-800/80 flex-shrink-0"
      >
        <div class="max-w-4xl mx-auto">
          <div
            class="relative flex items-center bg-slate-800 rounded-xl border border-slate-700 focus-within:border-emerald-500/80 focus-within:ring-1 focus-within:ring-emerald-500/50 transition-all duration-200 shadow-sm"
          >
            <div class="relative" ref="modeDropdownRef">
              <button
                @click.stop="toggleModeDropdown"
                class="flex items-center h-full px-2.5 sm:px-3.5 py-3.5 text-slate-400 hover:text-slate-200 border-r border-slate-700/50"
              >
                <span class="hidden sm:inline">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-5 w-5"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M18 10c0 4.418-3.582 8-8 8s-8-3.582-8-8 3.582-8 8-8 8 3.582 8 8zm-9-3a1 1 0 11-2 0 1 1 0 012 0zm4 0a1 1 0 11-2 0 1 1 0 012 0zm-2 4a1 1 0 01-1-1V9a1 1 0 112 0v1a1 1 0 01-1 1z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </span>
                <span class="sm:hidden">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-5 w-5"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </span>
                <span class="ml-1.5 text-xs font-medium">
                  {{
                    conversationHistory.find((c) => c.id === currentConversationId)
                      ?.mode === "agent"
                      ? "Agent"
                      : "Chat"
                  }}
                </span>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-3 w-3 ml-1"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fill-rule="evenodd"
                    d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                    clip-rule="evenodd"
                  />
                </svg>
              </button>
              
              <!-- 模式切换下拉菜单 -->
              <div 
                v-if="showModeDropdown"
                class="absolute bottom-full left-0 mb-1 w-48 bg-slate-800 border border-slate-700 rounded-md shadow-lg z-50 overflow-hidden"
              >
                <div class="py-1">
                  <button
                    v-for="mode in inputModes"
                    :key="mode.id"
                    @click="handleModeChange(mode.id)"
                    class="w-full flex items-center px-4 py-2 text-sm transition-colors hover:bg-slate-700"
                    :class="[
                      conversationHistory.find((c) => c.id === currentConversationId)?.mode === mode.id 
                        ? 'bg-emerald-600/20 text-white' 
                        : 'text-slate-300 hover:text-white'
                    ]"
                  >
                    <span v-if="mode.id === 'chat'" class="mr-2 text-emerald-500">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd" />
                      </svg>
                    </span>
                    <span v-else class="mr-2 text-blue-500">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
                      </svg>
                    </span>
                    <span>{{ mode.label }}</span>
                  </button>
                </div>
              </div>
            </div>
            <input
              type="text"
              v-model="newMessage"
              @keyup.enter="sendMessage"
              :placeholder="
                conversationHistory.find((c) => c.id === currentConversationId)?.mode ===
                'agent'
                  ? 'Describe your analysis goal...'
                  : 'Enter your question...'
              "
              class="flex-1 py-3 px-3 sm:px-4 bg-transparent border-0 focus:ring-0 outline-none placeholder-slate-500 text-slate-200 text-sm"
            />
            <button
              @click="sendMessage"
              class="bg-gradient-to-r from-emerald-500 to-green-500 hover:from-emerald-600 hover:to-green-600 text-white font-semibold py-3 px-3 sm:px-4 rounded-lg transition-all duration-200 ease-in-out shadow-md hover:shadow-lg transform hover:scale-105 flex items-center space-x-1 sm:space-x-2 mr-1 sm:mr-2 ml-1"
            >
              <span class="text-sm sm:text-base">Send</span>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-3.5 w-3.5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- Right Resizer -->
    <div
      v-if="isLargeScreen && isRightSidebarLogicallyOpen"
      @mousedown="startResizeRight"
      class="w-1 flex-shrink-0 cursor-col-resize bg-slate-700 hover:bg-emerald-600 transition-colors duration-150 z-20 lg:flex hidden"
      title="Resize file manager"
    ></div>

    <!-- Right Sidebar - Project Files -->
    <Sidebar
      v-model:showSidebar="isRightSidebarLogicallyOpen"
      v-model:sidebarWidth="rightSidebarWidth"
      :conversationId="currentConversationId"
      :projectFiles="projectFiles"
      :currentPath="currentDirectoryPath"
      :downloadTasks="downloadTasks"
      @file-search="searchFiles"
      @file-select="openFileContent"
      @delete-file="deleteFileOrFolder"
      @refresh-files="loadFiles"
      @create-file="openCreateFileModal"
      @create-directory="openCreateFileModal(true)"
      @upload-files="uploadFile"
      @view-file="openFileContent"
      @download-file="handleDownload"
      @rename-file="renameFile"
      @navigate="navigateToDirectory"
      @get-download-status="getDownloadStatus"
      @cancel-download="cancelDownload"
      @pause-download="pauseDownload"
      @resume-download="resumeDownload"
      @clear-completed="clearCompletedDownloads"
      @download-multiple-files="downloadBatchFilesAsZip"
      ref="sidebarRef"
    />

    <!-- Modals -->
    <div
      v-if="showCreateFileModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
    >
      <div class="bg-slate-800 rounded-lg p-6 w-full max-w-md sm:mx-auto">
        <h3 class="text-xl font-medium text-white mb-4">
          {{ selectedFile === "folder" ? "Create New Folder" : "Create New File" }}
        </h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Name</label>
            <input
              v-model="fileNameToCreate"
              type="text"
              class="w-full py-2 px-3 bg-slate-700 border border-slate-600 rounded-lg text-white"
              :placeholder="selectedFile === 'folder' ? 'Folder name' : 'File name'"
            />
          </div>
          <div v-if="selectedFile !== 'folder'">
            <label class="block text-sm font-medium text-slate-300 mb-1">Content</label>
            <textarea
              v-model="fileContentToCreate"
              rows="5"
              class="w-full py-2 px-3 bg-slate-700 border border-slate-600 rounded-lg text-white"
              placeholder="File content..."
            />
          </div>
          <div class="flex justify-end space-x-3 mt-6">
            <button
              @click="showCreateFileModal = false"
              class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white"
            >
              Cancel
            </button>
            <button
              @click="createFileOrFolder"
              class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white"
            >
              Create
            </button>
          </div>
        </div>
      </div>
    </div>
    <div
      v-if="showFileContentModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
    >
      <div
        class="bg-slate-800 rounded-lg p-6 w-full max-w-4xl sm:mx-auto max-h-[80vh] flex flex-col"
      >
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-xl font-medium text-white">{{ currentFileName }}</h3>
          <button
            @click="showFileContentModal = false"
            class="text-slate-400 hover:text-white"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
        <div class="flex-1 overflow-y-auto mb-4">
          <textarea
            v-model="currentFileContent"
            class="w-full h-full min-h-[300px] py-2 px-3 bg-slate-700 border border-slate-600 rounded-md text-white font-mono text-sm"
          />
        </div>
        <div class="flex justify-end space-x-3">
          <button
            @click="showFileContentModal = false"
            class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-md text-white"
          >
            Cancel
          </button>
          <button
            @click="saveFileContent()"
            class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-md text-white"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
.scrollbar-thin::-webkit-scrollbar {
  width: 6px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.1);
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(51, 65, 85, 0.5);
  border-radius: 20px;
}
.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: rgba(71, 85, 105, 0.7);
}

.shadow-up {
  box-shadow: 0 -4px 6px -1px rgba(0, 0, 0, 0.1), 0 -2px 4px -1px rgba(0, 0, 0, 0.06);
}
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.animate-fade-in {
  animation: fade-in 0.6s ease-out;
}
.mode-badge {
  font-size: 0.65rem;
  padding: 0.15rem 0.4rem;
  border-radius: 9999px;
  font-weight: 500;
  letter-spacing: 0.025em;
}
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
