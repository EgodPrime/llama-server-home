// Node
export interface Node {
	name: string;
	ip_address: string;
	llama_path: string;
	status: string; // "ONLINE" | "OFFLINE"
	last_heartbeat: number;
	registered_at: number;
	node_id: string;
}

// CreateInstanceTask
export interface CreateInstanceTask {
	task_id?: string;
	type: string; // "DEPLOY" | "CANCEL"
	instance_name: string;
	node_id: string;
	port: number;
	model_path: string;
	mmproj_path?: string;
	status?: string;
	created_at?: string;
	started_at?: string;
	finished_at?: string;
	error_msg?: string;
	env?: Record<string, string>;
	config?: Record<string, any>;
}

// Instance
export interface Instance {
	instance_name: string;
	node_id: string;
	status?: string; // "RUNNING" | "STOPPED" | "ERROR" | "RESTARTING"
	pid?: number;
	host?: string;
	port?: number;
	model_path: string;
	mmproj_path?: string;
	local_model_path?: string;
	local_mmproj_path?: string;
	model_size_b?: number;
	env?: Record<string, string>;
	config?: Record<string, any>;
	last_heartbeat?: string;
	last_error?: string;
	created_at?: string;
	started_at?: string;
	last_stopped_at?: string;
}

// ManageInstanceTask
export interface ManageInstanceTask {
	task_id: string;
	type: string; // "RESTART" | "STOP" | "START" | "DESTROY" | "MODIFY"
	instance_name: string;
	node_id: string;
	triggered_by?: string; // "USER" | "SYSTEM"
	status?: string;
	error_msg?: string;
	env_override?: Record<string, string>;
	config_override?: Record<string, any>;
	created_at?: string;
	started_at?: string;
	finished_at?: string;
}

// Log
export interface Log {
	node_id: string;
	instance_name: string;
	content?: string;
	created_at?: string;
	last_updated_at?: string;
}

// CPUInfo
export interface CPUInfo {
	usage_percent: number;
	cores_count: number;
}

// MemoryInfo
export interface MemoryInfo {
	total_mb: number;
	used_mb: number;
	free_mb: number;
	usage_percent: number;
}

// GPUInfo
export interface GPUInfo {
	id: number;
	model: string;
	temperature_c: number;
	power_draw_w: number;
	memory_total_mb: number;
	memory_used_mb: number;
	memory_free_mb: number;
}

// Metric
export interface Metric {
	node_id: string;
	timestamp: number;
	cpu: CPUInfo;
	memory: MemoryInfo;
	gpus: GPUInfo[];
}
