<template>
  <main class="workspace-page">
    <aside class="workspace-sidebar">
      <RouterLink class="brand compact" to="/">
        <img class="brand-logo" src="/think-land-logo.svg" alt="Think Land logo" />
        <strong>Think Land</strong>
      </RouterLink>

      <nav class="sidebar-nav">
        <button class="side-link" :class="{ active: activeView === 'chat' }" @click="activeView = 'chat'">创意工作台</button>
        <button class="side-link" :class="{ active: activeView === 'prd' }" @click="activeView = 'prd'">我的 PRD</button>
        <button class="side-link" :class="{ active: activeView === 'flow' }" @click="activeView = 'flow'">流程图</button>
        <button class="side-link" :class="{ active: activeView === 'tasks' }" @click="activeView = 'tasks'">任务计划</button>
        <button class="side-link" :class="{ active: activeView === 'community' }" @click="activeView = 'community'">创意社区</button>
        <button class="side-link" @click="logout">退出登录</button>
      </nav>

      <section v-if="user" class="sidebar-user">
        <span>{{ user.account }}</span>
        <strong>剩余 {{ points?.remaining_points ?? '--' }} / {{ points?.granted_points ?? 100 }} 点</strong>
      </section>
    </aside>

    <section class="workspace-main">
      <header class="workspace-header">
        <div>
          <h1>{{ pageTitle }}</h1>
        </div>
        <button class="settings-button" type="button" aria-label="AI 设置" title="AI 设置" @click="showConfig = true">
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
              <p>正在梳理你的产品想法...</p>
            </article>
          </div>

          <aside class="memory-rail" aria-label="对话记忆">
            <div class="memory-label">记忆</div>
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
                <em>{{ memoryTitle(message, index) }}</em>
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
            <span>{{ aiConfig?.configured ? 'Enter 发送，Shift + Enter 换行' : '请先点击右上角设置 AI 接口' }}</span>
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
          <div class="panel-actions">
            <b>{{ prd.length ? '已生成' : '等待对话' }}</b>
            <button v-if="prd.length" class="publish-mini" type="button" @click="preparePublishFromCurrent('prd')">公开</button>
          </div>
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

      <section v-else-if="activeView === 'tasks'" class="result-page tasks-panel">
        <div class="panel-title">
          <span>下一步任务</span>
          <div class="panel-actions">
            <b>{{ tasks.length }} 项</b>
            <button v-if="prd.length || tasks.length" class="publish-mini" type="button" @click="preparePublishFromCurrent('project')">发布项目</button>
          </div>
        </div>
        <div v-if="tasks.length" class="task-list">
          <p v-for="item in tasks" :key="item">{{ item }}</p>
        </div>
        <p v-else class="empty-state">完成需求问答后，任务计划会自动整理到这里。</p>
      </section>

      <section v-else class="community-page">
        <div class="community-toolbar">
          <div class="community-tabs" aria-label="社区筛选">
            <button :class="{ active: communityFilter === 'all' }" @click="setCommunityFilter('all')">全部</button>
            <button :class="{ active: communityFilter === 'prd' }" @click="setCommunityFilter('prd')">公开 PRD</button>
            <button :class="{ active: communityFilter === 'project' }" @click="setCommunityFilter('project')">上线项目</button>
          </div>
          <button class="refresh-button" type="button" :disabled="communityLoading" @click="loadCommunity">刷新</button>
        </div>

        <form class="publish-panel" @submit.prevent="publishCurrentIdea">
          <div class="panel-title">
            <span>公开你的创意</span>
            <b>{{ publishForm.item_type === 'project' ? '项目' : 'PRD' }}</b>
          </div>
          <div class="publish-grid">
            <label>
              类型
              <select v-model="publishForm.item_type">
                <option value="prd">公开 PRD</option>
                <option value="project">上线项目</option>
              </select>
            </label>
            <label>
              标题
              <input v-model.trim="publishForm.title" placeholder="给这个创意起个名字" />
            </label>
            <label v-if="publishForm.item_type === 'project'">
              项目地址
              <input v-model.trim="publishForm.project_url" placeholder="https://example.com" />
            </label>
          </div>
          <label>
            简介
            <textarea v-model.trim="publishForm.summary" placeholder="一句话说明它面向谁、解决什么问题。"></textarea>
          </label>
          <div class="composer-actions">
            <span>{{ prd.length ? '会带上当前 PRD、流程和任务内容' : '先生成 PRD 后发布会更完整' }}</span>
            <button type="submit" :disabled="publishing || !canPublishCommunity">{{ publishing ? '发布中...' : '公开发布' }}</button>
          </div>
        </form>

        <p v-if="communityMessage" class="form-success">{{ communityMessage }}</p>
        <p v-if="communityError" class="form-error">{{ communityError }}</p>

        <div v-if="communityLoading" class="empty-state">正在加载社区内容...</div>
        <div v-else-if="!communityItems.length" class="empty-state">社区里还没有公开内容，发布第一个创意吧。</div>
        <div v-else class="community-grid">
          <article v-for="item in communityItems" :key="item.id" class="community-card">
            <div class="community-card-top">
              <span>{{ item.item_type === 'project' ? '上线项目' : '公开 PRD' }}</span>
              <button class="star-button" :class="{ active: item.starred_by_me }" type="button" :title="item.starred_by_me ? '取消 Star' : 'Star'" @click="starCommunityItem(item)">
                {{ item.starred_by_me ? '★' : '☆' }} {{ item.star_count }}
              </button>
            </div>
            <h2>{{ item.title }}</h2>
            <p>{{ item.summary }}</p>
            <a v-if="item.project_url" class="project-link" :href="item.project_url" target="_blank" rel="noreferrer">打开项目</a>
            <div class="community-preview">
              <span v-for="line in previewLines(item)" :key="line">{{ line }}</span>
            </div>
            <small>{{ item.owner.account }} · {{ formatDate(item.created_at) }}</small>
          </article>
        </div>
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
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  clearToken,
  confirmConversation,
  generatePlan,
  getMe,
  listCommunityItems,
  publishCommunityItem,
  saveAIConfig,
  toggleCommunityStar
} from '@/api'

const router = useRouter()
const user = ref(null)
const points = ref(null)
const aiConfig = ref(null)
const activeView = ref('chat')
const showConfig = ref(false)
const loading = ref(false)
const configSaving = ref(false)
const savingConversation = ref(false)
const publishing = ref(false)
const communityLoading = ref(false)
const error = ref('')
const configMessage = ref('')
const saveMessage = ref('')
const communityMessage = ref('')
const communityError = ref('')
const draft = ref('')
const chatListEl = ref(null)
const conversationId = ref(null)
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
const communityFilter = ref('all')
const communityItems = ref([])
const publishForm = ref({
  item_type: 'prd',
  title: '',
  summary: '',
  project_url: ''
})

const pageTitle = computed(() => {
  const titles = {
    chat: '和 Think Land 梳理产品想法',
    prd: 'PRD',
    flow: '流程图',
    tasks: '任务计划',
    community: '创意社区'
  }
  return titles[activeView.value]
})

const canPublishCommunity = computed(() => {
  if (!publishForm.value.title.trim()) {
    return false
  }
  if (publishForm.value.item_type === 'project') {
    return Boolean(publishForm.value.project_url.trim())
  }
  return prd.value.length > 0
})

onMounted(loadProfile)

watch(activeView, (value) => {
  if (value === 'community' && !communityItems.value.length) {
    loadCommunity()
  }
})

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
    const response = await generatePlan(messages.value, conversationId.value)
    conversationId.value = response.conversation_id
    const result = response.result || {}
    messages.value.push({
      role: 'assistant',
      content: result.assistant_message || '我已经收到，可以继续补充更多细节。'
    })
    focusedMessageIndex.value = messages.value.length - 1
    if (Array.isArray(result.prd) && result.prd.length) {
      prd.value = result.prd
      fillPublishDraft()
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
      conversation_id: conversationId.value,
      prd: prd.value,
      flow: flow.value,
      tasks: tasks.value
    })
    saveMessage.value = `需求已保存，记录编号 #${response.record_id}`
    fillPublishDraft()
  } catch (err) {
    error.value = err.message
  } finally {
    savingConversation.value = false
  }
}

async function loadCommunity() {
  communityLoading.value = true
  communityError.value = ''
  try {
    const response = await listCommunityItems(communityFilter.value)
    communityItems.value = response.items || []
  } catch (err) {
    communityError.value = err.message
  } finally {
    communityLoading.value = false
  }
}

function setCommunityFilter(type) {
  communityFilter.value = type
  loadCommunity()
}

function preparePublishFromCurrent(type) {
  publishForm.value.item_type = type
  fillPublishDraft()
  activeView.value = 'community'
}

function fillPublishDraft() {
  const firstUserMessage = messages.value.find((message) => message.role === 'user')?.content || ''
  if (!publishForm.value.title) {
    publishForm.value.title = firstUserMessage.slice(0, 32) || '未命名创意'
  }
  if (!publishForm.value.summary) {
    publishForm.value.summary = prd.value[0] || tasks.value[0] || firstUserMessage.slice(0, 120)
  }
}

async function publishCurrentIdea() {
  communityError.value = ''
  communityMessage.value = ''
  publishing.value = true
  try {
    const payload = {
      conversation_id: conversationId.value,
      item_type: publishForm.value.item_type,
      title: publishForm.value.title,
      summary: publishForm.value.summary,
      prd: prd.value,
      flow: flow.value,
      tasks: tasks.value,
      project_url: publishForm.value.item_type === 'project' ? publishForm.value.project_url : null
    }
    const item = await publishCommunityItem(payload)
    communityMessage.value = `已公开发布：${item.title}`
    await loadCommunity()
  } catch (err) {
    communityError.value = err.message
  } finally {
    publishing.value = false
  }
}

async function starCommunityItem(item) {
  try {
    const response = await toggleCommunityStar(item.id)
    item.starred_by_me = response.starred
    item.star_count = response.star_count
  } catch (err) {
    communityError.value = err.message
  }
}

async function focusMessage(index) {
  focusedMessageIndex.value = index
  await nextTick()
  document.getElementById(`message-${index}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function memoryTitle(message, index) {
  const speaker = message.role === 'user' ? '你' : 'Think Land'
  return `${index + 1}. ${speaker}: ${message.content.slice(0, 42)}`
}

function previewLines(item) {
  const content = item.content || {}
  return [...(content.prd || []), ...(content.tasks || [])].slice(0, 3)
}

function formatDate(value) {
  if (!value) {
    return ''
  }
  return new Date(value).toLocaleDateString()
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
