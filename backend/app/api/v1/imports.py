from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_perm
from app.core.database import get_db
from app.core.exceptions import BizError
from app.core.response import ok
from app.services.import_service import ImportService, ImportTemplate
from app.services.permission_service import AuthContext

router = APIRouter(tags=["数据导入"])

_MAX_UPLOAD_SIZE = 10 * 1024 * 1024
_ALLOWED_SUFFIX = ".xlsx"


async def _read_upload(file: UploadFile) -> bytes:
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(_ALLOWED_SUFFIX):
        raise BizError("仅支持 .xlsx 格式的 Excel 文件，请使用模板导入")
    content = await file.read()
    if not content:
        raise BizError("上传文件为空")
    if len(content) > _MAX_UPLOAD_SIZE:
        raise BizError("上传文件不能超过 10MB")
    return content


def _template_response(template: ImportTemplate) -> Response:
    return Response(
        content=template.content,
        media_type=template.media_type,
        headers={
            "Content-Disposition": (
                "attachment; filename=\"import_template.xlsx\"; "
                f"filename*=UTF-8''{quote(template.filename)}"
            ),
            "Content-Length": str(len(template.content)),
        },
    )


@router.get("/imports/asset-categories/template", summary="下载资产分类导入模板")
async def download_category_template(
    _context: AuthContext = Depends(require_perm("asset:category:create")),
):
    return _template_response(ImportService.template_categories())


@router.post("/imports/asset-categories", summary="导入资产分类")
async def import_categories(
    file: UploadFile = File(...),
    context: AuthContext = Depends(require_perm("asset:category:create")),
    session: AsyncSession = Depends(get_db),
):
    content = await _read_upload(file)
    result = await ImportService(session).import_categories(content, context)
    return ok(
        {
            "total": result.total,
            "success": result.success,
            "failed": result.failed,
            "errors": result.errors,
        },
        message=f"导入完成：成功 {result.success} 条，失败 {result.failed} 条",
    )


@router.get("/imports/users/template", summary="下载用户导入模板")
async def download_user_template(
    _context: AuthContext = Depends(require_perm("system:user:create")),
):
    return _template_response(ImportService.template_users())


@router.post("/imports/users", summary="导入用户")
async def import_users(
    file: UploadFile = File(...),
    context: AuthContext = Depends(require_perm("system:user:create")),
    session: AsyncSession = Depends(get_db),
):
    content = await _read_upload(file)
    result = await ImportService(session).import_users(content, context)
    return ok(
        {
            "total": result.total,
            "success": result.success,
            "failed": result.failed,
            "errors": result.errors,
        },
        message=f"导入完成：成功 {result.success} 条，失败 {result.failed} 条",
    )


@router.get("/imports/assets/template", summary="下载资产导入模板")
async def download_asset_template(
    _context: AuthContext = Depends(require_perm("asset:ledger:create")),
):
    return _template_response(ImportService.template_assets())


@router.post("/imports/assets", summary="导入资产")
async def import_assets(
    file: UploadFile = File(...),
    context: AuthContext = Depends(require_perm("asset:ledger:create")),
    session: AsyncSession = Depends(get_db),
):
    content = await _read_upload(file)
    result = await ImportService(session).import_assets(content, context)
    return ok(
        {
            "total": result.total,
            "success": result.success,
            "failed": result.failed,
            "errors": result.errors,
        },
        message=f"导入完成：成功 {result.success} 条，失败 {result.failed} 条",
    )
