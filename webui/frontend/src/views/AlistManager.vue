<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openAdd">
        <el-icon><Plus /></el-icon> 添加 AList 服务器
      </el-button>
    </div>

    <el-table :data="list" border stripe v-loading="loading" class="mt-16">
      <el-table-column prop="id" label="ID" min-width="120" />
      <el-table-column prop="base_url" label="服务器地址" min-width="180" />
      <el-table-column prop="public_url" label="公共地址" min-width="160">
        <template #default="{ row }">{{ row.public_url || '-' }}</template>
      </el-table-column>
      <el-table-column prop="username" label="用户名" width="110">
        <template #default="{ row }">{{ row.username || '-' }}</template>
      </el-table-column>
      <el-table-column prop="token" label="Token" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.token" type="success" size="small">已配置</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="wait_time" label="请求间隔(s)" width="110" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'ok'" type="success" size="small">正常</el-tag>
          <el-tag v-else-if="row.status === 'checking'" type="info" size="small">检测中</el-tag>
          <el-tooltip v-else :content="row.statusMessage || '未检测'" placement="top">
            <el-tag type="danger" size="small">异常</el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="checkStatus(row)">检测</el-button>
          <el-button size="small" @click="browseFiles(row)">浏览</el-button>
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="del(row.id)">
            <template #reference>
              <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 文件浏览对话框 -->
    <el-dialog v-model="browseDialogVisible" :title="`浏览文件 - ${currentBrowseAlist?.id || ''}`" width="800px">
      <div v-loading="browseLoading" style="min-height: 300px; max-height: 500px; overflow-y: auto;">
        <!-- 面包屑导航 -->
        <el-breadcrumb separator="/" class="mb-16">
          <el-breadcrumb-item @click="navigateTo('/')">根目录</el-breadcrumb-item>
          <el-breadcrumb-item v-for="(part, index) in browsePathParts" :key="index" @click="navigateToPart(index)">
            {{ part }}
          </el-breadcrumb-item>
        </el-breadcrumb>

        <!-- 文件列表 -->
        <el-table :data="browseFilesList" border stripe @row-dblclick="handleDblClick">
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
    </el-dialog>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑 AList 服务器' : '添加 AList 服务器'" width="560px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-form-item label="ID" prop="id">
          <el-input v-model="form.id" :disabled="isEdit" placeholder="如：我的Alist" />
        </el-form-item>
        <el-form-item label="服务器地址" prop="base_url">
          <el-input v-model="form.base_url" placeholder="http://alist:5244" />
        </el-form-item>
        <el-form-item label="公共访问地址">
          <el-input v-model="form.public_url" placeholder="https://alist.example.com（可选）" />
        </el-form-item>
        <el-divider content-position="left">认证方式（Token 优先）</el-divider>
        <el-form-item label="永久 Token">
          <el-input v-model="form.token" placeholder="留空则使用用户名密码" show-password />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="admin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="两步验证码">
          <el-input v-model="form.otp_code" placeholder="可选" />
        </el-form-item>
        <el-form-item label="请求间隔(s)">
          <el-input-number v-model="form.wait_time" :min="0" :step="0.1" :precision="1" />
          <el-text type="info" size="small" style="margin-left:8px">0 表示不限速</el-text>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { listAlist, addAlist, updateAlist, deleteAlist, checkAlistStatus, browseAlistFiles } from '../api'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref()

// 文件浏览相关
const browseDialogVisible = ref(false)
const browseLoading = ref(false)
const currentBrowseAlist = ref(null)
const browsePath = ref('/')
const browseFilesList = ref([])

const browsePathParts = computed(() => {
  if (browsePath.value === '/') return []
  return browsePath.value.split('/').filter(p => p)
})

const defaultForm = () => ({
  id: '',
  base_url: '',
  public_url: '',
  username: '',
  password: '',
  otp_code: '',
  token: '',
  wait_time: 0,
})
const form = ref(defaultForm())

const rules = {
  id: [{ required: true, message: '请输入 ID', trigger: 'blur' }],
  base_url: [{ required: true, message: '请输入服务器地址', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    const res = await listAlist()
    list.value = res.data.map(item => ({
      ...item,
      status: 'unknown',
      statusMessage: '未检测'
    }))
  } finally {
    loading.value = false
  }
}

// 检测 AList 状态
async function checkStatus(row) {
  row.status = 'checking'
  row.statusMessage = '检测中...'
  try {
    const res = await checkAlistStatus(row.id)
    if (res.data.status === 'ok') {
      row.status = 'ok'
      row.statusMessage = res.data.message
      ElMessage.success(`${row.id}: ${res.data.message}`)
    } else {
      row.status = 'error'
      row.statusMessage = res.data.message
      ElMessage.error(`${row.id}: ${res.data.message}`)
    }
  } catch (e) {
    row.status = 'error'
    row.statusMessage = e.message
    ElMessage.error(`检测失败: ${e.message}`)
  }
}

// 浏览文件
function browseFiles(row) {
  currentBrowseAlist.value = row
  browsePath.value = '/'
  browseDialogVisible.value = true
  loadBrowseFiles()
}

async function loadBrowseFiles() {
  if (!currentBrowseAlist.value) return
  
  browseLoading.value = true
  try {
    const res = await browseAlistFiles(
      currentBrowseAlist.value.id,
      browsePath.value,
      1,
      100
    )
    browseFilesList.value = res.data.content || []
  } catch (e) {
    ElMessage.error('加载文件列表失败: ' + (e.response?.data?.detail || e.message))
    browseFilesList.value = []
  } finally {
    browseLoading.value = false
  }
}

// 双击文件夹进入
function handleDblClick(row) {
  if (row.is_dir) {
    browsePath.value = browsePath.value === '/'
      ? `/${row.name}`
      : `${browsePath.value}/${row.name}`
    loadBrowseFiles()
  }
}

// 导航到指定路径
function navigateTo(path) {
  browsePath.value = path
  loadBrowseFiles()
}

// 导航到面包屑部分
function navigateToPart(index) {
  const path = '/' + browsePathParts.value.slice(0, index + 1).join('/')
  navigateTo(path)
}

// 格式化文件大小
function formatSize(bytes) {
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

function openAdd() {
  isEdit.value = false
  form.value = defaultForm()
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  form.value = { ...defaultForm(), ...row }
  dialogVisible.value = true
}

async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateAlist(form.value.id, form.value)
    } else {
      await addAlist(form.value)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function del(id) {
  await deleteAlist(id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.mt-16 { margin-top: 0; }
</style>
