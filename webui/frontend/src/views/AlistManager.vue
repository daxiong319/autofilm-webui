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
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="del(row.id)">
            <template #reference>
              <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

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
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listAlist, addAlist, updateAlist, deleteAlist } from '../api'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref()

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
    list.value = res.data
  } finally {
    loading.value = false
  }
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
