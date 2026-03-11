# 日志系统使用指南

## 概述

API2Cursor 内置了完整的请求日志系统，记录每个 API 请求的完整生命周期，帮助你诊断问题和监控服务状态。

## 功能特性

- **完整记录**：记录请求信息、模型映射、上游响应、token 使用等
- **文件持久化**：日志存储在 `data/logs/` 目录，按日期分文件
- **Web 界面**：通过管理面板查看、过滤、搜索和导出日志
- **自动清理**：自动删除过期日志文件
- **可配置**：支持通过 UI 调整日志行为

## 日志内容

每条日志包含以下信息：

```json
{
  "id": "uuid",
  "timestamp": "2026-03-11T10:30:45.123Z",
  "client_ip": "192.168.1.100",
  "request": {
    "model": "claude-3-5-sonnet",
    "stream": true,
    "messages": [...],
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "mapping": {
    "original_model": "claude-3-5-sonnet",
    "upstream_model": "claude-3-5-sonnet-20241022",
    "backend": "anthropic",
    "target_url": "https://api.anthropic.com"
  },
  "upstream": {
    "status_code": 200,
    "duration_ms": 1234,
    "error": null,
    "response": {...}
  },
  "tokens": {
    "prompt": 150,
    "completion": 300,
    "total": 450
  }
}
```

## 使用 Web 界面

### 1. 访问日志页面

1. 打开管理面板：`http://localhost:3029/admin`
2. 登录后点击顶部的「日志」标签

### 2. 过滤和搜索

- **模型名**：模糊搜索原始模型或上游模型名
- **状态**：筛选成功或失败的请求
- **时间范围**：今天、最近7天、最近30天或自定义
- **关键词搜索**：搜索消息内容或错误信息

### 3. 查看详情

点击日志列表中的「详情」按钮，查看完整的请求和响应内容。

### 4. 导出日志

点击「导出日志」按钮，根据当前过滤条件导出日志为 JSON 文件。

## 配置选项

在管理面板的「设置」页面，可以配置以下选项：

- **启用请求日志记录**：开关日志功能
- **日志保留天数**：超过此天数的日志自动删除（默认 30 天）
- **记录请求内容**：是否记录完整的 messages（关闭后仅记录元数据）
- **记录响应内容**：是否记录完整的响应数据

## 日志文件位置

日志文件存储在：

```
data/logs/requests-YYYY-MM-DD.jsonl
```

每行一个 JSON 对象（JSONL 格式），便于处理和分析。

## 常见问题排查

### 场景 1：请求未到达服务器

**症状**：Cursor 报错，但日志中没有记录

**可能原因**：
- 网络连接问题
- Cursor 配置的 API 地址错误
- 防火墙或代理拦截

**排查方法**：
1. 检查 Cursor 的自定义模型配置
2. 确认服务器地址和端口正确
3. 查看服务器的标准日志（非请求日志）

### 场景 2：模型映射错误

**症状**：请求到达服务器，但使用了错误的上游模型

**排查方法**：
1. 在日志详情中查看 `mapping` 字段
2. 确认 `original_model` → `upstream_model` 的转换是否正确
3. 检查管理面板中的模型映射配置

### 场景 3：上游 API 失败

**症状**：日志显示请求失败，状态码非 2xx

**排查方法**：
1. 查看 `upstream.status_code` 和 `upstream.error`
2. 检查上游 API 的可用性
3. 确认 API Key 是否有效
4. 查看请求格式是否符合上游要求

### 场景 4：响应慢

**症状**：请求成功但耗时很长

**排查方法**：
1. 按 `upstream.duration_ms` 排序，找出慢请求
2. 分析是否是特定模型的问题
3. 检查是否是特定时间段的问题
4. 考虑网络延迟或上游服务负载

## 性能影响

日志系统对性能的影响很小：

- 日志写入使用线程安全的追加模式
- JSONL 格式避免了大文件加载
- 查询时使用生成器逐行读取
- 可以通过配置关闭请求/响应内容记录来减少磁盘占用

## 安全考虑

- 日志文件存储在 `data/` 目录，不对外暴露
- 日志查询 API 需要管理员认证
- 导出功能限制文件大小（最大 50MB）
- 可以通过配置关闭敏感内容记录

## 手动清理日志

如果需要手动清理日志：

```bash
# 删除所有日志
rm -rf data/logs/*.jsonl

# 删除 30 天前的日志
find data/logs -name "requests-*.jsonl" -mtime +30 -delete
```

## API 接口

如果需要通过 API 访问日志：

```bash
# 查询日志列表
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:3029/api/admin/logs?page=1&limit=50"

# 获取单条日志详情
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:3029/api/admin/logs/{log_id}"

# 导出日志
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:3029/api/admin/logs/export?start_time=2026-03-01" \
  -o logs.json
```

## 故障排除

### 日志未记录

1. 检查日志功能是否启用（管理面板 → 设置 → 日志配置）
2. 检查 `data/logs/` 目录权限
3. 查看服务器标准日志中是否有错误信息

### 日志查询失败

1. 确认已登录管理面板
2. 检查 API Key 是否正确
3. 查看浏览器控制台的错误信息

### 日志文件过大

1. 调整日志保留天数（减少保留时间）
2. 关闭请求/响应内容记录（仅保留元数据）
3. 手动清理旧日志文件
