<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openAdd">
        <el-icon><Plus /></el-icon> 新增 Alist2Strm 任务
      </el-button>
      <el-text type="info" size="small" style="margin-left:12px">
        扫描 AList/OpenList 目录，自动生成 .strm 文件供 Emby/Jellyfin 入库播放
      </el-text>
    </div>

    <el-table :data="list" border stripe v-loading="loading">
      <el-table-column prop="id" label="任务ID" min-width="100" />
      <el-table-column prop="alist" label="关联AList" min-width="110" />
      <el-table-column prop="source_dir" label="源目录" min-width="140" />
      <el-table-column prop="target_dir" label="输出目录" min-width="140" />
      <el-table-column prop="mode" label="模式" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.mode === 'RawURL' ? 'warning' : row.mode === 'AlistPath' ? 'info' : 'primary'">
            {{ row.mode }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="cron" label="Cron" min-width="140">
        <template #default="{ row }">
          <el-text type="info" size="small">{{ row.cron || '未设置' }}</el-text>
        </template>
      </el-table-column>
      <el-table-column label="同步清理" width="80">
        <template #default="{ row }">
          <el-tag :type="row.sync?.enabled ? 'success' : 'info'" size="small">
            {{ row.sync?.enabled ? '开启' : '关闭' }}
          </el-tag>
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

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑 Alist2Strm 任务' : '新增 Alist2Strm 任务'" width="680px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="任务 ID" prop="id">
              <el-input v-model="form.id" :disabled="isEdit" placeholder="如：动漫" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="关联 AList" prop="alist">
              <el-input v-model="form.alist" placeholder="与 AList 服务器 ID 对应" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="源目录" prop="source_dir">
              <el-input v-model="form.source_dir" placeholder="/ani">
                <template #append>
                  <el-button @click="openDirPicker('source_dir')">
                    <el-icon><FolderOpened /></el-icon>
                  </el-button>
                </template>
              </el-input>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="输出目录" prop="target_dir">
              <el-input v-model="form.target_dir" placeholder="/media/ani">
                <template #append>
                  <el-button @click="openDirPicker('target_dir')">
                    <el-icon><FolderOpened /></el-icon>
                  </el-button>
                </template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="Cron 表达式">
              <el-input v-model="form.cron" placeholder="0 0 20 * * *" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="STRM 模式">
              <el-select v-model="form.mode" style="width:100%">
                <el-option label="AlistURL（推荐）" value="AlistURL" />
                <el-option label="RawURL（直链）" value="RawURL" />
                <el-option label="AlistPath（路径）" value="AlistPath" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="平铺模式">
              <el-switch v-model="form.flatten_mode" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="覆盖已有">
              <el-switch v-model="form.overwrite" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="并发数">
              <el-input-number v-model="form.concurrency" :min="1" :max="200" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">伴生文件下载</el-divider>
        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="启用下载" label-width="70px">
              <el-switch v-model="form.download.enable" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="字幕" label-width="50px">
              <el-switch v-model="form.download.subtitle" :disabled="!form.download.enable" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="图片" label-width="50px">
              <el-switch v-model="form.download.image" :disabled="!form.download.enable" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="NFO" label-width="50px">
              <el-switch v-model="form.download.nfo" :disabled="!form.download.enable" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">同步清理</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="启用同步" label-width="80px">
              <el-switch v-model="form.sync.enabled" />
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="忽略正则" label-width="80px">
              <el-input v-model="form.sync.ignore" placeholder='\\.(nfo|jpg)$' :disabled="!form.sync.enabled" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16" v-if="form.sync.enabled">
          <el-col :span="8">
            <el-form-item label="智能保护" label-width="80px">
              <el-switch v-model="form.sync.smart_protection.enabled" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="保护阈值" label-width="70px">
              <el-input-number v-model="form.sync.smart_protection.threshold" :min="1" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="宽限次数" label-width="70px">
              <el-input-number v-model="form.sync.smart_protection.grace_scans" :min="1" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <!-- 目录选择器 -->
    <AlistDirectoryPicker v-model="dirPickerVisible" @select="handleDirSelect" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listAlist2Strm, addAlist2Strm, updateAlist2Strm, deleteAlist2Strm,
  runTask, getTaskStatus, getTaskRunLogs
} from '../api'
import AlistDirectoryPicker from '../components/AlistDirectoryPicker.vue'

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
const runStatus = ref({ running: false, exit_code: null })
const logBox = ref()
let pollTimer = null

// 目录选择器
const dirPickerVisible = ref(false)
const currentDirField = ref('') // 'source_dir' or 'target_dir'

const defaultForm = () => ({
  id: '', cron: '', alist: '', source_dir: '', target_dir: '',
  mode: 'AlistURL', flatten_mode: false, overwrite: false, concurrency: 50,
  download: { enable: false, subtitle: false, image: false, nfo: false, other_ext: [], concurrency: 5 },
  sync: { enabled: false, ignore: '', smart_protection: { enabled: false, threshold: 100, grace_scans: 3 } }
})
const form = ref(defaultForm())
const rules = {
  id: [{ required: true, message: '请输入任务 ID' }],
  alist: [{ required: true, message: '请输入关联 AList ID' }],
  source_dir: [{ required: true, message: '请输入源目录' }],
  target_dir: [{ required: true, message: '请输入输出目录' }],
}

async function load() {
  loading.value = true
  try { list.value = (await listAlist2Strm()).data }
  finally { loading.value = false }
}

function openAdd() { isEdit.value = false; form.value = defaultForm(); dialogVisible.value = true }
function openEdit(row) {
  isEdit.value = true
  const d = defaultForm()
  form.value = {
    ...d, ...row,
    download: { ...d.download, ...(row.download || {}) },
    sync: { ...d.sync, ...(row.sync || {}), smart_protection: { ...d.sync.smart_protection, ...(row.sync?.smart_protection || {}) } }
  }
  dialogVisible.value = true
}

async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (isEdit.value) await updateAlist2Strm(form.value.id, form.value)
    else await addAlist2Strm(form.value)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') }
  finally { submitting.value = false }
}

async function del(id) { await deleteAlist2Strm(id); ElMessage.success('已删除'); load() }

// 打开目录选择器
function openDirPicker(field) {
  currentDirField.value = field
  dirPickerVisible.value = true
}

// 处理目录选择
function handleDirSelect({ alistId, path }) {
  if (currentDirField.value === 'source_dir') {
    form.value.source_dir = path
    ElMessage.success(`已选择源目录: ${path}`)
  } else if (currentDirField.value === 'target_dir') {
    form.value.target_dir = path
    ElMessage.success(`已选择输出目录: ${path}`)
  }
}

async function runNow(id) {
  running.value[id] = true
  currentRunId.value = id
  runLogs.value = []
  runStatus.value = { running: true, exit_code: null }
  logVisible.value = true
  try {
    const res = await runTask(id)
    if (!res.data.ok) { ElMessage.warning(res.data.message); return }
    pollTimer = setInterval(async () => {
      const [statusRes, logsRes] = await Promise.all([getTaskStatus(id), getTaskRunLogs(id)])
      runStatus.value = statusRes.data
      runLogs.value = logsRes.data.logs
      await nextTick()
      if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight
      if (!statusRes.data.running) { clearInterval(pollTimer); running.value[id] = false }
    }, 800)
  } catch (e) {
    ElMessage.error('启动失败')
    running.value[id] = false
  }
}

onUnmounted(() => clearInterval(pollTimer))
onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; display: flex; align-items: center; }
.log-box {
  background: #1a1a2e; color: #c0c4cc; font-family: monospace; font-size: 12px;
  height: 380px; overflow-y: auto; padding: 12px; border-radius: 6px;
}
.log-line { padding: 1px 0; line-height: 1.5; white-space: pre-wrap; word-break: break-all; }
.log-empty { color: #606278; text-align: center; margin-top: 160px; }
</style>
