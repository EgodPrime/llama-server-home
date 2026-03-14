<template>
  <div class="sidebar">
    <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }"
      >节点管理</router-link
    >
    <router-link
      to="/instances"
      class="nav-item"
      :class="{ active: $route.path.startsWith('/instances') }"
      >实例管理</router-link
    >
    <router-link to="/nfs" class="nav-item" :class="{ active: $route.path.startsWith('/nfs') }"
      >NFS管理</router-link
    >
    <router-link to="/tasks" class="nav-item" :class="{ active: $route.path.startsWith('/tasks') }"
      >任务管理</router-link
    >
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router';
const $route = useRoute();
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  width: 180px;
  height: 100vh;
  background: #f8fafc;
  box-shadow: 2px 0 8px rgba(25, 121, 198, 0.08);
  display: flex;
  flex-direction: column;
  padding-top: 32px;
  z-index: 10;
}
.nav-item {
  padding: 16px 24px;
  font-size: 18px;
  color: #1979c6;
  text-decoration: none;
  border-radius: 8px;
  margin-bottom: 12px;
  transition:
    background 0.2s,
    color 0.2s;
}
.nav-item.active,
.nav-item:hover {
  background: #e6f7ff;
  color: #52c41a;
}
</style>
