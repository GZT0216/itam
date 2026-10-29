from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizError, ConflictError, NotFoundError
from app.models import AssetCategory, AssetCategoryField, AssetModel
from app.repositories.asset_repo import (
    AssetCategoryRepository,
    AssetModelRepository,
)
from app.schemas.asset import (
    CategoryCreate,
    CategoryFieldCreate,
    CategoryFieldOut,
    CategoryFieldUpdate,
    CategoryOut,
    CategoryUpdate,
    ModelCreate,
    ModelOut,
    ModelPageOut,
    ModelUpdate,
)
from app.services.audit_service import AuditService
from app.services.permission_service import AuthContext
from app.services.txn import commit_or_conflict


def _category_snapshot(category: AssetCategory) -> dict[str, object]:
    return {
        "parent_id": category.parent_id,
        "name": category.name,
        "code": category.code,
        "category_type": category.category_type,
        "path": category.path,
        "level": category.level,
        "sort": category.sort,
        "safety_stock": category.safety_stock,
        "status": category.status,
        "remark": category.remark,
        "version": category.version,
    }


def _field_snapshot(field: AssetCategoryField) -> dict[str, object]:
    return {
        "name": field.name,
        "field_key": field.field_key,
        "field_type": field.field_type,
        "required": field.required,
        "options": field.options,
        "sort": field.sort,
        "status": field.status,
        "remark": field.remark,
        "version": field.version,
    }


def _field_out(field: AssetCategoryField) -> CategoryFieldOut:
    return CategoryFieldOut(
        id=field.id,
        category_id=field.category_id,
        name=field.name,
        field_key=field.field_key,
        field_type=field.field_type,
        required=field.required,
        options=field.options,
        sort=field.sort,
        status=field.status,
        remark=field.remark,
        version=field.version,
    )


def _category_out(
    category: AssetCategory,
    *,
    model_count: int = 0,
    asset_count: int = 0,
) -> CategoryOut:
    return CategoryOut(
        id=category.id,
        parent_id=category.parent_id,
        name=category.name,
        code=category.code,
        category_type=category.category_type,
        path=category.path,
        level=category.level,
        sort=category.sort,
        safety_stock=category.safety_stock,
        status=category.status,
        remark=category.remark,
        version=category.version,
        model_count=model_count,
        asset_count=asset_count,
        field_defs=[_field_out(item) for item in category.field_defs],
    )


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.categories = AssetCategoryRepository(session)
        self.models = AssetModelRepository(session)
        self.audit = AuditService(session)

    async def tree(self, context: AuthContext) -> list[CategoryOut]:
        categories = await self.categories.list_all()
        model_counts = await self.categories.model_counts()
        asset_counts = await self.categories.asset_counts()

        nodes = {
            category.id: _category_out(
                category,
                model_count=model_counts.get(category.id, 0),
                asset_count=asset_counts.get(category.id, 0),
            )
            for category in categories
        }
        roots: list[CategoryOut] = []
        for category in categories:
            node = nodes[category.id]
            if category.parent_id and category.parent_id in nodes:
                nodes[category.parent_id].children.append(node)
            else:
                roots.append(node)
        self._sort_tree(roots)
        return roots

    @staticmethod
    def _sort_tree(nodes: list[CategoryOut]) -> None:
        nodes.sort(key=lambda item: (item.sort, item.id))
        for node in nodes:
            CategoryService._sort_tree(node.children)

    async def _get_or_error(self, category_id: int) -> AssetCategory:
        category = await self.categories.get(category_id)
        if category is None:
            raise NotFoundError("资产分类不存在")
        return category

    async def create(self, payload: CategoryCreate, context: AuthContext) -> CategoryOut:
        if await self.categories.get_by_code(payload.code):
            raise ConflictError("分类编码已存在", code=40920)

        parent: AssetCategory | None = None
        if payload.parent_id is not None:
            parent = await self._get_or_error(payload.parent_id)
            if parent.status != 1:
                raise BizError("上级分类已停用，无法新增下级分类")
            category_type = parent.category_type
        else:
            if not payload.category_type:
                raise BizError("根分类必须选择资产类型")
            category_type = payload.category_type

        category = AssetCategory(
            parent_id=parent.id if parent else None,
            name=payload.name,
            code=payload.code,
            category_type=category_type,
            path="",
            level=1,
            sort=payload.sort,
            safety_stock=payload.safety_stock,
            status=payload.status,
            remark=payload.remark,
            field_defs=[],
        )
        self.session.add(category)
        await self.session.flush()
        category.path = f"{parent.path if parent else '/'}{category.id}/"
        category.level = (parent.level + 1) if parent else 1

        await self.audit.record(
            action="asset.category.create",
            module="资产分类",
            summary=f"新增资产分类：{category.name}",
            actor=context.user,
            resource_type="asset_category",
            resource_id=category.id,
            after=_category_snapshot(category),
        )
        await commit_or_conflict(self.session)
        return _category_out(category)

    async def update(
        self,
        category_id: int,
        payload: CategoryUpdate,
        context: AuthContext,
    ) -> CategoryOut:
        category = await self._get_or_error(category_id)
        if category.version != payload.version:
            raise ConflictError("分类信息已被他人修改，请刷新后重试")

        duplicate = await self.categories.get_by_code(payload.code)
        if duplicate is not None and duplicate.id != category.id:
            raise ConflictError("分类编码已存在", code=40920)

        parent: AssetCategory | None = None
        if payload.parent_id is not None:
            if payload.parent_id == category.id:
                raise BizError("上级分类不能选择自身")
            parent = await self._get_or_error(payload.parent_id)
            if parent.path.startswith(category.path):
                raise BizError("上级分类不能选择当前分类的下级分类")
            if parent.status != 1:
                raise BizError("上级分类已停用，无法挂载下级分类")
            category_type = parent.category_type
        else:
            category_type = payload.category_type or category.category_type

        before = _category_snapshot(category)
        all_categories = await self.categories.list_all()
        old_path = category.path
        old_level = category.level
        type_changed = category_type != category.category_type

        category.parent_id = parent.id if parent else None
        category.name = payload.name
        category.code = payload.code
        category.category_type = category_type
        category.sort = payload.sort
        category.safety_stock = payload.safety_stock
        category.status = payload.status
        category.remark = payload.remark
        category.path = f"{parent.path if parent else '/'}{category.id}/"
        category.level = (parent.level + 1) if parent else 1

        if category.path != old_path or category.level != old_level:
            level_delta = category.level - old_level
            for item in all_categories:
                if item.id == category.id or not item.path.startswith(old_path):
                    continue
                item.path = category.path + item.path[len(old_path) :]
                item.level = max(1, item.level + level_delta)
        if type_changed:
            descendants = [
                item
                for item in all_categories
                if item.id != category.id and item.path.startswith(category.path)
            ]
            for item in descendants:
                item.category_type = category_type

        await self.audit.record(
            action="asset.category.update",
            module="资产分类",
            summary=f"编辑资产分类：{category.name}",
            actor=context.user,
            resource_type="asset_category",
            resource_id=category.id,
            before=before,
            after=_category_snapshot(category),
        )
        await commit_or_conflict(self.session)
        model_counts = await self.categories.model_counts()
        asset_counts = await self.categories.asset_counts()
        return _category_out(
            category,
            model_count=model_counts.get(category.id, 0),
            asset_count=asset_counts.get(category.id, 0),
        )

    async def delete(self, category_id: int, context: AuthContext) -> None:
        category = await self._get_or_error(category_id)
        if await self.categories.count_children(category.id):
            raise BizError("该分类存在下级分类，无法删除")
        if await self.categories.count_models(category.id):
            raise BizError("该分类下仍有型号，无法删除")
        if await self.categories.count_assets(category.id):
            raise BizError("该分类下仍有资产，无法删除")

        before = _category_snapshot(category)
        await self.session.delete(category)
        await self.audit.record(
            action="asset.category.delete",
            module="资产分类",
            summary=f"删除资产分类：{before['name']}",
            actor=context.user,
            resource_type="asset_category",
            resource_id=category_id,
            before=before,
        )
        await commit_or_conflict(self.session)

    async def create_field(
        self,
        category_id: int,
        payload: CategoryFieldCreate,
        context: AuthContext,
    ) -> CategoryFieldOut:
        category = await self._get_or_error(category_id)
        if any(item.field_key == payload.field_key for item in category.field_defs):
            raise ConflictError("字段标识在该分类下已存在", code=40921)

        field = AssetCategoryField(
            category_id=category.id,
            name=payload.name,
            field_key=payload.field_key,
            field_type=payload.field_type,
            required=payload.required,
            options=payload.options,
            sort=payload.sort,
            status=payload.status,
            remark=payload.remark,
        )
        self.session.add(field)
        await self.session.flush()
        await self.audit.record(
            action="asset.category.field.create",
            module="资产分类",
            summary=f"新增自定义字段：{field.name}",
            actor=context.user,
            resource_type="asset_category_field",
            resource_id=field.id,
            after=_field_snapshot(field),
        )
        await commit_or_conflict(self.session)
        return _field_out(field)

    async def update_field(
        self,
        category_id: int,
        field_id: int,
        payload: CategoryFieldUpdate,
        context: AuthContext,
    ) -> CategoryFieldOut:
        category = await self._get_or_error(category_id)
        field = await self.session.get(AssetCategoryField, field_id)
        if field is None or field.category_id != category.id:
            raise NotFoundError("自定义字段不存在")
        if field.version != payload.version:
            raise ConflictError("字段信息已被他人修改，请刷新后重试")
        duplicate = next(
            (
                item
                for item in category.field_defs
                if item.field_key == payload.field_key and item.id != field.id
            ),
            None,
        )
        if duplicate is not None:
            raise ConflictError("字段标识在该分类下已存在", code=40921)

        has_assets = await self.categories.count_assets(category.id) > 0
        if has_assets and (
            field.field_key != payload.field_key or field.field_type != payload.field_type
        ):
            raise BizError("分类下已有资产，不能修改字段标识或字段类型")

        before = _field_snapshot(field)
        field.name = payload.name
        field.field_key = payload.field_key
        field.field_type = payload.field_type
        field.required = payload.required
        field.options = payload.options
        field.sort = payload.sort
        field.status = payload.status
        field.remark = payload.remark
        await self.audit.record(
            action="asset.category.field.update",
            module="资产分类",
            summary=f"编辑自定义字段：{field.name}",
            actor=context.user,
            resource_type="asset_category_field",
            resource_id=field.id,
            before=before,
            after=_field_snapshot(field),
        )
        await commit_or_conflict(self.session)
        return _field_out(field)

    async def delete_field(
        self,
        category_id: int,
        field_id: int,
        context: AuthContext,
    ) -> None:
        category = await self._get_or_error(category_id)
        field = await self.session.get(AssetCategoryField, field_id)
        if field is None or field.category_id != category.id:
            raise NotFoundError("自定义字段不存在")
        if await self.categories.count_assets(category.id):
            raise BizError("分类下已有资产，不能删除自定义字段")

        before = _field_snapshot(field)
        await self.session.delete(field)
        await self.audit.record(
            action="asset.category.field.delete",
            module="资产分类",
            summary=f"删除自定义字段：{before['name']}",
            actor=context.user,
            resource_type="asset_category_field",
            resource_id=field_id,
            before=before,
        )
        await commit_or_conflict(self.session)


class ModelService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.models = AssetModelRepository(session)
        self.categories = AssetCategoryRepository(session)
        self.audit = AuditService(session)

    async def list(
        self,
        context: AuthContext,
        *,
        category_id: int | None,
        include_child: bool,
        keyword: str | None,
        status: int | None,
        page: int,
        page_size: int,
    ) -> ModelPageOut:
        category_ids: list[int] | None = None
        if category_id is not None:
            category = await self.categories.get(category_id)
            if category is None:
                raise NotFoundError("资产分类不存在")
            category_ids = [category.id]
            if include_child:
                categories = await self.categories.list_all()
                category_ids = [
                    item.id
                    for item in categories
                    if item.id == category.id or item.path.startswith(category.path)
                ]
        rows, total = await self.models.list_paginated(
            category_ids=category_ids,
            keyword=keyword,
            status=status,
            page=page,
            page_size=page_size,
        )
        items = []
        for model in rows:
            items.append(
                await self._model_out(model, asset_count=await self.models.count_assets(model.id))
            )
        return ModelPageOut(items=items, total=total, page=page, page_size=page_size)

    async def _get_or_error(self, model_id: int) -> AssetModel:
        model = await self.models.get(model_id)
        if model is None:
            raise NotFoundError("资产型号不存在")
        return model

    async def _model_out(self, model: AssetModel, *, asset_count: int = 0) -> ModelOut:
        return ModelOut(
            id=model.id,
            category_id=model.category_id,
            category_name=model.category.name if model.category else None,
            name=model.name,
            code=model.code,
            brand=model.brand,
            spec=model.spec,
            unit=model.unit,
            depreciation_months=model.depreciation_months,
            residual_rate=float(model.residual_rate or 0),
            status=model.status,
            remark=model.remark,
            version=model.version,
            asset_count=asset_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(self, payload: ModelCreate, context: AuthContext) -> ModelOut:
        category = await self.categories.get(payload.category_id)
        if category is None:
            raise NotFoundError("资产分类不存在")
        if category.status != 1:
            raise BizError("资产分类已停用，无法新增型号")
        if await self.models.get_by_code(payload.code):
            raise ConflictError("型号编码已存在", code=40922)

        model = AssetModel(
            category_id=category.id,
            category=category,
            name=payload.name,
            code=payload.code,
            brand=payload.brand,
            spec=payload.spec,
            unit=payload.unit,
            depreciation_months=payload.depreciation_months,
            residual_rate=payload.residual_rate,
            status=payload.status,
            remark=payload.remark,
        )
        self.session.add(model)
        await self.session.flush()
        await self.audit.record(
            action="asset.model.create",
            module="型号管理",
            summary=f"新增资产型号：{model.name}",
            actor=context.user,
            resource_type="asset_model",
            resource_id=model.id,
            after=self._snapshot(model),
        )
        await commit_or_conflict(self.session)
        return await self._model_out(model)

    @staticmethod
    def _snapshot(model: AssetModel) -> dict[str, object]:
        return {
            "category_id": model.category_id,
            "name": model.name,
            "code": model.code,
            "brand": model.brand,
            "spec": model.spec,
            "unit": model.unit,
            "depreciation_months": model.depreciation_months,
            "residual_rate": float(model.residual_rate or 0),
            "status": model.status,
            "remark": model.remark,
            "version": model.version,
        }

    async def update(
        self,
        model_id: int,
        payload: ModelUpdate,
        context: AuthContext,
    ) -> ModelOut:
        model = await self._get_or_error(model_id)
        if model.version != payload.version:
            raise ConflictError("型号信息已被他人修改，请刷新后重试")
        duplicate = await self.models.get_by_code(payload.code)
        if duplicate is not None and duplicate.id != model.id:
            raise ConflictError("型号编码已存在", code=40922)
        category = await self.categories.get(payload.category_id)
        if category is None:
            raise NotFoundError("资产分类不存在")
        if category.status != 1:
            raise BizError("资产分类已停用，无法挂载型号")
        if payload.category_id != model.category_id and await self.models.count_assets(model.id):
            raise BizError("该型号已被资产引用，不能变更所属分类")

        before = self._snapshot(model)
        model.category_id = category.id
        model.category = category
        model.name = payload.name
        model.code = payload.code
        model.brand = payload.brand
        model.spec = payload.spec
        model.unit = payload.unit
        model.depreciation_months = payload.depreciation_months
        model.residual_rate = payload.residual_rate
        model.status = payload.status
        model.remark = payload.remark
        await self.audit.record(
            action="asset.model.update",
            module="型号管理",
            summary=f"编辑资产型号：{model.name}",
            actor=context.user,
            resource_type="asset_model",
            resource_id=model.id,
            before=before,
            after=self._snapshot(model),
        )
        await commit_or_conflict(self.session)
        return await self._model_out(
            model,
            asset_count=await self.models.count_assets(model.id),
        )

    async def delete(self, model_id: int, context: AuthContext) -> None:
        model = await self._get_or_error(model_id)
        if await self.models.count_assets(model.id):
            raise BizError("该型号已被资产引用，无法删除")
        before = self._snapshot(model)
        await self.session.delete(model)
        await self.audit.record(
            action="asset.model.delete",
            module="型号管理",
            summary=f"删除资产型号：{before['name']}",
            actor=context.user,
            resource_type="asset_model",
            resource_id=model_id,
            before=before,
        )
        await commit_or_conflict(self.session)
