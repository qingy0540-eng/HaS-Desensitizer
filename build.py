#!/usr/bin/env python3
"""
打包脚本 - 将 HaS 脱敏工具打包为独立应用文件夹

用法:
    python build.py

输出:
    dist/HaS-Desensitizer/  (整个文件夹即开即用，可拷贝到其他电脑)
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

# 官方模型的 SHA-256 哈希值（来源: HuggingFace xuanwulab/HaS_Text_0209_0.6B_Q8）
# 如果模型更新，请更新此值
EXPECTED_MODEL_SHA256 = None  # 设为 None 跳过校验，设为字符串则启用


def verify_model(file_path: Path) -> bool:
    """校验模型文件完整性"""
    if EXPECTED_MODEL_SHA256 is None:
        print("  [SKIP] Model SHA-256 check disabled (EXPECTED_MODEL_SHA256 is None)")
        return True

    print("  Verifying model SHA-256...")
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()

    if actual != EXPECTED_MODEL_SHA256:
        print(f"  [FAIL] Model hash mismatch!")
        print(f"    Expected: {EXPECTED_MODEL_SHA256}")
        print(f"    Actual:   {actual}")
        return False

    print("  [OK] Model integrity verified")
    return True


def build():
    project_root = Path(__file__).parent
    backend_dir = project_root / "src" / "backend"
    static_dir = backend_dir / "static"
    model_file = project_root / "models" / "has_text_model.gguf"

    if not model_file.exists():
        print(f"[ERROR] Model file not found: {model_file}")
        print("Download the model first:")
        print("  huggingface-cli download xuanwulab/HaS_Text_0209_0.6B_Q8 has_text_model.gguf --local-dir models")
        sys.exit(1)

    # 校验模型完整性
    if not verify_model(model_file):
        print("[ERROR] Model integrity check failed. Aborting build.")
        sys.exit(1)

    model_size_mb = model_file.stat().st_size / 1024 / 1024
    print(f"Building HaS Desensitizer...")
    print(f"  Model size: {model_size_mb:.0f} MB")

    # 清理旧的构建
    for d in ["build", "dist"]:
        dpath = project_root / d
        if dpath.exists():
            shutil.rmtree(dpath)
            print(f"  Cleaned {d}/")

    # PyInstaller 参数
    # 使用 --onedir 模式：模型文件 600MB+，onefile 每次启动都要解压不现实
    # onedir 输出的整个文件夹可以直接拷贝到其他电脑使用
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", "HaS-Desensitizer",
        "--console",            # 显示控制台，方便查看状态和关闭
        "--onedir",             # 文件夹模式，方便外用
        "--clean",
        "--noconfirm",
        # 收集 llama-cpp 的所有文件（包括原生 llama.dll）
        "--collect-all", "llama_cpp",
        # 隐藏导入
        "--hidden-import", "llama_cpp",
        "--hidden-import", "fastapi",
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "pydantic",
        "--hidden-import", "starlette",
        "--hidden-import", "anyio",
        "--hidden-import", "h11",
        "--hidden-import", "click",
        "--hidden-import", "idna",
        "--hidden-import", "sniffio",
        "--hidden-import", "websockets",
        "--hidden-import", "python-docx",
        str(backend_dir / "main.py"),
    ]

    print("  Running PyInstaller...")
    result = subprocess.run(args, cwd=project_root)

    if result.returncode != 0:
        print(f"\n[ERROR] PyInstaller build failed (exit code: {result.returncode})")
        sys.exit(1)

    # --- 复制资源文件到输出目录 ---
    dist_dir = project_root / "dist" / "HaS-Desensitizer"
    print("\nCopying resource files...")

    # 复制模型文件
    model_dest = dist_dir / "models"
    model_dest.mkdir(exist_ok=True)
    shutil.copy2(model_file, model_dest / "has_text_model.gguf")
    print(f"  [OK] Model -> {model_dest / 'has_text_model.gguf'}")

    # 复制静态前端文件
    static_dest = dist_dir / "src" / "backend" / "static"
    static_dest.mkdir(parents=True, exist_ok=True)
    for f in static_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, static_dest / f.name)
    print(f"  [OK] Static files -> {static_dest}")

    # 创建启动批处理（方便用户双击启动）
    launcher = dist_dir / "启动-HaS脱敏工具.bat"
    launcher.write_text(
        '@echo off\r\n'
        'chcp 65001 >nul\r\n'
        'title HaS Desensitizer\r\n'
        'echo ==================================================\r\n'
        'echo   HaS Local Doc Desensitizer v1.0\r\n'
        'echo ==================================================\r\n'
        'echo.\r\n'
        'echo Starting...\r\n'
        'echo Browser will open http://127.0.0.1:8765\r\n'
        'echo.\r\n'
        'echo Close the console window to stop the service\r\n'
        'echo ==================================================\r\n'
        'echo.\r\n'
        'start "" /min "%~dp0HaS-Desensitizer.exe"\r\n'
        'echo Service started (running minimized)\r\n'
        'echo To stop, find the console window in taskbar and close it\r\n'
        'pause\r\n',
        encoding='utf-8'
    )
    print(f"  [OK] Launcher -> {launcher}")

    # 计算总大小
    total_size = sum(
        f.stat().st_size for f in dist_dir.rglob("*") if f.is_file()
    )
    print(f"\n{'='*50}")
    print(f"  [OK] Build complete!")
    print(f"  Output: {dist_dir}")
    print(f"  Total size: ~{total_size / 1024 / 1024:.0f} MB")
    print(f"{'='*50}")
    print(f"\nUsage:")
    print(f"  1. Copy the {dist_dir.name} folder to the target machine")
    print(f"  2. Double-click HaS-Desensitizer.exe or the .bat launcher")
    print(f"  3. Browser opens http://127.0.0.1:8765 automatically")
    print(f"\nNote: Target machine does NOT need Python or any dependencies")


if __name__ == "__main__":
    build()
