// 与后端契约严格对齐的 TypeScript 类型定义

export type Role = 'USER' | 'ADMIN' | 'DOCTOR'

export interface User {
  user_id: number
  username: string
  nickname: string | null
  avatar: string | null
  gender: string | null
  age: number | null
  role: Role
  tenant_id: number
  data_consent_at: string | null
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  user: User
}

export interface RefreshResponse {
  access_token: string
  refresh_token: string
}

export interface RegisterPayload {
  username: string
  password: string
  nickname?: string
  gender?: string
  age?: number
  consent: boolean
}

export interface UserProfile {
  user_id: number
  height: number | null
  weight: number | null
  allergies: string | null
  chronic_diseases: string | null
  medication_history: string | null
  remark: string | null
}

export interface SessionCreateResponse {
  session_id: number
  status: string
  trace_id: string
}

export interface ImageUploadResponse {
  job_id: string
  image_id: number
}

export type JobStatus = 'pending' | 'running' | 'success' | 'failed'

export interface Job {
  job_id: string
  job_type: string
  status: JobStatus
  progress: number
  result: Record<string, unknown> | null
  error: string | null
}

export type MessageRole = 'user' | 'assistant' | 'system'
export type MessageType = 'text' | 'image' | 'result'

export interface ChatMessage {
  record_id: number
  role: MessageRole
  type: MessageType
  content: string
  meta: unknown
  create_time: string
}

export interface SessionSummary {
  report_status: 'pending' | 'confirmed' | null
  analysis_id: number | null
  session_id: number
  complaint: string | null
  risk_level: string | null
  status: string
  start_time: string
  end_time: string | null
}

export interface InquiryChoice {
  multiple?: boolean
  input_type?: 'age' | null
  id: string
  label: string
  options: string[]
}

export interface Evidence {
  source: string
  description: string
  weight: number
}

export interface FormulaSuggestion {
  name: string
  source: string
  effects: string[]
  indications: string[]
  contraindications: string
  dosage_note: string
  note: string
}

export type GraphRefLabel = 'Formula' | 'Herb' | 'Syndrome' | 'Symptom'

export interface GraphRef {
  label: GraphRefLabel
  name: string
  source: string
  description: string
}

export type RiskLevel = 'low' | 'medium' | 'high' | 'emergency'

export interface SyndromeReport {
  review_status?: 'confirmed'
  confirmed_at?: string
  syndrome: string
  confidence: number
  evidence: Evidence[]
  differential: string[]
  treatment_principle: string
  formula_suggestions: FormulaSuggestion[]
  diet_advice: string[]
  acupoint_advice: string[]
  lifestyle_advice: string[]
  risk_level: RiskLevel
  emergency_flag: boolean
  disclaimer: string
  graph_refs: GraphRef[]
  analysis_id?: number
}

export interface PendingReport { review_status: 'pending'; analysis_id: number; message: string }

export type KnowledgeType = 'all' | 'formula' | 'herb' | 'syndrome' | 'symptom'

export interface KnowledgeItem {
  type: 'formula' | 'herb' | 'syndrome' | 'symptom'
  name: string
  title: string
  description: string
  source: string
}

export interface KnowledgeSearchResponse {
  items: KnowledgeItem[]
  total: number
}

export interface KnowledgeNodeDetail {
  node: Record<string, unknown>
  neighbors: Array<{ relation: string; related: Record<string, unknown> }>
}

export interface KnowledgeStats {
  herbs: number
  formulas: number
  syndromes: number
  symptoms: number
}

export interface FeedbackPayload {
  analysis_id: number
  rating: number
  comment?: string
  correct?: boolean
}

export interface FeedbackResponse {
  feedback_id: number
}

export interface AuditLogItem {
  log_id: number
  session_id: number | null
  stage: string
  check_result: string
  hit_rule: string | null
  raw_text: string | null
  action: string | null
  create_time: string
}

export interface OperationLogItem {
  op_id: number
  user_id: number
  action: string
  resource_type: string
  resource_id: string | null
  result: string | null
  ip: string | null
  trace_id: string | null
  create_time: string
}

export interface PromptVersion {
  version_id: number
  scene: string
  version: string
  status: string
  changelog: string | null
  create_time: string
}

export interface EvalDataset {
  dataset_id: number
  name: string
  scene: string
  sample_count: number
}

export interface EvalRun {
  run_id: number
  dataset_id: number
  prompt_version: string
  metrics: Record<string, unknown>
  create_time: string
}

export interface Paginated<T> {
  items: T[]
  total: number
}

// ---- SSE 流式事件负载 ----
export interface SSEPhasePayload {
  phase: 'inquiry' | 'syndrome' | 'treatment' | 'emergency'
}
export interface SSEChunkPayload {
  text: string
}
export interface SSEDonePayload {
  session_id: number
}
export interface SSEDisclaimerPayload {
  text: string
}
