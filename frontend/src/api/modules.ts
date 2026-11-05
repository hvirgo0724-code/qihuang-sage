import { http, ssePost } from './http'
import type { SSEHandlers } from './http'
import type {
  AuthResponse,
  RefreshResponse,
  User,
  UserProfile,
  RegisterPayload,
  SessionCreateResponse,
  ImageUploadResponse,
  Job,
  ChatMessage,
  SessionSummary,
  SyndromeReport,
  PendingReport,
  KnowledgeType,
  KnowledgeSearchResponse,
  KnowledgeNodeDetail,
  KnowledgeStats,
  FeedbackPayload,
  FeedbackResponse,
  AuditLogItem,
  OperationLogItem,
  PromptVersion,
  EvalDataset,
  EvalRun,
  Paginated,
} from '@/types'

// ---------------- 认证 ----------------
export function register(payload: RegisterPayload): Promise<AuthResponse> {
  return http.post<AuthResponse>('/auth/register', payload).then((r) => r.data)
}

export function login(username: string, password: string): Promise<AuthResponse> {
  return http.post<AuthResponse>('/auth/login', { username, password }).then((r) => r.data)
}

export function refreshToken(refresh_token: string): Promise<RefreshResponse> {
  return http.post<RefreshResponse>('/auth/refresh', { refresh_token }).then((r) => r.data)
}

export function fetchMe(): Promise<User> {
  return http.get<User>('/auth/me').then((r) => r.data)
}

export interface ProfileUpdatePayload {
  height?: number | null
  weight?: number | null
  allergies?: string | null
  chronic_diseases?: string | null
  medication_history?: string | null
  remark?: string | null
}

export function updateProfile(payload: ProfileUpdatePayload): Promise<UserProfile> {
  return http.put<UserProfile>('/auth/me/profile', payload).then((r) => r.data)
}

export function getProfile(): Promise<UserProfile> {
  return http.get<UserProfile>('/auth/me/profile').then((r) => r.data)
}

export function deleteMyData(): Promise<{ status: string }> {
  return http.delete<{ status: string }>('/auth/me/data').then((r) => r.data)
}

// ---------------- 问诊 ----------------
export function createSession(complaint?: string): Promise<SessionCreateResponse> {
  return http
    .post<SessionCreateResponse>('/consultation/session', { complaint: complaint ?? '' })
    .then((r) => r.data)
}

export function uploadImage(
  sessionId: number,
  file: Blob,
  imageType: 'tongue' | 'face',
): Promise<ImageUploadResponse> {
  const form = new FormData()
  form.append('file', file, `${imageType}.jpg`)
  form.append('image_type', imageType)
  return http
    .post<ImageUploadResponse>(`/consultation/${sessionId}/image`, form)
    .then((r) => r.data)
}

export function getJob(jobId: string): Promise<Job> {
  return http.get<Job>(`/jobs/${jobId}`).then((r) => r.data)
}

export function sendChatMessage(
  sessionId: number,
  message: string,
  handlers: SSEHandlers,
): Promise<void> {
  return ssePost(`/consultation/${sessionId}/chat`, { message }, handlers)
}

export function getSessionResult(sessionId: number): Promise<SyndromeReport | PendingReport> {
  return http.get<SyndromeReport | PendingReport>(`/consultation/${sessionId}/result`).then((r) => r.data)
}

export function getSessionMessages(sessionId: number): Promise<ChatMessage[]> {
  return http.get<ChatMessage[]>(`/consultation/${sessionId}/messages`).then((r) => r.data)
}

export function listSessions(): Promise<SessionSummary[]> {
  return http.get<SessionSummary[]>('/consultation/me').then((r) => r.data)
}

// ---------------- 知识库 ----------------
export function searchKnowledge(
  q: string,
  type: KnowledgeType,
  page = 1,
  pageSize = 20,
): Promise<KnowledgeSearchResponse> {
  return http
    .get<KnowledgeSearchResponse>('/knowledge/search', {
      params: { q, type, page, page_size: pageSize },
    })
    .then((r) => r.data)
}

export function getFormulaDetail(name: string): Promise<KnowledgeNodeDetail> {
  return http
    .get<KnowledgeNodeDetail>(`/knowledge/formulas/${encodeURIComponent(name)}`)
    .then((r) => r.data)
}

export function getHerbDetail(name: string): Promise<KnowledgeNodeDetail> {
  return http
    .get<KnowledgeNodeDetail>(`/knowledge/herbs/${encodeURIComponent(name)}`)
    .then((r) => r.data)
}

export function getSyndromeDetail(name: string): Promise<KnowledgeNodeDetail> {
  return http
    .get<KnowledgeNodeDetail>(`/knowledge/syndromes/${encodeURIComponent(name)}`)
    .then((r) => r.data)
}

export function getKnowledgeStats(): Promise<KnowledgeStats> {
  return http.get<KnowledgeStats>('/knowledge/stats').then((r) => r.data)
}

export function getSymptomDetail(name: string): Promise<KnowledgeNodeDetail> {
  return http.get<KnowledgeNodeDetail>(`/knowledge/symptoms/${encodeURIComponent(name)}`).then((r) => r.data)
}

// ---------------- 反馈 ----------------
export function submitFeedback(payload: FeedbackPayload): Promise<FeedbackResponse> {
  return http.post<FeedbackResponse>('/feedback', payload).then((r) => r.data)
}

// ---------------- 管理 ----------------
export function getGraphStats(): Promise<KnowledgeStats> {
  return http.get<KnowledgeStats>('/admin/graph/stats').then((r) => r.data)
}

export function importGraph(): Promise<{ job_id: string }> {
  return http.post<{ job_id: string }>('/admin/graph/import').then((r) => r.data)
}

export function getAuditLogs(page = 1, pageSize = 20): Promise<Paginated<AuditLogItem>> {
  return http
    .get<Paginated<AuditLogItem>>('/admin/auditlogs', { params: { page, page_size: pageSize } })
    .then((r) => r.data)
}

export function getOperationLogs(page = 1, pageSize = 20): Promise<Paginated<OperationLogItem>> {
  return http
    .get<Paginated<OperationLogItem>>('/admin/operationlogs', {
      params: { page, page_size: pageSize },
    })
    .then((r) => r.data)
}

export function getPrompts(): Promise<PromptVersion[]> {
  return http.get<PromptVersion[]>('/admin/prompts').then((r) => r.data)
}

export function createPrompt(payload: {
  scene: string
  content: string
  changelog?: string
}): Promise<PromptVersion> {
  return http.post<PromptVersion>('/admin/prompts', payload).then((r) => r.data)
}

export function activatePrompt(versionId: number): Promise<{ status: string }> {
  return http
    .post<{ status: string }>(`/admin/prompts/${versionId}/activate`)
    .then((r) => r.data)
}

export function getEvalDatasets(): Promise<EvalDataset[]> {
  return http.get<EvalDataset[]>('/admin/evals').then((r) => r.data)
}

export function runEval(datasetId: number): Promise<{ run_id: number }> {
  return http.post<{ run_id: number }>('/admin/evals/run', { dataset_id: datasetId }).then((r) => r.data)
}

export function getEvalRuns(): Promise<EvalRun[]> {
  return http.get<EvalRun[]>('/admin/evals/runs').then((r) => r.data)
}

export function healthz(): Promise<{ status: string }> {
  return http.get<{ status: string }>('/healthz', { baseURL: '' }).then((r) => r.data)
}
