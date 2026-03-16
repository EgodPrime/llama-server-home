<template>
  <div class="instance-groups-page">
    <h2>实例组管理</h2>
    <div class="actions">
      <a-button type="primary" @click="showCreateDialog = true" style="margin-bottom: 16px"
        >新建实例组</a-button
      >
    </div>
    <a-table :dataSource="groups" :columns="groupColumns" rowKey="group_name" :loading="loading">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'group_name'">
          <a @click.prevent="selectGroup(record)">{{ record.group_name }}</a>
        </template>
        <template v-if="column.key === 'status'">
          <span v-if="groupStatus[record.group_name]">
            {{ groupStatus[record.group_name].running }}/{{ record.instances.length }} 运行中
          </span>
          <span v-else>--</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-button
            @click="deployGroup(record)"
            style="margin-right: 8px"
            :disabled="!groupCanDeploy(record)"
            >全部部署</a-button
          >
          <a-button
            @click="stopGroup(record)"
            style="margin-right: 8px"
            :disabled="!groupCanStop(record)"
            >全部关闭</a-button
          >
          <a-button
            @click="resumeGroup(record)"
            style="margin-right: 8px"
            :disabled="!groupCanResume(record)"
            >全部恢复</a-button
          >
          <a-button
            @click="deleteGroupInstances(record)"
            style="margin-right: 8px"
            :disabled="!groupCanResume(record)"
            danger
            >批量删除实例</a-button
          >
          <a-button @click="deleteGroup(record)" danger>删除组</a-button>
        </template>
      </template>
    </a-table>

    <!-- 组详情弹窗 -->
    <a-modal
      v-model:open="detailModalVisible"
      title="实例组详情"
      width="700px"
      @cancel="detailModalVisible = false"
    >
      <template #footer><a-button @click="detailModalVisible = false">关闭</a-button></template>
      <a-table
        :dataSource="selectedGroup?.instances || []"
        :columns="instanceColumns"
        rowKey="instance_name"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <span>{{ getInstanceStatus(record) }}</span>
          </template>
        </template>
      </a-table>
    </a-modal>

    <!-- 新建实例组弹窗 -->
    <a-modal
      v-model:open="showCreateDialog"
      title="新建实例组"
      width="900px"
      @cancel="showCreateDialog = false"
    >
      <template #footer>
        <a-button @click="createGroup" type="primary">创建</a-button>
        <a-button @click="showCreateDialog = false">取消</a-button>
      </template>
      <div style="margin-bottom: 12px">
        <label>组名：<a-input v-model:value="newGroupName" /></label>
      </div>
      <div style="margin-bottom: 8px">选择要加入组的实例：</div>
      <a-checkbox-group v-model:value="selectedInstanceKeys">
        <div class="instances-list">
          <table style="width: 100%; border-collapse: collapse; table-layout: fixed">
            <thead>
              <tr>
                <th style="padding: 4px 8px; border-bottom: 1px solid #eee; width: 60px">选择</th>
                <th style="padding: 4px 8px; border-bottom: 1px solid #eee; width: 160px">
                  实例名称
                </th>
                <th style="padding: 4px 8px; border-bottom: 1px solid #eee; width: 120px">
                  节点ID
                </th>
                <th style="padding: 4px 8px; border-bottom: 1px solid #eee; width: 100px">状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="inst in allInstances" :key="inst.instance_name + '#@#' + inst.node_id">
                <td style="padding: 4px 8px; text-align: center">
                  <a-checkbox :value="inst.instance_name + '#@#' + inst.node_id" />
                </td>
                <td
                  style="
                    padding: 4px 8px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    max-width: 160px;
                  "
                >
                  {{ inst.instance_name }}
                </td>
                <td
                  style="
                    padding: 4px 8px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    max-width: 120px;
                  "
                >
                  {{ inst.node_id }}
                </td>
                <td style="padding: 4px 8px">{{ inst.status || '--' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </a-checkbox-group>
    </a-modal>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, computed } from 'vue';
import {
  listInstanceGroups,
  getInstanceGroupInstancesStatus,
  createInstanceGroup,
  deployInstanceGroup,
  stopInstanceGroup,
  resumeInstanceGroup,
  deleteInstanceGroupInstances,
  deleteInstanceGroup,
  listInstances,
} from '@/api/index.js';
import type { InstanceGroup, Instance, InstanceStatus } from '@/types/index.js';
import { message } from 'ant-design-vue';

export default defineComponent({
  name: 'InstanceGroups',
  setup() {
    const groups = ref<InstanceGroup[]>([]);
    const groupStatus = ref<Record<string, { running: number }>>({});
    const loading = ref(true);
    const selectedGroup = ref<InstanceGroup | null>(null);
    const detailModalVisible = ref(false);
    const showCreateDialog = ref(false);
    const newGroupName = ref('');
    const allInstances = ref<Instance[]>([]);
    const selectedInstanceKeys = ref<string[]>([]);
    const selectedGroupStatuses = ref<InstanceStatus[]>([]);

    // 表格列定义
    const groupColumns = [
      { title: '组名', dataIndex: 'group_name', key: 'group_name' },
      {
        title: '实例数量',
        dataIndex: 'instances',
        key: 'instances',
        customRender: ({ record }: { record: InstanceGroup }) => record.instances.length,
      },
      { title: '运行情况', key: 'status' },
      { title: '操作', key: 'action' },
    ];
    const instanceColumns = [
      { title: '实例名称', dataIndex: 'instance_name', key: 'instance_name' },
      { title: '节点', dataIndex: 'node_id', key: 'node_id' },
      { title: '状态', key: 'status' },
    ];

    // 加载实例组和所有实例
    const loadGroups = async () => {
      loading.value = true;
      groups.value = await listInstanceGroups();
      await Promise.all(
        groups.value.map(async (group) => {
          const statuses: InstanceStatus[] = await getInstanceGroupInstancesStatus(
            group.group_name
          );
          const running = statuses.filter((s) => s.status === 'RUNNING').length;
          groupStatus.value[group.group_name] = { running };
        })
      );
      loading.value = false;
    };
    const loadAllInstances = async () => {
      allInstances.value = await listInstances();
    };

    onMounted(() => {
      loadGroups();
      loadAllInstances();
    });

    // 选中组，弹窗显示详情并加载实例状态
    const selectGroup = async (group: InstanceGroup) => {
      selectedGroup.value = group;
      selectedGroupStatuses.value = await getInstanceGroupInstancesStatus(group.group_name);
      detailModalVisible.value = true;
    };
    // 获取实例状态（详情弹窗用）
    const getInstanceStatus = (instance: Instance) => {
      const found = selectedGroupStatuses.value.find(
        (s) => s.instance_name === instance.instance_name && s.node_id === instance.node_id
      );
      return found ? found.status : '--';
    };

    // 操作
    const deployGroup = async (group: InstanceGroup) => {
      await deployInstanceGroup(group.group_name);
      message.success('全部部署任务已创建');
      await loadGroups();
    };
    const stopGroup = async (group: InstanceGroup) => {
      await stopInstanceGroup(group.group_name);
      message.success('全部关闭任务已创建');
      await loadGroups();
    };
    const resumeGroup = async (group: InstanceGroup) => {
      await resumeInstanceGroup(group.group_name);
      message.success('全部恢复任务已创建');
      await loadGroups();
    };
    const deleteGroupInstances = async (group: InstanceGroup) => {
      if (confirm('确定要批量删除该组内所有实例吗？')) {
        await deleteInstanceGroupInstances(group.group_name);
        message.success('批量删除实例成功');
        await loadGroups();
      }
    };
    const deleteGroup = async (group: InstanceGroup) => {
      if (confirm('确定要删除该实例组吗？')) {
        await deleteInstanceGroup(group.group_name);
        message.success('删除实例组成功');
        await loadGroups();
      }
    };
    // 创建新组
    const createGroup = async () => {
      if (!newGroupName.value.trim() || selectedInstanceKeys.value.length === 0) return;
      const names = selectedInstanceKeys.value.map((key) => key.split('#@#')[0]);
      const nodeIds = selectedInstanceKeys.value.map((key) => key.split('#@#')[1]);
      await createInstanceGroup(newGroupName.value, names, nodeIds);
      showCreateDialog.value = false;
      newGroupName.value = '';
      selectedInstanceKeys.value = [];
      message.success('实例组创建成功');
      await loadGroups();
    };

    // 计算每组按钮可用性
    const groupCanStop = (group: InstanceGroup) => {
      const status = groupStatus.value[group.group_name];
      return status && group.instances.length > 0 && status.running === group.instances.length;
    };
    const groupCanResume = (group: InstanceGroup) => {
      const status = groupStatus.value[group.group_name];
      return status && group.instances.length > 0 && status.running === 0;
    };

    const groupCanDeploy = (group: InstanceGroup) => {
      const status = groupStatus.value[group.group_name];
      return status && group.instances.length > 0 && status.running === 0;
    };

    return {
      groups,
      groupStatus,
      loading,
      selectedGroup,
      detailModalVisible,
      showCreateDialog,
      newGroupName,
      allInstances,
      selectedInstanceKeys,
      groupColumns,
      instanceColumns,
      selectGroup,
      getInstanceStatus,
      deployGroup,
      stopGroup,
      resumeGroup,
      deleteGroupInstances,
      deleteGroup,
      createGroup,
      groupCanStop,
      groupCanResume,
      groupCanDeploy,
    };
  },
});
</script>

<style scoped>
.instance-groups-page {
  padding: 24px;
}
.instances-list {
  max-height: 200px;
  overflow: auto;
  border: 1px solid #eee;
  padding: 8px;
  margin-bottom: 12px;
}
h2 {
  color: #1979c6;
  margin-bottom: 24px;
}
.actions {
  margin-bottom: 16px;
}
</style>
