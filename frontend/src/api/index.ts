import axios from 'axios';
import { Node, Metric, CreateInstanceTask } from '../types/index.ts';

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

// 创建实例任务
export async function createInstanceTask(task: CreateInstanceTask): Promise<{ message: string; task_id: string }> {
	const res = await axios.post('/api/tasks/create_instance_task', task);
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

