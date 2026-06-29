#!/usr/bin/env python3
"""
改进点：
- 使用 logging 替代 print
- 使用 FastAPI 的 CORSMiddleware 替代手工 Origin 检查
- 在文件上传时尽早检查大小并返回 413
- 将开发中基于内存的速率限制标注为仅开发用
- 接入 core.desensitizer.HaSDesensitizer 实际脱敏逻辑（在启动时初始化）
"""
import json
import os
import threading
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import status

# 导入核心脱敏实现
from src.core.desensitizer import (
    ENTITY_ATTR_MAP,
    HaSDesensitizer,
    _deduplicate_entities,
    replace_with_tags,
)

# --- 配置 logging ---
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("has_desensitizer")

app = FastAPI(title="HaS Desensitizer")

# --- CORS: 使用可配置的 ALLOWED_ORIGINS 环境变量（逗号分隔） ---
raw_allowed = os.environ.get("ALLOWED_ORIGINS")
if raw_allowed:
    allowed_origins = [o.strip() for o in raw_allowed.split(",") if o.strip()]
else:
    # 默认仅允许本地开发地址
    allowed_origins = [
        "http://127.0.0.1:8765",
        "http://localhost:8765",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 简单的内存速率限制（仅开发用） ---
# 注意：该实现为单进程内存级别，不能用于多进程/多副本生产环境
RATE_LIMIT_STORE: Dict[str, List[float]] = {}
RATE_LIMIT_LOCK = threading.Lock()
RATE_LIMIT_MAX = int(os.environ.get("RATE_LIMIT_MAX", "60"))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))


def is_rate_limited(client_ip: str) -> bool:
    now = time.time()
    with RATE_LIMIT_LOCK:
        stamps = RATE_LIMIT_STORE.setdefault(client_ip, [])
        # 丢弃过期时间戳
        while stamps and stamps[0] <= now - RATE_LIMIT_WINDOW:
            stamps.pop(0)
        if len(stamps) >= RATE_LIMIT_MAX:
            return True
        stamps.append(now)
        return False


# --- 文件上传大小限制（字节） ---
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 默认 10MB
ALLOWED_MIME_TYPES = {
    "text/plain", "text/markdown", "text/csv", "application/json",
    "application/xml", "text/xml", "text/html", "text/css",
    "application/javascript", "text/javascript",
}
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".xml", ".py", ".js", ".java",
    ".c", ".cpp", ".go", ".rs", ".ts", ".html", ".css", ".sql", ".log",
}

# 全局脱敏器实例（在启动时初始化）
DES: Optional[HaSDesensitizer] = None


def _json_safe(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _desensitize_payload(text: str, entity_types: Optional[list[str]] = None) -> dict:
    if DES is None:
        logger.error("Desensitizer not loaded")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="service not ready")

    entities = DES.scan_entities(text, entity_types=entity_types)
    entities = _deduplicate_entities(entities)
    desensitized = replace_with_tags(text, entities, ENTITY_ATTR_MAP)
    return _json_safe({
        "original": text,
        "desensitized": desensitized,
        "entities": entities,
        "entity_count": len(entities),
    })


@app.on_event("startup")
async def startup_event():
    global DES
    model_path = os.environ.get("MODEL_PATH")
    try:
        logger.info("Initializing HaSDesensitizer (model_path=%s)...", model_path)
        DES = HaSDesensitizer(model_path=model_path)
        logger.info("HaSDesensitizer initialized")
    except Exception:
        logger.exception("Failed to initialize HaSDesensitizer on startup")
        # 不阻塞启动，但后续调用会返回 503


@app.get("/", response_class=HTMLResponse)
async def index():
    # 尽量返回前端 index 内容（保留原有行为）
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>HaS Desensitizer</h1>")


@app.post("/api/desensitize")
async def api_desensitize(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(client_ip):
        logger.warning("Rate limited request from %s", client_ip)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    if DES is None:
        logger.error("Desensitizer not loaded")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="service not ready")

    try:
        payload = await request.json()
    except Exception:
        logger.exception("Invalid JSON in request")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    text = (payload.get("text") or "").strip()
    if not text:
        return JSONResponse({"error": "empty text"}, status_code=400)

    entity_types = payload.get("entity_types")

    try:
        # 调用核心脱敏逻辑
        return JSONResponse(_desensitize_payload(text, entity_types=entity_types))
    except Exception:
        logger.exception("Desensitization failed")
        raise HTTPException(status_code=500, detail="internal error")


@app.post("/api/desensitize-file")
async def api_desensitize_file(
    request: Request,
    file: UploadFile = File(...),
    entity_types: Optional[str] = Form(None),
):
    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(client_ip):
        logger.warning("Rate limited file upload from %s", client_ip)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    if DES is None:
        logger.error("Desensitizer not loaded")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="service not ready")

    # 早期检查文件大小：使用 underlying file-like 对象的 tell/seek
    try:
        uploaded_file = file.file
        current = uploaded_file.tell()
        uploaded_file.seek(0, os.SEEK_END)
        size = uploaded_file.tell()
        uploaded_file.seek(current, os.SEEK_SET)
    except Exception:
        # 如果无法获取大小，作为保护，拒绝上载
        logger.exception("Could not determine uploaded file size")
        raise HTTPException(status_code=400, detail="Could not determine file size")

    if size > MAX_FILE_SIZE:
        logger.info("Rejected upload: size %d exceeds limit %d", size, MAX_FILE_SIZE)
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="file too large")

    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {ext}")

    content_type = file.content_type or ""
    if content_type and content_type not in ALLOWED_MIME_TYPES and content_type != "application/octet-stream":
        raise HTTPException(status_code=400, detail=f"unsupported content type: {content_type}")

    try:
        content_bytes = await file.read()
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("Uploaded file is not valid UTF-8")
            raise HTTPException(status_code=400, detail="Uploaded file must be UTF-8 text")

        try:
            types = json.loads(entity_types) if entity_types else None
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid entity_types")
        return JSONResponse(_desensitize_payload(text, entity_types=types))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to process uploaded file")
        raise HTTPException(status_code=500, detail="internal error")


@app.get("/api/status")
async def api_status():
    # 返回一些运行时状态（不要泄露敏感信息）
    try:
        model_loaded = False
        if DES is not None:
            try:
                # 如果有属性或方法可用于检测模型加载状态，可替换下面逻辑
                model_loaded = True
            except Exception:
                model_loaded = False
        return JSONResponse({
            "model_loaded": model_loaded,
            "mode": os.environ.get("APP_MODE", "dev"),
        })
    except Exception:
        logger.exception("Status check failed")
        raise HTTPException(status_code=500, detail="internal error")


def main():
    # 用 logging 替代 print
    logger.info("Starting HaS Desensitizer app")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8765"))
    logger.info("Host: %s, Port: %s", host, port)

    try:
        import uvicorn

        uvicorn.run("src.backend.main:app", host=host, port=port, log_level="info")
    except Exception:
        logger.exception("Failed to start server")


if __name__ == "__main__":
    main()
