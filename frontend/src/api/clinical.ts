import { http } from './http'
export interface Physician { user_id: number; nickname: string; username?: string; status?: string }
export interface Encounter {
  report_status?: string;
  report_review?: { analysis_id: number; revision: number; status: string; report: Record<string, unknown> } | null;
  session_id: number; doctor_id: number; status: string; review: string | null;
  patient_name?: string; complaint?: string;
  messages?: { message_id: number; author_role: string; content: string; created_at: string }[];
  records?: { role: string; content: string; type: string }[];
  report?: Record<string, unknown> | null;
  images?: { image_id: number; image_type: string; quality_pass: boolean; analysis_result: unknown }[];
}
export const statusLabel: Record<string, string> = { requested: '等待医生接诊', active: '接诊中', closed: '已结束', cancelled: '已撤回授权' }
export const clinical = {
  saveReport: (id: number, analysis: number, revision: number, report: unknown) => http.put(`/clinical/sessions/${id}/reports/${analysis}`, { revision, report }),
  confirmReport: (id: number, analysis: number, revision: number) => http.post(`/clinical/sessions/${id}/reports/${analysis}/confirm`, { revision }),
  doctors: () => http.get<Physician[]>('/clinical/doctors').then(r => r.data),
  cases: () => http.get<Encounter[]>('/clinical/cases').then(r => r.data),
  detail: (id: number) => http.get<Encounter | null>(`/clinical/sessions/${id}`).then(r => r.data),
  imageBlob: (id: number, imageId: number) => http.get<Blob>(`/clinical/sessions/${id}/images/${imageId}`, { responseType: 'blob' }).then(r => r.data),
  request: (id: number, doctor_id: number) => http.post(`/clinical/sessions/${id}/request`, { doctor_id, consent: true }),
  action: (id: number, action: string) => http.post(`/clinical/sessions/${id}/${action}`),
  message: (id: number, content: string) => http.post(`/clinical/sessions/${id}/messages`, { content }),
  review: (id: number, content: string) => http.put(`/clinical/sessions/${id}/review`, { content }),
  adminDoctors: () => http.get<Physician[]>('/clinical/admin/doctors').then(r => r.data),
  createDoctor: (body: { username: string; nickname: string; password: string }) => http.post('/clinical/admin/doctors', body),
}
