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
        <button class="side-link" :class="{ active: activeView === 'code' }" @click="activeView = 'code'">代码生成</button>
      </nav>

      <section v-if="user" class="sidebar-user">
        <div>
          <span>{{ user.account }}</span>
          <strong>{{ points?.remaining_points ?? '--' }} / {{ points?.granted_points ?? 100 }} 点</strong>
        </div>
        <button class="sidebar-logout" type="button" @click="logout">退出登录</button>
      </section>
    </aside>

    <section class="workspace-main">
      <header class="workspace-header">
        <h1>{{ pageTitle }}</h1>
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
              <details v-if="message.thinking" class="thinking-box">
                <summary>思考过程</summary>
                <p>{{ message.thinking }}</p>
              </details>
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
        <div v-if="prdItems.length" class="prd-history-strip">
          <button
            v-for="item in prdItems"
            :key="item.id"
            type="button"
            :class="{ active: String(item.id) === String(selectedPrdId) }"
            @click="selectPrdItem(item)"
          >
            <strong>{{ item.title }}</strong>
            <span>{{ item.prd.length }} 条 PRD · {{ formatDate(item.updated_at || item.created_at) }}</span>
          </button>
        </div>
        <div v-if="prd.length" class="prd-card-grid">
          <article v-for="(item, index) in prd" :key="item" class="prd-card">
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <h3>{{ prdTitle(item) }}</h3>
            <p>{{ prdBody(item) }}</p>
          </article>
        </div>
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

      <section v-else-if="activeView === 'community'" class="community-page">
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
              <button class="star-button" :class="{ active: item.starred_by_me }" type="button" @click="starCommunityItem(item)">
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

      <section v-else class="codegen-page">
        <div class="codegen-layout">
          <form class="codegen-panel" @submit.prevent="startCodeGeneration">
            <div class="panel-title">
              <span>代码生成</span>
              <b>{{ codeJob?.status || '未开始' }}</b>
            </div>
            <label>
              选择 PRD
              <select v-model="selectedPrdId" @change="applySelectedPrdToCodeForm(true)">
                <option value="">请选择已保存的 PRD</option>
                <option v-for="item in prdItems" :key="item.id" :value="String(item.id)">{{ item.title }}</option>
              </select>
            </label>
            <div v-if="selectedPrd" class="prd-select-preview">
              <strong>{{ selectedPrd.summary }}</strong>
              <span>{{ selectedPrd.prd.length }} 条 PRD · {{ selectedPrd.flow.length }} 个流程节点 · {{ selectedPrd.tasks.length }} 个任务</span>
            </div>
            <p v-else class="codegen-hint">代码生成会严格绑定一个已确认保存的 PRD。请先在创意工作台确认需求，或在这里选择历史 PRD。</p>
            <label>
              项目名称
              <input v-model.trim="codeForm.title" placeholder="例如：AI 学习计划助手" />
            </label>
            <label>
              生成目标
              <textarea v-model.trim="codeForm.target_description" placeholder="描述要生成的应用；可直接基于当前 PRD。"></textarea>
            </label>
            <div class="codegen-stack-grid">
              <label>
                前端
                <select v-model="codeForm.stack.frontend">
                  <option v-for="item in stackRegistry.frontend" :key="item.key" :value="item.key">{{ item.label }}</option>
                </select>
              </label>
              <label>
                后端
                <select v-model="codeForm.stack.backend">
                  <option v-for="item in stackRegistry.backend" :key="item.key" :value="item.key">{{ item.label }}</option>
                </select>
              </label>
              <label>
                数据库
                <select v-model="codeForm.stack.database">
                  <option v-for="item in stackRegistry.database" :key="item.key" :value="item.key">{{ item.label }}</option>
                </select>
              </label>
              <label>
                部署
                <select v-model="codeForm.stack.deploy">
                  <option v-for="item in stackRegistry.deploy" :key="item.key" :value="item.key">{{ item.label }}</option>
                </select>
              </label>
            </div>
            <div class="codegen-meter">
              <span>预计 {{ codeJob?.estimated_tokens || 0 }} token</span>
              <strong>{{ codeJob?.provider_type === 'platform' ? `扣点 ${codeJob?.actual_points || codeJob?.estimated_points || 0}` : '自有模型不扣点' }}</strong>
            </div>
            <button type="submit" :disabled="codeGenerating || !selectedPrdId || !codeForm.title || !codeForm.target_description">
              {{ codeGenerating ? '生成中...' : '开始生成代码' }}
            </button>
          </form>

          <div class="codegen-graph-panel">
            <div class="panel-title">
              <span>代码关系图谱</span>
              <b>{{ codeNodes.length }} 节点</b>
            </div>
            <div class="code-graph">
              <svg aria-hidden="true" viewBox="0 0 1000 390" preserveAspectRatio="none">
                <line
                  v-for="edge in codeEdges"
                  :key="`${edge.source}-${edge.target}`"
                  class="code-edge"
                  :x1="nodePosition(edge.source).x"
                  :y1="nodePosition(edge.source).y"
                  :x2="nodePosition(edge.target).x"
                  :y2="nodePosition(edge.target).y"
                />
              </svg>
              <button
                v-for="node in codeNodes"
                :key="node.key"
                class="code-node"
                :class="[{ active: selectedCodeNode?.key === node.key }, node.type]"
                :style="graphNodeStyle(node.key)"
                type="button"
                @click="selectCodeNode(node)"
              >
                <span>{{ node.type }}</span>
                <strong>{{ node.label }}</strong>
              </button>
            </div>
          </div>

          <aside class="codegen-detail">
            <div class="panel-title">
              <span>生成详情</span>
              <b>{{ codeEvents.length }} 条</b>
            </div>
            <div v-if="selectedCodeNode" class="code-node-detail">
              <strong>{{ selectedCodeNode.label }}</strong>
              <p>{{ selectedCodeNode.description }}</p>
              <button v-if="selectedCodeNode.file_path" type="button" @click="selectCodeFile(selectedCodeNode.file_path)">
                查看 {{ selectedCodeNode.file_path }}
              </button>
            </div>
            <div class="code-event-list">
              <p v-for="event in codeEvents" :key="event.id || event.sequence_index">{{ event.title }}</p>
            </div>
          </aside>
        </div>

        <div class="codegen-secondary-grid">
          <section class="frontend-preview-panel">
            <div class="panel-title">
              <span>前端内置预览</span>
              <b>{{ codeForm.stack.frontend }}</b>
            </div>
            <div class="preview-browser">
              <div class="preview-browser-bar">
                <span></span>
                <span></span>
                <span></span>
                <strong>{{ previewProject.title }}</strong>
              </div>
              <div v-if="previewProject.pageType === 'commerce'" class="commerce-preview">
                <header class="commerce-topbar">
                  <strong>{{ previewProject.brand }}</strong>
                  <span>{{ previewProject.search }}</span>
                  <button type="button">联系商家</button>
                </header>
                <section class="commerce-hero">
                  <small>NEW COLLECTION</small>
                  <h3>{{ previewProject.title }}</h3>
                  <p>{{ previewProject.summary }}</p>
                  <div>
                    <b v-for="tag in previewProject.heroTags" :key="tag">{{ tag }}</b>
                  </div>
                </section>
                <nav class="commerce-categories">
                  <button v-for="category in previewProject.categories" :key="category" type="button">{{ category }}</button>
                </nav>
                <section class="commerce-products">
                  <article v-for="product in previewProject.products" :key="product.name">
                    <div><span>{{ product.tag }}</span></div>
                    <small>{{ product.category }}</small>
                    <h4>{{ product.name }}</h4>
                    <p>{{ product.meta }}</p>
                    <footer><strong>{{ product.price }}</strong><button type="button">购买</button></footer>
                  </article>
                </section>
                <footer class="commerce-tabbar">
                  <button v-for="tab in previewProject.tabs" :key="tab" type="button">{{ tab }}</button>
                </footer>
              </div>
              <template v-else>
                <div class="preview-hero">
                  <small>{{ codeForm.stack.frontend }} · {{ codeForm.stack.backend }}</small>
                  <h3>{{ previewProject.title }}</h3>
                  <p>{{ previewProject.summary }}</p>
                  <button type="button">{{ previewProject.cta }}</button>
                </div>
                <div class="preview-sections">
                  <article v-for="(item, index) in previewProject.prd" :key="`preview-prd-${index}`">
                    <span>{{ String(index + 1).padStart(2, '0') }}</span>
                    <p>{{ item }}</p>
                  </article>
                </div>
              </template>
            </div>
          </section>

          <div class="code-files-panel">
            <div class="panel-title">
              <span>文件预览</span>
              <b>{{ codeFiles.length }} 个文件</b>
            </div>
            <div class="code-file-tabs">
              <button v-for="file in codeFiles" :key="file.path" type="button" :class="{ active: selectedCodeFile?.path === file.path }" @click="chooseCodeFile(file)">
                {{ file.path }}
              </button>
            </div>
            <div v-if="selectedCodeFile" class="code-file-viewbar">
              <p>{{ selectedCodeFile.explanation }}</p>
              <div v-if="selectedCodeFileIsFrontend" class="code-file-view-toggle">
                <button type="button" :class="{ active: codeFileViewMode === 'preview' }" @click="codeFileViewMode = 'preview'">页面预览</button>
                <button type="button" :class="{ active: codeFileViewMode === 'code' }" @click="codeFileViewMode = 'code'">查看代码</button>
              </div>
            </div>
            <div v-if="selectedCodeFile && selectedCodeFileIsFrontend && codeFileViewMode === 'preview'" class="code-inline-preview">
              <div class="preview-browser file-preview-browser">
                <div class="preview-browser-bar">
                  <span></span>
                  <span></span>
                  <span></span>
                  <strong>{{ previewProject.title }}</strong>
                </div>
                <div v-if="previewProject.pageType === 'commerce'" class="commerce-preview">
                  <header class="commerce-topbar">
                    <strong>{{ previewProject.brand }}</strong>
                    <span>{{ previewProject.search }}</span>
                    <button type="button">联系商家</button>
                  </header>
                  <section class="commerce-hero">
                    <small>NEW COLLECTION</small>
                    <h3>{{ previewProject.title }}</h3>
                    <p>{{ previewProject.summary }}</p>
                    <div>
                      <b v-for="tag in previewProject.heroTags" :key="tag">{{ tag }}</b>
                    </div>
                  </section>
                  <nav class="commerce-categories">
                    <button v-for="category in previewProject.categories" :key="category" type="button">{{ category }}</button>
                  </nav>
                  <section class="commerce-products">
                    <article v-for="product in previewProject.products" :key="product.name">
                      <div><span>{{ product.tag }}</span></div>
                      <small>{{ product.category }}</small>
                      <h4>{{ product.name }}</h4>
                      <p>{{ product.meta }}</p>
                      <footer><strong>{{ product.price }}</strong><button type="button">购买</button></footer>
                    </article>
                  </section>
                  <footer class="commerce-tabbar">
                    <button v-for="tab in previewProject.tabs" :key="tab" type="button">{{ tab }}</button>
                  </footer>
                </div>
                <template v-else>
                  <div class="preview-hero">
                    <small>{{ codeForm.stack.frontend }} · {{ codeForm.stack.backend }}</small>
                    <h3>{{ previewProject.title }}</h3>
                    <p>{{ previewProject.summary }}</p>
                    <button type="button">{{ previewProject.cta }}</button>
                  </div>
                  <div class="preview-sections">
                    <article v-for="(item, index) in previewProject.prd" :key="`file-preview-prd-${index}`">
                      <span>{{ String(index + 1).padStart(2, '0') }}</span>
                      <p>{{ item }}</p>
                    </article>
                  </div>
                </template>
              </div>
            </div>
            <pre v-if="selectedCodeFile && (!selectedCodeFileIsFrontend || codeFileViewMode === 'code')" class="code-file-preview"><code>{{ selectedCodeFile.content }}</code></pre>
            <p v-if="!selectedCodeFile" class="empty-state">生成完成后可以在这里查看代码文件。</p>
          </div>
        </div>

        <form class="github-panel" @submit.prevent="pushGeneratedCode">
          <div class="panel-title">
            <span>推送 GitHub</span>
            <b>{{ githubConfig?.configured ? '已配置' : '未配置' }}</b>
          </div>
          <div class="publish-grid">
            <label>
              GitHub PAT
              <input v-model.trim="githubForm.token" type="password" placeholder="只保存一次，后端加密存储" />
            </label>
            <label>
              仓库
              <input v-model.trim="githubForm.default_repo" placeholder="owner/repo" />
            </label>
            <label>
              基准分支
              <input v-model.trim="githubForm.default_branch" placeholder="main 或 master" />
            </label>
          </div>
          <div class="composer-actions">
            <span>{{ codeJob?.github_url ? `已推送：${codeJob.github_url}` : '默认推送到 thinkland/generated-* 新分支' }}</span>
            <div class="composer-buttons">
              <button type="button" class="confirm-button" :disabled="!githubForm.token" @click="saveGitHubSettings">保存 GitHub</button>
              <button type="submit" :disabled="!codeJob || !githubForm.default_repo || codePushing">{{ codePushing ? '推送中...' : '确认 OK 后推送' }}</button>
            </div>
          </div>
          <p v-if="codeMessage" class="form-success">{{ codeMessage }}</p>
          <p v-if="codeError" class="form-error">{{ codeError }}</p>
        </form>
      </section>
    </section>

    <div v-if="showConfig" class="settings-modal" @click.self="showConfig = false">
      <form class="settings-card" @submit.prevent="saveConfig">
        <div class="panel-title">
          <span>AI 接口配置</span>
          <b>{{ aiConfig?.configured ? '已保存' : '未配置' }}</b>
        </div>
        <label>
          模型来源
          <select v-model="configForm.provider_type">
            <option value="platform">平台提供模型（扣点）</option>
            <option value="custom">自有模型（不扣点）</option>
          </select>
        </label>
        <label v-if="configForm.provider_type === 'custom'">
          Base URL
          <input v-model.trim="configForm.base_url" placeholder="https://api.openai.com/v1" />
        </label>
        <label>
          模型
          <input v-model.trim="configForm.model" :placeholder="configForm.provider_type === 'platform' ? '平台默认模型，例如 gpt-4o-mini' : 'gpt-4o-mini'" />
        </label>
        <label v-if="configForm.provider_type === 'custom'">
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
  createCodeGenerationJob,
  generatePlan,
  getCodeGenerationJob,
  getCodeGenerationStackRegistry,
  getGitHubConfig,
  getMe,
  listCommunityItems,
  listPrds,
  publishCommunityItem,
  pushCodeGenerationToGitHub,
  saveAIConfig,
  saveGitHubToken,
  streamCodeGenerationEvents,
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
const codeGenerating = ref(false)
const codePushing = ref(false)
const error = ref('')
const configMessage = ref('')
const saveMessage = ref('')
const communityMessage = ref('')
const communityError = ref('')
const codeMessage = ref('')
const codeError = ref('')
const draft = ref('')
const chatListEl = ref(null)
const conversationId = ref(null)
const focusedMessageIndex = ref(0)
const configForm = ref({ provider_type: 'custom', base_url: '', model: '', api_key: '' })
const messages = ref([
  {
    role: 'assistant',
    content: '你好，我会通过几轮问答帮你把产品目标说清楚。先告诉我：你想做什么产品，给谁用，解决什么问题？'
  }
])
const prd = ref([])
const flow = ref([])
const tasks = ref([])
const prdItems = ref([])
const selectedPrdId = ref('')
const communityFilter = ref('all')
const communityItems = ref([])
const publishForm = ref({ item_type: 'prd', title: '', summary: '', project_url: '' })
const codeForm = ref({
  title: '',
  target_description: '',
  stack: { frontend: 'vue', backend: 'fastapi', database: 'mysql', deploy: 'ubuntu-nginx' }
})
const stackRegistry = ref({
  frontend: [{ key: 'vue', label: 'Vue' }, { key: 'react', label: 'React' }],
  backend: [
    { key: 'fastapi', label: 'Python FastAPI' },
    { key: 'nestjs', label: 'Node.js NestJS' },
    { key: 'springboot', label: 'Java Spring Boot' }
  ],
  database: [{ key: 'mysql', label: 'MySQL' }, { key: 'postgresql', label: 'PostgreSQL' }],
  deploy: [{ key: 'ubuntu-nginx', label: 'Ubuntu + Nginx' }, { key: 'docker', label: 'Docker' }]
})
const codeJob = ref(null)
const codeEvents = ref([])
const codeFiles = ref([])
const codeNodes = ref([])
const codeEdges = ref([])
const selectedCodeFile = ref(null)
const selectedCodeNode = ref(null)
const codeFileViewMode = ref('code')
const githubConfig = ref(null)
const githubForm = ref({ token: '', default_repo: '', default_branch: 'main' })

const pageTitle = computed(() => {
  const titles = {
    chat: '和 Think Land 梳理产品想法',
    prd: 'PRD',
    flow: '流程图',
    tasks: '任务计划',
    community: '创意社区',
    code: '代码生成'
  }
  return titles[activeView.value]
})

const canPublishCommunity = computed(() => {
  if (!publishForm.value.title.trim()) return false
  if (publishForm.value.item_type === 'project') return Boolean(publishForm.value.project_url.trim())
  return prd.value.length > 0
})

const selectedPrd = computed(() => prdItems.value.find((item) => String(item.id) === String(selectedPrdId.value)) || null)

const selectedCodeFileIsFrontend = computed(() => isFrontendFile(selectedCodeFile.value))

const previewProject = computed(() => {
  const source = selectedPrd.value || {}
  const targetLines = codeForm.value.target_description
    .split('\n')
    .map((line) => line.replace(/^(PRD|流程|任务)[:：]\s*/i, '').trim())
    .filter(Boolean)
  const sourcePrd = Array.isArray(source.prd) && source.prd.length ? source.prd : (prd.value.length ? prd.value : targetLines)
  const sourceFlow = Array.isArray(source.flow) && source.flow.length ? source.flow : flow.value
  const sourceTasks = Array.isArray(source.tasks) && source.tasks.length ? source.tasks : tasks.value
  const title = source.title || codeForm.value.title || '未命名项目'
  const summary = source.summary || sourcePrd[0] || '基于已确认需求生成可预览的前端页面。'
  const contentText = [title, summary, ...sourcePrd, ...sourceFlow, ...sourceTasks].join(' ')
  const isCommerce = /电商|商品|服装|价格|尺码|颜色|库存|购买|分类|banner|搜索|收藏|小程序/.test(contentText)

  if (isCommerce) {
    return {
      pageType: 'commerce',
      brand: '衣橱选品',
      title: contentText.includes('服装') ? '春夏服装新品馆' : '精选商品快逛',
      summary: '商品图片、价格、尺码、颜色和库存集中展示，支持分类浏览、搜索、收藏和购买引导。',
      search: '搜索上衣、裙子、通勤风格',
      heroTags: ['Banner轮播', '快捷分类', '新品推荐', '热卖商品'],
      categories: ['上衣', '裤子', '裙子', '春夏', '秋冬', '休闲', '商务'],
      products: [
        { name: '轻盈通勤衬衫', category: '上衣', price: '¥199', meta: 'S-XL · 3色 · 有库存', tag: '新品' },
        { name: '高腰垂感西裤', category: '裤子', price: '¥269', meta: 'XS-L · 黑/杏 · 少量库存', tag: '热卖' },
        { name: '法式碎花半裙', category: '裙子', price: '¥229', meta: 'S-L · 春夏 · 可收藏', tag: '推荐' },
        { name: '商务针织外套', category: '商务', price: '¥329', meta: 'M-XL · 2色 · 可联系商家', tag: '精选' }
      ],
      tabs: ['首页', '分类', '搜索', '收藏', '联系']
    }
  }

  return {
    pageType: 'product',
    title,
    summary,
    cta: sourceFlow[0] || '开始体验',
    prd: sourcePrd.slice(0, 6),
    flow: sourceFlow.slice(0, 5),
    tasks: sourceTasks.slice(0, 5)
  }
})

onMounted(async () => {
  await loadProfile()
  await loadGitHubConfig()
  await loadStackRegistry()
  await loadPrds()
})

watch(activeView, (value) => {
  if (['prd', 'flow', 'tasks'].includes(value)) {
    loadPrds()
  }
  if (value === 'community' && !communityItems.value.length) loadCommunity()
  if (value === 'code') {
    loadPrds().then(fillCodeDraft)
  }
})

async function loadProfile() {
  try {
    const response = await getMe()
    applyProfile(response)
    if (response.ai_config?.configured) {
      configForm.value.provider_type = response.ai_config.provider_type || 'custom'
      configForm.value.base_url = response.ai_config.base_url || ''
      configForm.value.model = response.ai_config.model || ''
    }
  } catch (err) {
    clearToken()
    router.push('/login')
  }
}

async function loadGitHubConfig() {
  try {
    const response = await getGitHubConfig()
    githubConfig.value = response
    githubForm.value.default_repo = response.default_repo || ''
    githubForm.value.default_branch = response.default_branch || 'main'
  } catch (err) {
    githubConfig.value = { configured: false }
  }
}

async function loadStackRegistry() {
  try {
    stackRegistry.value = await getCodeGenerationStackRegistry()
  } catch {
    // Keep built-in options available if the registry endpoint is temporarily unavailable.
  }
}

async function loadPrds() {
  try {
    const response = await listPrds()
    prdItems.value = response.items || []
    if (!selectedPrdId.value && conversationId.value && prdItems.value.some((item) => item.id === conversationId.value)) {
      selectedPrdId.value = String(conversationId.value)
    }
    if (!selectedPrdId.value && prdItems.value.length) {
      selectedPrdId.value = String(prdItems.value[0].id)
    }
    if (!prd.value.length && selectedPrd.value) {
      applyPrdToWorkspace(selectedPrd.value)
    }
  } catch {
    prdItems.value = []
  }
}

function applyPrdToWorkspace(item) {
  if (!item) return
  prd.value = item.prd || []
  flow.value = item.flow || []
  tasks.value = item.tasks || []
}

function selectPrdItem(item) {
  selectedPrdId.value = String(item.id)
  applyPrdToWorkspace(item)
  applySelectedPrdToCodeForm(true)
}

function applyProfile(response) {
  user.value = response.user
  points.value = response.points
  aiConfig.value = response.ai_config
}

function cleanAssistantMessage(content) {
  return String(content || '')
    .replace(/<think>[\s\S]*?<\/think>/gi, '')
    .trim()
}

async function saveConfig() {
  configMessage.value = ''
  error.value = ''
  if (!configForm.value.model || (configForm.value.provider_type === 'custom' && (!configForm.value.base_url || !configForm.value.api_key))) {
    error.value = '请填写模型；自有模型还需要 Base URL 和 API Key'
    return
  }
  configSaving.value = true
  try {
    const payload = {
      provider_type: configForm.value.provider_type,
      model: configForm.value.model,
      base_url: configForm.value.provider_type === 'custom' ? configForm.value.base_url : null,
      api_key: configForm.value.provider_type === 'custom' ? configForm.value.api_key : null
    }
    const response = await saveAIConfig(payload)
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
  if (!content || loading.value) return
  error.value = ''
  saveMessage.value = ''
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
      content: cleanAssistantMessage(result.assistant_message || '我已经收到，可以继续补充更多细节。'),
      thinking: result.thinking || ''
    })
    focusedMessageIndex.value = messages.value.length - 1
    if (Array.isArray(result.prd) && result.prd.length) {
      prd.value = result.prd
      fillPublishDraft()
      fillCodeDraft()
    }
    if (Array.isArray(result.flow) && result.flow.length) flow.value = result.flow
    if (Array.isArray(result.tasks) && result.tasks.length) tasks.value = result.tasks
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
    const response = await confirmConversation({ messages: messages.value, conversation_id: conversationId.value, prd: prd.value, flow: flow.value, tasks: tasks.value })
    saveMessage.value = `需求已保存，记录编号 #${response.record_id}`
    conversationId.value = response.conversation_id
    selectedPrdId.value = String(response.conversation_id)
    await loadPrds()
    applyPrdToWorkspace(selectedPrd.value)
    fillPublishDraft()
    fillCodeDraft()
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
  if (!publishForm.value.title) publishForm.value.title = firstUserMessage.slice(0, 32) || '未命名创意'
  if (!publishForm.value.summary) publishForm.value.summary = prd.value[0] || tasks.value[0] || firstUserMessage.slice(0, 120)
}

async function publishCurrentIdea() {
  communityError.value = ''
  communityMessage.value = ''
  publishing.value = true
  try {
    const item = await publishCommunityItem({
      conversation_id: conversationId.value,
      item_type: publishForm.value.item_type,
      title: publishForm.value.title,
      summary: publishForm.value.summary,
      prd: prd.value,
      flow: flow.value,
      tasks: tasks.value,
      project_url: publishForm.value.item_type === 'project' ? publishForm.value.project_url : null
    })
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

function fillCodeDraft() {
  applySelectedPrdToCodeForm(true)
  const firstUserMessage = messages.value.find((message) => message.role === 'user')?.content || ''
  if (!codeForm.value.title) codeForm.value.title = firstUserMessage.slice(0, 32) || publishForm.value.title || '未命名项目'
  if (!codeForm.value.target_description) {
    codeForm.value.target_description = [...prd.value, ...flow.value, ...tasks.value].join('\n') || firstUserMessage
  }
}

function applySelectedPrdToCodeForm(force = true) {
  const item = selectedPrd.value
  if (!item) return
  const target = [
    ...item.prd.map((line) => `PRD：${line}`),
    ...item.flow.map((line) => `流程：${line}`),
    ...item.tasks.map((line) => `任务：${line}`)
  ].join('\n')
  if (force || !codeForm.value.title) codeForm.value.title = item.title || '未命名项目'
  if (force || !codeForm.value.target_description) codeForm.value.target_description = target
}

async function startCodeGeneration() {
  if (!selectedPrdId.value) {
    codeError.value = '请先选择一个已保存的 PRD'
    return
  }
  applySelectedPrdToCodeForm(true)
  codeGenerating.value = true
  codeError.value = ''
  codeMessage.value = ''
  codeEvents.value = []
  try {
    const job = await createCodeGenerationJob({ ...codeForm.value, conversation_id: Number(selectedPrdId.value) })
    applyCodeJob(job)
    await streamCodeGenerationEvents(job.id, (event) => {
      if (event.status) return
      codeEvents.value.push(event)
    })
    codeMessage.value = '代码预览已生成，可以查看图谱和文件。'
    const refreshed = await getCodeGenerationJob(job.id)
    applyCodeJob(refreshed)
    points.value = (await getMe()).points
  } catch (err) {
    codeError.value = err.message
  } finally {
    codeGenerating.value = false
  }
}

function applyCodeJob(job) {
  codeJob.value = job
  codeFiles.value = job.files || []
  codeNodes.value = job.graph_nodes || []
  codeEdges.value = job.graph_edges || []
  chooseCodeFile(codeFiles.value.find(isFrontendFile) || codeFiles.value[0] || null)
  selectedCodeNode.value = codeNodes.value[0] || null
}

function isFrontendFile(file) {
  const path = file?.path || ''
  return path.startsWith('frontend/') || /\.(vue|jsx|tsx|html)$/i.test(path)
}

function chooseCodeFile(file) {
  selectedCodeFile.value = file
  codeFileViewMode.value = isFrontendFile(file) ? 'preview' : 'code'
}

function nodePosition(key) {
  const node = codeNodes.value.find((item) => item.key === key)
  return node?.position || { x: 120, y: 120 }
}

function graphNodeStyle(key) {
  const position = nodePosition(key)
  const left = Math.min(94, Math.max(6, (position.x / 1000) * 100))
  const top = Math.min(91, Math.max(9, (position.y / 390) * 100))
  return { left: `${left}%`, top: `${top}%` }
}

function selectCodeNode(node) {
  selectedCodeNode.value = node
  if (node.file_path) selectCodeFile(node.file_path)
}

function selectCodeFile(path) {
  const file = codeFiles.value.find((item) => item.path === path)
  if (file) chooseCodeFile(file)
}

async function saveGitHubSettings() {
  codeError.value = ''
  try {
    githubConfig.value = await saveGitHubToken(githubForm.value)
    githubForm.value.token = ''
    codeMessage.value = 'GitHub 配置已保存。'
  } catch (err) {
    codeError.value = err.message
  }
}

async function pushGeneratedCode() {
  if (!codeJob.value) return
  codePushing.value = true
  codeError.value = ''
  try {
    const result = await pushCodeGenerationToGitHub(codeJob.value.id, { repo: githubForm.value.default_repo })
    codeJob.value.github_url = result.url
    codeMessage.value = `已推送到 ${result.url}`
  } catch (err) {
    codeError.value = err.message
  } finally {
    codePushing.value = false
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

function splitPrdLine(item) {
  const text = String(item || '').trim()
  const match = text.match(/^([^：:，,。.\n]{2,18})[：:，,。.]?\s*(.*)$/)
  if (!match) return { title: '需求条目', body: text }
  return { title: match[1], body: match[2] || text }
}

function prdTitle(item) {
  return splitPrdLine(item).title
}

function prdBody(item) {
  return splitPrdLine(item).body
}

function previewLines(item) {
  const content = item.content || {}
  return [...(content.prd || []), ...(content.tasks || [])].slice(0, 3)
}

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString() : ''
}

async function scrollChat() {
  await nextTick()
  if (chatListEl.value) chatListEl.value.scrollTop = chatListEl.value.scrollHeight
}

function logout() {
  clearToken()
  router.push('/')
}
</script>
