from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.core.assets import ASSET_STATUS_LABELS
from app.models import Asset


def json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def asset_snapshot(asset: Asset) -> dict[str, Any]:
    data = {
        column.name: json_value(getattr(asset, column.name))
        for column in Asset.__table__.columns
    }
    data["status_label"] = ASSET_STATUS_LABELS.get(asset.status, asset.status)
    data["category_name"] = asset.category.name if asset.category else None
    data["model_name"] = asset.model.name if asset.model else None
    data["dept_name"] = asset.dept.name if asset.dept else None
    data["custodian_name"] = asset.custodian.real_name if asset.custodian else None
    return data
