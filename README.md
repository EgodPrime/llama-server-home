# Llama-server-home

> 这个项目的目的是提供一个轻量级的基于llama.cpp中llama-server程序的模型部署和管理平台，适用于在局域网内的多台服务器上部署和管理llama模型实例，并通过统一的前端界面进行监控和管理。

**Llama.cpp启动速度最快、资源使用最轻量，配置简单又灵活，为什么不呢？**

## 架构说明

- **存储中心**：NFS共享存储的挂载点和mongodb数据库的部署点。控制器和节点都需要访问NFS存储来读取模型文件，同时也需要访问mongodb来注册节点信息、创建部署任务、更新状态等。

- **前端**：提供用户界面，允许用户查看节点状态、创建部署任务、监控实例状态等。前端通过API与控制器交互。

- **控制器 (Controller)**：负责管理整个系统的状态，处理用户请求，分配实例管理任务，监控节点状态，与前端交互（即控制器兼任后端API服务器）。部署在一台服务器上。

- **节点 (Node)**：运行在每个物理服务器上，负责执行控制器分配的任务，如部署与维护模型实例、监控本地资源等。节点会定期在数据库中更新自己的状态、指标信息、实例状态等。

> 存储中心、前端和控制器可以部署在同一台服务器上，也可以分开部署。节点需要部署在每个物理服务器上。

## 使用说明

### Step 0: 环境准备

> 此处仅给出使用uv管理Python环境的说明，其他环境如conda等请自行适配。
> 操作系统以ubuntu为例。
> uv安装：`curl -LsSf https://astral.sh/uv/install.sh | sh`
> 各个服务器的防火墙设置此处不再赘述，请确保控制器和节点之间、前端和控制器之间的必要端口是开放的。

#### 存储中心
- nfs-utils (用于挂载NFS存储)
- mongodb

```bash
sudo apt update
sudo apt install nfs-utils
```

> mongodb-community-server的安装请参考官方文档：https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/

#### 前端

- node(v20+)

> 参考nodejs官方文档安装：https://nodejs.org/en/download/

#### 控制器与节点
- nfs-common (用于访问NFS存储)
- Python3.13

```bash
sudo apt update
sudo apt install nfs-common
uv python install python@3.13
```

### Step 1: 存储中心

```bash
# 注意操作前观察一下自己服务器的磁盘空间分配格局，理性选择NFS挂载点，别把根目录炸了
mkdir -p /mnt/nfs/models
sudo chown -R nobody:nogroup /mnt/nfs/models
sudo chmod -R 777 /mnt/nfs/models
sudo vim /etc/exports
# 在文件末尾添加下面这一行，允许局域网内的所有机器访问这个目录
# /mnt/nfs/models *(rw,sync,no_subtree_check)
sudo exportfs -a
sudo systemctl restart nfs-kernel-server

# 启动mongodb
sudo systemctl start mongod
```

### Step 2: 控制器兼后端

```bash
mkdir -p <本机想要的挂载点>
sudo mount -t nfs <NFS服务器IP>:<NFS服务器挂载点> <本机想要的挂载点>
git clone https://github.com/EgodPrime/llama-server-home.git
cd llama-server-home
uv venv
uv pip install -e .
cp controller.yaml.tmp controller.yaml
# 修改controller.yaml中的mongodb_url和nfs_path为实际值
vim controller.yaml
uv run uvicorn src.lsh.controller.app:app --host 0.0.0.0 --port 8000
```

> nfs挂载重启后可能会丢失，可以在/etc/fstab中添加一行来实现开机自动挂载：
>
> `<NFS服务器IP>:<NFS服务器挂载点> <本机想要的挂载点> nfs defaults 0 0`

### Step 3: 节点

```bash
mkdir -p <本机想要的挂载点>
sudo mount -t nfs <NFS服务器IP>:<NFS服务器挂载点> <本机想要的挂载点>
git clone https://github.com/EgodPrime/llama-server-home.git
cd llama-server-home
uv venv
uv pip install -e .
cp node.yaml.tmp node.yaml
# 修改node.yaml中的mongodb_url、name、ip、llama_path和nfs_path为实际值
vim node.yaml
uv run run-node
```

> nfs挂载重启后可能会丢失，可以在/etc/fstab中添加一行来实现开机自动挂载：
>
> `<NFS服务器IP>:<NFS服务器挂载点> <本机想要的挂载点> nfs defaults 0 0`

### Step 4: 前端

> 默认在3000端口启动，如果需要修改请修改vite.config.js中的server.port字段

```bash
git clone https://github.com/EgodPrime/llama-server-home.git
cd llama-server-home
cd frontend
npm install
# 修改vite.config.js中的server.proxy.target为控制器的实际地址
vim vite.config.js
npm run dev
```