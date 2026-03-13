## schema

> 数据库：MongoDB

### nodes

```json
{
  "_id": "ObjectId",              // MongoDB 自动生成的唯一 ID
  "name": "string",               // 用户配置的名称 (如: "Server-T4-01")
  "ip_address": "string",         // 节点 IP (如: "192.168.1.100")
  
  // --- 唯一标识生成逻辑 ---
  // 规则：node_id = name@ip_address
  // 示例："Server-T4-01@192.168.1.100"
  "node_id": "string",            // **唯一索引 (Unique Index)**

  "llama_path": "string",          // Agent 配置的 llama.cpp 二进制路径 (如: "/opt/llama.cpp/build2/bin")
  
  "status": "string",             // "ONLINE" (由 Agent 首次设置), "OFFLINE" (由 Controller 根据心跳超时自动设置)
  
  "last_heartbeat": "ISODate",    // Agent 定期更新的时间戳
  
  "registered_at": "ISODate",     // 首次注册的时间
  

}
```

### create_instance_tasks

```json
{
  "_id": "ObjectId",
  "task_id": "uuid-string",  // 控制器自动生成
  "type": "DEPLOY | CANCEL", // CANCEL 用来取消task_id相同的任务

  "instance_name": "string", // 用户自定义实例名称 (如: "Code-8B-Instruct")
  "instance_labels": ["string"], // 可选，实例标签列表 (如: ["text", "vision"])
  "node_id": "string",          // 目标节点 ID (如: "Server-T4-01@192.168.1.100")
  
  // --- 模型引用 ---
  "model_path": "string",           // NFS相对路径 (如: "qwen35_27b/xxx.gguf")
  "model_hash": "string",           // MD5
  "mmproj_path": "string",          // 可选，mmproj文件的NFS相对路径 (如: "qwen35_27b/mmproj.gguf")
  "mmproj_hash": "string",          // 可选，mmproj文件的MD5

  // --- 任务状态流转 ---
  // 状态定义：
  // INIT:     任务已创建，等待 Agent 领取
  // DOWNLOADING: Agent 正在从 NFS 复制模型到本地缓存
  // READY: 缓存完成，正在启动llama-server
  // FINISHED: 模型已就绪，Agent 已启动服务 (或停止操作完成)
  // FAILED:   任务执行失败 (网络错误、Hash 校验失败等)
  "status": "string",              
  
  // --- 时间戳 ---
  "created_at": "ISODate",          // Controller 创建任务的时间
  "started_at": "ISODate",          // Agent 开始处理的时间
  "finished_at": "ISODate",          // Agent 完成所有操作的时间 (FINISHED 时写入)
  
  // --- 错误信息 ---
  "error_msg": "string",             // 仅当 status=FAILED 时有值
    
  // --- 启动配置 --- 
  // 环境变量
  "env": {
    "CUDA_VISIBLE_DEVICES": "0,1",
  },
  // 启动参数，Agent会直接传给llama-server
  "config": {
    "--n-gpu-layers": 999,
    "--ctx-size": 131072,
    "--parallel": 16,
    "--batch-size": 8192,
    "--n-predict": 16384,
    "--temp": 0.7,
    "--top-k": 20,
    "--top-p": 0.8,
    "--min-p": 0,
    "--presence_penalty": 1.0,
    "--frequency-penalty": 0.0,
    "--repeat-penalty": 1.0,
    "--threads": 4,
    "--flash-attn": "on|off|auto",
    "--split-mode": "none|layer|row",
    "--tensor-split": "0.5,0.5"
  }
}

```

### instances

```json
{
  "_id": "ObjectId",
  
  // --- 核心标识 ---
  "instance_name": "string",      // 用户自定义名称 (如: "Code-8B-Instruct")
  "instance_labels": ["string"], // 可选，实例标签列表 (如: ["text", "vision"])
  "node_id": "string",            // 所属节点 ID (如: "Server-T4-01@192.168.1.10")
  
  // --- 运行状态 ---
  // 状态定义：
  // RUNNING: 进程正在运行 (Agent 定期更新心跳)
  // STOPPED: 进程已停止 (用户手动停止)
  // ERROR:   进程异常停止(如 OOM)或部署失败
  // RESTARTING: 进程正在重启
  "status": "RUNNING|STOPPED|ERROR|RESTARTING",
  
  // --- 进程信息 ---
  "pid": "int",                   // 进程 PID
  "port": "int",                  // 服务端口
  "host": "string",               // 绑定地址 (通常 0.0.0.0)
  
  // --- 模型路径与大小 ---
  "model_path": "string",         // **NFS 相对路径** (如: "models/Code-8B.gguf")
  "local_path": "string",         // **本地缓存绝对路径** (如: "/var/cache/llama/models/a1b2c3...gguf")
  "model_size_b": "float",        // **模型大小 (字节)**，单位为十进制 (如 4500000000.0)
  
  // --- 环境变量 ---
  "env": {
    "CUDA_VISIBLE_DEVICES": "0,1",
  },
  // --- 启动配置 (除--model和--mmproj外均直接继承自tasks记录) ---
  "config": {                     // 完整启动参数 JSON
    "--model": "string",            // 模型文件本地路径
    "--mmproj": "string",            // mmproj 文件本地路径，如果instance_labels包含"vision"则必填
    "--n-gpu-layers": 999,
    "--ctx-size": 131072,
    "--parallel": 16,
    "--batch-size": 8192,
    "--n-predict": 16384,
    "--temp": 0.7,
    "--top-k": 20,
    "--top-p": 0.8,
    "--min-p": 0,
    "--presence_penalty": 1.0,
    "--frequency-penalty": 0.0,
    "--repeat-penalty": 1.0,
    "--threads": 4,
    "--flash-attn": "on|off|auto",
    "--split-mode": "none|layer|row",
    "--tensor-split": "0.5,0.5"
  },

  // --- 元数据 ---
  "last_heartbeat": "ISODate",    // 最后一次心跳时间 (用于判断实例存活)
  "last_error": "string",         // 最近错误信息 (如 OOM)
  
  "created_at": "ISODate",        // 首次部署时间
  "started_at": "ISODate",        // 进程启动时间
  "last_stopped_at": "ISODate"    // 最后停止时间
}

```

### manage_instance_tasks

```json
{
  "_id": "ObjectId",
  
  // --- 任务标识 ---
  "task_id": "uuid-string",      // 全局唯一任务 ID

  // --- 操作类型 ---
  // RESTART: 重启服务 (杀掉进程以原配置再启动)
  // STOP:    停止服务 (保持配置，仅停止进程)
  // START:   以保留的配置启动已经停止的服务
  // DESTROY: 销毁实例 (停止服务 + 清理 instances 记录)
  // MODIFY:  修改配置，然后以新配置重启服务
  "type": "RESTART | STOP | START | DESTROY | MODIFY",
  

  // --- 目标实例关联 ---
  "instance_name": "string",     // 目标实例名称 (如: "Code-8B")
  "node_id": "string",           // 目标节点 ID (如: "Server-T4-01@192.168.1.10")
  
  // --- 触发来源 (可选) ---
  // USER: 用户手动点击按钮
  // SYSTEM: 系统自动调度 (如检测到 error 后自动重启)
  "triggered_by": "USER | SYSTEM",
  

  // --- 任务状态流转 ---
  // INIT:     任务已创建，等待 Agent 领取
  // PROCESSING: Agent 正在执行操作 (修改配置/杀进程/启动)
  // COMPLETED: 操作成功完成
  // FAILED:   操作失败
  "status": "string",
  
  // --- 错误信息 ---
  "error_msg": "string",          // 失败原因，当 status=FAILED 时有值

  // --- 额外参数 (type为MODIFY时使用) ---
  "env_override": {
    "CUDA_VISIBLE_DEVICES": "0,1", // 用户想更改GPU分配
    // ... 其他可覆盖的环境变量
  },

  // --- 配置覆盖 (type为MODIFY时使用) ---
  "config_override": {           
    "--n-gpu-layers": 999, // 用户想更改gpu层数
    // ... 其他可覆盖的配置项
  },
  
  // --- 时间戳 ---
  "created_at": "ISODate",       // Controller 创建时间
  "started_at": "ISODate",       // Agent 开始执行时间
  "finished_at": "ISODate",      // Agent 完成时间
}

```

### logs

```json
{
  "_id": "ObjectId", // MongoDB 自动生成
  
  // --- 核心标识 (唯一性) ---
  "instance_name": "string",      // 实例名称 (如: "Code-8B")
  "node_id": "string",            // 节点 ID (如: "Server-T4-01@...")
  
  // --- 日志内容 ---
  "content": "string",            // **最新 20 行日志拼接体** (每行用 \n 分隔)
  
  // --- 元数据 ---
  "created_at": "ISODate",        // 日志记录创建时间
  "last_updated_at": "ISODate"    // Agent 最后更新日志的时间
}
```

### metrics

```json
{
  "_id": "ObjectId",
  
  // --- 节点标识 ---
  "node_id": "string",              // 节点 ID (如: "Server-T4-01@192.168.1.10")
  
  // --- 时间戳 ---
  "timestamp": "ISODate",           // 采集时刻的时间
  
  // --- CPU 资源 (整体) ---
  "cpu": {
    "usage_percent": "float",       // 总 CPU 使用率 (0.0 - 100.0)
    "cores_count": "int",           // 逻辑核心数
  },
  
  // --- 内存资源 (整体) ---
  "memory": {
    "total_mb": "int",              // 总内存 (MB)
    "used_mb": "int",               // 已用内存 (MB)
    "free_mb": "int",               // 可用内存 (MB)
    "percent_used": "float"         // 使用率百分比 (0.0 - 100.0)
  },
  
  // --- GPU 资源 (列表，每个节点可能有多个) ---
  "gpus": [                         // 数组结构，包含该节点所有显卡信息
    {
      "id": "int",                  // GPU ID (0, 1, 2...)
      "model": "string",            // 显卡型号 (如: Tesla T4)
      "temperature_c": "int",       // 核心温度 (°C)
      "power_draw_w": "int",        // 功耗 (W)
      "memory_total_mb": "int",     // 显存总量 (MB)
      "memory_used_mb": "int",      // 显存已用 (MB)
      "memory_free_mb": "int",      // 显存空闲 (MB)
    },
    // ... 更多 GPU 对象
  ],
}
```



