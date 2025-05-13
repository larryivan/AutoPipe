<script setup lang="ts">
import { ref, defineProps, defineEmits, watch, nextTick, computed } from "vue";
import PipelineContainer from "./PipelineContainer.vue";

interface Message {
  id: string | number;
  text: string;
  sender: "user" | "bot" | "system";
  timestamp: string;
  isWelcome?: boolean;
  isSystem?: boolean;
  workflow_id?: string;
  plan?: any[];
}

interface Props {
  messages: Message[];
  currentConversationId: string | null;
  isLoading: boolean;
  mode: string;
}

const props = defineProps<Props>();
const emit = defineEmits(["send-message", "toggle-mode"]);

const newMessage = ref("");
const messageDisplayArea = ref<HTMLElement | null>(null);

const scrollToBottom = async (behavior: ScrollBehavior = "smooth") => {
  await nextTick();
  if (messageDisplayArea.value) {
    messageDisplayArea.value.scrollTop = messageDisplayArea.value.scrollHeight;
  }
};

watch(
  () => props.messages,
  async (newMessages, oldMessages) => {
    if (newMessages.length !== oldMessages?.length) {
      const behavior =
        newMessages.length > (oldMessages?.length ?? 0) ? "smooth" : "auto";
      await scrollToBottom(behavior);
    }
  },
  { deep: true }
);

watch(
  () => props.currentConversationId,
  async () => {
    await scrollToBottom("auto");
  }
);

const sendMessage = () => {
  if (newMessage.value.trim() === "" || !props.currentConversationId) return;
  emit("send-message", newMessage.value);
  newMessage.value = "";
};

const handleToggleMode = () => {
  emit("toggle-mode");
};

const regularMessages = computed(() => props.messages.filter((m) => !m.isWelcome));

const welcomeMessage = computed(() => props.messages.find((m) => m.isWelcome));
</script>

<template>
  <div class="flex-1 flex flex-col bg-slate-950 overflow-hidden">
    <!-- 简化的模式指示横幅 -->
    <div
      :class="[
        'py-1 px-4 text-center text-sm font-medium',
        mode === 'agent'
          ? 'bg-blue-600/30 text-blue-100 border-b border-blue-700/50'
          : 'bg-emerald-600/30 text-emerald-100 border-b border-emerald-700/50',
      ]"
    >
      <span v-if="mode === 'agent'">
        <span class="font-bold">代理模式</span> - 描述目标，我将为您自动创建和执行工作流
      </span>
      <span v-else> <span class="font-bold">聊天模式</span> - 随时提问，获得回答 </span>
    </div>

    <!-- Message Area -->
    <div
      class="flex-1 bg-slate-900 overflow-y-auto p-6 scrollbar-thin"
      ref="messageDisplayArea"
    >
      <!-- Welcome Message -->
      <div
        v-if="welcomeMessage"
        class="max-w-xl mx-auto mb-8 bg-slate-800/70 rounded-xl p-5 border border-slate-700/60 animate-fade-in"
      >
        <h1 class="text-xl font-bold text-slate-100 mb-3">欢迎使用</h1>
        <p class="text-slate-300 mb-2">这是一款智能AI助手，可以帮助您：</p>
        <ul class="text-slate-400 list-disc pl-6 mb-4 space-y-1">
          <li>回答您的问题</li>
          <li>提供知识和建议</li>
          <li>帮助您完成任务</li>
          <li v-if="mode === 'agent'">自动创建并执行工作流</li>
        </ul>
        <p class="text-slate-400 text-sm">
          您当前在<span class="font-bold">{{
            mode === "agent" ? "代理模式" : "聊天模式"
          }}</span
          >。
          {{
            mode === "agent"
              ? "您可以描述您想要完成的任务，我将自动创建工作流。"
              : "您可以随时提问，如需创建工作流，请切换到代理模式。"
          }}
        </p>
      </div>

      <!-- Message List -->
      <div v-if="regularMessages.length > 0">
        <div
          v-for="(message, index) in regularMessages"
          :key="message.id"
          :class="[
            message.sender === 'system'
              ? 'flex justify-center mb-4'
              : 'flex mb-6 animate-fade-in',
            message.sender === 'user'
              ? 'justify-end'
              : message.sender === 'system'
              ? 'justify-center'
              : 'justify-start',
          ]"
          :style="{ animationDelay: `${index * 0.05}s` }"
        >
          <!-- System Message -->
          <div
            v-if="message.sender === 'system'"
            class="px-3 py-1 rounded-full bg-slate-700/80 text-xs text-slate-300"
          >
            {{ message.text }}
          </div>

          <!-- User Bubble -->
          <div
            v-else-if="message.sender === 'user'"
            class="max-w-md lg:max-w-xl px-5 py-3.5 rounded-2xl shadow-md bg-gradient-to-r from-emerald-600 to-emerald-500 text-white shadow-emerald-700/20"
          >
            <p class="whitespace-pre-wrap text-sm leading-relaxed">
              {{ message.text }}
            </p>
          </div>

          <!-- AI Message -->
          <div
            v-else
            :class="[
              'max-w-2xl',
              {
                'w-full':
                  message.workflow_id || (message.plan && message.plan.length > 0),
              },
            ]"
          >
            <!-- Standard AI Bubble (no workflow) -->
            <div
              v-if="!message.workflow_id && (!message.plan || message.plan.length === 0)"
              class="max-w-md lg:max-w-lg px-5 py-3.5 rounded-2xl shadow-md bg-slate-800 text-slate-100 border border-slate-700/50 shadow-slate-900/30"
            >
              <p class="whitespace-pre-wrap text-sm leading-relaxed">
                {{ message.text }}
              </p>
            </div>

            <!-- Workflow/Analysis Plan Display -->
            <div v-else class="w-full">
              <!-- Plain text reply -->
              <div
                class="px-5 py-3.5 rounded-2xl shadow-md bg-slate-800 text-slate-100 border border-slate-700/50 shadow-slate-900/30 mb-4"
              >
                <p class="whitespace-pre-wrap text-sm leading-relaxed">
                  {{ message.text }}
                </p>
              </div>

              <!-- Insert PipelineContainer component if we have a workflow -->
              <PipelineContainer
                v-if="
                  currentConversationId &&
                  (message.workflow_id || (message.plan && message.plan.length > 0))
                "
                :conversationId="currentConversationId"
                :workflowId="message.workflow_id"
              />
            </div>
          </div>
        </div>
      </div>
      <div
        v-else-if="!welcomeMessage && !isLoading"
        class="text-center text-slate-500 py-10"
      >
        开始提问吧！
      </div>
    </div>

    <!-- Input Area -->
    <div class="p-4 bg-slate-900/80 border-t border-slate-800/50 shadow-up">
      <div class="max-w-4xl mx-auto flex">
        <input
          v-model="newMessage"
          @keyup.enter="sendMessage"
          class="flex-1 bg-slate-800 border border-slate-700 rounded-l-md px-4 py-2.5 text-white focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-shadow focus:shadow-lg"
          :placeholder="mode === 'agent' ? '描述您想要完成的任务...' : '输入您的问题...'"
          :disabled="!currentConversationId || isLoading"
        />
        <button
          @click="sendMessage"
          class="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2.5 rounded-r-md transition-colors flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="!newMessage.trim() || !currentConversationId || isLoading"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
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
</template>

<style scoped>
.scrollbar-thin::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(71, 85, 105, 0.5);
  border-radius: 20px;
}

.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.6);
}

.shadow-up {
  box-shadow: 0 -4px 15px -3px rgba(0, 0, 0, 0.2), 0 -2px 8px -2px rgba(0, 0, 0, 0.1);
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
  animation: fade-in 0.5s ease-out forwards;
}
</style>
