<template>
  <div class="create-task-page">
    <h2>创建实例</h2>
    <form @submit.prevent="handleSubmit">
      <div class="form-row">
        <label>实例名称</label>
        <input v-model="form.instance_name" required placeholder="如: Code-8B-Instruct" />
      </div>
      <div class="form-row">
        <label>节点</label>
        <select v-model="form.node_id" required>
          <option v-for="node in nodes" :value="node.node_id" :key="node.node_id">
            {{ node.name }} ({{ node.ip_address }})
          </option>
        </select>
      </div>
      <div class="form-row">
        <label>端口</label>
        <input v-model.number="form.port" type="number" required placeholder="如: 8001" />
      </div>
      <div class="form-row">
        <label>选择模型</label>
        <select v-model="selectedModel" required @change="onModelChange">
          <option value="" disabled>请选择模型</option>
          <option v-for="model in models" :value="model.model_name" :key="model.model_name">
            {{ model.model_name }}
          </option>
        </select>
      </div>
      <div class="form-row">
        <label>模型文件</label>
        <input v-model="form.model_path" readonly class="readonly-input" />
      </div>
      <div class="form-row">
        <label>mmproj文件</label>
        <input v-model="form.mmproj_path" readonly class="readonly-input" />
      </div>
      <div class="form-row">
        <label>环境变量(env)</label>
        <div class="param-select-row">
          <select v-model="envSelect">
            <option value="">选择环境变量</option>
            <option value="CUDA_VISIBLE_DEVICES">CUDA_VISIBLE_DEVICES</option>
            <!-- 可扩展更多选项 -->
          </select>
        </div>
        <div class="param-list">
          <div v-for="(item, idx) in envList" :key="item.key" class="param-card">
            <span class="param-key">{{ item.key }}</span>
            <input v-model="item.value" placeholder="参数值" class="param-input" />
            <button type="button" @click="removeEnv(idx)" class="param-remove">✕</button>
          </div>
        </div>
        <div class="hint">可填项参考：CUDA_VISIBLE_DEVICES</div>
      </div>
      <div class="form-row">
        <label>启动参数(config)</label>
        <div class="param-select-row">
          <select v-model="configSelect">
            <option value="">选择启动参数</option>
            <option value="--n-gpu-layers">--n-gpu-layers</option>
            <option value="--ctx-size">--ctx-size</option>
            <option value="--parallel">--parallel</option>
            <option value="--batch-size">--batch-size</option>
            <option value="--n-predict">--n-predict</option>
            <option value="--temp">--temp</option>
            <option value="--top-k">--top-k</option>
            <option value="--top-p">--top-p</option>
            <option value="--min-p">--min-p</option>
            <option value="--presence_penalty">--presence_penalty</option>
            <option value="--frequency-penalty">--frequency-penalty</option>
            <option value="--repeat-penalty">--repeat-penalty</option>
            <option value="--threads">--threads</option>
            <option value="--flash-attn">--flash-attn</option>
            <option value="--split-mode">--split-mode</option>
            <option value="--tensor-split">--tensor-split</option>
            <!-- 可扩展更多选项 -->
          </select>
        </div>
        <div class="param-list">
          <div v-for="(item, idx) in configList" :key="item.key" class="param-card">
            <span class="param-key">{{ item.key }}</span>
            <input v-model="item.value" placeholder="参数值" class="param-input" />
            <button type="button" @click="removeConfig(idx)" class="param-remove">✕</button>
          </div>
        </div>
        <div class="hint">
          可填项参考：--n-gpu-layers, --ctx-size, --parallel, --batch-size, --n-predict, --temp,
          --top-k, --top-p, --min-p, --presence_penalty, --frequency-penalty, --repeat-penalty,
          --threads, --flash-attn, --split-mode, --tensor-split
        </div>
      </div>
      <div class="form-row">
        <button type="submit">提交任务</button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { listNodes, createInstance, listNfsModels } from '@/api/index.js';
import type { InstanceTask, Node } from '@/types/index.js';
import { message } from 'ant-design-vue';

const nodes = ref<Node[]>([]);
const models = ref<any[]>([]);
const selectedModel = ref('');
const form = ref<InstanceTask>({
  type: 'DEPLOY',
  instance_name: '',
  node_id: '',
  port: 8001,
  model_path: '',
  mmproj_path: '',
  env: {},
  config: {},
});

const envList = ref<{ key: string; value: string }[]>([
  { key: 'CUDA_VISIBLE_DEVICES', value: '0,1' },
]);
const envSelect = ref('');
const configList = ref<{ key: string; value: string }[]>([
  { key: '--n-gpu-layers', value: '999' },
  { key: '--ctx-size', value: '131072' },
  { key: '--parallel', value: '1' },
  { key: '--batch-size', value: '8192' },
  { key: '--n-predict', value: '16384' },
  { key: '--temp', value: '0.7' },
  { key: '--top-k', value: '20' },
  { key: '--top-p', value: '0.8' },
  { key: '--min-p', value: '0' },
  { key: '--presence_penalty', value: '1.0' },
  { key: '--frequency-penalty', value: '0.0' },
  { key: '--repeat-penalty', value: '1.0' },
  { key: '--threads', value: '4' },
  { key: '--flash-attn', value: 'on' },
  { key: '--split-mode', value: 'layer' },
  { key: '--tensor-split', value: '0.5,0.5' },
  //--chat-template-kwargs "{\"enable_thinking\": false}"
  { key: '--chat-template-kwargs', value: '{"enable_thinking": false}' },
]);
const configSelect = ref('');

onMounted(async () => {
  nodes.value = await listNodes();
  models.value = await listNfsModels();
});

function onModelChange() {
  const model = models.value.find((m) => m.model_name === selectedModel.value);
  form.value.model_path = model?.model_file || '';
  form.value.mmproj_path = model?.mmproj_file || '';
  if (model?.model_name) {
    form.value.instance_name = model.model_name;
  }
}

function removeEnv(idx: number) {
  envList.value.splice(idx, 1);
  updateEnvObj();
}
function removeConfig(idx: number) {
  configList.value.splice(idx, 1);
  updateConfigObj();
}

function updateEnvObj() {
  const envObj: Record<string, string> = {};
  envList.value.forEach((item) => {
    if (item.key) envObj[item.key] = item.value;
  });
  form.value.env = envObj;
}
function updateConfigObj() {
  const configObj: Record<string, any> = {};
  configList.value.forEach((item) => {
    if (item.key) configObj[item.key] = item.value;
  });
  form.value.config = configObj;
}

watch(envSelect, (val) => {
  if (val && !envList.value.find((item) => item.key === val)) {
    envList.value.push({ key: val, value: '' });
    envSelect.value = '';
    updateEnvObj();
  }
});
watch(configSelect, (val) => {
  if (val && !configList.value.find((item) => item.key === val)) {
    configList.value.push({ key: val, value: '' });
    configSelect.value = '';
    updateConfigObj();
  }
});
watch(envList, updateEnvObj, { deep: true });
watch(configList, updateConfigObj, { deep: true });

async function handleSubmit() {
  updateEnvObj();
  updateConfigObj();
  const res = await createInstance(form.value);
  message.success(res.message);
  // 跳转到任务管理页面
  setTimeout(() => {
    window.location.href = '/tasks';
  }, 1000);
}
</script>

<style scoped>
/* ...existing code... */
.param-select-row {
  margin-bottom: 8px;
}
.param-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
/* 整体页面美化 */
.create-task-page {
  max-width: 600px;
  margin: 40px auto;
  background: linear-gradient(135deg, #f7fafd 0%, #e3eaf2 100%);
  border-radius: 18px;
  box-shadow: 0 4px 24px rgba(25, 121, 198, 0.12);
  padding: 40px 32px;
  transition: box-shadow 0.3s;
}
h2 {
  color: #1979c6;
  margin-bottom: 32px;
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: 1px;
  text-align: center;
}
.form-row {
  margin-bottom: 28px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
label {
  font-weight: 600;
  margin-bottom: 8px;
  color: #1979c6;
  font-size: 1.08rem;
}
input,
select,
textarea {
  border: 1.5px solid #cfd8dc;
  border-radius: 8px;
  padding: 10px;
  font-size: 16px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(25, 121, 198, 0.04);
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}
input:focus,
select:focus,
textarea:focus {
  border-color: #1979c6;
  box-shadow: 0 2px 8px rgba(25, 121, 198, 0.1);
}
textarea {
  min-height: 48px;
}
button {
  background: linear-gradient(90deg, #1979c6 60%, #52c41a 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 12px 28px;
  font-size: 17px;
  cursor: pointer;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(25, 121, 198, 0.08);
  transition:
    background 0.2s,
    box-shadow 0.2s;
}
button:hover {
  background: linear-gradient(90deg, #52c41a 60%, #1979c6 100%);
  box-shadow: 0 4px 16px rgba(82, 196, 26, 0.12);
}

.hint {
  font-size: 13px;
  color: #888;
  margin-top: 6px;
}
.param-select-row {
  margin-bottom: 10px;
}
.param-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.param-card {
  display: flex;
  align-items: center;
  background: #fff;
  border: 1.5px solid #e3eaf2;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(25, 121, 198, 0.08);
  padding: 10px 16px;
  gap: 14px;
  margin-bottom: 2px;
  max-width: 420px;
  margin-left: auto;
  margin-right: auto;
  transition:
    box-shadow 0.2s,
    border-color 0.2s;
}
.param-card:hover {
  box-shadow: 0 4px 16px rgba(25, 121, 198, 0.16);
  border-color: #1979c6;
}
.param-key {
  font-weight: 500;
  color: #1979c6;
  min-width: 120px;
  font-size: 1rem;
}
.param-input {
  border: 1.5px solid #cfd8dc;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 15px;
  width: 180px;
  background: #f7fafd;
  transition: border-color 0.2s;
}
.param-input:focus {
  border-color: #1979c6;
}
.param-remove {
  background: #fff;
  color: #ff4d4f;
  border: 1.5px solid #ff4d4f;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background 0.2s,
    color 0.2s,
    border-color 0.2s;
}
.param-remove:hover {
  background: #ff4d4f;
  color: #fff;
  border-color: #ff4d4f;
}
.readonly-input {
  background: #f5f5f5;
  color: #888;
  cursor: pointer;
  border-radius: 8px;
}
.param-key {
  font-weight: 500;
  color: #1979c6;
  min-width: 120px;
}
.param-input {
  border: 1px solid #cfd8dc;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 15px;
  width: 180px;
  background: #fff;
}
.param-remove {
  background: #fff;
  color: #ff4d4f;
  border: 1px solid #ff4d4f;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.param-remove:hover {
  background: #ff4d4f;
  color: #fff;
}
/* ...existing code... */
</style>
