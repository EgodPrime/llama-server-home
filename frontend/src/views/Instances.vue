<template>
  <div>
    <h2>实例管理</h2>
    <button @click="goToCreateTask" style="margin-bottom:16px; background:#1979C6; color:#fff; border:none; border-radius:6px; padding:8px 18px; font-weight:600;">创建实例</button>
    <a-table :dataSource="instances" :columns="columns" rowKey="instance_name">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <button
            style="color:#FA541C; margin-right:8px;"
            :disabled="record.status === 'RUNNING'"
            @click="handleDelete(record.node_id, record.instance_name)"
          >
            删除
          </button>
          <button
            style="color:#1979C6; margin-right:8px;"
            :disabled="record.status !== 'RUNNING'"
            @click="handleStop(record.node_id, record.instance_name)"
          >
            停止
          </button>
          <button
            style="color:#52C41A; margin-right:8px;"
            :disabled="record.status !== 'STOPPED'"
            @click="handleResume(record.node_id, record.instance_name)"
          >
            恢复
          </button>
          <button
            style="color:#FAAD14;"
            @click="handleModify(record.node_id, record.instance_name, record.config, record.env)"
          >
            修改配置
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
import { deleteInstance, stopInstance, resumeInstance, modifyInstance, listInstances } from '@/api/index.js';
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
  {
    title: '操作',
    key: 'action',
  },
];

async function handleDelete(nodeId: string, instanceName: string) {
  if (confirm('确定要删除该实例吗？')) {
    await deleteInstance(nodeId, instanceName);
    instances.value = await listInstances();
  }
}

async function handleStop(nodeId: string, instanceName: string) {
  if (confirm('确定要停止该实例吗？')) {
    await stopInstance(nodeId, instanceName);
    instances.value = await listInstances();
  }
}

async function handleResume(nodeId: string, instanceName: string) {
  if (confirm('确定要恢复该实例吗？')) {
    await resumeInstance(nodeId, instanceName);
    instances.value = await listInstances();
  }
}

async function handleModify(nodeId: string, instanceName: string, config: any, env: any) {
  // 可弹窗收集新配置和环境变量，这里直接调用
  await modifyInstance({
    task_id: '', // 可由后端生成
    type: 'MODIFY',
    instance_name: instanceName,
    node_id: nodeId,
    config_override: config,
    env_override: env,
    triggered_by: 'USER',
  });
  instances.value = await listInstances();
}

onMounted(async () => {
  instances.value = await listInstances();
  console.log('Fetched instances:', instances.value);
});
</script>

<style scoped>
h2 {
  color: #1979C6;
  margin-bottom: 24px;
}
</style>
