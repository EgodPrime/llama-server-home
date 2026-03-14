<template>
  <div>
    <h2>实例管理</h2>
    <button
      @click="goToCreateTask"
      style="
        margin-bottom: 16px;
        background: #1979c6;
        color: #fff;
        border: none;
        border-radius: 6px;
        padding: 8px 18px;
        font-weight: 600;
      "
    >
      创建实例
    </button>
    <a-table :dataSource="instances" :columns="columns" rowKey="instance_name">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <button
            style="color: #fa541c; margin-right: 8px"
            :disabled="record.status === 'RUNNING'"
            @click="handleDelete(record.node_id, record.instance_name)"
          >
            删除
          </button>
          <button
            style="color: #1979c6; margin-right: 8px"
            :disabled="record.status !== 'RUNNING'"
            @click="handleStop(record.node_id, record.instance_name)"
          >
            停止
          </button>
          <button
            style="color: #52c41a; margin-right: 8px"
            :disabled="record.status !== 'STOPPED'"
            @click="handleResume(record.node_id, record.instance_name)"
          >
            恢复
          </button>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Instance } from '@/types/index.js';
import { deleteInstance, stopInstance, resumeInstance, listInstances } from '@/api/index.js';
import { message } from 'ant-design-vue';

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
  {
    title: '最近心跳',
    dataIndex: 'last_heartbeat',
    key: 'last_heartbeat',
    customRender: ({ text }: { text: number | undefined }) => {
      if (typeof text !== 'number' || !text) return '';
      const date = new Date(text * 1000);
      return date.toLocaleString('zh-CN', { hour12: false });
    },
  },
  {
    title: '操作',
    key: 'action',
  },
];

async function handleDelete(nodeId: string, instanceName: string) {
  if (confirm('确定要删除该实例吗？')) {
    const res = await deleteInstance(nodeId, instanceName);
    message.success(res.message);
    instances.value = await listInstances();
  }
}

async function handleStop(nodeId: string, instanceName: string) {
  if (confirm('确定要停止该实例吗？')) {
    const res = await stopInstance(nodeId, instanceName);
    message.success(res.message);
    instances.value = await listInstances();
  }
}

async function handleResume(nodeId: string, instanceName: string) {
  if (confirm('确定要恢复该实例吗？')) {
    const res = await resumeInstance(nodeId, instanceName);
    message.success(res.message);
    instances.value = await listInstances();
  }
}

let timer: ReturnType<typeof setInterval> | null = null;

onMounted(async () => {
  instances.value = await listInstances();
  timer = setInterval(async () => {
    instances.value = await listInstances();
  }, 5000);
});

import { onUnmounted } from 'vue';
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped>
h2 {
  color: #1979c6;
  margin-bottom: 24px;
}
</style>
