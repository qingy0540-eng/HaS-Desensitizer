# HaS-Desensitizer

本地文档脱敏工具 —— 基于 [HaS_Text_0209_0.6B_Q8](https://huggingface.co/xuanwulab/HaS_Text_0209_0.6B_Q8) 模型的端侧隐私保护应用。

## 特性

- **本地推理**：数据全程不离开设备，无需联网
- **语义标签**：使用 `<EntityType[ID].Attribute>` 格式替换敏感信息，可逆还原
- **10 种实体类型**：姓名、电话、身份证、邮箱、地址、公司、银行卡、金额、IP、密码
- **文件支持**：.txt / .md / .csv / .json / .xml / .py / .js / .java / .go / .rs / .html / .css / .sql / .log / .docx
- **双版本**：Web 版（FastAPI 后端 + 浏览器前端）和桌面版（CustomTkinter GUI）
- **安全加固**：Prompt Injection 防护、CSRF 保护、速率限制、XSS 防御

## 快速开始

### 1. 下载模型

```bash
huggingface-cli download xuanwulab/HaS_Text_0209_0.6B_Q8 has_text_model.gguf --local-dir models
```

或从 [HuggingFace](https://huggingface.co/xuanwulab/HaS_Text_0209_0.6B_Q8) 手动下载 `has_text_model.gguf` 放到 `models/` 目录。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动应用

**Web 版**（推荐）：
```bash
python src/backend/main.py
```
浏览器自动打开 `http://127.0.0.1:8765`

**桌面版**：
```bash
python src/main.py
```

### 4. 使用

1. 粘贴待脱敏文本，或点击"打开文件"导入
2. 选择需要脱敏的实体类型
3. 点击"开始脱敏"
4. 复制结果或导出文件

## 打包为可执行文件

```bash
python build.py
```

输出：`dist/HaS-Desensitizer/` —— 整个文件夹可直接拷贝到其他电脑使用，无需安装 Python。

## 项目结构

```
HaS-Desensitizer/
├── src/
│   ├── main.py                 # 桌面 GUI 入口
│   ├── ui/
│   │   └── app.py              # CustomTkinter 界面
│   ├── core/
│   │   ├── desensitizer.py     # HaS 模型推理引擎（NER + 标签替换）
│   │   └── file_handler.py     # 文件读写
│   └── backend/
│       ├── main.py             # FastAPI Web 后端
│       └── static/
│           └── index.html      # Web 前端页面
├── models/                     # 模型文件（需自行下载）
├── requirements.txt
├── build.py                    # PyInstaller 打包脚本
└── LICENSE
```

## 模型信息

- **名称**：HaS_Text_0209_0.6B_Q8
- **来源**：腾讯玄武实验室 (xuanwulab)
- **架构**：基于 Qwen3-0.6B
- **量化**：Q8_0 (8.50 BPW)
- **大小**：约 610MB
- **许可**：Apache-2.0

## 许可

本项目基于 Apache License 2.0 开源。HaS 模型版权归腾讯玄武实验室所有。

## 安全

本项目已通过安全审计，修复了以下关键问题：
- Prompt Injection 防护（结构化 prompt + 输入转义）
- CSRF 保护（Origin 头校验）
- API 速率限制（IP 级别，60s/5次）
- 前端 XSS 防御（DOM API 替代 innerHTML）
- 路径遍历防护（路径规范化验证）
- MIME 类型白名单检查

详见审计报告。
