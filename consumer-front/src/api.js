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
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg).join('；') : message)
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

export async function generatePlan(messages) {
  return apiRequest('/api/generate', {
    method: 'POST',
    body: JSON.stringify({ messages })
  })
}

export async function confirmConversation(payload) {
  return apiRequest('/api/conversations/confirm', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}
