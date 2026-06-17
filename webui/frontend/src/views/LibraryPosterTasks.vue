<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openAdd">
        <el-icon><Plus /></el-icon> 新增媒体库海报任务
      </el-button>
    </div>
    <el-table :data="list" border stripe v-loading="loading">
      <el-table-column prop="id" label="任务ID" min-width="100" />
      <el-table-column prop="server" label="媒体服务器" min-width="120" />
      <el-table-column prop="render.style" label="海报风格" width="90">
        <template #default="{ row }">
          <el-tag size="small">{{ row.render?.style || 'collage' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="cron" label="Cron" min-width="140">
        <template #default="{ row }"><el-text type="info" size="small">{{ row.cron || '未设置' }}</el-text></template>
      </el-table-column>
      <el-table-column prop="upload" label="上传" width="70">
        <template #default="{ row }">
          <el-tag :type="row.upload ? 'success' : 'info'" size="small">{{ row.upload ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="success" @click="runNow(row.id)" :loading="running[row.id]">
            <el-icon><VideoPlay /></el-icon> 运行
          </el-button>
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="del(row.id)">
            <template #reference><el-button size="small" type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑海报任务' : '新增海报任务'" width="620px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="任务 ID" prop="id">
              <el-input v-model="form.id" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="媒体服务器" prop="server">
              <el-input v-model="form.server" placeholder="media_servers 中的 ID" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="Cron">
              <el-input v-model="form.cron" placeholder="0 50 13 * * *" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="上传海报" label-width="70px">
              <el-switch v-model="form.upload" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="输出目录">
          <el-input v-model="form.output_dir" placeholder="/media/posters" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="主标题字体">
              <el-input v-model="form.title_font" placeholder="/fonts/ch.ttf" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="副标题字体">
              <el-input v-model="form.subtitle_font" placeholder="/fonts/en.otf" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider content-position="left">渲染设置</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="风格" label-width="50px">
              <el-select v-model="form.render.style" style="width:100%">
                <el-option label="collage（拼贴）" value="collage" />
                <el-option label="card（卡片）" value="card" />
                <el-option label="split（分割）" value="split" />
                <el-option label="blur（模糊）" value="blur" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="分辨率" label-width="60px">
              <el-select v-model="form.render.resolution" style="width:100%">
                <el-option label="1080p" value="1080p" />
                <el-option label="720p" value="720p" />
                <el-option label="480p" value="480p" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="模糊半径" label-width="70px">
              <el-input-number v-model="form.render.blur_radius" :min="0" :max="200" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

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
import { listLibraryPoster, addLibraryPoster, updateLibraryPoster, deleteLibraryPoster, runTask, getTaskStatus, getTaskRunLogs } from '../api'

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
  id: '', cron: '', server: '', upload: false, output_dir: '/media/posters',
  title_font: '/fonts/ch.ttf', subtitle_font: '/fonts/en.otf',
  render: { style: 'collage', resolution: '1080p', blur_radius: 50, color_strength: 0.8 },
  libraries: []
})
const form = ref(defaultForm())
const rules = {
  id: [{ required: true, message: '请输入任务 ID' }],
  server: [{ required: true, message: '请输入媒体服务器 ID' }],
}
async function load() {
  loading.value = true
  try { list.value = (await listLibraryPoster()).data }
  finally { loading.value = false }
}
function openAdd() { isEdit.value = false; form.value = defaultForm(); dialogVisible.value = true }
function openEdit(row) {
  isEdit.value = true
  const d = defaultForm()
  form.value = { ...d, ...row, render: { ...d.render, ...(row.render || {}) } }
  dialogVisible.value = true
}
async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (isEdit.value) await updateLibraryPoster(form.value.id, form.value)
    else await addLibraryPoster(form.value)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') }
  finally { submitting.value = false }
}
async function del(id) { await deleteLibraryPoster(id); ElMessage.success('已删除'); load() }
async function runNow(id) {
  running.value[id] = true; currentRunId.value = id; runLogs.value = []; runStatus.value = { running: true }; logVisible.value = true
  try {
    await runTask(id)
    pollTimer = setInterval(async () => {
      const [s, l] = await Promise.all([getTaskStatus(id), getTaskRunLogs(id)])
      runStatus.value = s.data; runLogs.value = l.data.logs
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
.log-line { padding: 1px 0; line-height: 1.5; white-space: pre-wrap; }
.log-empty { color: #606278; text-align: center; margin-top: 160px; }
</style>
