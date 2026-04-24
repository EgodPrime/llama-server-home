import axios from 'axios';
import router from '@/router/index.js';
import {
  Node,
  Metric,
  Instance,
  InstanceTask,
  Log,
  InstanceGroup,
  InstanceStatus,
} from '../types/index.js';

// 自动在请求头中添加 Token
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 统一处理 401 错误，自动跳转到登录页
axios.interceptors.response.use(
  (response) => response, // 成功直接返回
  (error) => {
    if (error.response && error.response.status === 401) {
      // Token 过期或无效
      console.warn('认证失败，请重新登录');

      // 1. 清除本地 Token
      localStorage.removeItem('token');
      localStorage.removeItem('username');

      // 2. 跳转到登录页（使用 router 避免页面刷新）
      router.push('/login');
    }
    return Promise.reject(error);
  }
);

// 获取节点列表
export async function listNodes(): Promise<Node[]> {
  const res = await axios.get('/api/nodes/list_nodes');
  return res.data;
}

// 获取某节点的metrics
export async function getNodeMetrics(nodeId: string, n = 20): Promise<Metric[]> {
  const res = await axios.get(`/api/nodes/${nodeId}/metrics`, { params: { n } });
  return res.data;
}

// 获取实例任务列表
export async function listInstanceTasks(): Promise<InstanceTask[]> {
  const res = await axios.get('/api/tasks/list_instance_tasks');
  return res.data;
}

// 创建实例任务
export async function createInstance(task: InstanceTask): Promise<{ message: string }> {
  const res = await axios.post('/api/tasks/create_instance', task);
  return res.data;
}

// 删除实例任务
export async function deleteInstanceTask(taskId: string): Promise<{ message: string }> {
  const res = await axios.delete(`/api/tasks/delete_instance_task/${taskId}`);
  return res.data;
}

// 获取实例列表
export async function listInstances(): Promise<Instance[]> {
  const res = await axios.get('/api/instances/list_instances');
  return res.data;
}

// 删除实例
export async function deleteInstance(
  nodeId: string,
  instanceName: string
): Promise<{ message: string }> {
  const res = await axios.delete(`/api/instances/delete_instance/${nodeId}/${instanceName}`);
  return res.data;
}

// 停止实例
export async function stopInstance(
  nodeId: string,
  instanceName: string
): Promise<{ message: string }> {
  const res = await axios.post(`/api/tasks/stop_instance/${nodeId}/${instanceName}`);
  return res.data;
}

// 恢复实例
export async function resumeInstance(
  nodeId: string,
  instanceName: string
): Promise<{ message: string }> {
  const res = await axios.post(`/api/tasks/resume_instance/${nodeId}/${instanceName}`);
  return res.data;
}

// 获取实例日志
export async function getInstanceLogs(nodeId: string, instanceName: string): Promise<Log> {
  const res = await axios.get(`/api/instances/logs/${nodeId}/${instanceName}`);
  return res.data;
}

/* NFS 相关 API */

// NFS item types
export interface NfsItem {
  name: string;
  nfs_path: string;
  type: 'file' | 'directory';
}

export interface NfsModel {
  model_name: string;
  model_file?: string;
  mmproj_file?: string;
}

export async function listNfsRoot(): Promise<NfsItem[]> {
  const res = await axios.get('/api/nfs/list_root');
  return res.data;
}

export async function listNfsDir(dirPath: string): Promise<NfsItem[]> {
  const res = await axios.get(`/api/nfs/list_dir/${encodeURIComponent(dirPath)}`);
  return res.data;
}

export async function listNfsModels(): Promise<NfsModel[]> {
  const res = await axios.get('/api/nfs/list_models');
  return res.data;
}

/* 用户认证相关 API */

export async function register(username: string, password: string): Promise<{ message: string }> {
  const res = await axios.post('/api/user/register', { username, password });
  return res.data;
}

export async function login(username: string, password: string): Promise<{ token: string }> {
  const res = await axios.post('/api/user/login', { username, password });
  return res.data;
}

// --- 实例组相关 API --- //

// 创建实例组
export async function createInstanceGroup(
  groupName: string,
  instanceNames: string[],
  instanceNodeIds: string[]
): Promise<{ message: string }> {
  const res = await axios.post('/api/instance_groups/create', {
    group_name: groupName,
    instance_names: instanceNames,
    instance_node_ids: instanceNodeIds,
  });
  return res.data;
}

// 获取实例组列表
export async function listInstanceGroups(): Promise<InstanceGroup[]> {
  const res = await axios.get('/api/instance_groups/list');
  return res.data;
}

// 获取实例组详情
export async function getInstanceGroupDetail(groupName: string): Promise<InstanceGroup> {
  const res = await axios.get(`/api/instance_groups/detail/${encodeURIComponent(groupName)}`);
  return res.data;
}

// 查询实例组内所有实例状态
export async function getInstanceGroupInstancesStatus(
  groupName: string
): Promise<InstanceStatus[]> {
  const res = await axios.get(
    `/api/instance_groups/${encodeURIComponent(groupName)}/instances_status`
  );
  return res.data;
}

// 批量部署实例组
export async function deployInstanceGroup(groupName: string): Promise<{ message: string }> {
  const res = await axios.post(
    `/api/instance_groups/deploy_instances/${encodeURIComponent(groupName)}`
  );
  return res.data;
}

// 批量关闭实例组
export async function stopInstanceGroup(groupName: string): Promise<{ message: string }> {
  const res = await axios.post(
    `/api/instance_groups/stop_instances/${encodeURIComponent(groupName)}`
  );
  return res.data;
}

// 批量恢复实例组
export async function resumeInstanceGroup(groupName: string): Promise<{ message: string }> {
  const res = await axios.post(
    `/api/instance_groups/resume_instances/${encodeURIComponent(groupName)}`
  );
  return res.data;
}

// 批量删除实例组内所有实例
export async function deleteInstanceGroupInstances(
  groupName: string
): Promise<{ message: string }> {
  const res = await axios.post(
    `/api/instance_groups/delete_instances/${encodeURIComponent(groupName)}`
  );
  return res.data;
}

// 删除实例组
export async function deleteInstanceGroup(groupName: string): Promise<{ message: string }> {
  const res = await axios.post(`/api/instance_groups/delete/${encodeURIComponent(groupName)}`);
  return res.data;
}
