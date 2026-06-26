import 'element-plus/dist/index.css'
import 'vant/lib/index.css'
import './assets/styles.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import Vant from 'vant'
import App from './App.vue'
import { router } from './router'

createApp(App).use(createPinia()).use(router).use(ElementPlus).use(Vant).mount('#app')
