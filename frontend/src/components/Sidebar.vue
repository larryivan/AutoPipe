<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import FileManager from './FileManager.vue';
import Terminal from './Terminal.vue';
import SystemMonitor from './SystemMonitor.vue';
import Downloader from './Downloader.vue'; // 引入新的下载器组件

const props = defineProps({
  conversationId: {
    type: String,
    required: true
  },
  showSidebar: {
    type: Boolean,
    default: true
  },
  sidebarWidth: {
    type: Number,
    default: 350
  },
  projectFiles: {
    type: Array,
    default: () => []
  },
  downloadTasks: { // 从 App.vue 传入的下载任务
    type: Array,
    default: () => []
  },
  currentPath: {
    type: String,
    default: ''
  }
});

const emit = defineEmits([
  'update:showSidebar', 
  'update:sidebarWidth', 
  'file-search', 
  'file-select', 
  'delete-file', 
  'refresh-files', 
  'create-file', 
  'create-directory', 
  'upload-files', 
  'view-file',
  'download-file', 
  'get-download-status',
  'cancel-download',
  'rename-file',
  'navigate',
  'download-multiple-files', // 添加批量下载事件
  'pause-download', // 添加暂停下载事件
  'resume-download', // 添加恢复下载事件
  'clear-completed' // 添加清除已完成下载事件
]);

// 当前激活的功能
const activeFeature = ref('files'); // 'files', 'monitor', 'terminal', 'downloader'

// 子组件显示状态
const showFileManager = ref(true);
const showMonitor = ref(false);
const showTerminal = ref(false);
const showDownloader = ref(false); // 新增下载器显示状态

// 文件管理器状态
const fileSearchQuery = ref('');
const selectedFile = ref(null);

// 拖动调整宽度相关变量
const isResizing = ref(false);
const startX = ref(0);
const startWidth = ref(props.sidebarWidth);
const sidebarRef = ref(null);
const resizerId = 'sidebar-resizer';

// 切换侧边栏显示
const toggleSidebar = () => {
  emit('update:showSidebar', !props.showSidebar);
};

// 切换功能
const switchFeature = (feature) => {
  activeFeature.value = feature;
  
  // 更新子组件显示状态
  showFileManager.value = feature === 'files';
  showMonitor.value = feature === 'monitor';
  showTerminal.value = feature === 'terminal';
  showDownloader.value = feature === 'downloader'; // 更新下载器显示
  if (feature === 'downloader') {
    emit('get-download-status'); // 切换到下载器时，刷新一下状态
  }
};

// 监听激活功能变化
watch(activeFeature, (newFeature) => {
  switchFeature(newFeature);
});

// 监听侧边栏显示状态
watch(() => props.showSidebar, (isVisible) => {
  if (!isVisible) {
    // 隐藏所有子组件
    showFileManager.value = false;
    showMonitor.value = false;
    showTerminal.value = false;
    showDownloader.value = false;
  } else {
    // 显示当前选中的子组件
    switchFeature(activeFeature.value);
  }
});

// 监听projectFiles变化
watch(() => props.projectFiles, (newFiles) => {
  if (newFiles && Array.isArray(newFiles)) {
    console.log("Sidebar received new files:", newFiles);
  }
}, { deep: true });

// 拖动调整宽度函数
const startResize = (e) => {
  isResizing.value = true;
  startX.value = e.clientX || e.touches[0].clientX;
  startWidth.value = props.sidebarWidth;
  
  // 添加鼠标事件监听
  document.addEventListener('mousemove', resize, { passive: true });
  document.addEventListener('mouseup', stopResize);
  document.addEventListener('touchmove', resize, { passive: true });
  document.addEventListener('touchend', stopResize);
  
  // 添加调整时的样式
  document.body.style.cursor = 'ew-resize';
  document.body.style.userSelect = 'none';
  
  // 添加激活样式类
  if (sidebarRef.value) {
    sidebarRef.value.classList.add('resizing');
  }
  
  // 防止文本选择
  e.preventDefault();
};

let rafId = null;

const resize = (e) => {
  if (!isResizing.value) return;
  
  // 使用requestAnimationFrame优化性能
  if (rafId) {
    cancelAnimationFrame(rafId);
  }
  
  rafId = requestAnimationFrame(() => {
    const clientX = e.clientX || (e.touches && e.touches[0].clientX);
    if (!clientX) return;
    
    // 计算宽度差值（从右往左拖动）
    const deltaX = clientX - startX.value;
    const newWidth = Math.max(250, Math.min(800, startWidth.value - deltaX));
    
    // 更新侧边栏宽度
    emit('update:sidebarWidth', newWidth);
  });
};

const stopResize = () => {
  isResizing.value = false;
  
  // 取消任何挂起的动画帧
  if (rafId) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
  
  // 移除事件监听
  document.removeEventListener('mousemove', resize);
  document.removeEventListener('mouseup', stopResize);
  document.removeEventListener('touchmove', resize);
  document.removeEventListener('touchend', stopResize);
  
  // 恢复默认样式
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
  
  // 移除激活样式类
  if (sidebarRef.value) {
    sidebarRef.value.classList.remove('resizing');
  }
};

// 生命周期钩子
onMounted(() => {
  // 创建调整器DOM元素
  const resizer = document.createElement('div');
  resizer.id = resizerId;
  resizer.className = 'sidebar-resizer';
  
  // 添加调整器到DOM
  if (sidebarRef.value) {
    sidebarRef.value.appendChild(resizer);
    
    // 添加事件监听
    resizer.addEventListener('mousedown', startResize);
    resizer.addEventListener('touchstart', startResize, { passive: false });
  }
});

onUnmounted(() => {
  // 清理调整器元素
  const resizer = document.getElementById(resizerId);
  if (resizer) {
    resizer.removeEventListener('mousedown', startResize);
    resizer.removeEventListener('touchstart', startResize);
  }
});

// 文件管理函数
const onFileSearch = (query) => {
  fileSearchQuery.value = query;
  emit('file-search', query);
};

const onFileSelect = (file) => {
  selectedFile.value = file;
  emit('file-select', file);
};

const onDeleteFile = (filePath) => {
  emit('delete-file', filePath);
};

const onRefreshFiles = () => {
  emit('refresh-files');
};

const onCreateFile = () => {
  emit('create-file');
};

const onCreateDirectory = () => {
  console.log("Sidebar - onCreateDirectory被调用");
  emit('create-directory');
};

const onUploadFiles = (files, progressCallback) => {
  // 将进度回调传递给父组件
  emit('upload-files', files, progressCallback);
};

const onViewFile = (filePath) => {
  console.log("Sidebar - onViewFile被调用, 路径:", filePath);
  emit('view-file', filePath);
};

// 处理文件下载请求
const onDownloadFile = (filePath) => {
  console.log("Sidebar - onDownloadFile传递文件路径:", filePath);
  emit('download-file', filePath);
};

// 下载URL事件处理 (来自Downloader组件)
const onStartDownload = (downloadInfo) => {
  console.log("Sidebar - onStartDownload传递下载信息:", downloadInfo);
  // 确保传递正确的格式 { url, filename }
  emit('download-file', downloadInfo);
};

// 处理文件重命名请求
const onRenameFile = (data) => {
  emit('rename-file', data);
};

// 处理路径导航请求
const onNavigate = (path) => {
  emit('navigate', path);
};

// 设置下载任务列表
const setDownloadTasks = (tasks) => {
  console.log("Sidebar setDownloadTasks called, but tasks are now passed via props.", tasks);
};

// 处理批量文件下载请求
const onDownloadMultipleFiles = (filePaths) => {
  console.log("Sidebar - onDownloadMultipleFiles被调用, 路径:", filePaths);
  emit('download-multiple-files', filePaths);
};

// 确保clearCompleted事件在Downloader组件中能正确触发
const onClearCompleted = () => {
  console.log("Sidebar - 清除已完成下载");
  emit('clear-completed');
};
</script>

<template>
  <div
    ref="sidebarRef"
    class="sidebar"
    :class="{
      'translate-x-0': showSidebar,
      'translate-x-full absolute right-0 top-0 bottom-0 lg:relative lg:translate-x-0': !showSidebar,
      'opacity-0 invisible': !showSidebar,
      'fixed right-0 top-0 bottom-0 z-50 lg:relative lg:z-auto': showSidebar
    }"
    :style="{
      width: `${sidebarWidth}px`,
      height: '100vh'
    }"
  >
    <!-- 侧边栏标题栏 -->
    <div class="sidebar-header">
      <div class="flex justify-between items-center">
        <div class="feature-tabs">
          <button
            @click="switchFeature('files')"
            class="feature-tab"
            :class="{ 'active': activeFeature === 'files' }"
            title="文件管理"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="tab-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M2 6a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1H8a3 3 0 00-3 3v1.5a1.5 1.5 0 01-3 0V6z" clip-rule="evenodd" />
              <path d="M6 12a2 2 0 012-2h8a2 2 0 012 2v2a2 2 0 01-2 2H2h2a2 2 0 002-2v-2z" />
            </svg>
            <span class="tab-text">文件</span>
          </button>
          <button
            @click="switchFeature('downloader')"
            class="feature-tab"
            :class="{ 'active': activeFeature === 'downloader' }"
            title="下载器"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="tab-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
            <span class="tab-text">下载</span>
          </button>
          <button
            @click="switchFeature('monitor')"
            class="feature-tab"
            :class="{ 'active': activeFeature === 'monitor' }"
            title="性能监控"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="tab-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            <span class="tab-text">监控</span>
          </button>
          <button
            @click="switchFeature('terminal')"
            class="feature-tab"
            :class="{ 'active': activeFeature === 'terminal' }"
            title="终端"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="tab-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M2 5a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V5zm3.293 1.293a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 01-1.414-1.414L7.586 10 5.293 7.707a1 1 0 010-1.414zM11 12a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd" />
            </svg>
            <span class="tab-text">终端</span>
          </button>
        </div>
        <button
          @click="toggleSidebar"
          class="toggle-sidebar-btn lg:hidden"
          title="关闭侧边栏"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
    
    <!-- 侧边栏内容区域 -->
    <div class="sidebar-content">
      <!-- 文件管理器 -->
      <div v-show="activeFeature === 'files'" class="component-wrapper" data-feature="files">
        <FileManager
          v-model:showFileManager="showFileManager"
          :files="props.projectFiles"
          :currentPath="props.currentPath"
          :downloadTasks="props.downloadTasks" 
          @search-files="onFileSearch"
          @select-file="onFileSelect"
          @delete-file="onDeleteFile"
          @refresh-files="onRefreshFiles"
          @create-file="onCreateFile"
          @create-directory="onCreateDirectory"
          @upload-files="onUploadFiles"
          @view-file="onViewFile"
          @download-file="onDownloadFile"
          @rename-file="onRenameFile"
          @navigate="onNavigate"
          @download-multiple-files="onDownloadMultipleFiles"
        />
      </div>
      
      <!-- 下载器 -->
      <div v-show="activeFeature === 'downloader'" class="component-wrapper" data-feature="downloader">
        <Downloader 
            :downloadTasks="props.downloadTasks"
            @start-download="onStartDownload"
            @cancel-download="(id) => emit('cancel-download', id)"
            @refresh-downloads="() => emit('get-download-status')"
            @pause-download="(id) => emit('pause-download', id)"
            @resume-download="(id) => emit('resume-download', id)"
            @clear-completed="onClearCompleted"
        />
      </div>
      
      <!-- 性能监控 -->
      <div v-show="activeFeature === 'monitor'" class="component-wrapper" data-feature="monitor">
        <SystemMonitor
          v-model:showMonitor="showMonitor"
        />
      </div>
      
      <!-- 终端 -->
      <div v-show="activeFeature === 'terminal'" class="component-wrapper" data-feature="terminal">
        <Terminal
          v-model:showTerminal="showTerminal"
          :conversationId="props.conversationId"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.sidebar {
  background-color: rgba(17, 24, 39, 0.9);
  border-left: 1px solid rgba(55, 65, 81, 0.6);
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.25);
  transition: width 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar.resizing {
  transition: none !important;
  will-change: width;
}

/* 侧边栏头部 */
.sidebar-header {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(55, 65, 81, 0.6);
  background-color: rgba(30, 41, 59, 0.5);
  flex-shrink: 0;
}

/* 功能标签页 */
.feature-tabs {
  display: flex;
  gap: 0.75rem;
}

.feature-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem;
  border-radius: 0.375rem;
  color: rgb(156, 163, 175);
  transition: all 0.25s ease-out;
  background-color: transparent;
  border: 1px solid transparent;
}

.feature-tab:hover {
  color: rgb(229, 231, 235);
  background-color: rgba(55, 65, 81, 0.3);
}

.feature-tab.active {
  color: rgb(56, 189, 248);
  background-color: rgba(56, 189, 248, 0.1);
  border-color: rgba(56, 189, 248, 0.3);
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
}

.tab-icon {
  width: 1.25rem;
  height: 1.25rem;
  margin-bottom: 0.125rem;
}

.tab-text {
  font-size: 0.6875rem;
  font-weight: 500;
}

/* 关闭按钮 */
.toggle-sidebar-btn {
  padding: 0.375rem;
  background-color: rgba(55, 65, 81, 0.5);
  border-radius: 0.375rem;
  color: rgb(156, 163, 175);
  transition: all 0.2s ease;
}

.toggle-sidebar-btn:hover {
  background-color: rgba(75, 85, 99, 0.7);
  color: rgb(229, 231, 235);
}

/* 侧边栏内容区域 */
.sidebar-content {
  flex-grow: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

.sidebar-content::-webkit-scrollbar {
  width: 4px;
}

.sidebar-content::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background: rgba(75, 85, 99, 0.5);
  border-radius: 0.25rem;
}

.sidebar-content::-webkit-scrollbar-thumb:hover {
  background: rgba(107, 114, 128, 0.7);
}

/* 组件包装器 */
.component-wrapper {
  flex-grow: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 侧边栏宽度调整器样式 */
.sidebar-resizer {
  position: absolute;
  left: -5px; 
  top: 0;
  width: 10px; 
  height: 100%;
  background-color: transparent;
  cursor: ew-resize;
  z-index: 100;
  touch-action: none;
  transition: background-color 0.2s ease;
}

.sidebar-resizer:hover,
.sidebar.resizing .sidebar-resizer {
  background-color: rgba(56, 189, 248, 0.2);
}
</style> 