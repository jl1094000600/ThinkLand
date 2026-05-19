<template>
  <main class="auth-page">
    <RouterLink class="auth-brand" to="/">
      <img class="brand-logo" src="/think-land-logo.svg" alt="Think Land logo" />
      <strong>Think Land</strong>
    </RouterLink>

    <section class="auth-showcase">
      <article>
        <span>01</span>
        <h2>灵感型</h2>
        <p>适合创作、灵感记录和 AI 陪伴式产品规划。</p>
      </article>
      <article>
        <span>02</span>
        <h2>效率型</h2>
        <p>适合把个人任务、助手和知识库组合为每日工作台。</p>
      </article>
      <article>
        <span>03</span>
        <h2>会员型</h2>
        <p>适合持续保存项目、复用模板和管理更高额度服务。</p>
      </article>
    </section>

    <section class="auth-content">
      <div class="auth-copy">
        <p class="pill">注册 / 登录</p>
        <h1>先让用户轻松进来，再把 AI 能力慢慢展开</h1>
        <p>登录后进入个人工作台，配置自己的 AI 接口，就能把一句产品想法生成 PRD、流程和任务拆解。</p>
      </div>

      <form class="auth-card" @submit.prevent="submit">
        <div class="auth-tabs">
          <button type="button" :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
          <button type="button" :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
        </div>
        <label>
          手机号或邮箱
          <input v-model.trim="account" type="text" placeholder="name@example.com" autocomplete="username" />
        </label>
        <label>
          密码
          <input v-model="password" type="password" placeholder="请输入至少 6 位密码" autocomplete="current-password" />
        </label>
        <p v-if="error" class="form-error">{{ error }}</p>
        <button class="submit-btn" type="submit" :disabled="submitting">
          {{ submitting ? '处理中...' : mode === 'login' ? '进入 Think Land' : '创建账号' }}
        </button>
      </form>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, register, setToken } from '@/api'

const router = useRouter()
const mode = ref('login')
const account = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function submit() {
  error.value = ''
  if (!account.value || password.value.length < 6) {
    error.value = '请输入账号和至少 6 位密码'
    return
  }
  submitting.value = true
  try {
    const response = mode.value === 'login'
      ? await login(account.value, password.value)
      : await register(account.value, password.value)
    setToken(response.access_token)
    router.push('/workspace')
  } catch (err) {
    error.value = err.message
  } finally {
    submitting.value = false
  }
}
</script>

