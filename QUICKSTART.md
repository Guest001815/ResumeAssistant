# 🚀 快速启动指南

## 前后端联调已完成！立即开始使用

### 📋 前置条件

- Python 3.10+
- Node.js 16+
- 已安装依赖

### ⚡ 三步启动

#### 1️⃣ 启动后端 (终端1)

```bash
cd backend
python -m uvicorn api:app --reload --port 8001
```

✅ 看到以下输出表示成功：
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete.
```

#### 2️⃣ 启动前端 (终端2)

```bash
cd web
npm run dev
```

✅ 看到以下输出表示成功：
```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:5178/
```

#### 3️⃣ 打开浏览器

访问: **http://localhost:5178**

## 🎯 快速测试

### 方式1: 手动输入（推荐用于快速测试）

1. 选择"手动输入"标签
2. 粘贴以下测试简历：

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
```

3. 输入JD：
```
招聘高级Python后端工程师，要求3年以上经验，熟悉微服务架构
```

4. 点击"开始优化"

### 方式2: PDF上传

1. 选择"上传PDF"标签
2. 上传你的PDF简历
3. 输入职位描述
4. 点击"开始优化"

## 📊 预期结果

### 成功标志

✅ 进入工作区界面
✅ 顶部显示任务进度面板
✅ 左侧显示AI助手对话
✅ 右侧显示简历预览
✅ 可以与AI对话优化简历

### 完整流程

```
上传简历 → 生成任务计划 → 与AI对话 → 查看草稿 → 确认执行 → 查看结果 → 导出简历
```

## 🔧 故障排查

### 后端无法启动？

```bash
# 检查端口占用
netstat -ano | findstr :8001

# 使用其他端口
python -m uvicorn api:app --reload --port 8002
```

### 前端无法启动？

```bash
# 清除缓存重新安装
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### CORS错误？

确认后端 `api.py` 中的CORS配置包含前端端口：
```python
allow_origins=["http://localhost:5173", "http://localhost:5178"]
```

### PDF解析失败？

1. 检查API Key是否配置（`backend/parse_resume.py`）
2. 使用"手动输入"模式作为备选

## 📚 更多文档

- **集成测试**: `INTEGRATION_TEST.md`
- **部署指南**: `DEPLOYMENT_GUIDE.md`
- **完整报告**: `README_INTEGRATION.md`
- **实施总结**: `IMPLEMENTATION_SUMMARY.md`

## 🎉 开始使用

现在你可以：
- ✅ 上传简历或手动输入
- ✅ 与AI助手对话优化内容
- ✅ 实时预览修改结果
- ✅ 导出优化后的简历

**祝使用愉快！** 🚀

---

**服务地址**:
- 后端: http://localhost:8001
- 前端: http://localhost:5178
- API文档: http://localhost:8001/docs

**当前状态**: ✅ 所有功能正常

