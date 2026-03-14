import axios from 'axios';
import { Node, Metric } from '../types/index';

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
