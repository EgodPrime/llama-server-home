<template>
  <div>
    <h2>节点列表</h2>
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
import { ref, h } from 'vue';
import { listNodes } from '@/api/index.js';
import { Node } from '@/types/index.js';
import { useRouter } from 'vue-router';
import { usePolling } from '@/composables/usePolling';
import { useStatusColor } from '@/composables/useStatusColor';
import { useDateFormat } from '@/composables/useDateFormat';

const nodes = ref<Node[]>([]);
const router = useRouter();
const { getColor } = useStatusColor();
const { formatDate } = useDateFormat();

function goToMetrics(nodeId: string) {
  router.push({ name: 'Metrics', params: { node_id: nodeId } });
}

const columns = [
  { title: '节点ID', dataIndex: 'node_id', key: 'node_id' },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: 'IP地址', dataIndex: 'ip_address', key: 'ip_address' },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    customRender: ({ text }: { text: string }) => {
      const color = getColor(text);
      return h('span', { style: { color, fontWeight: 'bold' } }, text);
    },
  },
  {
    title: '注册时间',
    dataIndex: 'registered_at',
    key: 'registered_at',
    customRender: ({ text }: { text: number | undefined }) => {
      return formatDate(text);
    },
  },
  {
    title: '最近心跳',
    dataIndex: 'last_heartbeat',
    key: 'last_heartbeat',
    customRender: ({ text }: { text: number | undefined }) => {
      return formatDate(text);
    },
  },
  { title: '操作', key: 'action' },
];

const { start } = usePolling(async () => {
  nodes.value = await listNodes();
}, 1000, { immediate: true });
start();
</script>

<style scoped>
h2 {
  margin-bottom: 16px;
}
</style>
