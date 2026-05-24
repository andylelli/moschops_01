import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import './echarts'
import { createPinia } from 'pinia'
import router from './router'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import './icons'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.component('FontAwesomeIcon', FontAwesomeIcon)
app.mount('#app')
