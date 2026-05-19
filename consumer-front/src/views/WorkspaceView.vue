<template>
  <main class="workspace-page">
    <aside class="workspace-sidebar">
      <RouterLink class="brand compact" to="/">
        <img class="brand-logo" src="/think-land-logo.svg" alt="Think Land logo" />
        <strong>Think Land</strong>
      </RouterLink>
      <button class="side-link" :class="{ active: activeView === 'chat' }" @click="activeView = 'chat'">创意工作台</button>
      <button class="side-link" :class="{ active: activeView === 'prd' }" @click="activeView = 'prd'">我的 PRD</button>
      <button class="side-link" :class="{ active: activeView === 'flow' }" @click="activeView = 'flow'">流程图</button>
      <button class="side-link" :class="{ active: activeView === 'tasks' }" @click="activeView = 'tasks'">任务计划</button>
      <button class="side-link" @click="logout">退出登录</button>
    </aside>

    <section class="workspace-main">
      <header class="workspace-header">
        <div>
          <h1>{{ pageTitle }}</h1>
          <p v-if="user" class="workspace-meta">
            {{ user.account }} · 今日剩余 {{ points?.remaining_points ?? '--' }} / {{ points?.granted_points ?? 100 }} 点
          </p>
        </div>
        <button class="settings-button" type="button" aria-label="AI 接口设置" title="AI 接口设置" @click="showConfig = true">
          <span></span>
        </button>
      </header>

      <section v-if="activeView === 'chat'" class="chat-shell">
        <div class="chat-board">
          <div class="chat-list" ref="chatListEl">
            <article
              v-for="(message, index) in messages"
              :id="`message-${index}`"
              :key="index"
              class="chat-message"
              :class="[message.role, { focused: focusedMessageIndex === index }]"
            >
              <span>{{ message.role === 'user' ? '你' : 'Think Land' }}</span>
              <p>{{ message.content }}</p>
            </article>
            <article v-if="loading" class="chat-message assistant">
              <span>Think Land</span>
              <p>正在梳理你的想法...</p>
            </article>
          </div>

          <aside class="memory-rail" aria-label="对话记忆">
            <p>记忆</p>
            <div class="memory-line">
              <button
                v-for="(message, index) in messages"
                :key="index"
                type="button"
                class="memory-dot"
                :class="[message.role, { active: focusedMessageIndex === index }]"
                :title="memoryTitle(message, index)"
                @click="focusMessage(index)"
              >
                <span>{{ index + 1 }}</span>
              </button>
            </div>
          </aside>
        </div>

        <form class="chat-composer" @submit.prevent="sendMessage">
          <textarea
            v-model="draft"
            placeholder="描述你的产品想法；如果还没说清楚，AI 会继续追问你。"
            @keydown.enter.exact.prevent="sendMessage"
          ></textarea>
          <div class="composer-actions">
            <span>{{ aiConfig?.configured ? '按 Enter 发送，Shift + Enter 换行' : '请先点击右上角设置 AI 接口' }}</span>
            <div class="composer-buttons">
              <button type="button" class="confirm-button" :disabled="savingConversation || messages.length < 2" @click="confirmRequirement">
                {{ savingConversation ? '保存中...' : '确认并保存需求' }}
              </button>
              <button type="submit" :disabled="loading || !draft.trim()">发送</button>
            </div>
          </div>
        </form>
        <p v-if="saveMessage" class="form-success">{{ saveMessage }}</p>
        <p v-if="error" class="form-error">{{ error }}</p>
      </section>

      <section v-else-if="activeView === 'prd'" class="result-page prd-panel">
        <div class="panel-title">
          <span>PRD 草稿</span>
          <b>{{ prd.length ? '已生成' : '等待对话' }}</b>
        </div>
        <ul>
          <li v-for="item in prd" :key="item">{{ item }}</li>
        </ul>
        <p v-if="!prd.length" class="empty-state">先在创意工作台里完成一轮对话，PRD 会出现在这里。</p>
      </section>

      <section v-else-if="activeView === 'flow'" class="result-page flow-panel">
        <div class="panel-title">
          <span>业务流程图</span>
          <b>{{ flow.length ? '预览' : '等待对话' }}</b>
        </div>
        <div v-if="flow.length" class="workspace-flow">
          <template v-for="(item, index) in flow" :key="item">
            <i>{{ item }}</i>
            <b v-if="index < flow.length - 1"></b>
          </template>
        </div>
        <p v-else class="empty-state">生成结果里的流程节点会在这里串成流程图。</p>
      </section>

      <section v-else class="result-page tasks-panel">
        <div class="panel-title">
          <span>下一步任务</span>
          <b>{{ tasks.length }} 项</b>
        </div>
        <div v-if="tasks.length" class="task-list">
          <p v-for="item in tasks" :key="item">{{ item }}</p>
        </div>
        <p v-else class="empty-state">完成需求问答后，任务计划会自动整理到这里。</p>
      </section>
    </section>

    <div v-if="showConfig" class="settings-modal" @click.self="showConfig = false">
      <form class="settings-card" @submit.prevent="saveConfig">
        <div class="panel-title">
          <span>AI 接口配置</span>
          <b>{{ aiConfig?.configured ? '已保存' : '未配置' }}</b>
        </div>
        <label>
          Base URL
          <input v-model.trim="configForm.base_url" placeholder="https://api.openai.com/v1" />
        </label>
        <label>
          模型
          <input v-model.trim="configForm.model" placeholder="gpt-4o-mini" />
        </label>
        <label>
          API Key
          <input v-model.trim="configForm.api_key" type="password" placeholder="保存后将加密存储" />
        </label>
        <p v-if="configMessage" class="form-success">{{ configMessage }}</p>
        <p v-if="error" class="form-error">{{ error }}</p>
        <div class="settings-actions">
          <button type="button" class="secondary-action" @click="showConfig = false">取消</button>
          <button type="submit" :disabled="configSaving">{{ configSaving ? '保存中...' : '保存配置' }}</button>
        </div>
      </form>
    </div>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearToken, confirmConversation, generatePlan, getMe, saveAIConfig } from '@/api'

const router = useRouter()
const user = ref(null)
const points = ref(null)
const aiConfig = ref(null)
const activeView = ref('chat')
const showConfig = ref(false)
const loading = ref(false)
const configSaving = ref(false)
const savingConversation = ref(false)
const error = ref('')
const configMessage = ref('')
const saveMessage = ref('')
const draft = ref('')
const chatListEl = ref(null)
const focusedMessageIndex = ref(0)
const configForm = ref({ base_url: '', model: '', api_key: '' })
const messages = ref([
  {
    role: 'assistant',
    content: '你好，我会通过几轮问答帮你把产品目标说清楚。先告诉我：你想做什么产品，给谁用，解决什么问题？'
  }
])
const prd = ref([])
const flow = ref([])
const tasks = ref([])

const pageTitle = computed(() => {
  const titles = {
    chat: '和 Think Land 梳理产品想法',
    prd: '我的 PRD',
    flow: '流程图',
    tasks: '任务计划'
  }
  return titles[activeView.value]
})

onMounted(loadProfile)

async function loadProfile() {
  try {
    const response = await getMe()
    applyProfile(response)
    if (response.ai_config?.configured) {
      configForm.value.base_url = response.ai_config.base_url || ''
      configForm.value.model = response.ai_config.model || ''
    }
  } catch (err) {
    clearToken()
    router.push('/login')
  }
}

function applyProfile(response) {
  user.value = response.user
  points.value = response.points
  aiConfig.value = response.ai_config
}

async function saveConfig() {
  configMessage.value = ''
  error.value = ''
  if (!configForm.value.base_url || !configForm.value.model || !configForm.value.api_key) {
    error.value = '请填写 Base URL、模型和 API Key'
    return
  }
  configSaving.value = true
  try {
    const response = await saveAIConfig(configForm.value)
    applyProfile(response)
    configForm.value.api_key = ''
    configMessage.value = 'AI 配置已保存，API Key 已加密存储'
    showConfig.value = false
  } catch (err) {
    error.value = err.message
  } finally {
    configSaving.value = false
  }
}

async function sendMessage() {
  const content = draft.value.trim()
  if (!content || loading.value) {
    return
  }
  error.value = ''
  saveMessage.value = ''
  configMessage.value = ''
  draft.value = ''
  messages.value.push({ role: 'user', content })
  focusedMessageIndex.value = messages.value.length - 1
  await scrollChat()
  loading.value = true
  try {
    const response = await generatePlan(messages.value)
    const result = response.result || {}
    messages.value.push({
      role: 'assistant',
      content: result.assistant_message || '我已经收到，可以继续补充更多细节。'
    })
    focusedMessageIndex.value = messages.value.length - 1
    if (Array.isArray(result.prd) && result.prd.length) {
      prd.value = result.prd
    }
    if (Array.isArray(result.flow) && result.flow.length) {
      flow.value = result.flow
    }
    if (Array.isArray(result.tasks) && result.tasks.length) {
      tasks.value = result.tasks
    }
    points.value = response.points
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
    await scrollChat()
  }
}

async function confirmRequirement() {
  error.value = ''
  saveMessage.value = ''
  savingConversation.value = true
  try {
    const response = await confirmConversation({
      messages: messages.value,
      prd: prd.value,
      flow: flow.value,
      tasks: tasks.value
    })
    saveMessage.value = `需求已保存，记录编号 #${response.record_id}`
  } catch (err) {
    error.value = err.message
  } finally {
    savingConversation.value = false
  }
}

async function focusMessage(index) {
  focusedMessageIndex.value = index
  await nextTick()
  document.getElementById(`message-${index}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function memoryTitle(message, index) {
  const speaker = message.role === 'user' ? '你' : 'Think Land'
  return `${index + 1}. ${speaker}：${message.content.slice(0, 30)}`
}

async function scrollChat() {
  await nextTick()
  if (chatListEl.value) {
    chatListEl.value.scrollTop = chatListEl.value.scrollHeight
  }
}

function logout() {
  clearToken()
  router.push('/')
}
</script>

