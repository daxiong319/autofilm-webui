<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg,#409EFF,#67C23A)">
            <el-icon size="28" color="#fff"><Connection /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ status.alist_count ?? '-' }}</div>
            <div class="stat-label">AList 服务器</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg,#E6A23C,#F56C6C)">
            <el-icon size="28" color="#fff"><FolderOpened /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ status.alist2strm_task_count ?? '-' }}</div>
            <div class="stat-label">Alist2Strm 任务</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg,#909399,#409EFF)">
            <el-icon size="28" color="#fff"><VideoPlay /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ status.ani2alist_task_count ?? '-' }}</div>
            <div class="stat-label">Ani2Alist 任务</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg,#67C23A,#409EFF)">
            <el-icon size="28" color="#fff"><Picture /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ status.library_poster_task_count ?? '-' }}</div>
            <div class="stat-label">媒体库海报任务</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统信息 & 快捷入口 -->
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <el-card header="系统信息" shadow="hover">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="配置文件路径">
              <el-text type="info" size="small">{{ status.config_path || '-' }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="配置文件状态">
              <el-tag :type="status.config_exists ? 'success' : 'danger'" size="small">
                {{ status.config_exists ? '已存在' : '不存在' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="服务器时间">
              <el-text>{{ status.server_time || '-' }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="正在运行的任务">
              <span v-if="status.running_tasks && status.running_tasks.length">
                <el-tag
                  v-for="t in status.running_tasks"
                  :key="t"
                  type="warning"
                  size="small"
                  style="margin-right:4px"
                >{{ t }}</el-tag>
              </span>
              <el-text v-else type="info" size="small">无</el-text>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card header="快捷导航" shadow="hover">
          <div class="quick-nav">
            <el-button @click="$router.push('/alist')" type="primary" plain size="large" class="nav-btn">
              <el-icon><Connection /></el-icon>
              AList 服务器管理
            </el-button>
            <el-button @click="$router.push('/tasks/alist2strm')" type="success" plain size="large" class="nav-btn">
              <el-icon><FolderOpened /></el-icon>
              Alist2Strm 任务
            </el-button>
            <el-button @click="$router.push('/tasks/ani2alist')" type="warning" plain size="large" class="nav-btn">
              <el-icon><VideoPlay /></el-icon>
              Ani2Alist 追番
            </el-button>
            <el-button @click="$router.push('/logs')" type="info" plain size="large" class="nav-btn">
              <el-icon><Document /></el-icon>
              查看日志
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- AutoFilm 功能说明 -->
    <el-row style="margin-top:16px">
      <el-col :span="24">
        <el-card header="流程说明" shadow="hover">
          <el-steps :active="5" finish-status="success" align-center>
            <el-step title="配置 AList" description="连接你的 Alist/OpenList 服务器" />
            <el-step title="创建 Alist2Strm 任务" description="设置源目录与本地 strm 输出目录" />
            <el-step title="定时自动运行" description="按 Cron 表达式定期扫描并生成 .strm 文件" />
            <el-step title="Emby/Jellyfin 入库" description="将 strm 目录添加到媒体库并扫描" />
            <el-step title="直链播放" description="播放时直接请求网盘，不占用服务器带宽" />
          </el-steps>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getStatus } from '../api'

const status = ref({})
let timer = null

async function fetchStatus() {
  try {
    const res = await getStatus()
    status.value = res.data
  } catch (e) {
    // ignore
  }
}

onMounted(() => {
  fetchStatus()
  timer = setInterval(fetchStatus, 5000)
})

onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.dashboard {}

.stat-row {}

.stat-card {
  display: flex;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.quick-nav {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.nav-btn {
  width: 100%;
  height: 48px;
  font-size: 14px;
}
</style>
