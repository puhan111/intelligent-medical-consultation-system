import { createRouter, createWebHistory } from 'vue-router'
import { clearToken, getToken } from '../utils/request'
import { currentAdmin, loadCurrentAdmin } from '../stores/auth'
import { getRoleHomePath } from '../utils/roleAccess'

type RouteRole = 'superadmin' | 'admin' | 'doctor' | 'pharmacist' | 'cashier' | 'lab'

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
      name: 'Layout',
      component: () => import('../views/layout/Index.vue'),
      redirect: () => getRoleHomePath(currentAdmin.value?.role),
      children: [
        {
          path: '/departments',
          name: 'Departments',
          component: () => import('../views/department/Index.vue'),
          meta: { roles: ['superadmin'] satisfies RouteRole[] },
        },
        {
          path: '/knowledge',
          name: 'Knowledge',
          component: () => import('../views/knowledge/Index.vue'),
          meta: { roles: ['superadmin'] satisfies RouteRole[] },
        },
        {
          path: '/admins',
          name: 'Admins',
          component: () => import('../views/admin/Index.vue'),
          meta: { roles: ['superadmin'] satisfies RouteRole[] },
        },
        {
          path: '/doctors',
          name: 'Doctors',
          component: () => import('../views/doctor/Index.vue'),
          meta: { roles: ['superadmin'] satisfies RouteRole[] },
        },
        {
          path: '/drugs',
          name: 'Drugs',
          component: () => import('../views/drug/Index.vue'),
          meta: { roles: ['superadmin'] satisfies RouteRole[] },
        },
        {
          path: '/ai-monitor',
          name: 'AiMonitor',
          component: () => import('../views/ai-monitor/Index.vue'),
          meta: { roles: ['superadmin'] satisfies RouteRole[] },
        },
        {
          path: '/rag-evaluation',
          name: 'RagEvaluation',
          component: () => import('../views/rag-evaluation/Index.vue'),
          meta: { roles: ['superadmin'] satisfies RouteRole[] },
        },
        {
          path: '/my-appointments',
          name: 'MyAppointments',
          component: () => import('../views/appointment/Index.vue'),
          meta: { roles: ['doctor'] satisfies RouteRole[] },
        },
        {
          path: '/prescriptions',
          name: 'Prescriptions',
          component: () => import('../views/prescription/Index.vue'),
          meta: { roles: ['pharmacist'] satisfies RouteRole[] },
        },
        {
          path: '/bills',
          name: 'Bills',
          component: () => import('../views/bill/Index.vue'),
          meta: { roles: ['cashier'] satisfies RouteRole[] },
        },
        {
          path: '/reports',
          name: 'Reports',
          component: () => import('../views/report/Index.vue'),
          meta: { roles: ['lab'] satisfies RouteRole[] },
        },
        {
          path: '/profile',
          name: 'Profile',
          component: () => import('../views/profile/Index.vue'),
          meta: { roles: ['admin', 'superadmin', 'doctor', 'pharmacist', 'cashier', 'lab'] satisfies RouteRole[] },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const token = getToken()
  if (to.path !== '/login' && !token) {
    return '/login'
  }

  if (token && !currentAdmin.value) {
    try {
      await loadCurrentAdmin()
    } catch {
      clearToken()
      return '/login'
    }
  }

  if (to.path === '/login' && currentAdmin.value) {
    return getRoleHomePath(currentAdmin.value.role)
  }

  const allowedRoles = to.meta.roles as RouteRole[] | undefined
  if (allowedRoles && !allowedRoles.includes(currentAdmin.value?.role as RouteRole)) {
    return getRoleHomePath(currentAdmin.value?.role)
  }
})

export default router
