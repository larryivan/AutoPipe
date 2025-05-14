<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { monitorApi } from '../services/api';

const props = defineProps({
  showMonitor: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['update:showMonitor']);

// 状态
const systemInfo = ref({});
const currentMetrics = ref({});
const processes = ref([]);
const cpuHistory = ref([]);
const memoryHistory = ref([]);
const diskHistory = ref([]);
const networkHistory = ref([]);
const isLoading = ref(false);
const error = ref(null);
const activeTab = ref('metrics'); // metrics, processes, info
const metricsSpecificError = ref(null); // 新增：用于指标加载的特定错误信息

// 加载系统信息
const loadSystemInfo = async () => {
  try {
    isLoading.value = true;
    error.value = null;
    
    const response = await monitorApi.getSystemInfo();
    systemInfo.value = response.data;
  } catch (err) {
    console.error('加载系统信息失败:', err);
    error.value = '加载系统信息失败';
  } finally {
    isLoading.value = false;
  }
};

// 加载当前性能指标
const loadCurrentMetrics = async () => {
  try {
    metricsSpecificError.value = null; // 清除此部分的特定错误
    
    const response = await monitorApi.getCurrentMetrics();
    currentMetrics.value = response.data;

    // 如果API成功返回，但数据不符合预期，特别是CPU数据
    if (!response.data || typeof response.data.cpu?.percent === 'undefined') {
      console.warn('性能指标API返回数据不完整或CPU数据缺失:', response.data);
      metricsSpecificError.value = 'CPU数据加载异常或数据不完整';
      if (currentMetrics.value) {
         currentMetrics.value.cpu = undefined; // 确保UI不会显示旧的有效数据或错误回退
      }
    }
  } catch (err) {
    console.error('加载性能指标失败:', err);
    metricsSpecificError.value = '加载性能指标失败: ' + (err.response?.data?.error || err.message || '未知错误');
    // 当加载失败时，将 currentMetrics.cpu 设为 undefined
    if (currentMetrics.value) {
        currentMetrics.value.cpu = undefined;
    }
  }
};

// 加载进程信息
const loadProcesses = async (pythonOnly = false) => {
  try {
    isLoading.value = true;
    error.value = null;
    
    const response = await monitorApi.getProcesses(pythonOnly);
    processes.value = response.data;
    
    // 如果进程列表为空，可能是权限问题
    if (processes.value.length === 0) {
      console.warn('获取不到进程信息，可能是权限问题');
      error.value = '无法获取进程信息，可能需要管理员权限';
    }
  } catch (err) {
    console.error('加载进程信息失败:', err);
    error.value = '加载进程信息失败: ' + (err.response?.data?.error || err.message || '未知错误');
  } finally {
    isLoading.value = false;
  }
};

// 加载历史数据
const loadHistory = async () => {
  try {
    const response = await monitorApi.getHistory(null, 30); // 获取最近30个数据点
    
    if (response.data.cpu) {
      cpuHistory.value = response.data.cpu.map(point => ({
        timestamp: new Date(point.timestamp * 1000),
        value: point.value
      }));
    }
    
    if (response.data.memory) {
      memoryHistory.value = response.data.memory.map(point => ({
        timestamp: new Date(point.timestamp * 1000),
        value: point.value
      }));
    }
    
    if (response.data.disk) {
      diskHistory.value = response.data.disk.map(point => ({
        timestamp: new Date(point.timestamp * 1000),
        value: point.value
      }));
    }
    
    if (response.data.network) {
      networkHistory.value = response.data.network.map(point => ({
        timestamp: new Date(point.timestamp * 1000),
        sentRate: point.bytes_sent_rate,
        recvRate: point.bytes_recv_rate
      }));
    }
  } catch (err) {
    console.error('加载历史数据失败:', err);
  }
};

// 格式化字节大小
const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

// 定期刷新数据
let refreshInterval = null;

const startRefresh = () => {
  stopRefresh();
  
  // 立即加载一次
  loadSystemInfo();
  loadCurrentMetrics();
  loadProcesses(false); // 明确指定pythonOnly为false
  loadHistory();
  
  // 设置定时刷新
  refreshInterval = setInterval(() => {
    if (props.showMonitor) {
      loadCurrentMetrics();
      
      // 根据当前选项卡加载其他数据
      if (activeTab.value === 'processes') {
        loadProcesses(false); // 明确指定pythonOnly为false
      } else if (activeTab.value === 'metrics') {
        loadHistory();
      }
    }
  }, 3000);
};

const stopRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
};

// 切换监控显示
const toggleMonitor = () => {
  emit('update:showMonitor', !props.showMonitor);
};

// 切换选项卡
const setActiveTab = (tab) => {
  activeTab.value = tab;
  
  // 在切换选项卡时刷新数据
  if (tab === 'info') {
    loadSystemInfo();
  } else if (tab === 'processes') {
    loadProcesses(false); // 明确指定pythonOnly为false
  } else if (tab === 'metrics') {
    loadCurrentMetrics();
    loadHistory();
  }
};

// 生命周期钩子
onMounted(() => {
  startRefresh();
});

onUnmounted(() => {
  stopRefresh();
});

// 监听显示状态变化
watch(() => props.showMonitor, (newVal) => {
  if (newVal) {
    startRefresh();
  } else {
    stopRefresh();
  }
});

// 格式化日期时间
const formatDateTime = (date) => {
  if (!date) return '';
  if (typeof date === 'number') {
    date = new Date(date * 1000);
  }
  return date.toLocaleString();
};

// 格式化时间差
const formatUptime = (bootTime) => {
  const now = new Date();
  const bootDate = new Date(bootTime * 1000);
  const diff = Math.floor((now - bootDate) / 1000);
  
  const days = Math.floor(diff / 86400);
  const hours = Math.floor((diff % 86400) / 3600);
  const minutes = Math.floor((diff % 3600) / 60);
  const seconds = diff % 60;
  
  let result = '';
  if (days > 0) result += `${days}天 `;
  result += `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  
  return result;
};
</script>

<template>
  <div class="monitor-container">
    <div class="tabs flex space-x-2 mb-3">
      <button 
        @click="setActiveTab('metrics')"
        :class="[
          'px-3 py-1 text-sm rounded-md',
          activeTab === 'metrics' 
            ? 'bg-blue-700 text-blue-100' 
            : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        性能指标
      </button>
      <button 
        @click="setActiveTab('processes')"
        :class="[
          'px-3 py-1 text-sm rounded-md',
          activeTab === 'processes' 
            ? 'bg-blue-700 text-blue-100' 
            : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        进程
      </button>
      <button 
        @click="setActiveTab('info')"
        :class="[
          'px-3 py-1 text-sm rounded-md',
          activeTab === 'info' 
            ? 'bg-blue-700 text-blue-100' 
            : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        系统信息
      </button>
    </div>
    
    <div v-if="error" class="bg-red-900/60 text-red-200 p-2 mb-3 rounded text-xs">
      {{ error }}
    </div>
    <div v-if="metricsSpecificError && activeTab === 'metrics'" class="bg-yellow-900/60 text-yellow-200 p-2 mb-3 rounded text-xs">
      性能指标错误: {{ metricsSpecificError }}
    </div>
    
    <!-- 性能指标选项卡 -->
    <div v-if="activeTab === 'metrics'" class="metrics-container">
      <div v-if="isLoading && !currentMetrics.cpu && !metricsSpecificError" class="text-slate-400">
        加载性能指标...
      </div>
      
      <div v-else>
        <!-- CPU利用率 -->
        <div class="metric-card mb-3">
          <div class="flex justify-between items-center mb-2">
            <h4 class="text-sm font-medium text-blue-300">CPU利用率</h4>
            <span v-if="typeof currentMetrics.cpu?.percent === 'number'" 
                  class="text-lg font-bold" 
                  :class="currentMetrics.cpu.percent > 80 ? 'text-red-400' : 'text-blue-400'">
              {{ currentMetrics.cpu.percent }}%
            </span>
            <span v-else class="text-lg font-bold text-slate-500">
              N/A
            </span>
          </div>
          
          <div class="w-full bg-slate-700 rounded-full h-2">
            <div 
              class="h-2 rounded-full" 
              :class="typeof currentMetrics.cpu?.percent === 'number' && currentMetrics.cpu.percent > 80 ? 'bg-red-500' : 'bg-blue-500'"
              :style="{ width: `${typeof currentMetrics.cpu?.percent === 'number' ? currentMetrics.cpu.percent : 0}%` }"
            ></div>
          </div>
          
          <div class="mt-2 grid grid-cols-4 gap-2 text-xs text-slate-400" v-if="currentMetrics.cpu?.per_cpu">
            <div 
              v-for="(value, index) in currentMetrics.cpu.per_cpu" 
              :key="index"
              class="flex flex-col items-center"
            >
              <span class="mb-1">Core {{ index }}</span>
              <div class="w-full bg-slate-700 rounded-full h-1">
                <div 
                  class="h-1 rounded-full" 
                  :class="value > 80 ? 'bg-red-500' : 'bg-blue-500'"
                  :style="{ width: `${value}%` }"
                ></div>
              </div>
              <span class="mt-1" :class="value > 80 ? 'text-red-400' : 'text-blue-400'">{{ value }}%</span>
            </div>
          </div>
          <div v-else-if="typeof currentMetrics.cpu?.percent === 'number' && !metricsSpecificError" class="mt-2 text-xs text-slate-500">
            各核心数据不可用。
          </div>
        </div>
        
        <!-- 内存使用情况 -->
        <div class="metric-card mb-3">
          <div class="flex justify-between items-center mb-2">
            <h4 class="text-sm font-medium text-green-300">内存使用</h4>
            <span class="text-lg font-bold" :class="currentMetrics.memory?.percent > 80 ? 'text-red-400' : 'text-green-400'">
              {{ currentMetrics.memory?.percent }}%
            </span>
          </div>
          
          <div class="w-full bg-slate-700 rounded-full h-2">
            <div 
              class="h-2 rounded-full" 
              :class="currentMetrics.memory?.percent > 80 ? 'bg-red-500' : 'bg-green-500'"
              :style="{ width: `${currentMetrics.memory?.percent || 0}%` }"
            ></div>
          </div>
          
          <div class="mt-2 grid grid-cols-3 gap-2 text-xs">
            <div class="flex flex-col items-center">
              <span class="text-slate-400">总内存</span>
              <span class="text-green-300">{{ formatBytes(currentMetrics.memory?.total) }}</span>
            </div>
            <div class="flex flex-col items-center">
              <span class="text-slate-400">已用</span>
              <span class="text-yellow-300">{{ formatBytes(currentMetrics.memory?.used) }}</span>
            </div>
            <div class="flex flex-col items-center">
              <span class="text-slate-400">可用</span>
              <span class="text-blue-300">{{ formatBytes(currentMetrics.memory?.available) }}</span>
            </div>
          </div>
        </div>
        
        <!-- 磁盘使用情况 -->
        <div class="metric-card mb-3">
          <div class="flex justify-between items-center mb-2">
            <h4 class="text-sm font-medium text-yellow-300">磁盘使用</h4>
            <span class="text-lg font-bold" :class="currentMetrics.disk?.percent > 80 ? 'text-red-400' : 'text-yellow-400'">
              {{ currentMetrics.disk?.percent }}%
            </span>
          </div>
          
          <div class="w-full bg-slate-700 rounded-full h-2">
            <div 
              class="h-2 rounded-full" 
              :class="currentMetrics.disk?.percent > 80 ? 'bg-red-500' : 'bg-yellow-500'"
              :style="{ width: `${currentMetrics.disk?.percent || 0}%` }"
            ></div>
          </div>
          
          <div class="mt-2 grid grid-cols-3 gap-2 text-xs">
            <div class="flex flex-col items-center">
              <span class="text-slate-400">总容量</span>
              <span class="text-yellow-300">{{ formatBytes(currentMetrics.disk?.total) }}</span>
            </div>
            <div class="flex flex-col items-center">
              <span class="text-slate-400">已用</span>
              <span class="text-orange-300">{{ formatBytes(currentMetrics.disk?.used) }}</span>
            </div>
            <div class="flex flex-col items-center">
              <span class="text-slate-400">可用</span>
              <span class="text-blue-300">{{ formatBytes(currentMetrics.disk?.free) }}</span>
            </div>
          </div>
        </div>
        
        <!-- 网络使用情况 -->
        <div class="metric-card">
          <div class="flex justify-between items-center mb-2">
            <h4 class="text-sm font-medium text-purple-300">网络流量</h4>
          </div>
          
          <div class="mt-2 grid grid-cols-2 gap-4 text-xs">
            <div class="flex flex-col items-center">
              <span class="text-slate-400">总接收</span>
              <span class="text-green-300">{{ formatBytes(currentMetrics.network?.bytes_recv) }}</span>
              <span class="text-xs text-slate-500" v-if="networkHistory.length > 1">
                {{ formatBytes(networkHistory[networkHistory.length - 1]?.recvRate || 0) }}/s
              </span>
            </div>
            <div class="flex flex-col items-center">
              <span class="text-slate-400">总发送</span>
              <span class="text-blue-300">{{ formatBytes(currentMetrics.network?.bytes_sent) }}</span>
              <span class="text-xs text-slate-500" v-if="networkHistory.length > 1">
                {{ formatBytes(networkHistory[networkHistory.length - 1]?.sentRate || 0) }}/s
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 进程选项卡 -->
    <div v-if="activeTab === 'processes'" class="processes-container">
      <div v-if="isLoading && !processes.length" class="text-slate-400">
        加载中...
      </div>
      
      <div v-else>
        <div class="flex justify-between items-center mb-2">
          <h4 class="text-sm font-medium text-blue-300">活跃进程 (按CPU使用率排序)</h4>
          <button 
            @click="loadProcesses()"
            class="p-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded"
            title="刷新"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
        
        <div class="process-table">
          <table class="w-full text-xs">
            <thead class="bg-slate-800 text-slate-300">
              <tr>
                <th class="py-2 px-1 text-left">PID</th>
                <th class="py-2 px-1 text-left">名称</th>
                <th class="py-2 px-1 text-right">CPU%</th>
                <th class="py-2 px-1 text-right">内存%</th>
                <th class="py-2 px-1 text-left">用户</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="process in processes" 
                :key="process.pid"
                class="border-b border-slate-700 hover:bg-slate-700/50"
              >
                <td class="py-1 px-1">{{ process.pid }}</td>
                <td class="py-1 px-1">{{ process.name }}</td>
                <td class="py-1 px-1 text-right" :class="process.cpu_percent > 10 ? 'text-orange-400' : 'text-blue-400'">
                  {{ process.cpu_percent.toFixed(1) }}%
                </td>
                <td class="py-1 px-1 text-right" :class="process.memory_percent > 5 ? 'text-orange-400' : 'text-green-400'">
                  {{ process.memory_percent.toFixed(1) }}%
                </td>
                <td class="py-1 px-1 text-slate-400">{{ process.username }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- 系统信息选项卡 -->
    <div v-if="activeTab === 'info'" class="info-container">
      <div v-if="isLoading && !Object.keys(systemInfo).length" class="text-slate-400">
        加载中...
      </div>
      
      <div v-else>
        <h4 class="text-sm font-medium text-blue-300 mb-3">系统详情</h4>
        
        <div class="grid grid-cols-2 gap-3 text-xs">
          <div class="flex flex-col">
            <span class="text-slate-400">操作系统</span>
            <span class="text-white">{{ systemInfo.system }} {{ systemInfo.release }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-slate-400">主机名</span>
            <span class="text-white">{{ systemInfo.node }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-slate-400">处理器</span>
            <span class="text-white">{{ systemInfo.processor }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-slate-400">架构</span>
            <span class="text-white">{{ systemInfo.machine }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-slate-400">CPU核心数</span>
            <span class="text-white">{{ systemInfo.cpu_count }} (物理) / {{ systemInfo.cpu_count_logical }} (逻辑)</span>
          </div>
          <div class="flex flex-col">
            <span class="text-slate-400">总内存</span>
            <span class="text-white">{{ formatBytes(systemInfo.memory_total) }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-slate-400">启动时间</span>
            <span class="text-white">{{ formatDateTime(systemInfo.boot_time) }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-slate-400">运行时间</span>
            <span class="text-white">{{ formatUptime(systemInfo.boot_time) }}</span>
          </div>
        </div>
      </div>
    </div>
    
  </div>
</template>

<style scoped>
.monitor-container {
  height: 100%;
  overflow-y: auto;
}

.metric-card {
  padding: 0.75rem;
  border-radius: 0.375rem;
  transition: all 0.2s ease;
}

.metric-card:hover {
  background-color: rgba(15, 23, 42, 0.4);
}

.process-table {
  overflow-y: auto;
  max-height: 330px;
  border-radius: 0.25rem;
  background-color: rgba(15, 23, 42, 0.3);
}

.monitor-container::-webkit-scrollbar,
.process-table::-webkit-scrollbar {
  width: 4px;
}

.monitor-container::-webkit-scrollbar-track,
.process-table::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.3);
  border-radius: 4px;
}

.monitor-container::-webkit-scrollbar-thumb,
.process-table::-webkit-scrollbar-thumb {
  background: rgba(51, 65, 85, 0.8);
  border-radius: 4px;
}

.monitor-container::-webkit-scrollbar-thumb:hover,
.process-table::-webkit-scrollbar-thumb:hover {
  background: rgba(71, 85, 105, 0.8);
}
</style> 