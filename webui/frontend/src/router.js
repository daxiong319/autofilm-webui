import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import AlistManager from './views/AlistManager.vue'
import Alist2StrmTasks from './views/Alist2StrmTasks.vue'
import Ani2AlistTasks from './views/Ani2AlistTasks.vue'
import LibraryPosterTasks from './views/LibraryPosterTasks.vue'
import MediaServers from './views/MediaServers.vue'
import LogViewer from './views/LogViewer.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: Dashboard, meta: { title: '控制台' } },
  { path: '/alist', component: AlistManager, meta: { title: 'AList 服务器' } },
  { path: '/media-servers', component: MediaServers, meta: { title: '媒体服务器' } },
  { path: '/tasks/alist2strm', component: Alist2StrmTasks, meta: { title: 'Alist2Strm 任务' } },
  { path: '/tasks/ani2alist', component: Ani2AlistTasks, meta: { title: 'Ani2Alist 任务' } },
  { path: '/tasks/library-poster', component: LibraryPosterTasks, meta: { title: '媒体库海报任务' } },
  { path: '/logs', component: LogViewer, meta: { title: '日志中心' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
