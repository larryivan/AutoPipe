<template>
  <div class="download-manager p-4">
    <Downloader 
      :downloadTasks="downloadTasks" 
      @start-download="handleStartDownload"
      @cancel-download="handleCancelDownload"
      @refresh-downloads="fetchDownloadStatus"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { filesApi } from '@/services/api';
import Downloader from '@/components/Downloader.vue';

const route = useRoute();
const downloadTasks = ref([]);
const currentConversationId = ref(null);
let pollingInterval = null;

// 监听路由参数变化，获取会话ID
const updateConversationId = () => {
  currentConversationId.value = route.params.conversationId || localStorage.getItem('currentConversationId');
  if (currentConversationId.value) {
    localStorage.setItem('currentConversationId', currentConversationId.value);
    fetchDownloadStatus();
  }
};

// 获取下载状态
const fetchDownloadStatus = async () => {
  if (!currentConversationId.value) return;
  
  try {
    console.log('获取下载状态...');
    const response = await filesApi.getDownloadStatus(null, currentConversationId.value);
    if (response && response.data) {
      downloadTasks.value = response.data;
      console.log('下载任务:', downloadTasks.value);
    }
  } catch (error) {
    console.error('获取下载状态失败:', error);
  }
};

// 启动下载
const handleStartDownload = async (data) => {
  if (!currentConversationId.value) {
    console.error('未找到会话ID，无法开始下载');
    return;
  }
  
  try {
    await filesApi.downloadFile(data.url, currentConversationId.value, data.filename);
    console.log('已开始下载:', data.url);
    fetchDownloadStatus();
  } catch (error) {
    console.error('启动下载失败:', error);
  }
};

// 取消下载
const handleCancelDownload = async (downloadId) => {
  try {
    await filesApi.cancelDownload(downloadId);
    console.log('已取消下载:', downloadId);
    fetchDownloadStatus();
  } catch (error) {
    console.error('取消下载失败:', error);
  }
};

// 组件挂载时，获取会话ID并开始轮询
onMounted(() => {
  updateConversationId();
  
  // 启动轮询，每5秒更新一次下载状态
  pollingInterval = setInterval(fetchDownloadStatus, 5000);
});

// 组件卸载时，停止轮询
onUnmounted(() => {
  if (pollingInterval) {
    clearInterval(pollingInterval);
  }
});
</script>

<style scoped>
.download-manager {
  height: 100%;
  background-color: rgb(17, 24, 39, 0.7);
  border-radius: 0.5rem;
}
</style> 