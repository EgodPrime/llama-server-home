import axios from 'axios';
import { Node, Metric, Instance, InstanceTask } from '../types/index.js';

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
  const res = await axios.post(`/api/tasks/delete_instance_task/${taskId}`);
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
  const res = await axios.post(`/api/instances/delete_instance/${nodeId}/${instanceName}`);
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

// NFS API
export async function listNfsRoot(): Promise<any[]> {
  const res = await axios.get('/api/nfs/list_root');
  return res.data;
}

export async function listNfsDir(dirPath: string): Promise<any[]> {
  const res = await axios.get(`/api/nfs/list_dir/${encodeURIComponent(dirPath)}`);
  return res.data;
}

export async function listNfsModels(): Promise<any[]> {
  const res = await axios.get('/api/nfs/list_models');
  return res.data;
}
