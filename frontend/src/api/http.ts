import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { RefreshResponse, SyndromeReport } from '@/types'

const TOKEN_KEY = 'tcm_access_token'
const REFRESH_KEY = 'tcm_refresh_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens(access: string, refresh?: string): void {
  localStorage.setItem(TOKEN_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

const http: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
})

http.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean }

let refreshing: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) return null
  try {
    const resp = await axios.post<RefreshResponse>(`${API_BASE}/auth/refresh`, {
      refresh_token: refresh,
    })
    const { access_token, refresh_token } = resp.data
    setTokens(access_token, refresh_token)
    return access_token
  } catch {
    clearTokens()
    return null
  }
}

function redirectToLogin(): void {
  const path = window.location.pathname
  if (!['/login', '/admin/login', '/doctor/login'].includes(path)) {
    const login = path.startsWith('/admin') ? '/admin/login' : path.startsWith('/doctor') ? '/doctor/login' : '/login'
    window.location.href = `${login}?redirect=${encodeURIComponent(path + window.location.search)}`
  }
}

http.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    const err = error as {
      response?: { status: number; data?: { detail?: string } }
      config?: RetriableConfig
    }
    const response = err.response
    const config = err.config

    // A failed login must not attempt token refresh or silently redirect.
    if (response?.status === 401 && config?.url === '/auth/login') {
      ElMessage.error(response.data?.detail || '用户名或密码错误')
      return Promise.reject(error)
    }

    if (response && response.status === 401 && config && !config._retry) {
      config._retry = true
      if (!refreshing) {
        refreshing = refreshAccessToken().finally(() => {
          refreshing = null
        })
      }
      const token = await refreshing
      if (token) {
        config.headers = config.headers ?? {}
        config.headers.Authorization = `Bearer ${token}`
        return http.request(config)
      }
      clearTokens()
      redirectToLogin()
      return Promise.reject(error)
    }

    const detail = response?.data?.detail
    const msg = typeof detail === 'string' ? detail : ''
    if (msg && response && response.status !== 401 && response.status !== 404) {
      ElMessage.error(msg)
    } else if (!response) {
      ElMessage.error('网络连接失败或请求超时，请稍后重试')
    } else if ([502, 503, 504].includes(response.status)) {
      ElMessage.error('后端服务暂时不可用，请稍后重试')
    } else if (response.status >= 500) {
      ElMessage.error('服务器处理失败，请稍后重试')
    }
    return Promise.reject(error)
  },
)

export { http }

export interface SSEHandlers {
  onChoices?: (data: { questions: import('@/types').InquiryChoice[] }) => void
  onReviewPending?: (data: { message: string }) => void
  onPhase?: (phase: string) => void
  onChunk?: (text: string) => void
  onResult?: (report: SyndromeReport) => void
  onDisclaimer?: (text: string) => void
  onDone?: (data: { session_id: number }) => void
  onError?: (message: string) => void
}

/**
 * 以 fetch + ReadableStream 消费后端 text/event-stream 响应，
 * 解析 event / data 行并回调对应事件处理器。
 */
export async function ssePost(path: string, body: unknown, handlers: SSEHandlers): Promise<void> {
  const token = getAccessToken()
  let resp: Response
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    })
  } catch {
    handlers.onError?.('网络异常，请稍后重试')
    return
  }

  if (!resp.ok || !resp.body) {
    handlers.onError?.(`请求失败 (${resp.status})`)
    return
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let eventName = ''
  let dataLines: string[] = []

  const dispatch = (event: string, rawData: string) => {
    if (!rawData) return
    let payload: unknown
    try {
      payload = JSON.parse(rawData)
    } catch {
      return
    }
    switch (event) {
      case 'choices':
        handlers.onChoices?.(payload as { questions: import('@/types').InquiryChoice[] })
        break
      case 'review_pending':
        handlers.onReviewPending?.(payload as { message: string })
        break
      case 'phase': {
        const p = payload as { phase?: string }
        if (p.phase) handlers.onPhase?.(p.phase)
        break
      }
      case 'chunk': {
        const c = payload as { text?: string }
        if (c.text) handlers.onChunk?.(c.text)
        break
      }
      case 'result':
        handlers.onResult?.(payload as SyndromeReport)
        break
      case 'disclaimer': {
        const d = payload as { text?: string }
        if (d.text) handlers.onDisclaimer?.(d.text)
        break
      }
      case 'error':
        handlers.onError?.((payload as { message?: string }).message || '处理失败，请重试')
        break
      case 'done':
        handlers.onDone?.(payload as { session_id: number })
        break
      default:
        break
    }
  }

  const flush = () => {
    if (eventName || dataLines.length > 0) {
      dispatch(eventName || 'message', dataLines.join('\n'))
    }
    eventName = ''
    dataLines = []
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let idx: number
      while ((idx = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, idx).replace(/\r$/, '')
        buffer = buffer.slice(idx + 1)
        if (line === '') {
          flush()
        } else if (line.startsWith(':')) {
          continue
        } else if (line.startsWith('event:')) {
          eventName = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).replace(/^\s/, ''))
        }
      }
    }
    flush()
  } catch {
    handlers.onError?.('连接中断，请重试')
  }
}
