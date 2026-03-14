<template>
  <div>
    <h2>节点列表</h2>
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
    <a-table :dataSource="nodes" :columns="columns" rowKey="node_id">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <button @click="goToMetrics(record.node_id)">metrics</button>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { listNodes } from '@/api/index.js';
import { Node } from '@/types/index.js';
import { useRouter } from 'vue-router';

const nodes = ref<Node[]>([]);
const router = useRouter();

function goToMetrics(nodeId: string) {
  router.push({ name: 'Metrics', params: { node_id: nodeId } });
}

function goToCreateTask() {
  router.push({ name: 'CreateInstanceTask' });
}

const columns = [
  { title: '节点ID', dataIndex: 'node_id', key: 'node_id' },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: 'IP地址', dataIndex: 'ip_address', key: 'ip_address' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  { title: '注册时间', dataIndex: 'registered_at', key: 'registered_at' },
  { title: '最近心跳', dataIndex: 'last_heartbeat', key: 'last_heartbeat' },
  { title: '操作', key: 'action' },
];

onMounted(async () => {
  nodes.value = await listNodes();
});
</script>

<style scoped>
h2 {
  margin-bottom: 16px;
}
</style>
