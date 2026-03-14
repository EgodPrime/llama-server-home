<template>
  <div>
    <h2>NFS管理</h2>
    <div style="margin-bottom:16px;">
      <label>
        <input type="checkbox" v-model="onlyModels" />
        只看模型
      </label>
    </div>
    <div v-if="onlyModels">
      <h3>模型列表</h3>
      <div class="model-list">
        <div v-for="model in models" :key="model.model_name" class="model-card">
          <div class="model-title">{{ model.model_name }}</div>
          <div v-if="model.model_file" class="model-file">模型文件: <span class="file-path">{{ model.model_file }}</span></div>
          <div v-if="model.mmproj_file" class="model-file">mmproj文件: <span class="file-path">{{ model.mmproj_file }}</span></div>
        </div>
      </div>
    </div>
    <div v-else>
      <h3>文件浏览器</h3>
      <div>
        <button v-if="pathStack.length" @click="goBack">返回上一级</button>
        <span style="margin-left:8px;">当前路径: {{ currentPath }}</span>
      </div>
      <ul>
        <li v-for="item in items" :key="item.nfs_path">
          <span v-if="item.type === 'directory'" style="color:#1979C6; cursor:pointer;" @click="enterDir(item)">📁 {{ item.name }}</span>
          <span v-else>📄 {{ item.name }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { listNfsRoot, listNfsDir, listNfsModels } from '@/api/index.js';

const onlyModels = ref(true);
const models = ref<any[]>([]);
const items = ref<any[]>([]);
const pathStack = ref<string[]>([]);
const currentPath = ref('');

onMounted(async () => {
  if (onlyModels.value) {
    models.value = await listNfsModels();
  } else {
    items.value = await listNfsRoot();
    currentPath.value = '';
  }
});

watch(onlyModels, async (val) => {
  if (val) {
    models.value = await listNfsModels();
  } else {
    items.value = await listNfsRoot();
    pathStack.value = [];
    currentPath.value = '';
  }
});

async function enterDir(item: any) {
  pathStack.value.push(item.name);
  const dirPath = pathStack.value.join('/');
  items.value = await listNfsDir(dirPath);
  currentPath.value = dirPath;
}

async function goBack() {
  pathStack.value.pop();
  const dirPath = pathStack.value.join('/');
  if (dirPath) {
    items.value = await listNfsDir(dirPath);
    currentPath.value = dirPath;
  } else {
    items.value = await listNfsRoot();
    currentPath.value = '';
  }
}
</script>

<style scoped>
/* 页面美化 */
h2 {
  color: #1979C6;
  margin-bottom: 24px;
}
.model-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}
.model-card {
  background: linear-gradient(135deg, #f8fafc 60%, #e6f7ff 100%);
  border-radius: 14px;
  box-shadow: 0 2px 12px rgba(25,121,198,0.10);
  padding: 24px 18px;
  min-width: 320px;
  max-width: 520px;
  width: 100%;
  display: flex;
  flex-direction: column;
  margin-bottom: 12px;
}
.model-title {
  font-size: 20px;
  font-weight: 700;
  color: #1979C6;
  margin-bottom: 12px;
}
.model-file {
  font-size: 15px;
  color: #333;
  margin-bottom: 6px;
}
.file-path {
  color: #888;
  font-size: 13px;
  word-break: break-all;
}
button {
  background: #1979C6;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  font-size: 15px;
  cursor: pointer;
  font-weight: 600;
}
button:hover {
  background: #52C41A;
}
</style>
