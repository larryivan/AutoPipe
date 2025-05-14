<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { terminalApi } from '../services/api';

const props = defineProps({
  conversationId: {
    type: String,
    required: true
  },
  showTerminal: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['update:showTerminal']);

// 终端状态
const terminalSessions = ref([]);
const currentSessionId = ref(null);
const currentSession = ref(null);
const commandHistory = ref([]);
const currentCommand = ref('');
const commandHistoryIndex = ref(-1); // 当前历史命令索引
const savedCurrentCommand = ref(''); // 保存当前输入
const isLoading = ref(false);
const error = ref(null);
const terminalEl = ref(null);
const inputEl = ref(null); // 添加输入框的引用

// ANSI颜色代码解析函数
const parseAnsiColor = (text) => {
  if (!text) return '';
  
  // 颜色映射
  const colorMap = {
    '30': 'text-black',
    '31': 'text-red-500',
    '32': 'text-green-500',
    '33': 'text-yellow-500',
    '34': 'text-blue-500',
    '35': 'text-purple-500',
    '36': 'text-cyan-500',
    '37': 'text-slate-300',
    '90': 'text-slate-400',
    '91': 'text-red-400',
    '92': 'text-green-400',
    '93': 'text-yellow-400',
    '94': 'text-blue-400',
    '95': 'text-purple-400',
    '96': 'text-cyan-400',
    '97': 'text-white',
  };
  
  // 替换颜色代码
  const colorRegex = /\u001b\[(\d+)m(.*?)(\u001b\[0m|\u001b\[\d+m)/g;
  let result = text.replace(colorRegex, (match, color, content, end) => {
    const colorClass = colorMap[color] || '';
    return `<span class="${colorClass}">${content}</span>`;
  });
  
  // 清除剩余颜色代码
  result = result.replace(/\u001b\[\d+m/g, '');
  
  // 保留换行符
  result = result.replace(/\n/g, '<br>');
  
  return result;
};

// 清屏功能
const clearTerminal = () => {
  commandHistory.value = [];
};

// 复制到剪贴板
const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text).then(
    () => {
      // 成功
      showToast('已复制到剪贴板');
    },
    () => {
      // 失败
      showToast('复制失败，请手动复制');
    }
  );
};

// 显示提示
const toast = ref('');
const showToast = (message) => {
  toast.value = message;
  setTimeout(() => {
    toast.value = '';
  }, 2000);
};

// 显示帮助
const showHelp = ref(false);
const toggleHelp = () => {
  showHelp.value = !showHelp.value;
};

// 保持输入框焦点
const refocusInput = () => {
  if (inputEl.value) {
    inputEl.value.focus();
  }
};

// 创建一个新的终端会话
const createTerminalSession = async () => {
  try {
    isLoading.value = true;
    error.value = null;
    
    const response = await terminalApi.createSession(props.conversationId);
    const newSession = response.data;
    
    terminalSessions.value.push(newSession);
    currentSessionId.value = newSession.id;
    currentSession.value = newSession;
    commandHistory.value = newSession.commands || [];
    
    scrollToBottom();
  } catch (err) {
    console.error('创建终端会话失败:', err);
    error.value = '创建终端会话失败';
  } finally {
    isLoading.value = false;
  }
};

// 获取现有的终端会话
const loadTerminalSessions = async () => {
  try {
    isLoading.value = true;
    error.value = null;
    
    const response = await terminalApi.getSessions(props.conversationId);
    terminalSessions.value = response.data;
    
    if (terminalSessions.value.length > 0) {
      currentSessionId.value = terminalSessions.value[0].id;
      await loadSession(currentSessionId.value);
    } else {
      await createTerminalSession();
    }
  } catch (err) {
    console.error('加载终端会话失败:', err);
    error.value = '加载终端会话失败';
  } finally {
    isLoading.value = false;
  }
};

// 加载特定会话
const loadSession = async (sessionId) => {
  try {
    if (!sessionId) return;
    
    isLoading.value = true;
    error.value = null;
    
    const response = await terminalApi.getSession(sessionId);
    currentSession.value = response.data;
    
    // 检查是否有新命令或状态更新
    const currentCommands = commandHistory.value;
    const newCommands = currentSession.value.commands || [];
    
    // 使用Map来更高效地比较命令
    const currentCommandMap = new Map();
    currentCommands.forEach(cmd => {
      if (cmd.id && !cmd.id.startsWith('temp-')) {
        currentCommandMap.set(cmd.id, cmd);
      }
    });
    
    // 如果本地没有命令或命令数量不一致，直接用服务器的命令列表替换
    if (currentCommands.length === 0 || 
        currentCommands.some(cmd => cmd.id.startsWith('temp-')) ||
        currentCommands.length !== newCommands.length) {
      commandHistory.value = newCommands;
    } else {
      // 更新现有命令的状态和输出
      let hasUpdate = false;
      newCommands.forEach(newCmd => {
        const currentCmd = currentCommandMap.get(newCmd.id);
        if (currentCmd) {
          // 只有当状态或输出不同时才更新
          if (currentCmd.status !== newCmd.status || 
              currentCmd.output !== newCmd.output) {
            Object.assign(currentCmd, newCmd);
            hasUpdate = true;
          }
        } else {
          // 如果是新命令，添加到历史
          commandHistory.value.push(newCmd);
          hasUpdate = true;
        }
      });
      
      // 如果有更新，重新排序命令确保顺序一致
      if (hasUpdate) {
        const commandMap = new Map();
        newCommands.forEach(cmd => commandMap.set(cmd.id, cmd));
        commandHistory.value = commandHistory.value
          .filter(cmd => commandMap.has(cmd.id) || cmd.id.startsWith('temp-'))
          .sort((a, b) => {
            // 临时命令始终放在最后
            if (a.id.startsWith('temp-')) return 1;
            if (b.id.startsWith('temp-')) return -1;
            // 按照原始顺序排序
            return newCommands.findIndex(cmd => cmd.id === a.id) - 
                   newCommands.findIndex(cmd => cmd.id === b.id);
          });
      }
    }
    
    scrollToBottom();
    refocusInput(); // 重新获取焦点
  } catch (err) {
    console.error('加载会话详情失败:', err);
    error.value = '加载会话详情失败: ' + (err.message || '未知错误');
    
    // 如果会话不存在，尝试创建新会话
    if (err.response && err.response.status === 404) {
      await createTerminalSession();
    }
  } finally {
    isLoading.value = false;
    refocusInput(); // 确保加载完成后仍有焦点
  }
};

// 定期刷新当前会话 - 修改刷新策略
let refreshInterval = null;
const isTyping = ref(false); // 添加输入状态标记
const lastRefreshTime = ref(Date.now());

const startRefresh = () => {
  stopRefresh();
  refreshInterval = setInterval(async () => {
    // 不处于输入状态、未加载且距离上次刷新至少5秒时才刷新
    const now = Date.now();
    if (currentSessionId.value && 
        !isLoading.value && 
        !isTyping.value && 
        now - lastRefreshTime.value >= 5000) {
      lastRefreshTime.value = now;
      try {
        await loadSession(currentSessionId.value);
      } catch (err) {
        console.error('自动刷新会话失败:', err);
        // 如果刷新多次失败，停止刷新并显示错误
        if (err.response && err.response.status === 404) {
          stopRefresh();
          error.value = '会话已失效，请创建新会话';
        }
      }
    }
  }, 3000); // 3秒检查一次
};

const stopRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
};

// 添加输入开始和结束的处理
const handleInputFocus = () => {
  isTyping.value = true; // 获得焦点时标记为输入状态
};

const handleInputBlur = () => {
  // 延迟将输入状态设为false，给点击命令时间来执行
  setTimeout(() => {
    isTyping.value = false;
  }, 300);
};

// 处理输入变化
const handleInputChange = () => {
  isTyping.value = true; // 正在输入中
  // 设置一个延迟，在用户停止输入一段时间后认为输入结束
  clearTimeout(window.inputTimeout);
  window.inputTimeout = setTimeout(() => {
    isTyping.value = false;
  }, 2000);
};

// 执行命令
const executeCommand = async () => {
  if (!currentCommand.value.trim() || !currentSessionId.value) return;
  
  try {
    isLoading.value = true;
    error.value = null;
    
    const command = currentCommand.value.trim();
    const savedCommand = command; // 保存命令，避免清空后无法显示
    currentCommand.value = '';
    commandHistoryIndex.value = -1; // 重置历史索引
    
    // 优先在本地显示命令，让用户感觉更快
    const tempCommandEntry = {
      id: `temp-${Date.now()}`,
      command: savedCommand,
      status: 'running',
      output: '执行中...\n',
      start_time: Date.now() / 1000
    };
    
    commandHistory.value.push(tempCommandEntry);
    scrollToBottom();
    
    // 暂停自动刷新以避免闪烁
    stopRefresh();
    
    try {
      const response = await terminalApi.executeCommand(currentSessionId.value, savedCommand);
      const commandResult = response.data;
      
      // 检查特殊命令结果
      if (commandResult.output === 'CLEAR_TERMINAL') {
        // 清屏指令
        clearTerminal();
        isLoading.value = false;
        // 重新启动刷新
        startRefresh();
        return;
      }
      
      // 替换临时命令条目
      const tempIndex = commandHistory.value.findIndex(cmd => cmd.id === tempCommandEntry.id);
      if (tempIndex !== -1) {
        commandHistory.value[tempIndex] = commandResult;
      } else {
        commandHistory.value.push(commandResult);
      }
    } catch (err) {
      // 命令执行失败时更新临时条目
      const tempIndex = commandHistory.value.findIndex(cmd => cmd.id === tempCommandEntry.id);
      if (tempIndex !== -1) {
        commandHistory.value[tempIndex].status = 'failed';
        commandHistory.value[tempIndex].output = `执行失败: ${err.message || '未知错误'}\n`;
        commandHistory.value[tempIndex].end_time = Date.now() / 1000;
      }
      console.error('执行命令失败:', err);
      error.value = '执行命令失败: ' + (err.message || '未知错误');
    }
    
    // 获取最新会话状态
    try {
      await loadSession(currentSessionId.value);
    } catch (err) {
      console.error('加载会话状态失败:', err);
    }
    
  } catch (err) {
    console.error('执行命令失败:', err);
    error.value = '执行命令失败: ' + (err.message || '未知错误');
  } finally {
    isLoading.value = false;
    scrollToBottom();
    refocusInput();
    // 恢复自动刷新
    startRefresh();
  }
};

// 新建会话
const newSession = async () => {
  await createTerminalSession();
};

// 终止会话
const terminateSession = async () => {
  if (!currentSessionId.value) return;
  
  try {
    isLoading.value = true;
    error.value = null;
    
    await terminalApi.terminateSession(currentSessionId.value);
    
    const index = terminalSessions.value.findIndex(s => s.id === currentSessionId.value);
    if (index !== -1) {
      terminalSessions.value.splice(index, 1);
    }
    
    if (terminalSessions.value.length > 0) {
      currentSessionId.value = terminalSessions.value[0].id;
      await loadSession(currentSessionId.value);
    } else {
      await createTerminalSession();
    }
    
  } catch (err) {
    console.error('终止会话失败:', err);
    error.value = '终止会话失败';
  } finally {
    isLoading.value = false;
  }
};

// 滚动到底部
const scrollToBottom = () => {
  setTimeout(() => {
    if (terminalEl.value) {
      terminalEl.value.scrollTop = terminalEl.value.scrollHeight;
    }
  }, 50);
};

// 格式化时间戳
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString();
};

// 简化处理键盘事件，移除所有快捷键
const handleKeyDown = (e) => {
  // 执行命令
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    executeCommand();
  }
  
  // 向上浏览历史命令
  else if (e.key === 'ArrowUp') {
    e.preventDefault();
    
    // 查找可执行的命令（非临时命令）
    const executableCommands = commandHistory.value
      .filter(cmd => cmd.command && !cmd.command.startsWith('welcome'))
      .map(cmd => cmd.command);
    
    if (executableCommands.length === 0) return;
    
    // 首次按上箭头，保存当前输入
    if (commandHistoryIndex.value === -1) {
      savedCurrentCommand.value = currentCommand.value;
    }
    
    // 向上浏览历史
    if (commandHistoryIndex.value < executableCommands.length - 1) {
      commandHistoryIndex.value++;
      currentCommand.value = executableCommands[executableCommands.length - 1 - commandHistoryIndex.value];
    }
  }
  
  // 向下浏览历史命令
  else if (e.key === 'ArrowDown') {
    e.preventDefault();
    
    const executableCommands = commandHistory.value
      .filter(cmd => cmd.command && !cmd.command.startsWith('welcome'))
      .map(cmd => cmd.command);
    
    if (executableCommands.length === 0) return;
    
    // 向下浏览历史
    if (commandHistoryIndex.value > 0) {
      commandHistoryIndex.value--;
      currentCommand.value = executableCommands[executableCommands.length - 1 - commandHistoryIndex.value];
    } 
    // 恢复到保存的输入
    else if (commandHistoryIndex.value === 0) {
      commandHistoryIndex.value = -1;
      currentCommand.value = savedCurrentCommand.value;
    }
  }
  
  // Ctrl+L 清屏
  else if (e.key === 'l' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    clearTerminal();
  }
};

// 切换终端显示
const toggleTerminal = () => {
  emit('update:showTerminal', !props.showTerminal);
};

// 切换会话
const switchSession = async (sessionId) => {
  if (sessionId === currentSessionId.value) return;
  
  currentSessionId.value = sessionId;
  await loadSession(sessionId);
};

onMounted(() => {
  loadTerminalSessions();
  // 启动刷新后加载会话并聚焦输入框
  setTimeout(() => {
    startRefresh();
    refocusInput();
  }, 500);
});

onUnmounted(() => {
  stopRefresh();
});

// 监听会话ID变化
watch(currentSessionId, () => {
  if (currentSessionId.value) {
    loadSession(currentSessionId.value);
  }
});

// 监听显示状态变化
watch(() => props.showTerminal, (newVal) => {
  if (newVal && currentSessionId.value) {
    loadSession(currentSessionId.value);
    // 如果页面变为显示状态，重新启动刷新
    startRefresh();
  } else if (!newVal) {
    // 如果页面隐藏，停止刷新
    stopRefresh();
  }
});

// 监听会话ID变化
watch(() => props.conversationId, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    // 会话改变时停止旧刷新
    stopRefresh();
    loadTerminalSessions();
    // 加载完新会话后再启动刷新
    setTimeout(() => {
      startRefresh();
    }, 500);
  }
});

// 终止命令
const terminateCommand = async (commandId) => {
  if (!currentSessionId.value) return;
  
  try {
    // 查找命令
    const command = commandHistory.value.find(cmd => cmd.id === commandId);
    if (!command || command.status !== 'running') return;
    
    // 更新UI以快速反馈
    command.output += '\n正在终止命令...\n';
    
    // 调用API终止命令
    await terminalApi.terminateCommand(currentSessionId.value, commandId);
    
    // 立即更新会话状态
    await loadSession(currentSessionId.value);
    
    showToast('命令已终止');
  } catch (err) {
    console.error('终止命令失败:', err);
    error.value = '终止命令失败: ' + (err.message || '未知错误');
  }
};
</script>

<template>
  <div class="terminal-container">
    <!-- 终端标题栏 -->
    <div class="terminal-header flex justify-between items-center mb-2">
      <div class="flex items-center">
        <h3 class="text-md font-medium text-green-400 tracking-wide">终端</h3>
        <div class="terminal-tabs ml-4 flex space-x-1.5" v-if="terminalSessions.length > 1">
          <button
            v-for="session in terminalSessions"
            :key="session.id"
            @click="switchSession(session.id)"
            :class="[
              'px-2 py-1 text-xs rounded-md transition-colors',
              session.id === currentSessionId
                ? 'bg-green-800/60 text-green-100 shadow-inner'
                : 'bg-slate-800/60 text-slate-300 hover:bg-slate-700/70'
            ]"
          >
            会话 {{ session.id.slice(-4) }}
          </button>
        </div>
      </div>
      <div class="terminal-controls flex space-x-1.5">
        <button
          @click="toggleHelp"
          class="control-btn"
          title="帮助"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
          </svg>
        </button>
        <button
          @click="newSession"
          class="control-btn"
          title="新建会话"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 00-1 1v5H4a1 1 0 100 2h5v5a1 1 0 102 0v-5h5a1 1 0 100-2h-5V4a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
        </button>
        <button
          @click="clearTerminal"
          class="control-btn"
          title="清屏"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
          </svg>
        </button>
        <button
          @click="terminateSession"
          class="control-btn text-red-400"
          title="关闭会话"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-message">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1.5" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
      </svg>
      <span>{{ error }}</span>
    </div>
    
    <!-- 帮助提示框 -->
    <div v-if="showHelp" class="help-panel">
      <h4 class="text-blue-400 font-medium mb-2 flex items-center">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1.5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 011 1v4a1 1 0 11-2 0V7a1 1 0 011-1z" clip-rule="evenodd" />
          <path d="M9 14h2v2H9v-2z" />
        </svg>
        终端帮助
      </h4>
      <div class="grid grid-cols-2 gap-2">
        <div class="command-help">
          <kbd>Enter</kbd>
          <span>执行命令</span>
        </div>
        <div class="command-help">
          <kbd>cd 路径</kbd>
          <span>切换目录</span>
        </div>
        <div class="command-help">
          <kbd>help</kbd>
          <span>查看帮助</span>
        </div>
        <div class="command-help">
          <kbd>clear</kbd>
          <span>清屏</span>
        </div>
      </div>
    </div>

    <!-- 终端输出区域 -->
    <div
      ref="terminalEl"
      class="terminal-output"
    >
      <div v-if="isLoading && !commandHistory.length" class="loading-state">
        <div class="loader"></div>
        <span>正在连接终端...</span>
      </div>
      <div v-else-if="!commandHistory.length" class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" />
        </svg>
        <span>终端已准备就绪，输入命令开始操作...</span>
      </div>
      <template v-else>
        <div 
          v-for="(cmd, index) in commandHistory" 
          :key="`${cmd.id}-${index}`"
          class="command-block"
        >
          <!-- 命令输入部分 -->
          <div class="terminal-prompt">
            <div class="prompt-symbol">$</div>
            <div class="command-text" @click="() => currentCommand = cmd.command">{{ cmd.command }}</div>
            <div class="command-actions">
              <button 
                @click="copyToClipboard(cmd.command)" 
                class="action-button copy-button"
                title="复制命令"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
                  <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
                </svg>
              </button>
              <button 
                v-if="cmd.status === 'running'"
                @click="terminateCommand(cmd.id)" 
                class="action-button stop-button"
                title="终止命令"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
          
          <!-- 命令输出部分 -->
          <div 
            class="terminal-response"
            :class="{
              'failed': cmd.status === 'failed' || cmd.status === 'terminated', 
              'running': cmd.status === 'running'
            }"
          >
            <div v-if="cmd.status === 'running' && !cmd.output" class="running-indicator">
              <div class="dots-loader"></div>
              <span>执行中...</span>
            </div>
            <div v-else class="output-content" v-html="parseAnsiColor(cmd.output)">
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 命令输入框 -->
    <div class="terminal-input-wrapper">
      <div class="prompt-symbol">$</div>
      <input
        ref="inputEl"
        type="text"
        v-model="currentCommand"
        @keydown="handleKeyDown"
        @focus="handleInputFocus"
        @blur="handleInputBlur"
        @input="handleInputChange"
        class="terminal-input"
        placeholder="输入命令..."
        :disabled="isLoading"
      />
      <button
        @click="executeCommand"
        class="execute-button"
        :disabled="isLoading || !currentCommand.trim()"
        :class="{ 'active': currentCommand.trim() }"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" clip-rule="evenodd" />
        </svg>
      </button>
    </div>
    
    <!-- 提示信息 -->
    <div
      v-if="toast"
      class="toast"
    >
      {{ toast }}
    </div>
  </div>
</template>

<style scoped>
.terminal-container {
  background-color: rgba(15, 23, 42, 0.7);
  border-radius: 0.5rem;
  padding: 0.75rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(51, 65, 85, 0.5);
}

/* 控制按钮样式 */
.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.7);
  transition: all 0.15s ease;
  background-color: rgba(51, 65, 85, 0.5);
}

.control-btn:hover {
  background-color: rgba(71, 85, 105, 0.7);
  color: rgba(255, 255, 255, 0.95);
}

/* 错误信息 */
.error-message {
  display: flex;
  align-items: center;
  background-color: rgba(220, 38, 38, 0.2);
  border-left: 3px solid rgb(220, 38, 38);
  color: rgb(254, 202, 202);
  padding: 0.5rem 0.75rem;
  border-radius: 0.25rem;
  margin-bottom: 0.75rem;
  font-size: 0.75rem;
}

/* 帮助面板 */
.help-panel {
  background-color: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(71, 85, 105, 0.5);
  padding: 0.75rem;
  margin-bottom: 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.75rem;
}

.command-help {
  display: flex;
  align-items: center;
}

.command-help kbd {
  font-family: monospace;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  background-color: rgba(51, 65, 85, 0.8);
  color: rgb(203, 213, 225);
  border-radius: 0.25rem;
  margin-right: 0.5rem;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.command-help span {
  color: rgb(148, 163, 184);
}

/* 终端输出区域 */
.terminal-output {
  background-color: rgba(17, 24, 39, 0.95);
  color: rgb(134, 239, 172);
  padding: 0.75rem;
  border-radius: 0.375rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8125rem;
  line-height: 1.5;
  overflow-y: auto;
  height: 16rem;
  margin-bottom: 0.75rem;
  border: 1px solid rgba(51, 65, 85, 0.6);
  transition: border-color 0.2s ease;
}

.terminal-output:hover {
  border-color: rgba(71, 85, 105, 0.8);
}

.terminal-output::-webkit-scrollbar {
  width: 4px;
}

.terminal-output::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.5);
  border-radius: 3px;
}

.terminal-output::-webkit-scrollbar-thumb {
  background: rgba(71, 85, 105, 0.6);
  border-radius: 3px;
}

.terminal-output::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.8);
}

/* 加载和空状态 */
.loading-state, .empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: rgb(148, 163, 184);
  font-style: italic;
}

.loading-state .loader {
  height: 12px;
  width: 12px;
  border: 2px solid rgba(74, 222, 128, 0.5);
  border-radius: 50%;
  border-top-color: rgb(74, 222, 128);
  animation: spin 1s linear infinite;
  margin-right: 8px;
}

.dots-loader {
  display: inline-flex;
  align-items: center;
  margin-right: 6px;
}

.dots-loader::after {
  content: "...";
  animation: dots 1.5s steps(4, end) infinite;
  width: 12px;
  display: inline-block;
  text-align: left;
}

@keyframes dots {
  0%, 20% { content: "."; }
  40% { content: ".."; }
  60% { content: "..."; }
  80%, 100% { content: ""; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 命令块样式 */
.command-block {
  margin-bottom: 0.75rem;
}

.command-block:last-child {
  margin-bottom: 0;
}

/* 命令提示符样式 */
.terminal-prompt {
  display: flex;
  align-items: center;
  margin-bottom: 0.25rem;
}

.prompt-symbol {
  color: rgb(74, 222, 128);
  margin-right: 0.5rem;
  font-weight: bold;
}

.command-text {
  color: rgb(56, 189, 248);
  cursor: pointer;
  padding: 0.125rem 0.25rem;
  border-radius: 0.125rem;
  transition: all 0.2s ease;
}

.command-text:hover {
  background-color: rgba(56, 189, 248, 0.1);
  text-decoration: underline;
}

.command-actions {
  display: flex;
  margin-left: 0.5rem;
  gap: 0.25rem;
}

.action-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 3px;
  transition: all 0.2s ease;
  opacity: 0.5;
}

.action-button:hover {
  opacity: 1;
  background-color: rgba(51, 65, 85, 0.6);
}

.copy-button {
  color: rgb(148, 163, 184);
}

.copy-button:hover {
  color: rgb(203, 213, 225);
}

.stop-button {
  color: rgb(248, 113, 113);
}

.stop-button:hover {
  color: rgb(239, 68, 68);
}

/* 命令响应样式 */
.terminal-response {
  padding-left: 1.5rem;
  margin-top: 0.25rem;
  white-space: pre-wrap;
  word-break: break-all;
}

.terminal-response.failed {
  color: rgb(252, 165, 165);
}

.terminal-response.running {
  color: rgb(148, 163, 184);
}

.running-indicator {
  display: flex;
  align-items: center;
  font-style: italic;
}

.output-content {
  line-height: 1.4;
}

/* 命令输入区域 */
.terminal-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background-color: rgba(17, 24, 39, 0.8);
  border-radius: 0.375rem;
  border: 1px solid rgba(51, 65, 85, 0.6);
  padding: 0 0.5rem;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.terminal-input-wrapper:focus-within {
  border-color: rgba(56, 189, 248, 0.7);
  box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.25);
}

.terminal-input {
  flex: 1;
  background: transparent;
  color: rgb(134, 239, 172);
  border: none;
  padding: 0.5rem 2rem 0.5rem 0.5rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.875rem;
}

.terminal-input::placeholder {
  color: rgba(148, 163, 184, 0.6);
}

.terminal-input:focus {
  outline: none;
}

.execute-button {
  position: absolute;
  right: 0.5rem;
  color: rgba(74, 222, 128, 0.5);
  background: transparent;
  border: none;
  padding: 0.25rem;
  border-radius: 50%;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.execute-button.active {
  color: rgb(74, 222, 128);
}

.execute-button.active:hover {
  background-color: rgba(74, 222, 128, 0.1);
  transform: translateY(-1px);
}

.execute-button:disabled {
  color: rgba(148, 163, 184, 0.3);
  cursor: not-allowed;
}

/* 提示信息样式 */
.toast {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  background-color: rgba(34, 197, 94, 0.9);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 50;
  font-size: 0.875rem;
  animation: fade-in-out 2s ease-in-out;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(74, 222, 128, 0.4);
}

@keyframes fade-in-out {
  0% { opacity: 0; transform: translateY(10px); }
  10% { opacity: 1; transform: translateY(0); }
  80% { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; transform: translateY(-10px); }
}
</style> 