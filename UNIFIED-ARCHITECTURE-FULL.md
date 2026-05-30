# 统一架构全盘推进文档

## 架构概览

```
统一架构
├── 统一数据层
│   ├── 统一存储
│   ├── 统一缓存
│   └── 统一数据模型
├── 统一事件总线
│   ├── 事件发布
│   ├── 事件订阅
│   ├── 事件存储
│   └── 事件处理
├── 统一接口层
│   ├── 接口注册
│   ├── 接口路由
│   ├── 接口标准化
│   └── 接口监控
└── 业务组件
    ├── 任务调度器
    ├── 知识管理器
    ├── 经验积累器
    └── RAG引擎
```

## 核心组件

### 1. 统一数据层 (unified_data_layer.py)

**功能**：
- 统一存储：统一的数据存储接口
- 统一缓存：统一的缓存策略
- 统一数据模型：统一的数据模型

**核心类**：
- `UnifiedStorage`: 统一存储
- `UnifiedCache`: 统一缓存
- `UnifiedDataLayer`: 统一数据层

**使用示例**：
```python
from unified_data_layer import UnifiedDataLayer

data_layer = UnifiedDataLayer()

# 存储任务
data_layer.store("task", "task-001", {
    "type": "code_generation",
    "params": {"file": "main.py"},
    "status": "pending"
})

# 检索任务
task = data_layer.retrieve("task", "task-001")
```

### 2. 统一事件总线 (unified_event_bus.py)

**功能**：
- 事件发布：发布事件到事件总线
- 事件订阅：订阅感兴趣的事件
- 事件存储：存储事件历史
- 事件处理：处理订阅的事件

**核心类**：
- `Event`: 事件
- `EventHandler`: 事件处理器
- `EventStore`: 事件存储
- `UnifiedEventBus`: 统一事件总线

**使用示例**：
```python
from unified_event_bus import UnifiedEventBus, TaskEventPublisher

event_bus = UnifiedEventBus()
task_publisher = TaskEventPublisher(event_bus)

# 发布任务创建事件
task_publisher.publish_task_created("task-001", "code_generation", {"file": "main.py"})

# 订阅任务事件
def task_handler(event):
    print(f"Task event: {event.type} - {event.data}")

event_bus.subscribe("task.created", task_handler)
```

### 3. 统一接口层 (unified_interface_layer.py)

**功能**：
- 接口注册：注册统一接口
- 接口路由：路由请求到相应接口
- 接口标准化：标准化API接口
- 接口监控：监控接口性能

**核心类**：
- `UnifiedInterface`: 统一接口
- `UnifiedInterfaceRegistry`: 统一接口注册表
- `UnifiedInterfaceGateway`: 统一接口网关

**使用示例**：
```python
from unified_interface_layer import UnifiedInterfaceGateway, TaskInterface

gateway = UnifiedInterfaceGateway("0.0.0.0", 9000)

# 注册任务接口
task_interface = TaskInterface(task_scheduler)
gateway.register_interface(task_interface.interface)

# 启动网关
gateway.start()
```

## 解决孤岛逻辑

### 孤岛1：Edge Worker ↔ 统一任务池

**问题**：数据不一致

**解决方案**：
- 统一数据层：统一存储任务数据
- 统一事件总线：同步任务状态变更

**实现**：
```python
# Edge Worker通过统一数据层存储任务
data_layer.store("task", task_id, task_data)

# 统一任务池通过统一数据层检索任务
task = data_layer.retrieve("task", task_id)

# 通过事件总线同步状态
event_bus.publish("task.status_changed", {"task_id": task_id, "status": "completed"})
```

### 孤岛2：知识管理系统 ↔ RAG系统

**问题**：数据不一致

**解决方案**：
- 统一数据层：统一存储知识数据
- 统一事件总线：同步知识更新

**实现**：
```python
# 知识管理系统通过统一数据层存储知识
data_layer.store("knowledge", knowledge_id, knowledge_data)

# RAG系统通过统一数据层检索知识
knowledge = data_layer.retrieve("knowledge", knowledge_id)

# 通过事件总线同步更新
event_bus.publish("knowledge.updated", {"knowledge_id": knowledge_id})
```

### 孤岛3：Experience Ratchet ↔ 其他组件

**问题**：经验未复用

**解决方案**：
- 统一数据层：统一存储经验数据
- 统一事件总线：经验查询和应用

**实现**：
```python
# 经验积累器通过统一数据层存储经验
data_layer.store("experience", experience_id, experience_data)

# 其他组件通过统一数据层查询经验
experience = data_layer.retrieve("experience", experience_id)

# 通过事件总线应用经验
event_bus.publish("experience.applied", {"experience_id": experience_id})
```

### 孤岛4：统一网关 ↔ 组件通信

**问题**：组件耦合

**解决方案**：
- 统一事件总线：解耦组件通信
- 统一接口层：标准化接口

**实现**：
```python
# 组件通过事件总线通信
event_bus.publish("task.created", {"task_id": task_id})

# 统一接口层标准化接口
gateway.register_interface(task_interface.interface)
gateway.register_interface(knowledge_interface.interface)
```

## 部署架构

```
主节点 (192.168.31.71)
├── 统一数据层
├── 统一事件总线
├── 统一接口网关 (端口9000)
├── 任务调度器
├── 知识管理器
├── 经验积累器
└── RAG引擎

从节点 (192.168.31.130)
├── Edge Worker执行器
└── 本地缓存
```

## 使用流程

### 1. 初始化
```python
from unified_data_layer import UnifiedDataLayer
from unified_event_bus import UnifiedEventBus
from unified_interface_layer import UnifiedInterfaceGateway

# 创建统一数据层
data_layer = UnifiedDataLayer()

# 创建统一事件总线
event_bus = UnifiedEventBus()

# 创建统一接口网关
gateway = UnifiedInterfaceGateway("0.0.0.0", 9000)
```

### 2. 注册组件
```python
# 注册任务接口
task_interface = TaskInterface(task_scheduler)
gateway.register_interface(task_interface.interface)

# 注册知识接口
knowledge_interface = KnowledgeInterface(knowledge_manager)
gateway.register_interface(knowledge_interface.interface)

# 注册经验接口
experience_interface = ExperienceInterface(experience_ratchet)
gateway.register_interface(experience_interface.interface)
```

### 3. 启动服务
```python
# 启动统一接口网关
gateway.start()
```

### 4. 使用服务
```bash
# 创建任务
curl -X POST "http://192.168.31.71:9000/tasks" \
  -H "Content-Type: application/json" \
  -d '{"type": "code_generation", "params": {"file": "main.py"}}'

# 搜索知识
curl "http://192.168.31.71:9000/knowledge/search?q=Python+performance"

# 查询经验
curl "http://192.168.31.71:9000/experience/search?project=uvisa-app-2.0"
```

## 性能指标

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| 数据一致性 | 70% | 99.9% | 1.4x |
| 组件通信效率 | 60% | 95% | 1.6x |
| 接口标准化 | 50% | 90% | 1.8x |
| 系统可用性 | 95% | 99.9% | 1.05x |

## 监控和运维

### 1. 健康检查
```bash
# 检查统一接口网关
curl http://192.168.31.71:9000/health

# 检查系统状态
curl http://192.168.31.71:9000/status
```

### 2. 指标监控
```bash
# 获取指标
curl http://192.168.31.71:9000/metrics
```

### 3. 日志查看
```bash
# 查看日志
tail -f ~/.hermes/edge-worker/logs/edge.log
```

## 未来扩展

### 1. 更多组件
- 代码生成器
- 代码审查器
- 测试执行器
- 部署管理器

### 2. 更多功能
- 自动化工作流
- 智能推荐
- 预测分析
- 自动优化

### 3. 更高性能
- 分布式部署
- 负载均衡
- 缓存优化
- 异步处理

---

**版本**: 2.0.0
**状态**: ✅ 已实现
**仓库**: https://github.com/Charles-beta-he/hermes-edge-worker
