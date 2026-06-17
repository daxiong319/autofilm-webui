<template>
  <div class="log-viewer">
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="10">
        <el-select v-model="selectedFile" placeholder="选择日志文件" @change="loadLog" clearable style="width:100%">
          <el-option v-for="f in files" :key="f" :label="f" :value="f" />
        </el-select>
      </el-col>
      <el-col :span="6">
        <el-input-number v-model="tail" :min="50" :max="5000" :step="100" style="width:100%" />
        <el-text type="info" size="small">显示末尾行数</el-text>
      </el-col>
      <el-col :span="8">
        <el-button @click="loadLog" :disabled="!selectedFile" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button @click="autoRefresh = !autoRefresh" :type="autoRefresh ? 'warning' : 'default'">
          <el-icon><Timer /></el-icon> {{ autoRefresh ? '停止自动刷新' : '自动刷新(5s)' }}
        </el-button>
        <el-button @click="scrollBottom">
          <el-icon><ArrowDown /></el-icon> 跳到底部
        </el-button>
      </el-col>
    </el-row>

    <div v-if="!selectedFile" class="empty-tip">
      <el-empty description="请先选择日志文件" />
    </div>

    <div v-else class="log-terminal" ref="terminalRef">
      <div v-if="!lines.length && !loading" class="log-empty">暂无日志</div>
      <div
        v-for="(line, i) in lines"
        :key="i"
        class="log-line"
        :class="lineClass(line)"
      >{{ line }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { listLogFiles, getLogFile } from '../api'

const files = ref([])
const selectedFile = ref('')
const tail = ref(500)
const lines = ref([])
const loading = ref(false)
const autoRefresh = ref(false)
const terminalRef = ref()
let timer = null

async function loadFiles() {
  const res = await listLogFiles()
  files.value = res.data.files
}

async function loadLog() {
  if (!selectedFile.value) return
  loading.value = true
  try {
    const res = await getLogFile(selectedFile.value, tail.value)
    lines.value = res.data.lines
    await nextTick()
    scrollBottom()
  } finally {
    loading.value = false
  }
}

function scrollBottom() {
  nextTick(() => {
    if (terminalRef.value) terminalRef.value.scrollTop = terminalRef.value.scrollHeight
  })
}

function lineClass(line) {
  const l = line.toLowerCase()
  if (l.includes('error') || l.includes('错误') || l.includes('failed')) return 'line-error'
  if (l.includes('warn') || l.includes('警告')) return 'line-warn'
  if (l.includes('info') || l.includes('完成') || l.includes('成功')) return 'line-info'
  return ''
}

watch(autoRefresh, (val) => {
  if (val) {
    timer = setInterval(loadLog, 5000)
  } else {
    clearInterval(timer)
  }
})

onMounted(() => {
  loadFiles()
})

onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.log-viewer {}

.empty-tip {
  padding: 60px;
  text-align: center;
}

.log-terminal {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 16px;
  height: calc(100vh - 220px);
  overflow-y: auto;
  font-family: 'Menlo', 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.log-line {
  color: #c0c4cc;
  padding: 1px 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.line-error {
  color: #F56C6C;
}

.line-warn {
  color: #E6A23C;
}

.line-info {
  color: #67C23A;
}

.log-empty {
  color: #606278;
  text-align: center;
  padding: 80px;
}
</style>
