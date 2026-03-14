<template>
  <div>
    <h2>节点 {{ nodeId }} 的资源情况</h2>
    <!-- CPU 和 RAM 并排 -->
    <div class="row">
      <div class="card" style="flex:1; margin-right:16px;">
        <h3>CPU</h3>
        <div id="cpu-chart" class="chart"></div>
      </div>
      <div class="card" style="flex:1; margin-left:16px;">
        <h3>RAM</h3>
        <div id="ram-chart" class="chart"></div>
      </div>
    </div>
    <!-- GPUs 每两个一排 -->
    <div>
      <h3 style="color:#FA541C; margin-bottom:12px;">GPUs</h3>
      <div v-for="gpuPair in gpuPairs" :key="gpuPair[0]?.id || gpuPair[1]?.id" class="gpu-row">
        <div v-for="gpu in gpuPair" :key="gpu.id" class="card gpu-card" style="flex:1; margin:0 8px;">
          <h3>{{ gpu.id }}: {{ gpu.model }}</h3>
          <div :id="'gpu-chart-' + gpu.id" class="chart"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import { getNodeMetrics } from '@/api/index.js';
import { GPUInfo, MemoryInfo, CPUInfo, Metric } from '@/types/index.js';
import { Line } from '@antv/g2plot';

const route = useRoute();
const nodeId = route.params.node_id as string;
const metrics = ref<Metric[]>([]);
const gpuData = ref<GPUInfo[]>([]);
var cpuChart: Line | null = null;
var ramLine: Line | null = null;
var gpuLines: { [gpuId: number]: Line } = {};
// 计算GPU每两个一组
import { computed } from 'vue';
const gpuPairs = computed(() => {
  const arr:GPUInfo[][] = [];
  for (let i = 0; i < gpuData.value.length; i += 2) {
    arr.push([gpuData.value[i], gpuData.value[i+1]].filter(Boolean));
  }
  return arr;
});

let timer: ReturnType<typeof setInterval> | null = null;

const fetchAndRender = async () => {
  metrics.value = await getNodeMetrics(nodeId);
  gpuData.value = metrics.value[0]?.gpus || [];
  await nextTick();
  renderCharts();
};

onMounted(() => {
  fetchAndRender();
  timer = setInterval(fetchAndRender, 5000);
});

// 离开页面时清除定时器
import { onUnmounted } from 'vue';
onUnmounted(() => {
  if (timer) clearInterval(timer);
});

function renderCharts() {
  if (!metrics.value.length) return;
  // 按 timestamp 升序排序
  const sortedMetrics: Metric[] = [...metrics.value].sort((a: any, b: any) => a.timestamp - b.timestamp);
  // 计算最新时间戳
  const latest = Math.max(...sortedMetrics.map((item: any) => item.timestamp));
  

  // CPU chart
  if (document.getElementById('cpu-chart')) {
    const cpuData = sortedMetrics.map((item: any) => ({
    x: item.timestamp === latest
      ? new Date(item.timestamp * 1000).toLocaleString('zh-CN', { hour12: false })
      : `${Math.round(latest - item.timestamp)}秒前`,
    CPU: item.cpu.usage_percent,
  }));
    const new_config = {
      data: cpuData,
      xField: 'x',
      yField: 'CPU',
      point: { size: 4, shape: 'diamond' },
      smooth: true,
      color: '#1979C6',
      title: { visible: true, text: 'CPU 使用率' },
      xAxis: {
        label: {
          formatter: (v: any) => v,
        },
        // 保证最新时间在最右
        type: 'cat',
      },
      yAxis: {
        min: 0,
      },
    };
    if (cpuChart) {
      cpuChart.update(new_config);
    } else {
      cpuChart = new Line('cpu-chart', new_config);
      cpuChart.render();
    }
  }

  // RAM chart
  if (document.getElementById('ram-chart')) {
    const ramData = sortedMetrics.map((item: any) => ({
    x: item.timestamp === latest
      ? new Date(item.timestamp * 1000).toLocaleString('zh-CN', { hour12: false })
      : `${Math.round(latest - item.timestamp)}秒前`,
    RAM: item.memory.used_mb
  }));
  const MAX_RAM = sortedMetrics[0].memory.total_mb;
  const new_config= {
    data: ramData,
    xField: 'x',
    yField: 'RAM',
    point: { size: 4, shape: 'circle' },
    smooth: true,
    color: '#52C41A',
    title: { visible: true, text: 'RAM 使用量' },
    xAxis: {
    label: {
        formatter: (v: any) => v,
    },
    type: 'cat',
    },
    yAxis: {
    min: 0,
    max: MAX_RAM,
    label: {
        formatter: (v: any) => `${v} MB`,
    },
    },
  };
    if(ramLine) {
        ramLine.update(new_config);
    } else {
        ramLine = new Line('ram-chart', new_config);
        ramLine.render();
    }
  }

  // GPU charts
  if (gpuData.value.length) {
// 先提取出 timestamp: GPUInfo[] 的格式，方便后续处理
  const gpuMixedDataSeq = sortedMetrics.map((item: any) => ({
    x: item.timestamp === latest
      ? new Date(item.timestamp * 1000).toLocaleString('zh-CN', { hour12: false })
      : `${Math.round(latest - item.timestamp)}秒前`,
    GPUS: item.gpus
  }));
  // 在转换成 GPU ID: [{x, memory_used_mb}] 的格式，方便后续每个 GPU 单独画图
  const gpuSeqs: { [gpuId: number]: any[] } = {};
  gpuMixedDataSeq.forEach((item: any) => {
    item.GPUS.forEach((gpu: any) => {
      if (!gpuSeqs[gpu.id]) gpuSeqs[gpu.id] = [];
      gpuSeqs[gpu.id].push({
        x: item.x,
        memory_used_mb: gpu.memory_used_mb,
      });
    });
  });

  gpuMixedDataSeq[0].GPUS.forEach((gpu: any) => {
    const gpuMaxRAM = gpu.memory_total_mb;
    const chart_id = `gpu-chart-${gpu.id}`;
    if (document.getElementById(chart_id) ){
      const gpuConfig = {
        data: gpuSeqs[gpu.id],
      xField: 'x',
      yField: 'memory_used_mb',
      point: { size: 4, shape: 'circle' },
      smooth: true,
      color: '#FA541C',
      title: { visible: true, text: `GPU ${gpu.model} (ID: ${gpu.id}) 内存使用` },
      xAxis: {
        label: {
          formatter: (v: any) => v,
        },
        type: 'cat',
      },
      yAxis: {
        min: 0,
        max: gpuMaxRAM,
        label: {
          formatter: (v: any) => `${v} MB`,
        },
      },
    }
    if (gpuLines[gpu.id]) {
      gpuLines[gpu.id].update(gpuConfig);
    } else {
      gpuLines[gpu.id] = new Line(chart_id, gpuConfig);
      gpuLines[gpu.id].render();
    }
    
  }
  });
  }
    
}
</script>

<style scoped>
/* 并排布局 */
.row {
  display: flex;
  flex-direction: row;
  margin-bottom: 32px;
}
.gpu-row {
  display: flex;
  flex-direction: row;
  margin-bottom: 24px;
}
/* 页面整体美化 */
h2 {
  margin-bottom: 24px;
  color: #1979C6;
  font-weight: 700;
  letter-spacing: 1px;
}
.card {
  background: linear-gradient(135deg, #f8fafc 60%, #e6f7ff 100%);
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(25,121,198,0.10);
  padding: 32px 28px;
  margin-bottom: 32px;
  transition: box-shadow 0.2s;
}
.card:hover {
  box-shadow: 0 8px 32px rgba(25,121,198,0.18);
}
.card h3 {
  color: #52C41A;
  font-size: 22px;
  margin-bottom: 18px;
  font-weight: 600;
}
.chart {
  width: 600px;
  height: 300px;
  margin-bottom: 24px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.gpu-card {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px dashed #cfd8dc;
}
.gpu-card h3 {
  color: #FA541C;
  font-size: 18px;
  margin-bottom: 12px;
  font-weight: 500;
}
body {
  background: #f0f5ff;
}
</style>
