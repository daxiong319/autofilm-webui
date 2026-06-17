<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openAdd">
        <el-icon><Plus /></el-icon> 新增媒体服务器
      </el-button>
    </div>

    <el-table :data="list" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" min-width="120" />
      <el-table-column prop="kind" label="类型" width="90">
        <template #default="{ row }">
          <el-tag :type="row.kind === 'emby' ? 'primary' : 'success'" size="small">{{ row.kind }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="base_url" label="服务器地址" min-width="180" />
      <el-table-column prop="api_key" label="API Key" min-width="140">
        <template #default="{ row }">
          <el-text type="info">{{ row.api_key ? '******' : '-' }}</el-text>
        </template>
      </el-table-column>
      <el-table-column prop="timeout" label="超时(s)" width="80" />
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑媒体服务器' : '添加媒体服务器'" width="520px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="ID" prop="id">
          <el-input v-model="form.id" :disabled="isEdit" placeholder="如：我的Jellyfin" />
        </el-form-item>
        <el-form-item label="类型" prop="kind">
          <el-radio-group v-model="form.kind">
            <el-radio value="emby">Emby</el-radio>
            <el-radio value="jellyfin">Jellyfin</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="服务器地址" prop="base_url">
          <el-input v-model="form.base_url" placeholder="http://emby:8096" />
        </el-form-item>
        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="form.api_key" show-password />
        </el-form-item>
        <el-form-item label="用户 ID">
          <el-input v-model="form.user_id" placeholder="留空自动使用首个用户" />
        </el-form-item>
        <el-form-item label="超时(s)">
          <el-input-number v-model="form.timeout" :min="5" :max="120" />
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
import { listMediaServers, addMediaServer, updateMediaServer, deleteMediaServer } from '../api'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref()

const defaultForm = () => ({
  id: '', kind: 'emby', base_url: '', api_key: '', user_id: '', timeout: 30,
})
const form = ref(defaultForm())
const rules = {
  id: [{ required: true, message: '请输入 ID' }],
  base_url: [{ required: true, message: '请输入服务器地址' }],
  api_key: [{ required: true, message: '请输入 API Key' }],
}

async function load() {
  loading.value = true
  try { list.value = (await listMediaServers()).data }
  finally { loading.value = false }
}
function openAdd() { isEdit.value = false; form.value = defaultForm(); dialogVisible.value = true }
function openEdit(row) { isEdit.value = true; form.value = { ...defaultForm(), ...row }; dialogVisible.value = true }
async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (isEdit.value) await updateMediaServer(form.value.id, form.value)
    else await addMediaServer(form.value)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') }
  finally { submitting.value = false }
}
async function del(id) { await deleteMediaServer(id); ElMessage.success('已删除'); load() }
onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
</style>
