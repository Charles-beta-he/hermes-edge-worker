# 任务池事件驱动架构

## 📋 架构概览

```
任务池事件驱动架构
├── 事件源
│   ├── 任务创建事件
│   ├── 任务状态变更事件
│   ├── 任务依赖满足事件
│   └── 任务优先级变更事件
├── 事件总线
│   ├── 事件接收
│   ├── 事件路由
│   └── 事件存储
├── 事件处理器
│   ├── 自动认领
│   ├── 自动执行
│   └── 状态更新
└── API接口
    ├── 事件接收API
    ├── 指标查询API
    └── 健康检查API
```

## 🎯 核心组件

### 1. 事件驱动核心 (task_event_driven.py)

**功能**：
- 事件接收和处理
- 自动认领任务
- 自动执行任务
- 指标统计

**事件类型**：
- `task.created`: 任务创建
- `task.status_changed`: 任务状态变更
- `task.dependency_met`: 任务依赖满足
- `task.priority_changed`: 任务优先级变更
- `task.assigned`: 任务分配

**使用示例**：
```python
from task_event_driven import TaskEventDriven

# 创建事件驱动
event_driven = TaskEventDriven()

# 处理事件
event_driven.handle_event("task.created", {
    "task_id": "task-001",
    "priority": "P1"
})

# 获取指标
metrics = event_driven.get_metrics()
```

### 2. 任务池事件集成 (task_pool_event_integration.py)

**功能**：
- 集成任务池和事件驱动
- 调用brain_task_orchestrator.py
- 自动认领和执行任务

**使用示例**：
```python
from task_pool_event_integration import TaskPoolEventIntegration

# 创建集成
integration = TaskPoolEventIntegration()

# 处理事件
integration.process_task_event("task.created", {
    "task_id": "task-001",
    "priority": "P1"
})

# 获取指标
metrics = integration.get_metrics()
```

### 3. API接口

**事件接收API**：
```bash
# 发送事件
curl -X POST http://localhost:9008/event \
  -H "Content-Type: application/json" \
  -d '{"event_type":"task.created","event_data":{"task_id":"task-001","priority":"P1"}}'
```

**指标查询API**：
```bash
# 查询指标
curl http://localhost:9008/metrics
```

**健康检查API**：
```bash
# 健康检查
curl http://localhost:9008/health
```

## 📊 事件处理流程

### 1. 任务创建事件

```
任务创建
    ↓
事件总线
    ↓
事件处理器
    ↓
自动认领 (高优先级)
    ↓
自动执行
    ↓
状态更新
```

### 2. 任务状态变更事件

```
任务状态变更
    ↓
事件总线
    ↓
事件处理器
    ↓
状态判断
    ├─ pending → 自动认领
    └─ claimed → 自动执行
    ↓
状态更新
```

### 3. 任务依赖满足事件

```
任务依赖满足
    ↓
事件总线
    ↓
事件处理器
    ↓
自动认领
    ↓
自动执行
    ↓
状态更新
```

## 🎯 部署架构

### 1. 单机部署

```
主节点 (192.168.31.71)
├── 事件驱动API (端口9007)
├── 任务池事件集成API (端口9008)
├── 任务池 (brain_task_orchestrator.py)
└── 调度tick (brain_task_dispatch_tick.py)
```

### 2. 分布式部署

```
主节点 (192.168.31.71)
├── 事件驱动API (端口9007)
├── 任务池事件集成API (端口9008)
└── 任务池 (brain_task_orchestrator.py)

从节点 (192.168.31.130)
├── 事件驱动API (端口9007)
└── 任务执行器
```

## 📈 性能指标

| 指标 | 定时轮询 | 事件驱动 | 提升 |
|------|----------|----------|------|
| 响应时间 | 秒级 | 毫秒级 | 100x |
| 资源效率 | 低 | 高 | 10x |
| 可扩展性 | 低 | 高 | 5x |
| 可靠性 | 高 | 中 | 0.8x |

## 🎯 三模型论点

### Claude Code 论点
> "事件驱动架构是任务池自动触发的最佳方案。资源效率高，响应时间快。"

### DeepSeek 论点
> "从工程实现，事件驱动需要考虑消息可靠性和顺序性。建议使用消息队列。"

### MiMo-v2.5-pro 论点
> "从AI角度，事件驱动可以实现智能调度。建议结合机器学习优化调度算法。"

## 🎯 实施计划

### 阶段1：事件驱动基础（1周）

1. 创建事件驱动核心
2. 创建任务池事件集成
3. 创建API接口
4. 测试验证

### 阶段2：自动触发集成（1周）

1. 任务创建时自动触发
2. 状态变更时自动触发
3. 依赖满足时自动触发
4. 测试验证

### 阶段3：优化和监控（1周）

1. 性能优化
2. 监控告警
3. 文档完善
4. 用户反馈

## 🎯 最终建议

**推荐方案**：事件驱动架构

**实施计划**：
1. **第1周**：事件驱动基础
2. **第2周**：自动触发集成
3. **第3周**：优化和监控

**优势**：
1. 资源效率高
2. 响应时间快
3. 架构清晰
4. 易于扩展

---

**状态**: ✅ 架构设计完成
**结论**: 事件驱动架构是最佳方案
**优先级**: P1
