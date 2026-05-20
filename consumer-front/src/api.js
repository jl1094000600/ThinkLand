const TOKEN_KEY = 'consumer-token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export async function apiRequest(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  }
  const token = getToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(path, { ...options, headers })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = data.detail || '请求失败，请稍后重试'
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg).join('，') : message)
  }
  return data
}

export async function register(account, password) {
  return apiRequest('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ account, password })
  })
}

export async function login(account, password) {
  return apiRequest('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ account, password })
  })
}

export async function getMe() {
  return apiRequest('/api/me')
}

export async function saveAIConfig(config) {
  return apiRequest('/api/me/ai-config', {
    method: 'PUT',
    body: JSON.stringify(config)
  })
}

export async function generatePlan(messages, conversationId = null) {
  return apiRequest('/api/generate', {
    method: 'POST',
    body: JSON.stringify({ messages, conversation_id: conversationId })
  })
}

export async function confirmConversation(payload) {
  return apiRequest('/api/conversations/confirm', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function listPrds() {
  return apiRequest('/api/prds')
}

export async function listCommunityItems(itemType = 'all') {
  return apiRequest(`/api/community/items?item_type=${encodeURIComponent(itemType)}`)
}

export async function publishCommunityItem(payload) {
  return apiRequest('/api/community/items', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function toggleCommunityStar(itemId) {
  return apiRequest(`/api/community/items/${itemId}/star`, {
    method: 'POST'
  })
}

export async function saveGitHubToken(config) {
  return apiRequest('/api/me/github-token', {
    method: 'PUT',
    body: JSON.stringify(config)
  })
}

export async function getGitHubConfig() {
  return apiRequest('/api/me/github-config')
}

export async function getCodeGenerationStackRegistry() {
  return apiRequest('/api/code-generation/stack-registry')
}

export async function createCodeGenerationJob(payload) {
  return apiRequest('/api/code-generation/jobs', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function getCodeGenerationJob(jobId) {
  return apiRequest(`/api/code-generation/jobs/${jobId}`)
}

export async function pushCodeGenerationToGitHub(jobId, payload) {
  return apiRequest(`/api/code-generation/jobs/${jobId}/push-github`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function streamCodeGenerationEvents(jobId, onEvent) {
  const token = getToken()
  const response = await fetch(`/api/code-generation/jobs/${jobId}/events`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  if (!response.ok || !response.body) {
    throw new Error('代码生成事件连接失败')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''
    for (const chunk of chunks) {
      const dataLine = chunk.split('\n').find((line) => line.startsWith('data: '))
      if (dataLine) {
        onEvent(JSON.parse(dataLine.slice(6)))
      }
    }
  }
}
