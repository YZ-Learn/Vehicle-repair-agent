# 🔧 车辆维修智能助手

面向维修工程师的 AI 客服系统。输入车辆故障现象或故障码，Agent 自动检索知识库、调用工具，给出诊断建议和维修方案。

## 在线体验

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://vehicle-repair.streamlit.app)

> 扫码或点击上方按钮使用

## 本地运行

### 环境要求
- Python 3.10+
- 安装依赖

```bash
cd 项目目录
pip install -r requirements.txt
```

### 配置 API Key

编辑 `config/model.yml`，填入你的 DeepSeek API Key。

或者设置环境变量：

```bash
set DEEPSEEK_API_KEY=sk-xxx
```

### 导入知识库（首次运行）

```bash
python run.py ingest
```

### 启动

```bash
python run.py start
```

浏览器自动打开 http://localhost:8501

## 知识库管理

知识库文件在 `knowledge/` 目录下，目前包含 6 篇车辆维修文档：

- 发动机系统维修指南
- 制动系统维修指南
- 电气系统维修指南
- 变速箱系统维修指南
- 空调系统维修指南
- 底盘悬挂系统维修指南

### 更新知识库

1. 在 `knowledge/` 中添加或修改 `.md` 文件
2. 运行 `python run.py ingest` 重新导入

## 技术架构

```
前端 (Streamlit) → Agent (多步推理) → 工具集 + RAG 检索 → DeepSeek 大模型
                    ↓
                SQLite 对话历史  |  Chroma 向量知识库
```

## 部署到 Streamlit Cloud

1. 将本项目推送到 GitHub 仓库
2. 打开 https://share.streamlit.io
3. 用 GitHub 登录，选择本仓库
4. 在 Deploy 页面设置 Secrets：
   - Key: `DEEPSEEK_API_KEY`
   - Value: 你的 DeepSeek API Key
5. 点击 Deploy，等待 2-3 分钟
6. 得到一个公开 URL，如 `your-app-name.streamlit.app`

> **首次访问等待约 30-60 秒**（模型下载 + 知识库构建），后续访问即开即用。

## 许可证

MIT
