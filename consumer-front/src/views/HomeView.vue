<template>
  <main class="site-page home-page">
    <nav class="site-nav">
      <RouterLink class="brand" to="/">
        <img class="brand-logo" src="/think-land-logo.svg" alt="Think Land logo" />
        <strong>Think Land</strong>
      </RouterLink>
      <div class="nav-links">
        <a href="#product">产品</a>
        <a href="#motion">演示</a>
        <a href="#notice">说明</a>
      </div>
      <RouterLink class="nav-cta" to="/login">开始使用</RouterLink>
    </nav>

    <section class="hero">
      <div class="hero-scene" aria-hidden="true">
        <div class="scene-grid"></div>
        <div class="prd-window">
          <div class="window-top">
            <span></span><span></span><span></span>
          </div>
          <p class="voice-line">"帮我做一个面向个人创作者的 AI 项目助手"</p>
          <div class="typing-card">
            <span>正在生成 PRD</span>
            <strong>产品目标 / 用户旅程 / 核心功能 / 里程碑</strong>
          </div>
        </div>
        <div class="flow-window">
          <div class="flow-node node-a">想法</div>
          <div class="flow-node node-b">PRD</div>
          <div class="flow-node node-c">流程图</div>
          <div class="flow-node node-d">任务</div>
          <svg viewBox="0 0 500 280" role="img" aria-label="流程图动画">
            <path class="flow-line line-one" d="M92 96 C170 64 210 74 250 116" />
            <path class="flow-line line-two" d="M276 142 C334 176 354 188 408 178" />
            <path class="flow-line line-three" d="M244 152 C208 198 178 222 124 222" />
          </svg>
        </div>
      </div>

      <div class="hero-copy">
        <h1>把一句话灵感，变成可执行的产品计划。</h1>
        <p>
          Think Land 面向个人创作者、独立开发者和小团队，把需求梳理、PRD 生成、流程图规划和任务拆解放进一个轻量工作台。
        </p>
        <div class="hero-actions">
          <RouterLink class="primary-btn" to="/login">开始使用</RouterLink>
          <button class="secondary-btn" @click="openDemo">查看生成动画</button>
        </div>
      </div>
    </section>

    <section id="product" class="intro-section">
      <div>
        <p class="eyebrow">网站介绍</p>
        <h2>它不是聊天框，而是帮你把想法往前推的产品搭子。</h2>
      </div>
      <div class="intro-grid">
        <article>
          <span>01</span>
          <h3>自然语言生成 PRD</h3>
          <p>输入你的产品想法，系统会整理目标用户、使用场景、功能范围和验收标准。</p>
        </article>
        <article>
          <span>02</span>
          <h3>自动生成业务流程</h3>
          <p>根据 PRD 识别关键节点，生成从用户触发到交付结果的流程图。</p>
        </article>
        <article>
          <span>03</span>
          <h3>沉淀个人项目空间</h3>
          <p>登录后可以保存创意、继续补充上下文，并把计划拆成可执行任务。</p>
        </article>
      </div>
    </section>

    <section id="motion" class="motion-section">
      <div class="motion-copy">
        <p class="eyebrow">动态演示</p>
        <h2>从一句话到 PRD，再到流程图。</h2>
        <p>你描述目标，AI 先归纳需求，再将需求变成可以讨论和落地的流程结构。</p>
        <button class="primary-btn small" style="margin-top:18px" @click="openDemo">观看生成动画</button>
      </div>
      <div class="motion-board">
        <div class="prompt-stream">
          <span>用户输入</span>
          <strong>{{ activePrompt }}</strong>
        </div>
        <div class="generated-prd">
          <span>PRD 片段</span>
          <p v-for="item in prdItems" :key="item">{{ item }}</p>
        </div>
        <div class="mini-flow">
          <i>需求</i><b></b><i>页面</i><b></b><i>接口</i><b></b><i>交付</i>
        </div>
      </div>
    </section>

    <footer id="notice" class="site-footer">
      <div class="footer-brand">Think Land</div>
      <p>京ICP备20260519号-1 · AI 使用说明 · 信息收集说明 · 免责声明</p>
      <small>本网站提供的 AI 生成内容用于辅助创作和效率提升，可能存在不准确或不完整之处，请结合实际业务自行判断。我们仅收集完成注册、登录和产品体验所需的必要信息。</small>
    </footer>

    <!-- ── DEMO MODAL ──────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="demoVisible" class="demo-modal" @click.self="closeDemo">
        <div class="demo-backdrop"></div>
        <div class="demo-card">

          <div class="demo-header">
            <div class="demo-header-left">
              <span class="footer-brand" style="font-size:15px">Think Land · 生成演示</span>
              <div class="demo-steps">
                <button
                  v-for="(step, i) in steps"
                  :key="step.label"
                  class="demo-step"
                  :class="{ active: demoPhase === i, done: demoPhase > i }"
                  @click="setPhase(i)"
                >
                  <span class="step-dot"></span>
                  {{ step.label }}
                </button>
              </div>
            </div>
            <button class="demo-close" @click="closeDemo">×</button>
          </div>

          <div class="demo-body">

            <!-- Phase 0: 自然语言输入 -->
            <div class="demo-phase" :class="{ visible: demoPhase === 0 }">
              <div class="demo-input-scene">
                <div class="demo-terminal">
                  <div class="demo-terminal-bar">
                    <span></span><span></span><span></span>
                  </div>
                  <div class="demo-terminal-body">
                    <div class="prompt">&gt; 输入你的产品想法：</div>
                    <div class="typed-text">{{ typedIdea }}</div>
                  </div>
                </div>
                <div class="demo-prd-preview">
                  <h3>Think Land 正在为你生成...</h3>
                  <div class="demo-prd-line">目标用户：独立开发者与小团队</div>
                  <div class="demo-prd-line">核心功能：PRD 生成、流程图、任务拆解</div>
                  <div class="demo-prd-line">使用场景：产品构思到可执行计划</div>
                </div>
              </div>
            </div>

            <!-- Phase 1: 生成代码 -->
            <div class="demo-phase" :class="{ visible: demoPhase === 1 }">
              <div class="demo-code-window">
                <div class="demo-code-bar">
                  <span>app/index.tsx</span>
                </div>
                <div class="demo-code-body">
                  <div v-for="(line, i) in codeLines" :key="i" class="code-line" :class="{ appeared: codeVisible >= i }">
                    <span class="line-num">{{ i + 1 }}</span>
                    <span v-html="line"></span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Phase 2: 部署中 -->
            <div class="demo-phase" :class="{ visible: demoPhase === 2 }">
              <div class="demo-deploy">
                <div class="deploy-orbit">
                  <div class="orbit-ring"></div>
                  <div class="orbit-ring-inner"></div>
                  <div class="orbit-dot"></div>
                  <div class="orbit-core">🚀</div>
                </div>
                <div class="deploy-status">
                  <span>{{ deployLabel }}</span>
                  <div class="deploy-bar"><div class="deploy-bar-fill"></div></div>
                </div>
                <div class="deploy-logs">
                  <div v-for="log in deployLogs" :key="log.text" class="log-entry" :class="[log.type, { visible: log.visible }]">
                    <span class="log-icon">{{ log.icon }}</span>
                    <span>{{ log.text }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Phase 3: 上线预览 -->
            <div class="demo-phase" :class="{ visible: demoPhase === 3 }">
              <div class="demo-site-frame">
                <div class="site-browser-bar">
                  <div class="site-dots"><span></span><span></span><span></span></div>
                  <div class="site-url-bar">thinkland.app/workspace/project</div>
                </div>
                <div class="site-content">
                  <nav class="site-nav-bar">
                    <strong>ThinkLand</strong>
                    <span>产品</span><span>功能</span><span>定价</span>
                  </nav>
                  <div class="site-hero-section">
                    <h2>把想法变成产品计划</h2>
                    <p>面向独立开发者和小团队，把需求梳理、PRD 生成、<br/>流程图规划和任务拆解放进一个轻量工作台。</p>
                    <button class="site-cta-btn">立即开始</button>
                  </div>
                  <div class="site-features">
                    <div class="site-feature-card">
                      <h4>PRD 生成</h4>
                      <p>自然语言输入，结构化输出</p>
                    </div>
                    <div class="site-feature-card">
                      <h4>流程图</h4>
                      <p>自动识别关键节点</p>
                    </div>
                    <div class="site-feature-card">
                      <h4>任务拆解</h4>
                      <p>从需求到可执行计划</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>

          <div class="demo-footer">
            <span class="demo-footer-note">{{ steps[demoPhase]?.note }}</span>
            <div class="demo-footer-cta">
              <button v-if="demoPhase > 0" class="secondary-btn" style="min-height:40px;padding:0 18px;font-size:14px" @click="prevPhase">
                ← 上一步
              </button>
              <button v-if="demoPhase < steps.length - 1" class="primary-btn" style="min-height:40px;padding:0 18px;font-size:14px" @click="nextPhase">
                下一步 →
              </button>
              <RouterLink v-else class="primary-btn" style="min-height:40px;padding:0 18px;font-size:14px" to="/login" @click="closeDemo">
                开始使用 →
              </RouterLink>
            </div>
          </div>

        </div>
      </div>
    </Teleport>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const prompts = [
  '我想做一个能帮学生规划复习的 AI 工具',
  '帮我设计一个给自由职业者用的客户管理产品',
  '我要做一个能自动生成活动方案的小程序'
]

const index = ref(0)
let timer

const activePrompt = computed(() => prompts[index.value])
const prdItems = computed(() => [
  `目标用户：${index.value === 1 ? '自由职业者和小型工作室' : index.value === 2 ? '活动运营人员' : '学生和备考人群'}`,
  '核心价值：把零散想法整理成可执行计划',
  '关键路径：输入目标 -> 生成 PRD -> 生成流程图 -> 拆解任务'
])

onMounted(() => {
  timer = window.setInterval(() => {
    index.value = (index.value + 1) % prompts.length
  }, 3200)
})

onBeforeUnmount(() => {
  window.clearInterval(timer)
})

// ── Demo modal logic ─────────────────────────────────────────
const demoVisible = ref(false)
const demoPhase = ref(0)

const steps = [
  { label: '自然语言', note: '输入产品想法，AI 理解用户目标与场景' },
  { label: '生成代码', note: '将结构化需求转化为可运行的产品代码' },
  { label: '部署上线', note: '一键部署到全球 CDN，平均 8 秒完成' },
  { label: '查看站点', note: '你的产品已上线，可通过链接访问' },
]

function openDemo() {
  demoVisible.value = true
  demoPhase.value = 0
  resetDemo()
  startDemo()
}

function closeDemo() {
  demoVisible.value = false
  stopDemo()
}

function nextPhase() {
  if (demoPhase.value < steps.length - 1) {
    demoPhase.value++
    onPhaseEnter()
  }
}

function prevPhase() {
  if (demoPhase.value > 0) {
    demoPhase.value--
    onPhaseEnter()
  }
}

function setPhase(i) {
  demoPhase.value = i
  onPhaseEnter()
}

// ── Phase 0: typing effect ───────────────────────────────────
const typedIdea = ref('')
let typingTimer = null

function startTyping() {
  const text = '我想做一个面向独立开发者的 AI 项目助手，帮助梳理产品需求并生成可执行的开发计划'
  let i = 0
  typedIdea.value = ''
  clearInterval(typingTimer)
  typingTimer = setInterval(() => {
    typedIdea.value = text.slice(0, i++)
    if (i > text.length) clearInterval(typingTimer)
  }, 55)
}

// ── Phase 1: code reveal ─────────────────────────────────────
const codeLines = [
  '<span class="code-comment">// ThinkLand App — generated by AI</span>',
  '<span class="code-keyword">import</span> { useState } <span class="code-keyword">from</span> <span class="code-string">\'react\'</span>',
  '<span class="code-keyword">import</span> { generatePRD } <span class="code-keyword">from</span> <span class="code-string">\'@thinkland/ai\'</span>',
  '',
  '<span class="code-keyword">export default function</span> <span class="code-func">App</span>() {',
  '  <span class="code-keyword">const</span> [idea, setIdea] = <span class="code-func">useState</span>(<span class="code-string">\'\'</span>)',
  '  <span class="code-keyword">const</span> [prd, setPrd]   = <span class="code-func">useState</span>([])',
  '',
  '  <span class="code-keyword">async function</span> <span class="code-func">handleGenerate</span>() {',
  '    <span class="code-keyword">const</span> result = <span class="code-keyword">await</span> <span class="code-func">generatePRD</span>(idea)',
  '    setPrd(result.<span class="code-var">prd</span>)',
  '  }',
  '',
  '  <span class="code-keyword">return</span> (',
  '    &lt;<span class="code-func">main</span> className=<span class="code-string">"app-container"</span>&gt;',
  '      &lt;<span class="code-func">Header</span> /&gt;',
  '      &lt;<span class="code-func">PromptInput</span> value={idea} onChange={setIdea} /&gt;',
  '      &lt;<span class="code-func">PRDList</span> items={prd} /&gt;',
  '    &lt;/<span class="code-func">main</span>&gt;',
  '  )',
  '}',
]

const codeVisible = ref(-1)
let codeTimer = null

function startCodeReveal() {
  codeVisible.value = -1
  clearInterval(codeTimer)
  let i = 0
  codeTimer = setInterval(() => {
    codeVisible.value = i++
    if (i >= codeLines.length) clearInterval(codeTimer)
  }, 120)
}

// ── Phase 2: deploy logs ──────────────────────────────────────
const deployLabel = ref('准备上传文件...')
const deployLogs = ref([
  { type: 'success', icon: '✓', text: '构建完成 — 42 个模块', visible: false },
  { type: 'success', icon: '✓', text: '上传到 Cloudflare CDN', visible: false },
  { type: 'progress', icon: '●', text: '配置边缘节点...', visible: false },
  { type: 'success', icon: '✓', text: 'HTTPS 证书签发成功', visible: false },
  { type: 'progress', icon: '●', text: '更新全球路由表...', visible: false },
  { type: 'success', icon: '✓', text: 'thinkland.app 上线 · 耗时 8.2s', visible: false },
])
let deployTimer = null
const deployPhases = [
  { label: '准备上传文件...', logIndices: [] },
  { label: '正在上传到 CDN...', logIndices: [0, 1] },
  { label: '配置边缘节点...', logIndices: [2, 3] },
  { label: '上线完成！', logIndices: [4, 5] },
]

function startDeploy() {
  deployLabel.value = deployPhases[0].label
  deployLogs.value.forEach(l => { l.visible = false })
  let step = 0
  clearTimeout(deployTimer)

  function next() {
    if (step >= deployPhases.length) return
    const ph = deployPhases[step]
    deployLabel.value = ph.label
    ph.logIndices.forEach(idx => {
      setTimeout(() => { deployLogs.value[idx].visible = true }, 400)
    })
    step++
    deployTimer = setTimeout(next, 1400)
  }
  next()
}

// ── Phase orchestration ──────────────────────────────────────
let timers = []

function stopDemo() {
  ;[typingTimer, codeTimer, deployTimer].forEach(t => clearInterval(t))
  timers.forEach(t => clearTimeout(t))
  timers = []
}

function resetDemo() {
  stopDemo()
  typedIdea.value = ''
  codeVisible.value = -1
  deployLogs.value.forEach(l => { l.visible = false })
}

function startDemo() {
  if (demoPhase.value === 0) {
    startTyping()
  }
}

function onPhaseEnter() {
  stopDemo()
  if (demoPhase.value === 0) startTyping()
  else if (demoPhase.value === 1) startCodeReveal()
  else if (demoPhase.value === 2) startDeploy()
}
</script>