import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
    requiresDoctor?: boolean
    hideHeader?: boolean
    title?: string
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/patient', component: () => import('@/views/PatientView.vue'), meta: { requiresAuth: true, title: '患者端' } },
    { path: '/doctor', component: () => import('@/views/DoctorView.vue'), meta: { requiresAuth: true, requiresDoctor: true, title: '医生工作台' } },
    { path: '/admin/login', component: () => import('@/views/LoginView.vue'), meta: { title: '管理员登录', hideHeader: true } },
    { path: '/doctor/login', component: () => import('@/views/LoginView.vue'), meta: { title: '医生登录', hideHeader: true } },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { title: '首页' },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: '登录', hideHeader: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { title: '注册', hideHeader: true },
    },
    {
      path: '/consult/start',
      name: 'consult-start',
      component: () => import('@/views/ConsultStartView.vue'),
      meta: { title: '开始问诊', requiresAuth: true },
    },
    {
      path: '/consult/:id',
      name: 'consult',
      component: () => import('@/views/ConsultView.vue'),
      meta: { title: '四诊问诊', requiresAuth: true },
    },
    {
      path: '/consult/:id/result',
      name: 'consult-result',
      component: () => import('@/views/ResultView.vue'),
      meta: { title: '辨证报告', requiresAuth: true },
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('@/views/HistoryView.vue'),
      meta: { title: '历史问诊', requiresAuth: true },
    },
    {
      path: '/knowledge',
      name: 'knowledge',
      component: () => import('@/views/KnowledgeView.vue'),
      meta: { title: '中医知识库' },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { title: '个人中心', requiresAuth: true },
    },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        { path: 'doctors', component: () => import('@/views/AdminDoctorView.vue'), meta: { title: '医生账号' } },
        {
          path: '',
          name: 'admin',
          component: () => import('@/views/AdminView.vue'),
          meta: { title: '管理后台', requiresAuth: true, requiresAdmin: true },
        },
        {
          path: 'monitor',
          name: 'admin-monitor',
          component: () => import('@/views/MonitorView.vue'),
          meta: { title: '监控大盘', requiresAuth: true, requiresAdmin: true },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const requiresAuth = to.matched.some((r) => r.meta.requiresAuth)
  const requiresAdmin = to.matched.some((r) => r.meta.requiresAdmin)
  const loginPath = requiresAdmin ? '/admin/login' : to.meta.requiresDoctor ? '/doctor/login' : '/login'

  if (requiresAuth && !auth.token) {
    return { path: loginPath, query: { redirect: to.fullPath } }
  }
  if (auth.token && (to.path === '/login' || to.path === '/register')) {
    return { path: '/' }
  }
  if (auth.token && !auth.user) {
    try { await auth.fetchMe() } catch { auth.logout(); return { path: loginPath, query: { redirect: to.fullPath } } }
  }
  const home = auth.user?.role === 'DOCTOR' ? '/doctor' : auth.isAdmin ? '/admin' : '/patient'
  if (to.path === '/' && auth.token) return home
  if (to.meta.requiresDoctor && auth.user?.role !== 'DOCTOR') return { path: '/doctor/login', query: { redirect: to.fullPath } }
  if ((to.path === '/patient' || to.path.startsWith('/consult') || to.path === '/history') && auth.user?.role === 'DOCTOR') return '/doctor'
  if (requiresAdmin) {
    if (!auth.user) {
      try {
        await auth.fetchMe()
      } catch {
        auth.logout()
        return { path: '/login', query: { redirect: to.fullPath } }
      }
    }
    if (!auth.isAdmin) {
      return { path: '/admin/login', query: { redirect: to.fullPath } }
    }
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 岐黄智诊` : '岐黄智诊 · 中医智能诊疗协同平台'
})

export default router
