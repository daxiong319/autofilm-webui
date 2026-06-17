import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getStatus = () => api.get('/status')
export const getConfig = () => api.get('/config')
export const saveConfig = (cfg) => api.post('/config', cfg)

// AList
export const listAlist = () => api.get('/alist')
export const addAlist = (item) => api.post('/alist', item)
export const updateAlist = (id, item) => api.put(`/alist/${encodeURIComponent(id)}`, item)
export const deleteAlist = (id) => api.delete(`/alist/${encodeURIComponent(id)}`)

// 媒体服务器
export const listMediaServers = () => api.get('/media_servers')
export const addMediaServer = (item) => api.post('/media_servers', item)
export const updateMediaServer = (id, item) => api.put(`/media_servers/${encodeURIComponent(id)}`, item)
export const deleteMediaServer = (id) => api.delete(`/media_servers/${encodeURIComponent(id)}`)

// Alist2Strm 任务
export const listAlist2Strm = () => api.get('/tasks/alist2strm')
export const addAlist2Strm = (task) => api.post('/tasks/alist2strm', task)
export const updateAlist2Strm = (id, task) => api.put(`/tasks/alist2strm/${encodeURIComponent(id)}`, task)
export const deleteAlist2Strm = (id) => api.delete(`/tasks/alist2strm/${encodeURIComponent(id)}`)

// Ani2Alist 任务
export const listAni2Alist = () => api.get('/tasks/ani2alist')
export const addAni2Alist = (task) => api.post('/tasks/ani2alist', task)
export const updateAni2Alist = (id, task) => api.put(`/tasks/ani2alist/${encodeURIComponent(id)}`, task)
export const deleteAni2Alist = (id) => api.delete(`/tasks/ani2alist/${encodeURIComponent(id)}`)

// LibraryPoster 任务
export const listLibraryPoster = () => api.get('/tasks/library_poster')
export const addLibraryPoster = (task) => api.post('/tasks/library_poster', task)
export const updateLibraryPoster = (id, task) => api.put(`/tasks/library_poster/${encodeURIComponent(id)}`, task)
export const deleteLibraryPoster = (id) => api.delete(`/tasks/library_poster/${encodeURIComponent(id)}`)

// 手动运行
export const runTask = (id) => api.post(`/run/${encodeURIComponent(id)}`)
export const getTaskStatus = (id) => api.get(`/run/${encodeURIComponent(id)}/status`)
export const getTaskRunLogs = (id) => api.get(`/run/${encodeURIComponent(id)}/logs`)

// 日志
export const listLogFiles = () => api.get('/logs')
export const getLogFile = (filename, tail = 500) => api.get(`/logs/${encodeURIComponent(filename)}?tail=${tail}`)
