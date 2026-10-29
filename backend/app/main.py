import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.context import (
    client_ip_ctx,
    request_id_ctx,
    request_method_ctx,
    request_path_ctx,
    user_agent_ctx,
)
from app.core.database import dispose_engine, get_db
from app.core.exceptions import BizError
from app.core.response import fail, ok
from app.core.token_store import close_token_store
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("itam")


@asynccontextmanager
async def lifespan(_: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    if settings.APP_ENV == "production" and (
        settings.SECRET_KEY.startswith("itam-dev") or "change_me" in settings.SECRET_KEY
    ):
        logger.warning("SECRET_KEY 仍为默认值，请立即在 .env 中更换！")
    logger.info("ITAM backend started (env=%s)", settings.APP_ENV)
    yield
    await close_token_store()
    await dispose_engine()
    logger.info("ITAM backend stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="IT 资产管理系统后端 API（统一响应：code/message/data）",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "")
    )
    context_tokens = [
        (request_id_ctx, request_id_ctx.set(request_id)),
        (client_ip_ctx, client_ip_ctx.set(client_ip)),
        (user_agent_ctx, user_agent_ctx.set(request.headers.get("user-agent", ""))),
        (request_method_ctx, request_method_ctx.set(request.method)),
        (request_path_ctx, request_path_ctx.set(request.url.path)),
    ]
    try:
        response = await call_next(request)
    finally:
        for var, token in reversed(context_tokens):
            var.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(BizError)
async def biz_error_handler(request: Request, exc: BizError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=fail(exc.code, exc.message, exc.data),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = jsonable_encoder(exc.errors())
    messages = []
    for item in exc.errors():
        location = ".".join(str(part) for part in item.get("loc", []) if part != "body")
        message = item.get("msg", "参数错误")
        messages.append(f"{location}: {message}" if location else message)
    return JSONResponse(
        status_code=422,
        content=fail(42200, messages[0] if messages else "参数校验失败", {"errors": errors}),
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(exc.status_code * 100, message),
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(StaleDataError)
async def stale_data_handler(request: Request, exc: StaleDataError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=fail(40901, "数据已被他人修改，请刷新后重试"),
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=409,
        content=fail(40902, "数据冲突：唯一字段已被占用或存在关联限制"),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    data = {"request_id": request_id_ctx.get()}
    if settings.APP_ENV != "production":
        data["detail"] = str(exc)
    return JSONResponse(
        status_code=500,
        content=fail(50000, "服务器内部错误，请稍后重试或联系管理员", data),
    )


@app.get("/", include_in_schema=False)
async def root():
    return ok({"name": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/api/docs"})


@app.get("/health", tags=["系统"], summary="健康检查")
async def health(session: AsyncSession = Depends(get_db)):
    try:
        await session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        logger.exception("Health check failed: database unavailable")
        return JSONResponse(
            status_code=503,
            content=fail(50300, "数据库不可用", {"database": "down"}),
        )
    return ok(
        {
            "status": "ok",
            "database": database,
            "env": settings.APP_ENV,
            "version": settings.APP_VERSION,
        }
    )


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
