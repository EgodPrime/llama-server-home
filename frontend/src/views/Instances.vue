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
            :disabled="record.status === 'RUNNING'"
            @click="handleResume(record.node_id, record.instance_name)"
          >
            恢复
          </button>
          <button
            style="color: #722ed1; margin-right: 8px"
            @click="handleViewLog(record.node_id, record.instance_name)"
          >
            查看日志
          </button>
        </template>
      </template>
    </a-table>
    <a-modal
      v-model:open="logModalVisible"
      title="实例日志"
      width="700px"
      @cancel="logModalVisible = false"
      @ok="logModalVisible = false"
    >
      <pre
        style="
          max-height: 400px;
          overflow: auto;
          background: #f6f6f6;
          padding: 12px;
          border-radius: 6px;
        "
        >{{ logContent }}</pre
      >
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue';
import { useRouter } from 'vue-router';
import { Instance } from '@/types/index.js';
import {
  deleteInstance,
  stopInstance,
  resumeInstance,
  listInstances,
  getInstanceLogs,
} from '@/api/index.js';
import { message } from 'ant-design-vue';

const instances = ref<Instance[]>([]);
const router = useRouter();
const logModalVisible = ref(false);
const logContent = ref('');

async function handleViewLog(nodeId: string, instanceName: string) {
  logContent.value = '加载中...';
  logModalVisible.value = true;
  try {
    const res = await getInstanceLogs(nodeId, instanceName);
    logContent.value = res.content || '日志内容为空';
  } catch (e) {
    logContent.value = '日志获取失败';
  }
}

function goToCreateTask() {
  router.push({ name: 'CreateInstanceTask' });
}

const columns = [
  { title: '实例名称', dataIndex: 'instance_name', key: 'instance_name' },
  { title: '节点ID', dataIndex: 'node_id', key: 'node_id' },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    customRender: ({ text }: { text: string }) => {
      let color = '#595959';
      switch (text) {
        case 'RUNNING':
          color = '#52c41a';
          break;
        case 'STOPPED':
          color = '#faad14';
          break;
        case 'ERROR':
          color = '#ff4d4f';
          break;
        default:
          color = '#595959';
      }
      return h('span', { style: { color, fontWeight: 'bold' } }, text);
    },
  },
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
  }, 1000);
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
