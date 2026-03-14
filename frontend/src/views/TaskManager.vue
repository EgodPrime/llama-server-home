<template>
  <div>
    <h2>任务管理</h2>
    <a-table :dataSource="tasks" :columns="columns" rowKey="task_id">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <button style="color: #fa541c" @click="handleDelete(record.task_id)">删除</button>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { listInstanceTasks, deleteInstanceTask } from '@/api/index.js';

const tasks = ref<any[]>([]);

async function handleDelete(taskId: string) {
  if (confirm('确定要删除该任务吗？')) {
    await deleteInstanceTask(taskId);
    tasks.value = await listInstanceTasks();
  }
}

const columns = [
  { title: '任务ID', dataIndex: 'task_id', key: 'task_id' },
  { title: '任务类型', dataIndex: 'type', key: 'type' },
  { title: '实例名称', dataIndex: 'instance_name', key: 'instance_name' },
  { title: '节点ID', dataIndex: 'node_id', key: 'node_id' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at',
    customRender: ({ text }: { text: number | undefined }) => {
      if (typeof text !== 'number' || !text) return '';
      const date = new Date(text * 1000);
      return date.toLocaleString('zh-CN', { hour12: false });
    },
  },
  {
    title: '完成时间',
    dataIndex: 'completed_at',
    key: 'completed_at',
    customRender: ({ text }: { text: number | undefined }) => {
      if (typeof text !== 'number' || !text) return '';
      const date = new Date(text * 1000);
      return date.toLocaleString('zh-CN', { hour12: false });
    },
  },
  { title: '操作', key: 'action' },
];

onMounted(async () => {
  tasks.value = await listInstanceTasks();
  console.log('Fetched tasks:', tasks.value);
});
</script>

<style scoped>
h2 {
  color: #1979c6;
  margin-bottom: 24px;
}
</style>
