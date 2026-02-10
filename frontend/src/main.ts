import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'
import './assets/styles/main.scss'

const app = createApp(App)

// 状态管理
app.use(createPinia())

// 路由
app.use(router)

// Element Plus (中文)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
