import { defineStore } from 'pinia'
import type { SyndromeReport } from '@/types'

export const useConsultStore = defineStore('consult', {
  state: () => ({
    sessionId: null as number | null,
    traceId: null as string | null,
    complaint: '' as string,
    report: null as SyndromeReport | null,
    disclaimer: '' as string,
    currentPhase: '' as string,
  }),
  actions: {
    setSession(sessionId: number, traceId: string | null, complaint = '') {
      this.sessionId = sessionId
      this.traceId = traceId
      this.complaint = complaint
      this.report = null
      this.disclaimer = ''
      this.currentPhase = ''
    },
    setReport(report: SyndromeReport) {
      this.report = report
      if (report.disclaimer) this.disclaimer = report.disclaimer
    },
    setDisclaimer(text: string) {
      this.disclaimer = text
    },
    setPhase(phase: string) {
      this.currentPhase = phase
    },
    reset() {
      this.sessionId = null
      this.traceId = null
      this.complaint = ''
      this.report = null
    },
  },
})