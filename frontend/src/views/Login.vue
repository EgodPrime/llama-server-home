<template>
  <div class="login-container">
    <a-card class="login-card" :bordered="false">
      <template #title>
        <h2 class="login-title">用户登录</h2>
      </template>

      <a-form name="login_form" :model="formState" @finish="handleLogin" layout="vertical">
        <!-- 用户名 -->
        <a-form-item label="用户名" name="username" rules="[required: { message: '请输入用户名' }]">
          <a-input v-model:value="formState.username" placeholder="请输入用户名" size="large">
            <template #prefix>
              <user-outlined class="input-icon" />
            </template>
          </a-input>
        </a-form-item>

        <!-- 密码 -->
        <a-form-item label="密码" name="password" rules="[required: { message: '请输入密码' }]">
          <a-input-password
            v-model:value="formState.password"
            placeholder="请输入密码"
            size="large"
          >
            <template #prefix>
              <lock-outlined class="input-icon" />
            </template>
          </a-input-password>
        </a-form-item>

        <!-- 按钮组 -->
        <a-form-item>
          <div class="btn-group">
            <a-button type="primary" html-type="submit" :loading="loading" block size="large">
              登 录
            </a-button>
            <a-button @click="handleRegister" block size="large" style="margin-top: 10px">
              注 册
            </a-button>
          </div>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { login, register } from '@/api/index.js';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue';

// 路由和状态
const router = useRouter();
const loading = ref(false);

// 表单状态对象
const formState = reactive({
  username: '',
  password: '',
});

// 登录处理
async function handleLogin() {
  if (!formState.username || !formState.password) {
    message.warning('请填写完整信息');
    return;
  }

  loading.value = true;
  try {
    const res = await login(formState.username, formState.password);
    localStorage.setItem('token', res.token);
    localStorage.setItem('username', formState.username);
    message.success('登录成功，正在跳转...');
    // 延迟跳转以便用户看到提示
    setTimeout(() => {
      router.push('/');
    }, 500);
  } catch (e) {
    message.error('登录失败，请检查账号密码');
  } finally {
    loading.value = false;
  }

  // 刷新页面
  window.location.reload();
}

// 注册处理
async function handleRegister() {
  if (!formState.username || !formState.password) {
    message.warning('请先填写用户名和密码');
    return;
  }

  try {
    const res = await register(formState.username, formState.password);
    message.success('注册成功，请登录');
    // 注册成功后通常清空表单或切换回登录逻辑，这里简单提示
  } catch (e) {
    message.error('注册失败，用户名可能已存在');
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh; /* 占满全屏高度 */
  background-color: #f0f2f5; /* 浅灰背景 */
}

.login-card {
  width: 400px;
  max-width: 90%; /* 移动端适配 */
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); /* 柔和阴影 */
}

.login-title {
  text-align: center;
  margin: 0 0 20px 0;
  font-weight: 600;
  color: #333;
}

.input-icon {
  color: rgba(0, 0, 0, 0.25);
}

/* 简单的动画效果 */
.login-card {
  animation: fadeIn 0.5s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
