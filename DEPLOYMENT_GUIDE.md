# 部署指南

## 前后端联调成功！

### 已完成的功能

✅ **后端服务**
- FastAPI服务运行在 `http://localhost:8001`
- 所有工作流API端点已实现并测试通过
- Plan Agent、Guide Agent、Editor Agent 集成完成
- SSE流式响应支持

✅ **前端应用**
- React + Vite 应用运行在 `http://localhost:5178`
- 支持PDF上传和手动输入两种方式
- 任务进度面板显示
- 实时聊天交互
- 简历预览和导出功能

✅ **核心流程**
1. 用户上传简历或手动输入
2. 系统创建会话并生成优化计划
3. 逐个任务与Guide Agent对话
4. 查看草稿并确认执行
5. Editor Agent修改简历
6. 实时预览更新
7. 导出优化后的简历

## 快速启动

### 1. 启动后端

```bash
cd backend
python -m uvicorn api:app --reload --port 8001
```

### 2. 启动前端

```bash
cd web
npm run dev
```

### 3. 访问应用

打开浏览器访问: `http://localhost:5178`

## 测试建议

### 快速测试流程

1. **手动输入模式**（推荐用于快速测试）
   - 选择"手动输入"
   - 粘贴简历文本
   - 输入JD
   - 点击"开始优化"

2. **PDF上传模式**
   - 选择"上传PDF"
   - 上传PDF文件
   - 输入JD
   - 等待AI解析
   - 点击"开始优化"

### 测试数据

可以使用以下测试简历文本：

```
张三
邮箱: zhangsan@example.com
电话: 138****1234

工作经历：
2020-2023 ABC公司 - Python开发工程师
- 负责后端API开发
- 使用Django框架开发RESTful API
- 参与数据库设计和优化

项目经验：
电商平台后端系统
- 使用Python + Django + PostgreSQL
- 实现用户认证、订单管理等功能
- 日均处理订单1000+笔
```

JD示例：
```
招聘高级Python后端工程师，要求：
- 3年以上Python开发经验
- 熟悉微服务架构
- 有高并发系统经验
- 熟悉Docker、K8s等容器技术
```

## 已知问题和改进建议

### 当前已知问题

1. **Guide Agent响应格式**
   - 某些情况下可能返回500错误
   - 建议：增加响应格式验证和错误处理

2. **PDF解析依赖外部API**
   - 需要有效的API Key
   - 建议：添加API Key配置检查

### 改进建议

1. **用户体验优化**
   - [ ] 添加更详细的加载提示
   - [ ] 优化错误提示信息
   - [ ] 添加操作引导动画
   - [ ] 支持简历模板选择

2. **功能增强**
   - [ ] 支持会话持久化（localStorage）
   - [ ] 支持历史会话查看
   - [ ] 支持多种简历格式导出
   - [ ] 添加简历评分功能

3. **性能优化**
   - [ ] 添加请求缓存
   - [ ] 优化大文件上传
   - [ ] 实现增量更新

4. **移动端适配**
   - [ ] 优化移动端布局
   - [ ] 改进触摸交互
   - [ ] 适配小屏幕设备

## 技术栈

### 后端
- Python 3.10+
- FastAPI
- Pydantic
- OpenAI SDK (兼容API)
- PyMuPDF (PDF解析)

### 前端
- React 18
- TypeScript
- Vite
- TailwindCSS
- Framer Motion
- Radix UI

## API文档

访问 `http://localhost:8001/docs` 查看完整的API文档（Swagger UI）

## 环境变量

### 后端 (backend/parse_resume.py)
```python
API_KEY = "your-api-key"
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL = "Qwen/Qwen3-VL-8B-Instruct"
```

### 前端 (web/.env.development)
```
VITE_API_BASE=http://localhost:8001
```

## 故障排查

### 后端无法启动
- 检查Python版本 (>=3.10)
- 安装依赖: `pip install -r requirements.txt`
- 检查端口占用

### 前端无法启动
- 检查Node版本 (>=16)
- 安装依赖: `npm install`
- 清除缓存: `npm run build --clean`

### CORS错误
- 确认后端CORS配置包含前端端口
- 检查 `api.py` 中的 `allow_origins` 配置

### PDF解析失败
- 检查API Key是否有效
- 查看后端日志中的详细错误
- 尝试使用"手动输入"模式

## 下一步

1. **生产部署**
   - 配置生产环境变量
   - 设置反向代理（Nginx）
   - 启用HTTPS
   - 配置域名

2. **监控和日志**
   - 添加应用监控
   - 配置日志收集
   - 设置告警规则

3. **安全加固**
   - API认证和授权
   - 速率限制
   - 输入验证增强
   - XSS/CSRF防护

## 联系方式

如有问题，请查看：
- 后端日志: 终端4 (`terminals/4.txt`)
- 前端日志: 浏览器开发者工具Console
- API测试: 运行 `python test_api.py`
- 集成测试指南: `INTEGRATION_TEST.md`

---

**祝贺！前后端联调已成功完成！** 🎉

