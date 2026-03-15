<template>
  <div>
    <h2>登录</h2>
    <input v-model="username" placeholder="用户名" />
    <input v-model="password" type="password" placeholder="密码" />
    <button @click="handleLogin">登录</button>
    <button @click="handleRegister">注册</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { login, register } from '@/api/index.js';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';

const username = ref('');
const password = ref('');
const router = useRouter();

async function handleLogin() {
  try {
    const res = await login(username.value, password.value);
    localStorage.setItem('token', res.token);
    message.success('登录成功');
    router.push('/');
  } catch (e) {
    message.error('登录失败');
  }
}

async function handleRegister() {
  try {
    const res = await register(username.value, password.value);
    message.success('注册成功');
  } catch (e) {
    message.error('注册失败');
  }
}
</script>