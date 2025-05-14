<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';

interface DownloadTask {
  id: string;
  filename: string;
  url: string;
  status: 'downloading' | 'completed' | 'failed' | 'cancelled' | 'paused';
  progress: number;
  size?: number; // 文件大小（字节）
  downloaded_size?: number; // 已下载大小（字节）
  speed?: number; // 下载速度（字节/秒）
  eta?: number; // 预计剩余时间（秒）
  start_time?: number; // 开始时间（毫秒时间戳）
}

const props = defineProps({
  downloadTasks: {
    type: Array as () => DownloadTask[],
    default: () => []
  }
});

const emit = defineEmits([
  'start-download',
  'cancel-download',
  'refresh-downloads',
  'pause-download',
  'resume-download',
  'clear-completed'
]);

const downloadUrl = ref('');
const downloadFileName = ref('');
const localError = ref<string | null>(null);

const localDownloadTasks = ref<DownloadTask[]>([]);

watch(() => props.downloadTasks, (newTasks) => {
  if (newTasks && Array.isArray(newTasks)) {
    localDownloadTasks.value = [...newTasks];
  } else {
    // 如果 newTasks 是 null, undefined, 或者不是数组
    // 清空本地列表以避免显示陈旧或无效数据
    localDownloadTasks.value = [];
  }
}, { deep: true, immediate: true });

onMounted(() => {
  // 组件挂载时立即获取一次下载状态
  emit('refresh-downloads');
});

const handleStartDownload = () => {
  if (!downloadUrl.value.trim()) {
    localError.value = "请输入有效的下载URL";
    setTimeout(() => { localError.value = null; }, 3000);
    return;
  }
  emit('start-download', { url: downloadUrl.value, filename: downloadFileName.value || null });
  downloadUrl.value = '';
  downloadFileName.value = '';
  setTimeout(() => emit('refresh-downloads'), 500); // Refresh after a short delay
};

const handleCancelDownload = (taskId: string) => {
  emit('cancel-download', taskId);
  setTimeout(() => emit('refresh-downloads'), 500);
};

const handleRefreshDownloads = () => {
  console.log("Downloader - 手动刷新下载列表");
  emit('refresh-downloads');
};

const handleClearCompleted = () => {
  emit('clear-completed');
  setTimeout(() => emit('refresh-downloads'), 500);
};

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    downloading: '下载中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    paused: '已暂停'
  };
  return map[status] || status;
};

const getStatusColorClass = (status: string) => {
  const map: Record<string, string> = {
    downloading: 'text-blue-400 bg-blue-500/10',
    completed: 'text-green-400 bg-green-500/10',
    failed: 'text-red-400 bg-red-500/10',
    cancelled: 'text-yellow-400 bg-yellow-500/10',
    paused: 'text-gray-400 bg-gray-500/10'
  };
  return map[status] || 'text-slate-400 bg-slate-500/10';
};

const getProgressBarClass = (status: string) => {
  const map: Record<string, string> = {
    downloading: 'bg-blue-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    cancelled: 'bg-yellow-500',
    paused: 'bg-gray-500'
  };
  return map[status] || 'bg-slate-500';
};

// 格式化文件大小
const formatFileSize = (bytes?: number): string => {
  if (bytes === undefined || bytes === null || bytes <= 0) return '等待中';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
};

// 格式化下载速度
const formatSpeed = (bytesPerSecond?: number): string => {
  if (bytesPerSecond === undefined || bytesPerSecond === null || bytesPerSecond <= 0) return '计算中';
  
  const k = 1024;
  const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
  const i = Math.floor(Math.log(bytesPerSecond) / Math.log(k));
  
  return (bytesPerSecond / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
};

// 格式化预计剩余时间
const formatETA = (seconds?: number): string => {
  if (seconds === undefined || seconds === null || seconds <= 0) return '计算中';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}小时 ${minutes}分钟`;
  } else if (minutes > 0) {
    return `${minutes}分钟 ${secs}秒`;
  } else {
    return `${secs}秒`;
  }
};

// 计算下载百分比
const calculateProgress = (task: DownloadTask): number => {
  if (task.progress !== undefined && task.progress > 0) return task.progress;
  
  if (task.size && task.size > 0 && task.downloaded_size && task.downloaded_size > 0) {
    return Math.min(Math.max(1, Math.floor((task.downloaded_size / task.size) * 100)), 99);
  }
  
  // 确保至少显示1%进度
  return 1;
};

</script>

<template>
  <div class="downloader-container p-1 text-sm text-slate-300 flex flex-col h-full">
    <h2 class="text-lg font-semibold text-slate-100 mb-3 p-2 border-b border-slate-700">下载管理器</h2>

    <!-- 下载表单 -->
    <div class="download-form mb-4 p-3 bg-slate-800/50 rounded-lg shadow">
      <div class="grid grid-cols-1 gap-3">
        <div>
          <label for="download-url" class="block text-xs font-medium text-slate-400 mb-1">下载链接 (URL)</label>
          <input 
            id="download-url"
            type="text" 
            v-model="downloadUrl" 
            placeholder="https://example.com/file.zip"
            class="w-full p-2 bg-slate-700 border border-slate-600 rounded-md focus:ring-sky-500 focus:border-sky-500 text-slate-200 text-xs"
          />
        </div>
        <div>
          <label for="download-filename" class="block text-xs font-medium text-slate-400 mb-1">文件名 (可选)</label>
          <input 
            id="download-filename"
            type="text" 
            v-model="downloadFileName" 
            placeholder="自定义文件名.zip"
            class="w-full p-2 bg-slate-700 border border-slate-600 rounded-md focus:ring-sky-500 focus:border-sky-500 text-slate-200 text-xs"
          />
        </div>
      </div>
      <button 
        @click="handleStartDownload" 
        class="mt-3 w-full flex items-center justify-center px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-md text-xs font-medium transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-800"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 mr-1.5" viewBox="0 0 20 20" fill="currentColor">
          <path d="M13 8V2H7v6H2l8 8 8-8h-5zM0 18h20v2H0v-2z"/>
        </svg>
        开始下载
      </button>
      <div v-if="localError" class="mt-2 text-xs text-red-400 p-2 bg-red-500/10 rounded-md">{{ localError }}</div>
    </div>

    <!-- 操作按钮 -->
    <div class="download-actions mb-3 flex justify-between items-center p-2 border-t border-b border-slate-700">
      <button 
        @click="handleRefreshDownloads" 
        class="flex items-center px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-slate-100 rounded-md text-xs transition-colors duration-150"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 00-15.357-2m15.357 2H15" />
        </svg>
        刷新列表
      </button>
      <button 
        @click="handleClearCompleted" 
        class="flex items-center px-3 py-1.5 bg-red-700/40 hover:bg-red-600/40 text-red-300 hover:text-red-100 rounded-md text-xs transition-colors duration-150"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
        清除已完成
      </button>
    </div>

    <!-- 下载任务列表 -->
    <div class="download-list flex-grow overflow-y-auto pr-1 space-y-2">
      <div v-if="!localDownloadTasks || localDownloadTasks.length === 0" class="text-center py-10">
        <svg xmlns="http://www.w3.org/2000/svg" class="mx-auto h-12 w-12 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p class="mt-2 text-xs text-slate-500">没有活动的下载任务</p>
      </div>

      <div 
        v-for="task in localDownloadTasks" 
        :key="task.id" 
        class="download-item p-3 bg-slate-800/60 rounded-lg shadow-sm border border-slate-700/50 hover:border-slate-600 transition-all duration-150"
      >
        <div class="flex items-center justify-between mb-2">
          <div class="font-medium text-slate-200 text-xs truncate pr-2 flex-1" :title="task.filename">
            {{ task.filename }}
          </div>
          <div 
            class="px-1.5 py-0.5 text-xxs font-semibold rounded-full"
            :class="getStatusColorClass(task.status)"
          >
            {{ getStatusText(task.status) }}
          </div>
        </div>
        
        <div class="text-xxs text-slate-400 truncate mb-1.5" :title="task.url">{{ task.url || '本地文件下载' }}</div>

        <!-- 文件信息 -->
        <div class="file-info grid grid-cols-3 gap-2 mb-2 text-xxs">
          <div class="bg-slate-750/40 p-1.5 rounded">
            <div class="font-medium text-slate-500 mb-0.5">文件大小</div>
            <div class="text-slate-300">{{ formatFileSize(task.size) }}</div>
          </div>
          <div class="bg-slate-750/40 p-1.5 rounded">
            <div class="font-medium text-slate-500 mb-0.5">速度</div>
            <div class="text-slate-300">{{ task.status === 'downloading' ? formatSpeed(task.speed) : '-' }}</div>
          </div>
          <div class="bg-slate-750/40 p-1.5 rounded">
            <div class="font-medium text-slate-500 mb-0.5">剩余时间</div>
            <div class="text-slate-300">{{ task.status === 'downloading' ? formatETA(task.eta) : '-' }}</div>
          </div>
        </div>

        <div class="progress-bar-container bg-slate-700/50 h-2 rounded-full overflow-hidden mb-1.5">
          <div 
            class="progress-bar h-full rounded-full transition-all duration-300 ease-out"
            :class="getProgressBarClass(task.status)"
            :style="{ width: calculateProgress(task) + '%' }"
          ></div>
        </div>
        <div class="flex items-center justify-between text-xxs text-slate-400">
          <span>{{ calculateProgress(task) }}%</span>
          <div class="actions flex space-x-1">
            <button 
              v-if="task.status === 'downloading'" 
              class="text-yellow-400 hover:text-yellow-300 transition-colors duration-150 p-0.5 rounded hover:bg-yellow-500/10"
              title="暂停下载"
              @click="emit('pause-download', task.id)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm4 0a1 1 0 012 0v4a1 1 0 11-2 0V8z" clip-rule="evenodd" />
              </svg>
            </button>
            <button 
              v-if="task.status === 'paused'" 
              class="text-green-400 hover:text-green-300 transition-colors duration-150 p-0.5 rounded hover:bg-green-500/10"
              title="恢复下载"
              @click="emit('resume-download', task.id)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
              </svg>
            </button>
            <button 
              v-if="task.status === 'downloading' || task.status === 'paused'" 
              @click="handleCancelDownload(task.id)" 
              class="text-red-400 hover:text-red-300 transition-colors duration-150 p-0.5 rounded hover:bg-red-500/10"
              title="取消下载"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.downloader-container {
  scrollbar-width: thin;
  scrollbar-color: rgba(71, 85, 105, 0.4) transparent;
}
.downloader-container::-webkit-scrollbar {
  width: 6px;
}
.downloader-container::-webkit-scrollbar-track {
  background: transparent;
}
.downloader-container::-webkit-scrollbar-thumb {
  background-color: rgba(71, 85, 105, 0.4);
  border-radius: 3px;
}
.downloader-container::-webkit-scrollbar-thumb:hover {
  background-color: rgba(100, 116, 139, 0.6);
}

.download-list {
  scrollbar-width: thin;
  scrollbar-color: rgba(71, 85, 105, 0.3) transparent;
}
.download-list::-webkit-scrollbar {
  width: 4px;
}
.download-list::-webkit-scrollbar-track {
  background: transparent;
}
.download-list::-webkit-scrollbar-thumb {
  background-color: rgba(71, 85, 105, 0.3);
  border-radius: 2px;
}
.download-list::-webkit-scrollbar-thumb:hover {
  background-color: rgba(100, 116, 139, 0.5);
}

.text-xxs {
  font-size: 0.65rem; /* 10.4px */
  line-height: 0.8rem; /* 12.8px */
}
</style> 