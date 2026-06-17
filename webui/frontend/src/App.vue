<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <el-icon size="28" color="#409EFF"><Film /></el-icon>
        <span class="logo-text">AutoFilm</span>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#1a1a2e"
        text-color="#c0c4cc"
        active-text-color="#409EFF"
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>控制台</span>
        </el-menu-item>

        <el-menu-item-group title="存储配置">
          <el-menu-item index="/alist">
            <el-icon><Connection /></el-icon>
            <span>AList 服务器</span>
          </el-menu-item>
          <el-menu-item index="/media-servers">
            <el-icon><Monitor /></el-icon>
            <span>媒体服务器</span>
          </el-menu-item>
        </el-menu-item-group>

        <el-menu-item-group title="任务管理">
          <el-menu-item index="/tasks/alist2strm">
            <el-icon><FolderOpened /></el-icon>
            <span>Alist2Strm</span>
          </el-menu-item>
          <el-menu-item index="/tasks/ani2alist">
            <el-icon><VideoPlay /></el-icon>
            <span>Ani2Alist 追番</span>
          </el-menu-item>
          <el-menu-item index="/tasks/library-poster">
            <el-icon><Picture /></el-icon>
            <span>媒体库海报</span>
          </el-menu-item>
        </el-menu-item-group>

        <el-menu-item-group title="系统">
          <el-menu-item index="/logs">
            <el-icon><Document /></el-icon>
            <span>日志中心</span>
          </el-menu-item>
        </el-menu-item-group>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="main-container">
      <el-header class="header">
        <span class="page-title">{{ $route.meta.title || 'AutoFilm WebUI' }}</span>
        <div class="header-right">
          <el-tag type="success" size="small">
            <el-icon><CircleCheck /></el-icon> 服务运行中
          </el-tag>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body, #app { height: 100%; }

.app-container {
  height: 100vh;
  background: #f5f7fa;
}

.sidebar {
  background: #1a1a2e;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow-y: auto;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px;
  border-bottom: 1px solid #2a2a4a;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 1px;
}

.sidebar-menu {
  border-right: none;
  flex: 1;
}

.sidebar-menu .el-menu-item-group__title {
  color: #606278 !important;
  font-size: 11px;
  padding-left: 20px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.sidebar-menu .el-menu-item {
  border-radius: 6px;
  margin: 2px 8px;
}

.sidebar-menu .el-menu-item.is-active {
  background: rgba(64, 158, 255, 0.15) !important;
}

.main-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.header {
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-content {
  padding: 20px;
  overflow-y: auto;
  background: #f5f7fa;
}
</style>
