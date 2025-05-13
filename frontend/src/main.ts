import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
// import router from './router'

// 应用挂载前检查并应用保存的主题
const savedTheme = localStorage.getItem('appTheme')
if (savedTheme === 'light') {
  document.documentElement.classList.remove('dark')
  document.body.classList.remove('dark')
} else {
  document.documentElement.classList.add('dark')
  document.body.classList.add('dark')
  // 确保localStorage中有值
  if (!savedTheme) {
    localStorage.setItem('appTheme', 'dark')
  }
}

const app = createApp(App)

// app.use(router)

app.mount('#app')
