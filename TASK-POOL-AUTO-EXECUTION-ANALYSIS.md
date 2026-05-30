# 任务池自动执行机制分析

## 📋 当前状态

### 自动执行机制

| 组件 | 功能 | 状态 |
|------|------|------|
| autorun-runner | 自动执行运行器 | ✅ 已实现 |
| auto-claim-and-handoff | 自动认领和交接 | ✅ 已实现 |
| brain_task_autorun_step.py | 自动执行步骤 | ✅ 已实现 |
| brain_task_dispatch_tick.py | 调度tick | ✅ 已实现 |

### 自动执行流程

```
任务池
    ↓
调度tick (brain_task_dispatch_tick.py)
    ↓
自动认领 (auto-claim-and-handoff)
    ↓
自动执行 (autorun-runner)
    ↓
结果验证
    ↓
状态更新
```

## 🎯 自动执行机制详解

### 1. 调度tick (brain_task_dispatch_tick.py)

**功能**：
- 摄取Obsidian收件箱草稿到规范任务笔记
- 调和过期租约/过期任务/到期重试
- 重新生成派生仪表盘
- 为下一个可调度任务发出调度提示
- 记录JSONL证明日志

**触发方式**：
- 手动触发
- 定时触发（cron）
- 事件触发

**示例**：
```bash
# 手动触发
python3 ~/.hermes/scripts/brain_task_dispatch_tick.py

# 定时触发（cron）
0 * * * * python3 ~/.hermes/scripts/brain_task_dispatch_tick.py
```

### 2. 自动认领 (auto-claim-and-handoff)

**功能**：
- 自动认领待处理任务
- 自动分配给合适的Agent
- 自动交接任务

**触发方式**：
- 手动触发
- 调度tick触发

**示例**：
```bash
# 手动触发
python3 ~/.hermes/scripts/brain_task_orchestrator.py auto-claim-and-handoff

# 指定任务
python3 ~/.hermes/scripts/brain_task_orchestrator.py auto-claim-and-handoff --task "任务ID"
```

### 3. 自动执行 (autorun-runner)

**功能**：
- 自动执行已认领的任务
- 执行预定义的命令
- 验证执行结果

**触发方式**：
- 手动触发
- 调度tick触发

**示例**：
```bash
# 手动触发
python3 ~/.hermes/scripts/brain_task_orchestrator.py autorun-runner

# 指定任务
python3 ~/.hermes/scripts/brain_task_orchestrator.py autorun-runner --task "任务ID"
```

### 4. 自动执行步骤 (brain_task_autorun_step.py)

**功能**：
- 有界本地大脑自动执行步骤
- 结合提示/摘要调度与有界执行
- 从不解析任务笔记正文中的命令
- 仅运行此文件注册表中的静态命令ID

**命令注册表**：
```python
COMMAND_REGISTRY = {
    "noop": ["python3", "-c", "print('noop PASS')"],
    "fail": ["python3", "-c", "raise SystemExit(7)"],
    "py_compile_taskpool": ["python3", "-m", "py_compile", "scripts/brain_task_orchestrator.py"],
    "test_brain_task_dispatch_tick": ["python3", "scripts/test_brain_task_dispatch_tick.py"],
}
```

## 📊 自动执行配置

### 1. 策略文件

**位置**：`~/.hermes/state/auto_run_policy.json`

**内容**：
```json
{
  "enabled": true,
  "allowed_tasks": ["task-id-1", "task-id-2"],
  "allowed_profiles": ["default"],
  "allowed_commands": ["noop", "py_compile_taskpool"],
  "allowed_workspaces": ["/Users/charles/hermes-edge-worker"]
}
```

### 2. 状态文件

**位置**：`~/.hermes/state/brain_task_dispatch_tick_state.json`

**内容**：
```json
{
  "last_tick": "2026-05-31T03:40:00+08:00",
  "tick_count": 100,
  "last_task": "task-id",
  "errors": []
}
```

### 3. 日志文件

**位置**：`~/.hermes/logs/brain_task_dispatch_tick.jsonl`

**内容**：
```json
{"timestamp": "2026-05-31T03:40:00+08:00", "event": "tick_start", "task_id": "task-id"}
{"timestamp": "2026-05-31T03:40:01+08:00", "event": "task_claimed", "task_id": "task-id"}
{"timestamp": "2026-05-31T03:40:02+08:00", "event": "task_executed", "task_id": "task-id"}
{"timestamp": "2026-05-31T03:40:03+08:00", "event": "tick_end", "task_id": "task-id"}
```

## 🎯 自动执行触发方式

### 1. 手动触发

```bash
# 运行调度tick
python3 ~/.hermes/scripts/brain_task_dispatch_tick.py

# 自动认领和交接
python3 ~/.hermes/scripts/brain_task_orchestrator.py auto-claim-and-handoff

# 自动执行
python3 ~/.hermes/scripts/brain_task_orchestrator.py autorun-runner
```

### 2. 定时触发（cron）

```bash
# 每小时运行一次调度tick
0 * * * * python3 ~/.hermes/scripts/brain_task_dispatch_tick.py

# 每5分钟运行一次自动认领
*/5 * * * * python3 ~/.hermes/scripts/brain_task_orchestrator.py auto-claim-and-handoff

# 每10分钟运行一次自动执行
*/10 * * * * python3 ~/.hermes/scripts/brain_task_orchestrator.py autorun-runner
```

### 3. 事件触发

```bash
# 任务创建时触发
python3 ~/.hermes/scripts/brain_task_orchestrator.py add "任务标题" --priority P2

# 任务状态变更时触发
python3 ~/.hermes/scripts/brain_task_orchestrator.py transition "任务ID" --to running
```

## 📈 自动执行监控

### 1. 查看自动执行状态

```bash
# 查看调度tick状态
cat ~/.hermes/state/brain_task_dispatch_tick_state.json

# 查看自动执行日志
tail -f ~/.hermes/logs/brain_task_dispatch_tick.jsonl
```

### 2. 查看任务池状态

```bash
# 查看任务池仪表盘
python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard

# 查看待处理任务
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --status pending
```

### 3. 查看自动执行指标

```bash
# 查看自动执行指标
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck
```

## 🎯 三模型论点

### Claude Code 论点
> "任务池自动执行机制已实现，但需要配置策略文件和定时任务。建议配置cron定时触发。"

### DeepSeek 论点
> "从工程实现，自动执行需要考虑安全性和可靠性。建议使用有界执行和策略文件。"

### MiMo-v2.5-pro 论点
> "从AI角度，自动执行需要考虑任务优先级和资源分配。建议使用智能调度算法。"

## 🎯 最终建议

### 立即行动

1. **配置策略文件**
   ```bash
   # 创建策略文件
   cat > ~/.hermes/state/auto_run_policy.json << 'EOF'
   {
     "enabled": true,
     "allowed_tasks": [],
     "allowed_profiles": ["default"],
     "allowed_commands": ["noop", "py_compile_taskpool"],
     "allowed_workspaces": ["/Users/charles/hermes-edge-worker"]
   }
   EOF
   ```

2. **配置定时任务**
   ```bash
   # 添加cron定时任务
   crontab -e
   # 添加以下内容：
   # 每小时运行一次调度tick
   0 * * * * python3 ~/.hermes/scripts/brain_task_dispatch_tick.py
   ```

3. **测试自动执行**
   ```bash
   # 手动触发调度tick
   python3 ~/.hermes/scripts/brain_task_dispatch_tick.py
   
   # 查看自动执行状态
   cat ~/.hermes/state/brain_task_dispatch_tick_state.json
   ```

### 短期计划

1. **完善自动执行机制**
   - 添加更多命令到注册表
   - 优化调度算法
   - 完善监控告警

2. **集成到Hermes**
   - 集成到Hermes工作流
   - 添加自动执行技能
   - 完善文档

### 中期计划

1. **智能调度**
   - 基于优先级的调度
   - 基于资源的调度
   - 基于依赖的调度

2. **自动优化**
   - 基于执行结果的优化
   - 基于性能指标的优化
   - 基于用户反馈的优化

---

**状态**: ✅ 分析完成
**结论**: 任务池自动执行机制已实现，需要配置和优化
**优先级**: P1
