<script setup lang="ts">
import { ref, defineProps, defineEmits, onMounted, computed, watch } from 'vue';
import { workflowsApi } from '../services/api';

const props = defineProps({
  conversationId: { type: String, required: true },
  workflowId: { type: String, required: true }
});

const emit = defineEmits(['execute-step', 'update-workflow', 'request-ai-modification']);

const workflow = ref(null);
const isLoading = ref(true);
const error = ref('');
const isEditing = ref(false);
const editedWorkflow = ref(null);

// 加载工作流数据
const loadWorkflow = async () => {
  if (!props.workflowId) return;
  
  try {
    isLoading.value = true;
    const response = await workflowsApi.getWorkflow(props.workflowId);
    workflow.value = response.data;
    
    // 初始化每个步骤的展开状态
    if (workflow.value && workflow.value.steps) {
      workflow.value.steps.forEach(step => {
        step._isExpanded = false;
      });
    }
  } catch (err) {
    console.error('Error loading workflow:', err);
    error.value = '加载工作流失败';
  } finally {
    isLoading.value = false;
  }
};

// 执行步骤
const executeStep = async (stepId) => {
  if (!props.conversationId || !props.workflowId) return;
  
  try {
    isLoading.value = true;
    const response = await workflowsApi.executeStep(
      props.workflowId, 
      stepId, 
      props.conversationId
    );
    
    // 更新步骤状态
    if (workflow.value && workflow.value.steps) {
      const stepIndex = workflow.value.steps.findIndex(s => s.id === stepId);
      if (stepIndex !== -1) {
        workflow.value.steps[stepIndex] = response.data;
      }
    }
    
    // 通知父组件
    emit('execute-step', { stepId, result: response.data });
  } catch (err) {
    console.error('Error executing step:', err);
    error.value = '执行步骤失败';
  } finally {
    isLoading.value = false;
  }
};

// 切换步骤展开状态
const toggleStep = (stepId) => {
  if (!workflow.value || !workflow.value.steps) return;
  
  const step = workflow.value.steps.find(s => s.id === stepId);
  if (step) {
    step._isExpanded = !step._isExpanded;
  }
};

// 进入编辑模式
const startEditing = () => {
  editedWorkflow.value = JSON.parse(JSON.stringify(workflow.value));
  isEditing.value = true;
};

// 保存编辑
const saveEditing = async () => {
  if (!editedWorkflow.value) return;
  
  try {
    isLoading.value = true;
    const response = await workflowsApi.updateWorkflow(props.workflowId, editedWorkflow.value);
    workflow.value = response.data;
    isEditing.value = false;
    
    // 通知父组件工作流已更新
    emit('update-workflow', workflow.value);
  } catch (err) {
    console.error('Error updating workflow:', err);
    error.value = '更新工作流失败';
  } finally {
    isLoading.value = false;
  }
};

// 取消编辑
const cancelEditing = () => {
  isEditing.value = false;
  editedWorkflow.value = null;
};

// 添加新步骤
const addStep = () => {
  if (!editedWorkflow.value) return;
  
  const newStepId = `step${Date.now()}`;
  const newStep = {
    id: newStepId,
    title: '新步骤',
    command: '',
    description: '添加对此步骤的描述'
  };
  
  editedWorkflow.value.steps.push(newStep);
};

// 删除步骤
const removeStep = (stepIndex) => {
  if (!editedWorkflow.value || !editedWorkflow.value.steps) return;
  editedWorkflow.value.steps.splice(stepIndex, 1);
};

// 移动步骤
const moveStep = (stepIndex, direction) => {
  if (!editedWorkflow.value || !editedWorkflow.value.steps) return;
  
  const newIndex = stepIndex + direction;
  if (newIndex < 0 || newIndex >= editedWorkflow.value.steps.length) return;
  
  const step = editedWorkflow.value.steps[stepIndex];
  editedWorkflow.value.steps.splice(stepIndex, 1);
  editedWorkflow.value.steps.splice(newIndex, 0, step);
};

// 获取步骤状态的颜色
const getStatusColor = (status) => {
  switch(status) {
    case 'completed': return 'bg-green-500';
    case 'running': return 'bg-blue-500';
    case 'failed': return 'bg-red-500';
    case 'timeout': return 'bg-amber-500';
    default: return 'bg-slate-500';
  }
};

// 获取步骤状态的图标
const getStatusIcon = (status) => {
  switch(status) {
    case 'completed': return `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
    </svg>`;
    case 'running': return `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 animate-spin" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
    </svg>`;
    case 'failed': return `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
    </svg>`;
    case 'timeout': return `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
    </svg>`;
    default: return `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clip-rule="evenodd" />
    </svg>`;
  }
};

// 请求AI帮助修改
const requestAIModification = () => {
  emit('request-ai-modification', workflow.value);
};

// 加载工作流
onMounted(() => {
  if (props.workflowId) {
    loadWorkflow();
  }
});

// 监听工作流ID变化，重新加载工作流
watch(() => props.workflowId, (newId) => {
  if (newId) {
    loadWorkflow();
  } else {
    workflow.value = null;
  }
});
</script>

<template>
  <div class="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
    <!-- 加载中状态 -->
    <div v-if="isLoading" class="p-6 flex items-center justify-center">
      <div class="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
      <span class="ml-3 text-slate-300">加载工作流...</span>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="p-6 text-center">
      <div class="text-red-400">{{ error }}</div>
      <button 
        @click="loadWorkflow" 
        class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded"
      >
        重试
      </button>
    </div>
    
    <!-- 工作流内容 -->
    <div v-else-if="workflow" class="flex flex-col">
      <!-- 工作流标题和操作栏 -->
      <div class="bg-slate-700 p-4 flex justify-between items-center border-b border-slate-600">
        <div v-if="!isEditing" class="flex items-center">
          <h2 class="text-xl font-bold text-slate-100">{{ workflow.title }}</h2>
          <span 
            :class="[
              'ml-3 text-xs px-2 py-0.5 rounded-full',
              workflow.status === 'completed' ? 'bg-green-500/20 text-green-300' :
              workflow.status === 'in_progress' ? 'bg-blue-500/20 text-blue-300' :
              workflow.status === 'failed' ? 'bg-red-500/20 text-red-300' :
              'bg-slate-500/20 text-slate-300'
            ]"
          >
            {{ workflow.status }}
          </span>
        </div>
        <div v-else class="flex-1 mr-4">
          <input 
            v-model="editedWorkflow.title" 
            class="w-full px-3 py-1.5 bg-slate-800 border border-slate-600 rounded text-white"
            placeholder="工作流标题"
          />
        </div>
        
        <div class="flex space-x-2">
          <!-- 新增AI修改建议按钮 -->
          <button 
            v-if="!isEditing"
            @click="requestAIModification" 
            class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded flex items-center"
            title="请求AI帮助修改方案"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            AI修改建议
          </button>
          <button 
            v-if="!isEditing"
            @click="startEditing" 
            class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded flex items-center"
            title="手动编辑研究方案"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
            手动编辑
          </button>
          <div v-else class="flex space-x-2">
            <button 
              @click="cancelEditing" 
              class="px-3 py-1.5 bg-slate-600 hover:bg-slate-500 text-white rounded"
            >
              取消
            </button>
            <button 
              @click="saveEditing" 
              class="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded"
            >
              保存
            </button>
          </div>
        </div>
      </div>
      
      <!-- 工作流步骤列表 -->
      <div class="p-4 divide-y divide-slate-700/50">
        <!-- 非编辑模式的步骤展示 -->
        <template v-if="!isEditing">
          <div class="flex items-center mb-4 px-2 text-sm bg-slate-700/40 py-2 rounded">
            <div class="w-8 text-center text-slate-400">#</div>
            <div class="ml-4 flex-1 text-slate-300 font-medium">步骤</div>
            <div class="w-20 text-center text-slate-400">状态</div>
            <div class="w-16 text-center text-slate-400">操作</div>
          </div>
          <div 
            v-for="(step, index) in workflow.steps" 
            :key="step.id" 
            class="py-4"
          >
            <div class="flex items-start">
              <!-- 步骤序号 -->
              <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white bg-slate-700">
                {{ index + 1 }}
              </div>
              
              <!-- 步骤内容 -->
              <div class="ml-4 flex-1">
                <div class="flex items-center justify-between">
                  <h3 class="text-lg font-semibold text-slate-200">{{ step.title }}</h3>
                  <div class="flex space-x-2">
                    <span 
                      :class="[
                        'text-xs px-2 py-1 rounded-full flex items-center',
                        step.status === 'completed' ? 'bg-green-500/20 text-green-300' :
                        step.status === 'running' ? 'bg-blue-500/20 text-blue-300 animate-pulse' :
                        step.status === 'failed' ? 'bg-red-500/20 text-red-300' :
                        'bg-slate-500/20 text-slate-300'
                      ]"
                    >
                      <div class="w-1.5 h-1.5 rounded-full mr-1"
                        :class="[
                          step.status === 'completed' ? 'bg-green-400' :
                          step.status === 'running' ? 'bg-blue-400' :
                          step.status === 'failed' ? 'bg-red-400' :
                          'bg-slate-400'
                        ]"
                      ></div>
                      {{ step.status || '未执行' }}
                    </span>
                    <button 
                      @click="toggleStep(step.id)"
                      class="p-1.5 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-700"
                      :title="step._isExpanded ? '折叠详情' : '展开详情'"
                    >
                      <svg 
                        v-if="!step._isExpanded"
                        xmlns="http://www.w3.org/2000/svg" 
                        class="h-5 w-5" 
                        fill="none" 
                        viewBox="0 0 24 24" 
                        stroke="currentColor"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                      <svg 
                        v-else
                        xmlns="http://www.w3.org/2000/svg" 
                        class="h-5 w-5" 
                        fill="none" 
                        viewBox="0 0 24 24" 
                        stroke="currentColor"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                      </svg>
                    </button>
                    <button 
                      v-if="!step.status || step.status === 'failed'"
                      @click="executeStep(step.id)"
                      class="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-sm rounded"
                      title="执行这个步骤"
                    >
                      执行
                    </button>
                  </div>
                </div>
                
                <p class="mt-1 text-slate-400 text-sm">{{ step.description }}</p>
                
                <!-- 展开的详细内容 -->
                <div v-if="step._isExpanded" class="mt-3 space-y-3 bg-slate-800/60 p-3 rounded-lg border border-slate-700/50">
                  <div class="bg-slate-900 p-3 rounded-md">
                    <div class="flex justify-between items-center mb-2">
                      <span class="text-xs font-medium text-slate-400">命令</span>
                    </div>
                    <pre class="text-amber-300 text-sm font-mono whitespace-pre-wrap bg-slate-900/70 p-2 rounded">{{ step.command }}</pre>
                  </div>
                  
                  <!-- 输出结果 -->
                  <div v-if="step.output" class="bg-slate-900 p-3 rounded-md">
                    <div class="flex justify-between items-center mb-2">
                      <span class="text-xs font-medium text-slate-400">输出</span>
                    </div>
                    <pre class="text-green-300 text-sm font-mono whitespace-pre-wrap bg-slate-900/70 p-2 rounded max-h-48 overflow-y-auto">{{ step.output }}</pre>
                  </div>
                  
                  <!-- 错误信息 -->
                  <div v-if="step.error" class="bg-slate-900 p-3 rounded-md">
                    <div class="flex justify-between items-center mb-2">
                      <span class="text-xs font-medium text-slate-400">错误</span>
                    </div>
                    <pre class="text-red-300 text-sm font-mono whitespace-pre-wrap bg-slate-900/70 p-2 rounded">{{ step.error }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
        
        <!-- 编辑模式的步骤表单 -->
        <template v-else>
          <div 
            v-for="(step, index) in editedWorkflow.steps" 
            :key="index" 
            class="py-4"
          >
            <div class="flex items-start">
              <!-- 拖动排序和状态图标 -->
              <div class="flex-shrink-0 flex flex-col items-center mr-2">
                <button 
                  @click="moveStep(index, -1)" 
                  :disabled="index === 0"
                  :class="[
                    'p-1 rounded',
                    index === 0 ? 'text-slate-600' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
                  ]"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
                  </svg>
                </button>
                <span class="text-slate-500 text-xs my-1">{{ index + 1 }}</span>
                <button 
                  @click="moveStep(index, 1)" 
                  :disabled="index === editedWorkflow.steps.length - 1"
                  :class="[
                    'p-1 rounded',
                    index === editedWorkflow.steps.length - 1 ? 'text-slate-600' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
                  ]"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                </button>
              </div>
              
              <!-- 步骤表单 -->
              <div class="flex-1 space-y-3">
                <div>
                  <label class="block text-xs text-slate-400 mb-1">标题</label>
                  <input 
                    v-model="step.title" 
                    class="w-full px-3 py-1.5 bg-slate-800 border border-slate-600 rounded text-white"
                    placeholder="步骤标题"
                  />
                </div>
                
                <div>
                  <label class="block text-xs text-slate-400 mb-1">描述</label>
                  <textarea 
                    v-model="step.description" 
                    class="w-full px-3 py-1.5 bg-slate-800 border border-slate-600 rounded text-white h-20"
                    placeholder="步骤描述"
                  ></textarea>
                </div>
                
                <div>
                  <label class="block text-xs text-slate-400 mb-1">命令</label>
                  <textarea 
                    v-model="step.command" 
                    class="w-full px-3 py-1.5 bg-slate-800 border border-slate-600 rounded text-white h-20 font-mono"
                    placeholder="Bash 命令"
                  ></textarea>
                </div>
              </div>
              
              <!-- 删除按钮 -->
              <button 
                @click="removeStep(index)" 
                class="ml-3 p-2 text-red-400 hover:text-red-300 hover:bg-red-900/30 rounded"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
          
          <!-- 添加步骤按钮 -->
          <div class="py-4 flex justify-center">
            <button 
              @click="addStep" 
              class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded flex items-center"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
              </svg>
              添加新步骤
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 任何额外的组件样式 */
</style> 