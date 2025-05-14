<script setup lang="ts">
import { ref, defineProps, defineEmits, computed, onMounted, watch } from "vue";

// 定义文件类型接口
interface FileType {
  id?: string;
  path: string;
  name: string;
  type: string;
  size?: number;  // 修正类型，size是可选的
  children?: FileType[];
}

const props = defineProps({
  files: {
    type: Array as () => FileType[],
    default: () => []
  },
  showFileManager: {
    type: Boolean,
    default: true
  },
  currentPath: {
    type: String,
    default: ""
  }
});

const emit = defineEmits([
  "update:showFileManager",
  "search-files",
  "select-file",
  "delete-file",
  "refresh-files",
  "create-directory",
  "upload-files",
  "view-file",
  "rename-file",
  "download-file",
  "navigate",
  "download-multiple-files" // 新增批量下载事件
]);

const fileInput = ref<HTMLInputElement | null>(null);
const dragover = ref(false);
const fileSearchQuery = ref("");
const localError = ref<string | null>(null);
const isLoading = ref(false);

// 用于跟踪活动上传的状态
interface ActiveUpload {
  id: string;
  name: string;
  size: number;
  progress: number;
  error?: string;
}
const activeUploads = ref<ActiveUpload[]>([]);

// 排序相关状态
const sortBy = ref('name');
const sortDirection = ref('asc');

// 上下文菜单相关状态
const showContextMenu = ref(false);
const contextMenuPosition = ref({ x: 0, y: 0 });
const selectedFileForContextMenu = ref<FileType | null>(null); // 重命名以区分

// 重命名相关状态
const showRenameDialog = ref(false);
const fileToRename = ref<FileType | null>(null);
const newFileName = ref("");

// 批量下载相关状态
const selectedFilesForBatchDownload = ref<Set<string>>(new Set());

// Helper function
const formatFileSize = (size: number): string => {
  if (size < 1024) return size + " B";
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + " KB";
  return (size / (1024 * 1024)).toFixed(1) + " MB";
};

const handleFilesForUpload = (files: FileList) => {
  const newUploads: ActiveUpload[] = [];
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const uploadId = `upload-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    newUploads.push({
      id: uploadId,
      name: file.name,
      size: file.size,
      progress: 0,
    });
  }
  activeUploads.value = [...activeUploads.value, ...newUploads];
  
  emit("upload-files", files, (uploadId: string, progress: number, error?: string) => {
    const upload = activeUploads.value.find(u => u.id === uploadId);
    if (upload) {
      upload.progress = progress;
      if (error) {
        upload.error = error;
      }
      if (progress === 100 && !error) {
        setTimeout(() => {
          activeUploads.value = activeUploads.value.filter(u => u.id !== uploadId);
        }, 5000);
      }
    }
  });
};

const onFileSelected = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (!target.files || target.files.length === 0) return;

  try {
    handleFilesForUpload(target.files);
    target.value = ""; 
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
    handleFilesForUpload(event.dataTransfer.files);
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

const handleFileInputChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (!target || !target.files || target.files.length === 0) return;
  
  try {
    handleFilesForUpload(target.files);
    target.value = '';
  } catch (error) {
    console.error("文件选择错误:", error);
    localError.value = "文件选择过程中出现错误";
    setTimeout(() => {
      localError.value = null;
    }, 3000);
  }
};

const deleteFile = (file: FileType) => {
  if (!file || !file.path || file.path.trim() === "") {
    localError.value = "无效的文件路径";
    setTimeout(() => {
      localError.value = null;
    }, 3000);
    return;
  }
  
  if (confirm(`确定要删除 ${file.name} 吗？`)) {
    emit("delete-file", file.path);
    selectedFilesForBatchDownload.value.delete(file.path); // 从批量选择中移除
  }
};

const viewFile = (filePath: string) => {
  console.log("FileManager - viewFile被调用, 路径:", filePath);
  if (!filePath || filePath.trim() === "") {
    localError.value = "无效的文件路径";
    setTimeout(() => {
      localError.value = null;
    }, 3000);
    return;
  }

  const fileExt = filePath.split(".").pop()?.toLowerCase();
  const binaryFileTypes = ["exe", "dll", "bin", "obj", "o", "so", "dylib"];
  if (fileExt && binaryFileTypes.includes(fileExt)) {
    localError.value = "不支持查看二进制文件";
    setTimeout(() => {
      localError.value = null;
    }, 3000);
    return;
  }

  console.log("FileManager - 发出view-file事件, 路径:", filePath);
  emit("view-file", filePath);
};

const downloadFile = (file: FileType) => {
  if (!file || !file.path || file.path.trim() === "") {
    localError.value = "无效的文件路径";
    setTimeout(() => {
      localError.value = null;
    }, 3000);
    return;
  }
  
  if (file.type === 'folder') {
    localError.value = "不能直接下载文件夹";
    setTimeout(() => {
      localError.value = null;
    }, 3000);
    return;
  }
  
  emit("download-file", file.path);
};

const openRenameDialog = (file: FileType) => {
  fileToRename.value = file;
  newFileName.value = file.name;
  showRenameDialog.value = true;
};

const renameFile = () => {
  if (!fileToRename.value || !newFileName.value.trim()) {
    localError.value = "文件名不能为空";
    return;
  }
  
  if (newFileName.value === fileToRename.value.name) {
    showRenameDialog.value = false;
    return;
  }
  
  emit("rename-file", {
    oldPath: fileToRename.value.path,
    newName: newFileName.value,
    isDirectory: fileToRename.value.type === 'folder'
  });
  
  showRenameDialog.value = false;
};

const cancelRename = () => {
  showRenameDialog.value = false;
  fileToRename.value = null;
  newFileName.value = "";
};

const refreshFiles = () => {
  emit("refresh-files");
  selectedFilesForBatchDownload.value.clear(); // 刷新时清空选择
};

const toggleFileManager = () => {
  emit("update:showFileManager", !props.showFileManager);
};

const handleFileSearch = () => {
  emit("search-files", fileSearchQuery.value);
};

const openCreateDirectoryModal = () => {
  console.log("FileManager - openCreateDirectoryModal被调用");
  emit("create-directory");
};

const getFileIcon = (file: FileType | any) => {
  if (file.type === "directory") {
    return "folder";
  }

  const fileExt = file.name?.split(".").pop()?.toLowerCase();
  const codeTypes = [
    "py", "r", "js", "ts", "c", "cpp", "h", "java", "sh", "pl", "go", "rb",
  ];
  const dataTypes = [
    "csv", "tsv", "txt", "fasta", "fastq", "bam", "sam", "vcf", "gff", "bed",
  ];

  if (codeTypes.includes(fileExt)) return "code";
  if (dataTypes.includes(fileExt)) return "data";

  return "file";
};

// 导航到特定路径
const navigateTo = (path: string) => {
  emit("navigate", path);
};

// 导航到上一级目录
const navigateUp = () => {
  if (!props.currentPath) return;
  
  // 如果当前已经在根目录，直接返回
  if (!props.currentPath.includes('/')) {
    navigateTo('');
    return;
  }
  
  // 否则导航到上一级目录
  const pathParts = props.currentPath.split('/');
  pathParts.pop();
  navigateTo(pathParts.join('/'));
};

// 计算面包屑
const breadcrumbs = computed(() => {
  if (!props.currentPath) return [];
  
  const parts = props.currentPath.split('/');
  const result = [];
  
  // 添加根目录
  result.push({ name: '根目录', path: '' });
  
  // 添加每个子目录
  let currentPath = '';
  for (let i = 0; i < parts.length; i++) {
    if (!parts[i]) continue;
    
    currentPath += (currentPath ? '/' : '') + parts[i];
    result.push({
      name: parts[i],
      path: currentPath
    });
  }
  
  return result;
});

// 处理文件或文件夹点击
const handleItemClick = (file: FileType, event: MouseEvent) => {
  console.log("FileManager - handleItemClick 被触发, 文件:", file);
  // 如果点击的是复选框，则不执行导航或查看操作
  if ((event.target as HTMLElement).tagName === 'INPUT') {
    return;
  }

  if (file.type === 'folder') {
    console.log("FileManager - 导航到文件夹:", file.path);
    navigateTo(file.path);
  } else {
    console.log("FileManager - 查看文件:", file.path);
    viewFile(file.path);
  }
};

// 切换文件选择状态 (用于批量下载)
const toggleFileSelection = (filePath: string) => {
  if (selectedFilesForBatchDownload.value.has(filePath)) {
    selectedFilesForBatchDownload.value.delete(filePath);
  } else {
    selectedFilesForBatchDownload.value.add(filePath);
  }
};

// 检查文件是否被选中 (用于批量下载)
const isFileSelectedForBatch = (filePath: string) => {
  return selectedFilesForBatchDownload.value.has(filePath);
};

// 处理批量下载
const handleBatchDownload = () => {
  if (selectedFilesForBatchDownload.value.size === 0) {
    localError.value = "请至少选择一个文件进行下载";
    setTimeout(() => localError.value = null, 3000);
    return;
  }
  emit("download-multiple-files", Array.from(selectedFilesForBatchDownload.value));
  selectedFilesForBatchDownload.value.clear(); // 下载后清空选择
};

// 处理文件拖放时样式
const handleDragOver = (event: DragEvent) => {
  event.preventDefault();
  dragover.value = true;
};

const handleDragLeave = () => {
  dragover.value = false;
};

// 处理排序
const toggleSort = (field: string) => {
  if (sortBy.value === field) {
    // 如果已经按这个字段排序，则切换方向
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
  } else {
    // 否则设置新的排序字段，默认升序
    sortBy.value = field;
    sortDirection.value = 'asc';
  }
};

// 计算排序后的文件列表
const sortedFiles = computed(() => {
  if (!props.files || props.files.length === 0) return [];

  return [...props.files].sort((a, b) => {
    // 始终将文件夹排在前面
    if (a.type === 'folder' && b.type !== 'folder') return -1;
    if (a.type !== 'folder' && b.type === 'folder') return 1;

    let result = 0;
    // 根据选择的字段排序
    switch (sortBy.value) {
      case 'name':
        result = a.name.localeCompare(b.name);
        break;
      case 'type':
        result = a.type.localeCompare(b.type);
        break;
      case 'size':
        const sizeA = a.size || 0;
        const sizeB = b.size || 0;
        result = sizeA - sizeB;
        break;
      // 加入更多排序选项...
    }

    // 应用排序方向
    return sortDirection.value === 'asc' ? result : -result;
  });
});

// 显示文件上下文菜单
const showFileContextMenu = (event: MouseEvent, file: FileType) => {
  event.preventDefault();
  
  contextMenuPosition.value = {
    x: event.clientX,
    y: event.clientY
  };
  selectedFileForContextMenu.value = file; // 使用新的 ref 名称
  showContextMenu.value = true;
  
  const closeContextMenu = () => {
    showContextMenu.value = false;
    document.removeEventListener('click', closeContextMenu);
  };
  
  setTimeout(() => {
    document.addEventListener('click', closeContextMenu);
  }, 0);
};

// 执行上下文菜单操作
const handleContextMenuAction = (action: string) => {
  if (!selectedFileForContextMenu.value) return; // 使用新的 ref 名称
  
  switch (action) {
    case 'view':
      if (selectedFileForContextMenu.value.type !== 'folder') {
        viewFile(selectedFileForContextMenu.value.path);
      }
      break;
    case 'download':
      if (selectedFileForContextMenu.value.type !== 'folder') {
        downloadFile(selectedFileForContextMenu.value);
      }
      break;
    case 'rename':
      openRenameDialog(selectedFileForContextMenu.value);
      break;
    case 'delete':
      deleteFile(selectedFileForContextMenu.value);
      break;
  }
  
  showContextMenu.value = false;
};

// 测试方法 - 用于检测功能是否正常
const testFunctions = () => {
  console.log("FileManager - 测试功能");
  
  // 测试创建文件夹
  console.log("FileManager - 测试新建文件夹功能");
  emit("create-directory");
  
  // 模拟1秒后测试查看文件功能
  setTimeout(() => {
    if (props.files && props.files.length > 0) {
      // 找到第一个非文件夹文件
      const testFile = props.files.find(f => f.type !== 'folder');
      if (testFile) {
        console.log("FileManager - 测试查看文件功能, 文件:", testFile);
        viewFile(testFile.path);
      } else {
        console.log("FileManager - 没有找到可测试的文件");
      }
    } else {
      console.log("FileManager - 文件列表为空，无法测试查看文件功能");
    }
  }, 1000);
};

onMounted(() => {
  console.log("FileManager mounted, files:", props.files);
  
  // 延迟2秒测试功能，确保文件列表已加载
  // setTimeout(testFunctions, 2000);
});

watch(() => props.files, (newFiles) => {
  console.log("FileManager - files changed:", newFiles);
  // 当文件列表变化时（例如导航到新目录），清空选择
  selectedFilesForBatchDownload.value.clear();
}, { deep: true });

watch(() => props.currentPath, (newPath) => {
  console.log("FileManager - currentPath changed:", newPath);
  selectedFilesForBatchDownload.value.clear(); // 路径变化时清空选择
});

</script>

<template>
  <div class="file-manager">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <svg xmlns="http://www.w3.org/2000/svg" class="search-icon" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
      </svg>
      <input
        type="text"
        v-model="fileSearchQuery"
        @input="handleFileSearch"
        placeholder="搜索文件..."
        class="search-input"
      />
    </div>
    
    <!-- 错误信息 -->
    <div v-if="localError" class="error-message">
      {{ localError }}
    </div>
    
    <!-- 面包屑导航 -->
    <div class="breadcrumb-nav">
      <div class="breadcrumb-container">
        <span 
          v-for="(crumb, index) in breadcrumbs" 
          :key="crumb.path"
          class="breadcrumb-item"
        >
          <span 
            class="breadcrumb-link" 
            @click="navigateTo(crumb.path)"
          >
            {{ crumb.name }}
          </span>
          <span v-if="index < breadcrumbs.length - 1" class="breadcrumb-separator">/</span>
        </span>
      </div>
      <button v-if="props.currentPath" @click="navigateUp" class="nav-up-btn" title="返回上级目录">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
        </svg>
      </button>
    </div>
    
    <!-- 操作按钮区域 -->
    <div class="actions-area">
      <div 
        class="upload-area" 
        @dragover="handleDragOver" 
        @dragleave="handleDragLeave" 
        @drop="onFileDrop"
        :class="{'drag-over': dragover}"
      >
        <button @click="triggerFileUpload" class="action-btn-main upload-btn">
          <svg xmlns="http://www.w3.org/2000/svg" class="icon-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <span>上传</span>
        </button>
        <button @click="openCreateDirectoryModal" class="action-btn-main create-btn">
          <svg xmlns="http://www.w3.org/2000/svg" class="icon-sm" viewBox="0 0 20 20" fill="currentColor">
            <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
          </svg>
          <span>新建</span>
        </button>
        <input type="file" ref="fileInput" class="hidden" @change="handleFileInputChange" multiple />
      </div>
      <button 
        v-if="selectedFilesForBatchDownload.size > 0" 
        @click="handleBatchDownload" 
        class="action-btn-main batch-download-btn"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="icon-sm" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
        <span>下载选中 ({{ selectedFilesForBatchDownload.size }})</span>
      </button>
    </div>
    
    <!-- 拖放提示区域 -->
    <div v-if="dragover" class="drag-drop-overlay">
      <div class="drag-drop-container">
        <svg xmlns="http://www.w3.org/2000/svg" class="drag-drop-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p class="drag-drop-text">拖放文件到这里上传</p>
      </div>
    </div>

    <!-- 上传进度显示区域 -->
    <div v-if="activeUploads.length > 0" class="upload-progress-area">
      <div v-for="upload in activeUploads" :key="upload.id" class="upload-item">
        <div class="upload-info">
          <span class="upload-name">{{ upload.name }} ({{ formatFileSize(upload.size) }})</span>
          <span v-if="upload.error" class="upload-error-text">{{ upload.error }}</span>
          <span v-else class="upload-progress-text">{{ upload.progress.toFixed(0) }}%</span>
        </div>
        <div class="progress-bar-container">
          <div 
            class="progress-bar" 
            :style="{ width: upload.progress + '%' }"
            :class="{ 'error': upload.error }"
          ></div>
        </div>
      </div>
    </div>
    
    <!-- 排序控制 -->
    <div class="sort-controls">
      <span class="sort-label">排序:</span>
      <button 
        @click="toggleSort('name')" 
        class="sort-btn" 
        :class="{ active: sortBy === 'name' }"
      >
        名称
        <svg v-if="sortBy === 'name'" xmlns="http://www.w3.org/2000/svg" class="sort-icon" viewBox="0 0 20 20" fill="currentColor">
          <path v-if="sortDirection === 'asc'" fill-rule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clip-rule="evenodd" />
          <path v-else fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
      </button>
      <button 
        @click="toggleSort('type')" 
        class="sort-btn" 
        :class="{ active: sortBy === 'type' }"
      >
        类型
        <svg v-if="sortBy === 'type'" xmlns="http://www.w3.org/2000/svg" class="sort-icon" viewBox="0 0 20 20" fill="currentColor">
          <path v-if="sortDirection === 'asc'" fill-rule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clip-rule="evenodd" />
          <path v-else fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
      </button>
      <button 
        @click="toggleSort('size')" 
        class="sort-btn" 
        :class="{ active: sortBy === 'size' }"
      >
        大小
        <svg v-if="sortBy === 'size'" xmlns="http://www.w3.org/2000/svg" class="sort-icon" viewBox="0 0 20 20" fill="currentColor">
          <path v-if="sortDirection === 'asc'" fill-rule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clip-rule="evenodd" />
          <path v-else fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
      </button>
    </div>
    
    <!-- 文件列表 -->
    <div class="file-list">
      <!-- 加载中状态 -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>
      
      <!-- 空文件状态 -->
      <div v-else-if="!props.files || props.files.length === 0" class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" class="empty-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012-2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
        </svg>
        <p>沒有文件</p>
      </div>
      
      <!-- 文件列表内容 -->
      <div v-else class="file-items">
        <div v-for="file in sortedFiles" :key="file.id || file.path" class="file-item">
          <div 
            class="file-row" 
            :class="{'folder': file.type === 'folder', 'selected-for-batch': isFileSelectedForBatch(file.path)}" 
            @click="handleItemClick(file, $event)"
            @contextmenu="showFileContextMenu($event, file)"
          >
            <input 
              v-if="file.type !== 'folder'"
              type="checkbox"
              :checked="isFileSelectedForBatch(file.path)"
              @change="toggleFileSelection(file.path)"
              @click.stop 
              class="file-checkbox"
            />
            <span class="file-icon">
              <svg v-if="file.type === 'folder'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
              </svg>
            </span>
            <span class="file-name">{{ file.name }}</span>
            <div class="file-actions">
              <button v-if="file.type !== 'folder'" @click.stop="viewFile(file.path)" class="action-btn view-btn" title="查看文件">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                  <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" />
                </svg>
              </button>
              <button v-if="file.type !== 'folder'" @click.stop="downloadFile(file)" class="action-btn download-btn" title="下载文件">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              </button>
              <button @click.stop="openRenameDialog(file)" class="action-btn rename-btn" title="重命名">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                </svg>
              </button>
              <button @click.stop="deleteFile(file)" class="action-btn delete-btn" title="删除文件">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
          <div v-if="file.type === 'folder' && file.children && file.children.length > 0" class="subfolder">
            <div v-for="childFile in file.children" :key="childFile.id || childFile.path" class="file-item child-item">
              <div 
                class="file-row" 
                @click="childFile.type !== 'folder' ? viewFile(`${file.path}/${childFile.name}`) : navigateTo(`${file.path}/${childFile.name}`)"
                @contextmenu="showFileContextMenu($event, {
                  ...childFile,
                  path: `${file.path}/${childFile.name}`
                })"
              >
                <span class="file-icon child-icon">
                  <svg v-if="childFile.type === 'folder'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                  </svg>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
                  </svg>
                </span>
                <span class="file-name">{{ childFile.name }}</span>
                <div class="file-actions">
                  <button v-if="childFile.type !== 'folder'" @click.stop="viewFile(`${file.path}/${childFile.name}`)" class="action-btn view-btn" title="查看文件">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                      <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <button v-if="childFile.type !== 'folder'" @click.stop="downloadFile(childFile)" class="action-btn download-btn" title="下载文件">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <button @click.stop="openRenameDialog(childFile)" class="action-btn rename-btn" title="重命名">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                    </svg>
                  </button>
                  <button @click.stop="deleteFile(childFile)" class="action-btn delete-btn" title="删除文件">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 上传进度显示区域 -->
    <div v-if="activeUploads.length > 0" class="upload-progress-area">
      <div v-for="upload in activeUploads" :key="upload.id" class="upload-item">
        <div class="upload-info">
          <span class="upload-name">{{ upload.name }} ({{ formatFileSize(upload.size) }})</span>
          <span v-if="upload.error" class="upload-error-text">{{ upload.error }}</span>
          <span v-else class="upload-progress-text">{{ upload.progress.toFixed(0) }}%</span>
        </div>
        <div class="progress-bar-container">
          <div 
            class="progress-bar" 
            :style="{ width: upload.progress + '%' }"
            :class="{ 'error': upload.error }"
          ></div>
        </div>
      </div>
    </div>
    
    <!-- 底部按钮 -->
    <div class="footer-actions">
      <button @click="refreshFiles" class="refresh-btn">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mr-1.5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
        </svg>
        <span>刷新文件列表</span>
      </button>
    </div>
    
    <!-- 重命名对话框 -->
    <div v-if="showRenameDialog" class="modal-overlay">
      <div class="modal-container">
        <div class="modal-header">
          <h3 class="modal-title">重命名</h3>
          <button @click="cancelRename" class="modal-close-btn">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="newFileName" class="form-label">新名称:</label>
            <input 
              type="text" 
              id="newFileName" 
              v-model="newFileName" 
              class="form-input" 
              @keyup.enter="renameFile"
              ref="renameInput"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="cancelRename" class="modal-btn cancel-btn">取消</button>
          <button @click="renameFile" class="modal-btn confirm-btn">确认</button>
        </div>
      </div>
    </div>
    
    <!-- 上下文菜单 -->
    <div 
      v-if="showContextMenu" 
      class="context-menu" 
      :style="{ 
        top: `${contextMenuPosition.y}px`, 
        left: `${contextMenuPosition.x}px` 
      }"
    >
      <button 
        v-if="selectedFileForContextMenu && selectedFileForContextMenu.type !== 'folder'" 
        @click="handleContextMenuAction('view')" 
        class="context-menu-item"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="context-menu-icon" viewBox="0 0 20 20" fill="currentColor">
          <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
          <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" />
        </svg>
        <span>查看</span>
      </button>
      <button 
        v-if="selectedFileForContextMenu && selectedFileForContextMenu.type !== 'folder'" 
        @click="handleContextMenuAction('download')" 
        class="context-menu-item"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="context-menu-icon" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
        <span>下载</span>
      </button>
      <button 
        @click="handleContextMenuAction('rename')" 
        class="context-menu-item"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="context-menu-icon" viewBox="0 0 20 20" fill="currentColor">
          <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
        </svg>
        <span>重命名</span>
      </button>
      <button 
        @click="handleContextMenuAction('delete')" 
        class="context-menu-item delete"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="context-menu-icon" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <span>删除</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.file-manager {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  height: 100%;
}

/* 搜索栏 */
.search-bar {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  width: 16px;
  height: 16px;
  color: rgba(148, 163, 184, 0.7);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 8px 12px 8px 32px;
  background-color: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(71, 85, 105, 0.3);
  border-radius: 6px;
  color: rgba(226, 232, 240, 0.9);
  font-size: 0.8125rem;
  transition: all 0.2s ease;
}

.search-input:focus {
  outline: none;
  border-color: rgba(56, 189, 248, 0.4);
  background-color: rgba(30, 41, 59, 0.6);
  box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.1);
}

.search-input::placeholder {
  color: rgba(148, 163, 184, 0.6);
}

/* 错误信息 */
.error-message {
  padding: 8px 12px;
  background-color: rgba(220, 38, 38, 0.15);
  border-left: 2px solid rgba(220, 38, 38, 0.7);
  border-radius: 4px;
  color: rgba(254, 202, 202, 0.9);
  font-size: 0.75rem;
}

/* 操作按钮区域 */
.actions-area {
  display: flex;
  justify-content: space-between; /* 使按钮分布在两端 */
  align-items: center; /* 垂直居中对齐 */
  gap: 0.5rem;
  margin-bottom: 0.5rem; /* 与原 upload-area 的 margin 一致 */
}

/* 上传区域 */
.upload-area {
  display: flex; /* 保持内部按钮的 flex 布局 */
  gap: 0.5rem;
  flex-grow: 1; /* 允许上传和新建按钮区域占据可用空间 */
}

/* 文件列表 */
.file-list {
  flex-grow: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  border-radius: 6px;
  background-color: rgba(15, 23, 42, 0.3);
  min-height: 100px;
}

.file-list::-webkit-scrollbar {
  width: 4px;
}

.file-list::-webkit-scrollbar-track {
  background: transparent;
}

.file-list::-webkit-scrollbar-thumb {
  background: rgba(71, 85, 105, 0.4);
  border-radius: 8px;
}

.file-list::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.6);
}

/* 加载状态 */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 100px;
  color: rgba(148, 163, 184, 0.7);
  font-size: 0.75rem;
  gap: 8px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(56, 189, 248, 0.3);
  border-top-color: rgba(56, 189, 248, 0.8);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 100px;
  color: rgba(148, 163, 184, 0.7);
  font-size: 0.75rem;
  gap: 8px;
}

.empty-icon {
  width: 24px;
  height: 24px;
  color: rgba(100, 116, 139, 0.5);
}

/* 文件项 */
.file-items {
  padding: 0.25rem;
}

.file-item {
  margin-bottom: 1px;
}

.file-row {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  border-radius: 4px;
  transition: background-color 0.15s ease;
  cursor: pointer;
}

.file-row:hover {
  background-color: rgba(30, 41, 59, 0.5);
}

.file-row.folder {
  background-color: rgba(30, 41, 59, 0.2);
}

.file-icon {
  width: 16px;
  height: 16px;
  margin-right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-row.folder .file-icon svg {
  color: rgba(56, 189, 248, 0.8);
}

.file-row:not(.folder) .file-icon svg {
  color: rgba(148, 163, 184, 0.7);
}

.file-name {
  flex-grow: 1;
  font-size: 0.8125rem;
  color: rgba(226, 232, 240, 0.9);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.file-row:hover .file-actions {
  opacity: 1;
}

.action-btn {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background-color: rgba(51, 65, 85, 0.7);
}

.action-btn svg {
  width: 14px;
  height: 14px;
}

.view-btn svg {
  color: rgba(56, 189, 248, 0.8);
}

.delete-btn svg {
  color: rgba(239, 68, 68, 0.8);
}

/* 子文件夹 */
.subfolder {
  margin-left: 16px;
  padding-left: 8px;
  border-left: 1px solid rgba(51, 65, 85, 0.4);
}

.child-icon {
  width: 14px;
  height: 14px;
}

/* 底部按钮 */
.footer-actions {
  margin-top: auto;
}

.refresh-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  border-radius: 6px;
  font-size: 0.75rem;
  transition: all 0.2s ease;
  background-color: rgba(30, 41, 59, 0.4);
  color: rgba(226, 232, 240, 0.9);
}

.refresh-btn:hover {
  background-color: rgba(51, 65, 85, 0.7);
}

.refresh-btn svg {
  color: rgba(125, 211, 252, 0.8);
}

/* 上传进度条样式 */
.upload-progress-area {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background-color: rgba(15, 23, 42, 0.3); /* 与 file-list 背景色一致或相似 */
  border-radius: 6px;
}

.upload-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.upload-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem; /* 调整为与文件列表项相似 */
  color: rgba(226, 232, 240, 0.8);
}

.upload-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%; /* 避免文件名过长挤压进度百分比 */
}

.upload-progress-text {
  color: rgba(56, 189, 248, 0.9); /* 进度条蓝色 */
}

.upload-error-text {
  color: rgba(239, 68, 68, 0.9); /* 错误红色 */
  font-size: 0.7rem;
}

.progress-bar-container {
  width: 100%;
  height: 6px; /* 进度条高度 */
  background-color: rgba(30, 41, 59, 0.5); /* 进度条背景色 */
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: rgba(56, 189, 248, 0.7); /* 进度条颜色 */
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-bar.error {
  background-color: rgba(220, 38, 38, 0.7); /* 错误时进度条颜色 */
}

/* 新增按钮样式 */
.download-btn svg {
  color: rgba(245, 158, 11, 0.8); /* 下载按钮橙色 */
}

.rename-btn svg {
  color: rgba(167, 139, 250, 0.8); /* 重命名按钮紫色 */
}

/* 模态对话框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-container {
  background-color: rgba(15, 23, 42, 0.95);
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  border: 1px solid rgba(71, 85, 105, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(71, 85, 105, 0.3);
}

.modal-title {
  font-size: 1rem;
  font-weight: 600;
  color: rgba(226, 232, 240, 0.9);
  margin: 0;
}

.modal-close-btn {
  width: 20px;
  height: 20px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: rgba(148, 163, 184, 0.7);
}

.modal-close-btn:hover {
  color: rgba(226, 232, 240, 0.9);
}

.modal-body {
  padding: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-size: 0.875rem;
  color: rgba(226, 232, 240, 0.9);
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid rgba(71, 85, 105, 0.3);
  background-color: rgba(30, 41, 59, 0.4);
  color: rgba(226, 232, 240, 0.9);
  font-size: 0.875rem;
}

.form-input:focus {
  outline: none;
  border-color: rgba(56, 189, 248, 0.4);
  box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.1);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  padding: 16px;
  border-top: 1px solid rgba(71, 85, 105, 0.3);
  gap: 8px;
}

.modal-btn {
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cancel-btn {
  background-color: transparent;
  border: 1px solid rgba(71, 85, 105, 0.3);
  color: rgba(226, 232, 240, 0.9);
}

.cancel-btn:hover {
  background-color: rgba(51, 65, 85, 0.5);
}

.confirm-btn {
  background-color: rgba(56, 189, 248, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: rgba(56, 189, 248, 0.9);
}

.confirm-btn:hover {
  background-color: rgba(56, 189, 248, 0.3);
}

/* 面包屑导航 */
.breadcrumb-nav {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background-color: rgba(30, 41, 59, 0.4);
  border-radius: 6px;
  margin-bottom: 0.5rem;
  overflow-x: auto;
  white-space: nowrap;
  scrollbar-width: none; /* 隐藏Firefox滚动条 */
}

.breadcrumb-nav::-webkit-scrollbar {
  display: none; /* 隐藏Chrome滚动条 */
}

.breadcrumb-container {
  flex-grow: 1;
  overflow-x: auto;
  white-space: nowrap;
  scrollbar-width: none;
}

.breadcrumb-container::-webkit-scrollbar {
  display: none;
}

.breadcrumb-item {
  display: inline-flex;
  align-items: center;
  font-size: 0.75rem;
  color: rgba(148, 163, 184, 0.7);
}

.breadcrumb-link {
  cursor: pointer;
  transition: color 0.2s ease;
  padding: 2px 4px;
  border-radius: 4px;
}

.breadcrumb-link:hover {
  color: rgba(226, 232, 240, 0.9);
  background-color: rgba(51, 65, 85, 0.5);
}

.breadcrumb-separator {
  margin: 0 4px;
  color: rgba(100, 116, 139, 0.6);
}

.nav-up-btn {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
  color: rgba(148, 163, 184, 0.7);
  background-color: transparent;
  border: none;
  flex-shrink: 0;
  margin-left: 8px;
}

.nav-up-btn:hover {
  color: rgba(226, 232, 240, 0.9);
  background-color: rgba(51, 65, 85, 0.5);
}

/* 拖放覆盖层 */
.drag-drop-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(15, 23, 42, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.drag-drop-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  border: 3px dashed rgba(56, 189, 248, 0.5);
  border-radius: 1rem;
  background-color: rgba(30, 41, 59, 0.7);
}

.drag-drop-icon {
  width: 64px;
  height: 64px;
  color: rgba(56, 189, 248, 0.8);
  margin-bottom: 1rem;
}

.drag-drop-text {
  font-size: 1.25rem;
  color: rgba(226, 232, 240, 0.9);
}

/* 排序控制 */
.sort-controls {
  display: flex;
  align-items: center;
  padding: 0.5rem;
  margin-bottom: 0.5rem;
  background-color: rgba(30, 41, 59, 0.4);
  border-radius: 6px;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.sort-label {
  font-size: 0.75rem;
  color: rgba(148, 163, 184, 0.7);
  margin-right: 0.5rem;
}

.sort-btn {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  color: rgba(226, 232, 240, 0.8);
  background-color: transparent;
  border: 1px solid rgba(71, 85, 105, 0.3);
  display: flex;
  align-items: center;
  gap: 0.25rem;
  transition: all 0.2s ease;
}

.sort-btn:hover, .sort-btn.active {
  background-color: rgba(51, 65, 85, 0.7);
  border-color: rgba(56, 189, 248, 0.4);
}

.sort-icon {
  width: 12px;
  height: 12px;
  color: rgba(56, 189, 248, 0.8);
}

/* 上下文菜单 */
.context-menu {
  position: fixed;
  background-color: rgba(15, 23, 42, 0.95);
  border-radius: 6px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(71, 85, 105, 0.3);
  padding: 0.5rem;
  z-index: 1000;
  width: 160px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  width: 100%;
  text-align: left;
  border-radius: 4px;
  font-size: 0.875rem;
  color: rgba(226, 232, 240, 0.9);
  background-color: transparent;
  transition: background-color 0.2s ease;
}

.context-menu-item:hover {
  background-color: rgba(51, 65, 85, 0.7);
}

.context-menu-item.delete {
  color: rgba(239, 68, 68, 0.8);
}

.context-menu-item.delete:hover {
  background-color: rgba(239, 68, 68, 0.15);
}

.context-menu-icon {
  width: 16px;
  height: 16px;
}

/* 批量下载相关样式 */
.file-checkbox {
  margin-right: 10px; /* 稍微增加与图标的间距 */
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  cursor: pointer;
  accent-color: #0ea5e9; /* Tailwind Sky 500 - 更鲜明一些 */
  vertical-align: middle; /* 使其与图标和文本更好地对齐 */
}

.file-row.selected-for-batch {
  background-color: rgba(14, 165, 233, 0.15); /* Sky 500 with 15% opacity */
  border-left: 3px solid #0ea5e9; /* Sky 500 */
  box-shadow: inset 0 0 5px rgba(14, 165, 233, 0.1); /* 轻微内阴影增加层次感 */
}

.actions-area {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem; /* 稍微增加按钮组之间的间距 */
  margin-bottom: 0.75rem;
  padding: 0.25rem; /* 为整个区域添加一点内边距 */
  background-color: rgba(30, 41, 59, 0.5); /* 给操作区一个轻微的背景 */
  border-radius: 6px;
}

.upload-area {
  display: flex;
  gap: 0.5rem;
  /* flex-grow: 1; // 移除，让批量下载按钮有自己的空间 */
}

.action-btn-main {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.6rem 1rem; /* 增加内边距，使按钮更大方 */
  border-radius: 6px;
  font-size: 0.8125rem; /* 稍微增大字体 */
  font-weight: 500;
  transition: all 0.2s ease;
  background-color: rgba(51, 65, 85, 0.7); /* 调整背景色 */
  color: rgba(226, 232, 240, 0.95); /* 提高文本对比度 */
  border: 1px solid rgba(71, 85, 105, 0.6);
  white-space: nowrap;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05); /* 添加细微阴影 */
}

.action-btn-main:hover {
  background-color: rgba(71, 85, 105, 0.9);
  border-color: rgba(100, 116, 139, 0.8);
  transform: translateY(-1px); /* 轻微上浮效果 */
  box-shadow: 0 2px 4px rgba(0,0,0,0.07);
}

.action-btn-main .icon-sm {
  width: 16px;
  height: 16px;
  margin-right: 0.5rem; /* 增大图标和文本间距 */
}

.upload-btn .icon-sm {
  color: #38bdf8; /* Sky 400 */
}

.create-btn .icon-sm {
  color: #34d399; /* Emerald 400 */
}

.batch-download-btn {
  background-color: rgba(14, 165, 233, 0.8); /* Sky 500, 更强的背景色 */
  border-color: rgba(14, 165, 233, 1); /* Sky 500 */
  color: #ffffff;
}

.batch-download-btn:hover {
  background-color: rgba(11, 131, 189, 1); /* Sky 600 */
  border-color: rgba(11, 131, 189, 1);
}

.batch-download-btn .icon-sm {
  color: #ffffff;
}

/* 文件列表项的间距调整 */
.file-items {
  padding: 0.25rem;
}

.file-item {
  margin-bottom: 2px; /* 增加文件行之间的间距 */
}

.file-row {
  padding: 8px 10px; /* 调整内边距 */
  border-radius: 5px; /* 更圆润的边角 */
}

</style>
