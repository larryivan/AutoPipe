<script setup lang="ts">
import { ref, defineProps, defineEmits, computed } from "vue";

interface ProjectFile {
  id: string;
  name: string;
  path: string;
  size: number;
  type?: string; // 'file' or 'directory'
  // Add other relevant properties
}

interface Props {
  files: ProjectFile[] | any[]; // 修改类型定义，兼容非类型化数据
  conversationId: string | null;
  isLoading: boolean;
  showFileManager: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits([
  "update:showFileManager",
  "refresh-files",
  "upload-files",
  "delete-file",
  "view-file",
  "create-file",
  "create-directory",
  "search-files",
]);

const fileInput = ref<HTMLInputElement | null>(null);
const dragover = ref(false);
const fileSearchQuery = ref("");
const localError = ref<string | null>(null); // 添加本地错误状态

// Helper function from App.vue
const formatFileSize = (size: number): string => {
  if (size < 1024) return size + " B";
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + " KB";
  return (size / (1024 * 1024)).toFixed(1) + " MB";
};

const onFileSelected = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (!target.files || target.files.length === 0) return;

  // 移除文件大小限制，直接上传文件
  try {
    emit("upload-files", target.files);
    target.value = ""; // Reset input
    localError.value = null;
  } catch (error) {
    console.error("文件选择错误:", error);
    localError.value = "文件选择过程中出现错误";
    setTimeout(() => {
      localError.value = null;
    }, 3000);
  }
};

const onFileDrop = (event: DragEvent) => {
  dragover.value = false;
  if (!event.dataTransfer?.files || event.dataTransfer.files.length === 0) return;

  try {
    // 移除文件大小限制，直接上传文件
    emit("upload-files", event.dataTransfer.files);
    localError.value = null;
  } catch (error) {
    console.error("文件拖放错误:", error);
    localError.value = "文件拖放过程中出现错误";
    setTimeout(() => {
      localError.value = null;
    }, 3000);
  }
};

const triggerFileUpload = () => {
  fileInput.value?.click();
};

const deleteFile = (filePath: string) => {
  // 添加简单验证确保路径存在
  if (!filePath || filePath.trim() === "") {
    localError.value = "无效的文件路径";
    setTimeout(() => {
      localError.value = null;
    }, 3000);
    return;
  }
  emit("delete-file", filePath);
};

const viewFile = (filePath: string) => {
  // 验证文件路径
  if (!filePath || filePath.trim() === "") {
    localError.value = "无效的文件路径";
    setTimeout(() => {
      localError.value = null;
    }, 3000);
    return;
  }

  // 验证文件类型是否可查看
  const fileExt = filePath.split(".").pop()?.toLowerCase();
  const binaryFileTypes = ["exe", "dll", "bin", "obj", "o", "so", "dylib"];
  if (fileExt && binaryFileTypes.includes(fileExt)) {
    localError.value = "不支持查看二进制文件";
    setTimeout(() => {
      localError.value = null;
    }, 3000);
    return;
  }

  emit("view-file", filePath);
};

const refreshFiles = () => {
  emit("refresh-files");
};

const toggleFileManager = () => {
  emit("update:showFileManager", !props.showFileManager);
};

const handleFileSearch = () => {
  emit("search-files", fileSearchQuery.value);
};

// Placeholder for create file/directory modal trigger
const openCreateFileModal = () => {
  emit("create-file");
};

const openCreateDirectoryModal = () => {
  emit("create-directory");
};

// 添加文件类型判断函数
const getFileIcon = (file: ProjectFile | any) => {
  if (file.type === "directory") {
    return "folder";
  }

  const fileExt = file.name?.split(".").pop()?.toLowerCase();
  const codeTypes = [
    "py",
    "r",
    "js",
    "ts",
    "c",
    "cpp",
    "h",
    "java",
    "sh",
    "pl",
    "go",
    "rb",
  ];
  const dataTypes = [
    "csv",
    "tsv",
    "txt",
    "fasta",
    "fastq",
    "bam",
    "sam",
    "vcf",
    "gff",
    "bed",
  ];

  if (codeTypes.includes(fileExt)) return "code";
  if (dataTypes.includes(fileExt)) return "data";

  return "file";
};
</script>

<template>
  <div
    :class="[
      'w-96 bg-slate-900/60 border-l border-slate-800/50 overflow-y-auto transition-all duration-300 scrollbar-thin',
      {
        'translate-x-0': showFileManager,
        'translate-x-full absolute right-0 top-0 bottom-0 lg:relative lg:translate-x-0': !showFileManager,
        'opacity-0 invisible': !showFileManager,
      },
      {
        'fixed right-0 top-0 bottom-0 z-50 lg:relative lg:z-auto': showFileManager,
      },
    ]"
    style="height: calc(100vh - 65px)"
  >
    <div class="p-4">
      <div class="flex justify-between items-center mb-4">
        <h2 class="font-medium text-slate-300">文件管理</h2>
        <button
          @click="toggleFileManager"
          class="p-1.5 bg-slate-800 hover:bg-slate-700 rounded-md text-slate-400 hover:text-slate-200 lg:hidden transition-colors"
          title="关闭文件管理"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
      </div>

      <!-- 错误提示 -->
      <div
        v-if="localError"
        class="mb-4 p-2 bg-red-900/50 border border-red-800 rounded-md text-red-200 text-sm"
      >
        {{ localError }}
      </div>

      <!-- Command Terminal Placeholder/Slot -->
      <slot name="terminal"></slot>

      <!-- File Upload Area -->
      <div
        class="mb-4 border-2 border-dashed border-slate-700 rounded-lg p-4 text-center"
        @dragover.prevent="dragover = true"
        @dragleave.prevent="dragover = false"
        @drop.prevent="onFileDrop"
        :class="{ 'bg-slate-800/50 border-emerald-600': dragover }"
      >
        <input
          type="file"
          ref="fileInput"
          @change="onFileSelected"
          class="hidden"
          multiple
        />
        <div v-if="!dragover">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-10 w-10 mx-auto text-slate-600 mb-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1"
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p class="text-sm text-slate-400 mb-1">
            拖拽文件到这里或
            <button
              @click.stop="triggerFileUpload"
              class="text-emerald-500 hover:text-emerald-400 font-medium transition-colors"
              :disabled="isLoading"
            >
              浏览文件
            </button>
          </p>
          <p class="text-xs text-slate-500">支持多种生物信息学数据文件</p>
        </div>
        <div v-else>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-10 w-10 mx-auto text-emerald-500 mb-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p class="text-sm text-emerald-300 font-medium">松开鼠标上传文件</p>
        </div>
        <div v-if="isLoading" class="mt-2 text-sm text-slate-400">上传中...</div>
      </div>

      <!-- Create Buttons -->
      <div class="mb-4 flex space-x-2">
        <button
          @click="openCreateFileModal"
          class="flex-1 px-3 py-1.5 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-md text-sm text-center transition-colors"
          :disabled="!conversationId || isLoading"
        >
          创建文件
        </button>
        <button
          @click="openCreateDirectoryModal"
          class="flex-1 px-3 py-1.5 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-md text-sm text-center transition-colors"
          :disabled="!conversationId || isLoading"
        >
          创建目录
        </button>
      </div>

      <!-- File Search -->
      <div class="mb-4 relative">
        <input
          type="text"
          v-model="fileSearchQuery"
          @keyup.enter="handleFileSearch"
          placeholder="搜索文件..."
          class="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500 pl-8"
          :disabled="isLoading"
        />
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4 absolute left-2.5 top-1/2 transform -translate-y-1/2 text-slate-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </div>

      <!-- File List -->
      <div class="mb-2 flex justify-between items-center">
        <h3 class="text-sm font-medium text-slate-400">文件列表</h3>
        <button
          @click="refreshFiles"
          class="p-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-400 hover:text-slate-200 transition-colors"
          title="刷新文件列表"
          :disabled="isLoading"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </div>

      <div
        v-if="isLoading && (!files || files.length === 0)"
        class="text-center py-8 text-slate-500 text-sm"
      >
        加载中...
      </div>
      <div
        v-else-if="!files || files.length === 0"
        class="text-center py-8 text-slate-500 text-sm"
      >
        当前对话没有文件<span v-if="fileSearchQuery">匹配 "{{ fileSearchQuery }}"</span>。
      </div>
      <div v-else class="space-y-2">
        <div
          v-for="file in files"
          :key="file.path"
          class="p-2.5 bg-slate-800/50 rounded-md border border-slate-700/60 flex items-center group cursor-pointer hover:bg-slate-800 transition-colors"
          @click="viewFile(file.path)"
        >
          <!-- File Icon with enhanced icon logic -->
          <div
            class="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-slate-700/30 rounded-md text-slate-300"
          >
            <!-- Folder icon -->
            <svg
              v-if="getFileIcon(file) === 'folder'"
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4 text-yellow-300"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"
              />
            </svg>
            <!-- Code file icon -->
            <svg
              v-else-if="getFileIcon(file) === 'code'"
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4 text-blue-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z"
                clip-rule="evenodd"
              />
            </svg>
            <!-- Data file icon -->
            <svg
              v-else-if="getFileIcon(file) === 'data'"
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4 text-green-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z"
              />
              <path
                d="M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z"
              />
              <path d="M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z" />
            </svg>
            <!-- Default file icon -->
            <svg
              v-else
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                clip-rule="evenodd"
              />
            </svg>
          </div>
          <!-- File Info -->
          <div class="ml-3 flex-1 min-w-0">
            <div class="text-sm font-medium text-slate-200 truncate" :title="file.name">
              {{ file.name }}
            </div>
            <div class="text-xs text-slate-500">
              <span v-if="file.type !== 'directory'"
                >{{ formatFileSize(file.size) }} ·
              </span>
              {{ file.type || "文件" }}
            </div>
          </div>
          <!-- Delete Button -->
          <button
            @click.stop="deleteFile(file.path)"
            class="ml-2 p-1.5 text-slate-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity focus:opacity-100"
            title="删除"
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
                d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Add scoped styles if needed */
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
