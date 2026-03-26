import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import './assets/styles/main.scss'

const app = createApp(App)

// 状态管理
app.use(createPinia())

// 路由
app.use(router)

app.use(ElementPlus)

app.mount('#app')
