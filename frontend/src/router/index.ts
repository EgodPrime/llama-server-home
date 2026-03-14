import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';
import Nodes from '../views/Nodes.vue';

import Metrics from '../views/Metrics.vue';
import CreateInstanceTask from '../views/CreateInstanceTask.vue';

import Instances from '../views/Instances.vue';
import NfsManager from '../views/NfsManager.vue';

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'Nodes', component: Nodes },
  { path: '/metrics/:node_id', name: 'Metrics', component: Metrics },
  { path: '/instances', name: 'Instances', component: Instances },
  { path: '/instance-task', name: 'CreateInstanceTask', component: CreateInstanceTask },
  { path: '/nfs', name: 'NfsManager', component: NfsManager },
  { path: '/tasks', name: 'TaskManager', component: () => import('../views/TaskManager.vue') },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
