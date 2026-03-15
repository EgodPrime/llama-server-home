import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';
import Nodes from '@/views/Nodes.vue';

import Metrics from '@/views/Metrics.vue';
import CreateInstanceTask from '@/views/CreateInstanceForm.vue';

import Instances from '@/views/Instances.vue';
import NfsManager from '@/views/NfsManager.vue';
import Login from '@/views/Login.vue';

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'Nodes', component: Nodes },
  { path: '/login', name: 'Login', component: Login},
  { path: '/metrics/:node_id', name: 'Metrics', component: Metrics ,meta: { 
      requiresAuth: true 
    }},
  { path: '/instances', name: 'Instances', component: Instances,meta: { 
      requiresAuth: true 
    } },
  { path: '/instance-task', name: 'CreateInstanceTask', component: CreateInstanceTask ,meta: { 
      requiresAuth: true 
    }},
  { path: '/nfs', name: 'NfsManager', component: NfsManager },
  { path: '/tasks', name: 'TaskManager', component: () => import('@/views/TaskManager.vue') },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token');
  
  // 1. 如果目标页面需要认证，且没 Token -> 去登录页
  if (to.meta.requiresAuth && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } });
  } 
  // 2. 如果目标页面是登录页，但已经有 Token -> 踢回首页 (避免重复登录)
  else if (to.path === '/login' && token) {
    next('/'); 
  } 
  // 3. 其他情况放行
  else {
    next();
  }
});

export default router;
