import { defineStore } from 'pinia'
import type { AuthResponse, RegisterPayload, User } from '@/types'
import * as api from '@/api/modules'
import { clearTokens, getAccessToken, setTokens } from '@/api/http'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getAccessToken() as string | null,
    user: null as User | null,
  }),
  getters: {
    isLoggedIn: (state): boolean => !!state.token,
    isAdmin: (state): boolean => state.user?.role === 'ADMIN',
  },
  actions: {
    applyAuth(data: AuthResponse) {
      setTokens(data.access_token, data.refresh_token)
      this.token = data.access_token
      this.user = data.user
    },
    async login(username: string, password: string) {
      const data = await api.login(username, password)
      this.applyAuth(data)
    },
    async registerAccount(payload: RegisterPayload) {
      const data = await api.register(payload)
      this.applyAuth(data)
    },
    async fetchMe(): Promise<User> {
      this.user = await api.fetchMe()
      return this.user
    },
    logout() {
      clearTokens()
      this.token = null
      this.user = null
    },
  },
})