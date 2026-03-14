import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';
import Nodes from '../views/Nodes.vue';

import Metrics from '../views/Metrics.vue';

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'Nodes', component: Nodes },
  { path: '/metrics/:node_id', name: 'Metrics', component: Metrics },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
