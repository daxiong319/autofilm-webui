<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openAdd">
        <el-icon><Plus /></el-icon> 新增 Ani2Alist 追番任务
      </el-button>
    </div>

    <el-table :data="list" border stripe v-loading="loading">
      <el-table-column prop="id" label="任务ID" min-width="100" />
      <el-table-column prop="alist" label="关联AList" min-width="110" />
      <el-table-column prop="target_dir" label="目标目录" min-width="120" />
      <el-table-column prop="update.mode" label="更新模式" width="90">
        <template #default="{ row }">
          <el-tag size="small" type="primary">{{ row.update?.mode || 'rss' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="cron" label="Cron" min-width="140">
        <template #default="{ row }">
          <el-text type="info" size="small">{{ row.cron || '未设置' }}</el-text>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="success" @click="runNow(row.id)" :loading="running[row.id]">
            <el-icon><VideoPlay /></el-icon> 运行
          </el-button>
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="del(row.id)">
            <template #reference>
              <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑追番任务' : '新增追番任务'" width="600px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="任务 ID" prop="id">
              <el-input v-model="form.id" :disabled="isEdit" placeholder="如：新番追更" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="关联 AList" prop="alist">
              <el-input v-model="form.alist" placeholder="AList 服务器 ID" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="目标目录" prop="target_dir">
              <el-input v-model="form.target_dir" placeholder="/Anime" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Cron 表达式">
              <el-input v-model="form.cron" placeholder="0 20 12 * * *" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider content-position="left">数据源</el-divider>
        <el-form-item label="Source URL">
          <el-input v-model="form.source.source_url" placeholder="https://aniopen.an-i.workers.dev" />
        </el-form-item>
        <el-form-item label="RSS URL">
          <el-input v-model="form.source.rss_url" placeholder="https://api.ani.rip/ani-download.xml" />
        </el-form-item>
        <el-divider content-position="left">更新模式</el-divider>
        <el-form-item label="模式">
          <el-radio-group v-model="form.update.mode">
            <el-radio value="rss">RSS 追更</el-radio>
            <el-radio value="latest">当前季度</el-radio>
            <el-radio value="keyword">关键字</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="目录模板" v-if="form.update.mode === 'latest'">
          <el-input v-model="form.update.template" placeholder="{{ year }}年/{{ month }}月" />
        </el-form-item>
        <el-form-item label="关键字" v-if="form.update.mode === 'keyword'">
          <el-input v-model="form.update.keyword" placeholder="如：2026-4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <!-- 运行日志弹窗 -->
    <el-dialog v-model="logVisible" :title="`任务 ${currentRunId} 运行日志`" width="700px" destroy-on-close>
      <div class="log-box" ref="logBox">
        <div v-for="(line, i) in runLogs" :key="i" class="log-line">{{ line }}</div>
        <div v-if="!runLogs.length" class="log-empty">等待输出...</div>
      </div>
      <template #footer>
        <el-tag :type="runStatus.running ? 'warning' : (runStatus.exit_code === 0 ? 'success' : 'danger')">
          {{ runStatus.running ? '运行中...' : (runStatus.exit_code === 0 ? '完成' : `退出码: ${runStatus.exit_code}`) }}
        </el-tag>
        <el-button @click="logVisible = false" style="margin-left:12px">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { listAni2Alist, addAni2Alist, updateAni2Alist, deleteAni2Alist, runTask, getTaskStatus, getTaskRunLogs } from '../api'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref()
const running = ref({})
const logVisible = ref(false)
const currentRunId = ref('')
const runLogs = ref([])
const runStatus = ref({})
const logBox = ref()
let pollTimer = null

const defaultForm = () => ({
  id: '', cron: '', alist: '', target_dir: '',
  source: { source_url: 'https://aniopen.an-i.workers.dev', rss_url: 'https://api.ani.rip/ani-download.xml' },
  update: { mode: 'rss', template: '', keyword: '' }
})
const form = ref(defaultForm())
const rules = {
  id: [{ required: true, message: '请输入任务 ID' }],
  alist: [{ required: true, message: '请输入关联 AList ID' }],
  target_dir: [{ required: true, message: '请输入目标目录' }],
}

async function load() {
  loading.value = true
  try { list.value = (await listAni2Alist()).data }
  finally { loading.value = false }
}
function openAdd() { isEdit.value = false; form.value = defaultForm(); dialogVisible.value = true }
function openEdit(row) {
  isEdit.value = true
  const d = defaultForm()
  form.value = { ...d, ...row, source: { ...d.source, ...(row.source || {}) }, update: { ...d.update, ...(row.update || {}) } }
  dialogVisible.value = true
}
async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (isEdit.value) await updateAni2Alist(form.value.id, form.value)
    else await addAni2Alist(form.value)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') }
  finally { submitting.value = false }
}
async function del(id) { await deleteAni2Alist(id); ElMessage.success('已删除'); load() }
async function runNow(id) {
  running.value[id] = true
  currentRunId.value = id
  runLogs.value = []
  runStatus.value = { running: true }
  logVisible.value = true
  try {
    await runTask(id)
    pollTimer = setInterval(async () => {
      const [s, l] = await Promise.all([getTaskStatus(id), getTaskRunLogs(id)])
      runStatus.value = s.data
      runLogs.value = l.data.logs
      await nextTick()
      if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight
      if (!s.data.running) { clearInterval(pollTimer); running.value[id] = false }
    }, 800)
  } catch { running.value[id] = false }
}
onUnmounted(() => clearInterval(pollTimer))
onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.log-box { background: #1a1a2e; color: #c0c4cc; font-family: monospace; font-size: 12px; height: 380px; overflow-y: auto; padding: 12px; border-radius: 6px; }
.log-line { padding: 1px 0; line-height: 1.5; white-space: pre-wrap; word-break: break-all; }
.log-empty { color: #606278; text-align: center; margin-top: 160px; }
</style>
