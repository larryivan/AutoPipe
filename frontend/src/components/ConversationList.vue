<script setup lang="ts">
import { defineProps, defineEmits } from "vue";

interface Conversation {
  id: string;
  title: string;
  messages?: any[]; // 添加可选的messages字段
  // Add other relevant properties if needed
}

interface Props {
  conversations: Conversation[];
  currentConversationId: string | null;
  isLoading: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits([
  "new-conversation",
  "select-conversation",
  "delete-conversation",
]);

const createNewConversation = () => {
  if (props.isLoading) return; // 防止加载时创建新对话
  emit("new-conversation");
};

const selectConversation = (convId: string) => {
  if (props.isLoading || props.currentConversationId === convId) return; // 防止重复选择
  emit("select-conversation", convId);
};

// Note: Delete functionality might require confirmation or more complex handling later
const deleteConversation = (convId: string) => {
  if (props.isLoading) return; // 防止加载时删除对话
  emit("delete-conversation", convId);
};
</script>

<template>
  <div
    class="w-64 p-4 bg-slate-900/50 border-r border-slate-800/50 flex flex-col overflow-y-auto scrollbar-thin"
  >
    <div class="mb-4 flex justify-between items-center">
      <h2 class="text-sm font-medium text-slate-400">对话列表</h2>
      <button
        @click="createNewConversation"
        class="p-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-400 hover:text-slate-200 transition-colors"
        title="新建对话"
        :disabled="isLoading"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z"
            clip-rule="evenodd"
          />
        </svg>
      </button>
    </div>

    <div class="space-y-1.5 flex-1">
      <!-- Loading state can be added here -->
      <p
        v-if="isLoading && conversations.length === 0"
        class="text-slate-500 text-sm text-center py-4"
      >
        加载中...
      </p>
      <p
        v-else-if="!isLoading && conversations.length === 0"
        class="text-slate-500 text-sm text-center py-4"
      >
        没有对话
      </p>
      <button
        v-else
        v-for="conversation in conversations"
        :key="conversation.id"
        @click="selectConversation(conversation.id)"
        class="w-full px-3 py-2 rounded-md text-left text-sm transition-colors flex justify-between items-center group"
        :class="{
          'bg-emerald-600/30 text-emerald-300 border border-emerald-700/30':
            currentConversationId === conversation.id,
          'hover:bg-slate-800 text-slate-300': currentConversationId !== conversation.id,
        }"
        :disabled="isLoading"
      >
        <span class="truncate flex-1 mr-2">{{ conversation.title || "新对话" }}</span>
        <button
          @click.stop="deleteConversation(conversation.id)"
          class="p-1 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity focus:opacity-100"
          title="删除对话"
          v-if="currentConversationId !== conversation.id"
          :disabled="isLoading"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-3.5 w-3.5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
      </button>
    </div>
    <!-- Add other sidebar elements like user info/settings button if needed -->
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
  background: rgba(71, 85, 105, 0.5); /* slate-600 with opacity */
  border-radius: 20px;
}

.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.6); /* slate-500 with opacity */
}
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 按钮禁用样式 */
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
