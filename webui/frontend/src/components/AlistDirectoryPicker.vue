<template>
  <el-dialog v-model="visible" title="选择目录" width="700px" @close="handleClose">
    <!-- AList 选择器 -->
    <el-form inline class="mb-16">
      <el-form-item label="AList 服务器">
        <el-select v-model="selectedAlistId" placeholder="选择 AList" @change="loadFiles" style="width: 200px">
          <el-option v-for="alist in alists" :key="alist.id" :label="alist.id" :value="alist.id" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button @click="refresh" :loading="loading" :disabled="!selectedAlistId">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </el-form-item>
    </el-form>

    <!-- 面包屑导航 -->
    <el-breadcrumb separator="/" class="mb-16" v-if="currentPath">
      <el-breadcrumb-item @click="navigateTo('/')">根目录</el-breadcrumb-item>
      <el-breadcrumb-item v-for="(part, index) in pathParts" :key="index" @click="navigateToPart(index)">
        {{ part }}
      </el-breadcrumb-item>
    </el-breadcrumb>

    <!-- 文件列表 -->
    <div v-loading="loading" style="min-height: 300px; max-height: 400px; overflow-y: auto;">
      <el-table :data="files" border stripe @row-dblclick="handleDblClick" @current-change="handleSelect">
        <el-table-column label="名称" min-width="200">
          <template #default="{ row }">
            <el-icon v-if="row.is_dir" style="color: #E6A23C"><Folder /></el-icon>
            <el-icon v-else style="color: #67C23A"><Document /></el-icon>
            <span style="margin-left: 8px">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100">
          <template #default="{ row }">
            {{ row.is_dir ? '-' : formatSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column prop="modified" label="修改时间" width="180" />
      </el-table>
    </div>

    <!-- 当前选中路径显示 -->
    <el-input v-model="selectedPath" readonly placeholder="双击文件夹或点击选择" class="mt-16">
      <template #append>
        <el-button @click="confirmSelection" type="primary" :disabled="!selectedPath">
          选择此目录
        </el-button>
      </template>
    </el-input>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { listAlist, browseAlistFiles } from '../api'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue', 'select'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const alists = ref([])
const selectedAlistId = ref('')
const currentPath = ref('/')
const files = ref([])
const selectedPath = ref('')
const loading = ref(false)

const pathParts = computed(() => {
  if (currentPath.value === '/') return []
  return currentPath.value.split('/').filter(p => p)
})

// 加载 AList 列表
const loadAlists = async () => {
  try {
    const res = await listAlist()
    alists.value = res.data
  } catch (e) {
    ElMessage.error('加载 AList 列表失败')
  }
}

// 加载文件列表
const loadFiles = async () => {
  if (!selectedAlistId.value) return
  
  loading.value = true
  try {
    const res = await browseAlistFiles(selectedAlistId.value, currentPath.value, 1, 100)
    // 只显示文件夹
    files.value = res.data.content.filter(item => item.is_dir)
  } catch (e) {
    ElMessage.error('加载文件列表失败: ' + (e.response?.data?.detail || e.message))
    files.value = []
  } finally {
    loading.value = false
  }
}

// 双击文件夹进入
const handleDblClick = (row) => {
  if (row.is_dir) {
    currentPath.value = currentPath.value === '/' 
      ? `/${row.name}` 
      : `${currentPath.value}/${row.name}`
    selectedPath.value = currentPath.value
    loadFiles()
  }
}

// 单击选中
const handleSelect = (row) => {
  if (row && row.is_dir) {
    const path = currentPath.value === '/' 
      ? `/${row.name}` 
      : `${currentPath.value}/${row.name}`
    selectedPath.value = path
  }
}

// 导航到指定路径
const navigateTo = (path) => {
  currentPath.value = path
  selectedPath.value = path
  loadFiles()
}

// 导航到面包屑部分
const navigateToPart = (index) => {
  const path = '/' + pathParts.value.slice(0, index + 1).join('/')
  navigateTo(path)
}

// 刷新
const refresh = () => {
  loadFiles()
}

// 格式化文件大小
const formatSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

// 确认选择
const confirmSelection = () => {
  if (selectedPath.value) {
    emit('select', {
      alistId: selectedAlistId.value,
      path: selectedPath.value
    })
    visible.value = false
  }
}

// 关闭时重置
const handleClose = () => {
  currentPath.value = '/'
  selectedPath.value = ''
  selectedAlistId.value = ''
  files.value = []
}

// 监听对话框打开
watch(visible, async (val) => {
  if (val) {
    await loadAlists()
  }
})
</script>

<style scoped>
.mb-16 {
  margin-bottom: 16px;
}
.mt-16 {
  margin-top: 16px;
}
.el-breadcrumb {
  cursor: pointer;
}
.el-breadcrumb__item:hover {
  color: #409EFF;
}
</style>
