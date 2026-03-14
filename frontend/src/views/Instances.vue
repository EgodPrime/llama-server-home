<template>
  <div>
    <h2>实例管理</h2>
    <button @click="goToCreateTask" style="margin-bottom:16px; background:#1979C6; color:#fff; border:none; border-radius:6px; padding:8px 18px; font-weight:600;">创建实例</button>
    <a-table :dataSource="instances" :columns="columns" rowKey="instance_name" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Instance } from '@/types/index.js';
import axios from 'axios';

const instances = ref<Instance[]>([]);
const router = useRouter();

function goToCreateTask() {
  router.push({ name: 'CreateInstanceTask' });
}

const columns = [
  { title: '实例名称', dataIndex: 'instance_name', key: 'instance_name' },
  { title: '节点ID', dataIndex: 'node_id', key: 'node_id' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  { title: '端口', dataIndex: 'port', key: 'port' },
  { title: '最近心跳', dataIndex: 'last_heartbeat', key: 'last_heartbeat' },
  { title: '操作', key: 'action' },
];

onMounted(async () => {
  const res = await axios.get('/api/instances/list_instances');
  instances.value = res.data;
});
</script>

<style scoped>
h2 {
  color: #1979C6;
  margin-bottom: 24px;
}
</style>
