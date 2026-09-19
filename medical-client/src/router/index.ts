import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../utils/request'
import { currentUser, loadCurrentUser } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/login/Index.vue'),
    },
    {
      path: '/',
      component: () => import('../views/layout/Index.vue'),
      children: [
        {
          path: '',
          name: 'Home',
          component: () => import('../views/home/Index.vue'),
        },
        {
          path: 'triage',
          name: 'Triage',
          component: () => import('../views/triage/Index.vue'),
        },
        {
          path: 'booking',
          name: 'Booking',
          component: () => import('../views/booking/Index.vue'),
        },
        {
          path: 'appointments',
          name: 'Appointments',
          component: () => import('../views/appointment/Index.vue'),
        },
        {
          path: 'prescriptions',
          name: 'Prescriptions',
          component: () => import('../views/prescription/Index.vue'),
        },
        {
          path: 'bills',
          name: 'Bills',
          component: () => import('../views/bill/Index.vue'),
        },
        {
          path: 'reports',
          name: 'Reports',
          component: () => import('../views/report/Index.vue'),
        },
        {
          path: 'medical-records',
          name: 'MedicalRecords',
          component: () => import('../views/medicalRecord/Index.vue'),
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('../views/profile/Index.vue'),
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const hasToken = !!getToken()

  if (to.path !== '/login' && !hasToken) {
    return '/login'
  }
  // 已登录时访问登录页，直接回首页
  if (to.path === '/login' && hasToken) {
    return '/'
  }
  if (hasToken && !currentUser.value) {
    await loadCurrentUser()
  }
})

export default router
