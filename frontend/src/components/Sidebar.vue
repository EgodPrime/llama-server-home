<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <span class="username">{{ username }}</span>
      <button class="logout-btn" @click="logout">退出登录</button>
    </div>
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
import { ref, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
const $route = useRoute();

const username = ref(window.localStorage.getItem('username') || '未登录');

function updateUsername() {
  username.value = window.localStorage.getItem('username') || '未登录';
}

onMounted(() => {
  window.addEventListener('storage', updateUsername);
});
onUnmounted(() => {
  window.removeEventListener('storage', updateUsername);
});

function logout() {
  window.localStorage.removeItem('token');
  window.localStorage.removeItem('username');
  username.value = '未登录';
  window.location.href = '/login';
}
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
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px 24px 16px;
  font-size: 16px;
}
.username {
  color: #1979c6;
  font-weight: bold;
}
.logout-btn {
  background: #52c41a;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}
.logout-btn:hover {
  background: #389e0d;
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
