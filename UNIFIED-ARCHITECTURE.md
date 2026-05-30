# 统一架构文档

## 架构概览

```
统一架构
├── 统一入口层
│   ├── 统一网关 (端口9000)
│   ├── 负载均衡
│   └── 认证授权
├── 业务逻辑层
│   ├── 任务调度器
│   ├── 知识管理器
│   ├── 经验积累器
│   └── RAG引擎
├── 数据存储层
│   ├── 向量数据库 (FAISS)
│   ├── 关系数据库 (SQLite)
│   ├── 缓存 (Redis)
│   └── 文件存储
├── 执行层
│   ├── Edge Worker执行器
│   ├── Agent管理器
│   └── 结果聚合器
└── 监控层
    ├── 指标收集
    ├── 日志管理
    └── 告警通知
```

## 核心组件

### 1. 统一网关 (unified_gateway.py)

**功能**：
- 统一入口：所有请求通过网关
- 路由分发：根据请求类型分发到相应组件
- 认证授权：统一的认证和授权
- 监控统计：统一的监控和统计

**API端点**：
- `GET /health`: 健康检查
- `GET /status`: 系统状态
- `GET /tasks`: 列出任务
- `POST /tasks`: 创建任务
- `POST /tasks/execute`: 执行任务
- `GET /knowledge/search`: 搜索知识
- `POST /knowledge`: 添加知识
- `GET /experience/search`: 搜索经验
- `POST /experience`: 添加经验
- `POST /search`: 统一搜索
- `GET /metrics`: 获取指标

### 2. 统一管理器 (unified_manager.py)

**功能**：
- 组件注册：注册所有组件
- 状态管理：管理所有组件状态
- 指标统计：统计所有组件指标
- 生命周期管理：管理组件生命周期

**核心类**：
- `UnifiedManager`: 统一管理器
- `TaskSchedulerComponent`: 任务调度器组件
- `KnowledgeManagerComponent`: 知识管理器组件
- `ExperienceRatchetComponent`: 经验积累器组件
- `RAGEngineComponent`: RAG引擎组件

### 3. 任务调度器组件

**功能**：
- 任务创建：创建新任务
- 任务执行：执行任务
- 状态管理：管理任务状态
- 经验应用：应用相关经验

**使用示例**：
```python
scheduler = TaskSchedulerComponent()

# 创建任务
task_id = scheduler.create_task("code_generation", {"file": "main.py"}, priority=2)

# 执行任务
result = scheduler.execute_task(task_id, experience={"claim": "使用TypeScript"})

# 获取指标
metrics = scheduler.get_metrics()
```

### 4. 知识管理器组件

**功能**：
- 知识添加：添加新知识
- 知识搜索：搜索相关知识
- 指标统计：统计搜索次数

**使用示例**：
```python
manager = KnowledgeManagerComponent()

# 添加知识
manager.add_knowledge("1", "Python性能优化技巧", {"category": "programming"})

# 搜索知识
results = manager.search("Python performance")

# 获取指标
metrics = manager.get_metrics()
```

### 5. 经验积累器组件

**功能**：
- 经验创建：创建新经验
- 经验验证：验证经验有效性
- 经验查询：查询相关经验
- 经验应用：应用已验证经验

**使用示例**：
```python
ratchet = ExperienceRatchetComponent()

# 创建经验
experience_id = ratchet.create_experience({
    "project": "uvisa-app-2.0",
    "claim": "React组件应该使用TypeScript严格模式",
    "pattern_type": "architecture"
})

# 验证经验
ratchet.validate_experience(experience_id, "项目验证:多个项目成功应用")

# 查询经验
experience = ratchet.query_experience("uvisa-app-2.0", "code_generation")
```

### 6. RAG引擎组件

**功能**：
- 知识添加：添加知识到RAG
- 语义搜索：基于语义搜索知识
- 指标统计：统计搜索性能

**使用示例**：
```python
engine = RAGEngineComponent()

# 添加知识
engine.add_knowledge("1", "Python性能优化技巧", {"category": "programming"})

# 搜索知识
results = engine.search("Python performance optimization")

# 获取指标
metrics = engine.get_metrics()
```

## 部署架构

```
主节点 (192.168.31.71)
├── 统一网关 (端口9000)
├── 任务调度器 (端口9001)
├── 知识管理器 (端口9004)
├── RAG引擎 (端口9005)
└── 监控系统 (端口9006)

从节点 (192.168.31.130)
├── Edge Worker执行器
└── 本地缓存
```

## 使用流程

### 1. 初始化
```python
from unified_gateway import UnifiedGateway
from unified_manager import UnifiedManager, TaskSchedulerComponent, KnowledgeManagerComponent

# 创建统一管理器
manager = UnifiedManager()

# 注册组件
manager.register_component("task_scheduler", TaskSchedulerComponent())
manager.register_component("knowledge_manager", KnowledgeManagerComponent())

# 创建统一网关
gateway = UnifiedGateway("0.0.0.0", 9000)

# 注册组件到网关
gateway.register_component("task_scheduler", manager.get_component("task_scheduler"))
gateway.register_component("knowledge_manager", manager.get_component("knowledge_manager"))

# 启动网关
gateway.start()
```

### 2. 创建任务
```python
# 通过API创建任务
curl -X POST "http://192.168.31.71:9000/tasks" \
  -H "Content-Type: application/json" \
  -d '{"type": "code_generation", "params": {"file": "main.py"}, "priority": 2}'
```

### 3. 执行任务
```python
# 通过API执行任务
curl -X POST "http://192.168.31.71:9000/tasks/execute" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task-001"}'
```

### 4. 搜索知识
```python
# 通过API搜索知识
curl "http://192.168.31.71:9000/knowledge/search?q=Python+performance&top_k=5"
```

### 5. 获取指标
```python
# 通过API获取指标
curl "http://192.168.31.71:9000/metrics"
```

## 性能指标

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| 系统可用性 | 95% | 99.9% | 1.05x |
| 响应时间 | 100ms | 50ms | 2x |
| 任务成功率 | 90% | 99% | 1.1x |
| 经验复用率 | 30% | 80% | 2.7x |
| 搜索精度 | 70% | 95% | 1.4x |

## 监控和运维

### 1. 健康检查
```bash
# 检查统一网关
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

**版本**: 1.9.0
**状态**: ✅ 已实现
**仓库**: https://github.com/Charles-beta-he/hermes-edge-worker
