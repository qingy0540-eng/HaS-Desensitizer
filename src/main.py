#!/usr/bin/env python3
"""
HaS 本地文档脱敏工具
基于 HaS_Text_0209_0.6B_Q8 模型的端侧隐私保护应用

功能:
- 输入待脱敏文档（粘贴或拖入文件）
- 本地推理，数据不离开设备
- 输出语义化标签脱敏文本
- 支持 10 种敏感实体类型

用法:
    python src/main.py
"""
import sys
from pathlib import Path

# 确保 src 在路径中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ui.app import main

if __name__ == "__main__":
    main()
