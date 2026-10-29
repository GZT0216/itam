from datetime import timedelta

from app.models.base import now_cst
from tests.helpers import auth_headers, login


async def test_dashboard_summary_metrics_and_charts(client):
    tokens = await login(client)
    headers = auth_headers(tokens["access_token"])

    empty = await client.get("/api/v1/dashboard/summary", headers=headers)
    assert empty.status_code == 200, empty.text
    empty_data = empty.json()["data"]
    assert empty_data["metrics"]["total_assets"] == 0
    assert len(empty_data["purchase_trend"]) == 12
    assert empty_data["status_distribution"]
    assert all(item["count"] == 0 for item in empty_data["status_distribution"])
    assert empty_data["category_distribution"] == []
    assert empty_data["warranty_expiring"] == []

    category = await client.post(
        "/api/v1/asset-categories",
        json={
            "name": "驾驶舱测试分类",
            "code": "DASH-CAT",
            "category_type": "HARDWARE",
            "sort": 10,
            "status": 1,
        },
        headers=headers,
    )
    assert category.status_code == 200, category.text
    category_id = category.json()["data"]["id"]

    today = now_cst().date()
    warranty_end = today + timedelta(days=10)
    created = await client.post(
        "/api/v1/assets",
        json={
            "name": "驾驶舱测试资产",
            "category_id": category_id,
            "purchase_date": today.isoformat(),
            "purchase_price": 1234.5,
            "warranty_end": warranty_end.isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text

    summary = await client.get("/api/v1/dashboard/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    data = summary.json()["data"]

    metrics = data["metrics"]
    assert metrics["total_assets"] == 1
    assert metrics["total_value"] == 1234.5
    assert metrics["pending_stock"] == 1
    assert metrics["warranty_30d"] == 1

    status_map = {item["status"]: item["count"] for item in data["status_distribution"]}
    assert status_map["PENDING_STOCK"] == 1
    assert status_map["IN_USE"] == 0

    categories = data["category_distribution"]
    assert categories[0]["name"] == "驾驶舱测试分类"
    assert categories[0]["count"] == 1

    trend = data["purchase_trend"]
    assert trend[-1]["month"] == today.strftime("%Y-%m")
    assert trend[-1]["count"] == 1

    warranty = data["warranty_expiring"]
    assert len(warranty) == 1
    assert warranty[0]["days_left"] == 10
    assert warranty[0]["name"] == "驾驶舱测试资产"

    recent = data["recent_assets"]
    assert recent[0]["name"] == "驾驶舱测试资产"
    assert recent[0]["status_label"] == "待入库"

    assert data["data_scope_label"] == "全部数据"
    assert data["metrics"]["month_inbound"] == 0
    assert data["metrics"]["month_requisition"] == 0
    assert data["metrics"]["contract_expiring"] == 0
    assert data["metrics"]["idle_rate"] == 0.0
    assert data["period"]["months"] == 12
    assert data["period"]["new_assets"] == 1
    assert data["dept_options"]
    assert data["dept_id"] is None


async def _dept_ids(client, headers) -> dict[str, int]:
    tree = await client.get("/api/v1/departments/tree", headers=headers)
    assert tree.status_code == 200, tree.text
    result: dict[str, int] = {}

    def walk(nodes: list[dict]) -> None:
        for node in nodes:
            result[node["code"]] = node["id"]
            walk(node.get("children") or [])

    walk(tree.json()["data"])
    return result


async def test_dashboard_dept_filter_period_and_contract(client):
    tokens = await login(client)
    headers = auth_headers(tokens["access_token"])
    dept_ids = await _dept_ids(client, headers)
    it_id = dept_ids["IT"]
    fin_id = dept_ids["FIN"]

    category = await client.post(
        "/api/v1/asset-categories",
        json={
            "name": "驾驶舱筛选分类",
            "code": "DASH-FILTER",
            "category_type": "HARDWARE",
            "sort": 10,
            "status": 1,
        },
        headers=headers,
    )
    assert category.status_code == 200, category.text
    category_id = category.json()["data"]["id"]

    today = now_cst().date()
    for name, dept_id in (("IT 测试资产", it_id), ("财务测试资产", fin_id)):
        created = await client.post(
            "/api/v1/assets",
            json={
                "name": name,
                "category_id": category_id,
                "dept_id": dept_id,
                "purchase_date": today.isoformat(),
                "purchase_price": 100,
            },
            headers=headers,
        )
        assert created.status_code == 200, created.text

    contract = await client.post(
        "/api/v1/contracts",
        json={
            "name": "IT 维保合同",
            "contract_type": "MAINTENANCE",
            "start_date": (today - timedelta(days=300)).isoformat(),
            "end_date": (today + timedelta(days=10)).isoformat(),
            "dept_id": it_id,
        },
        headers=headers,
    )
    assert contract.status_code == 200, contract.text

    all_summary = await client.get(
        "/api/v1/dashboard/summary?months=3", headers=headers
    )
    assert all_summary.status_code == 200, all_summary.text
    all_data = all_summary.json()["data"]
    assert all_data["metrics"]["total_assets"] == 2
    assert all_data["metrics"]["contract_expiring"] == 1
    assert all_data["period"]["months"] == 3
    assert all_data["period"]["new_assets"] == 2
    assert len(all_data["purchase_trend"]) == 3

    filtered = await client.get(
        f"/api/v1/dashboard/summary?dept_id={it_id}", headers=headers
    )
    assert filtered.status_code == 200, filtered.text
    filtered_data = filtered.json()["data"]
    assert filtered_data["dept_id"] == it_id
    assert filtered_data["metrics"]["total_assets"] == 1
    assert filtered_data["metrics"]["contract_expiring"] == 1
    assert [item["name"] for item in filtered_data["category_distribution"]] == [
        "驾驶舱筛选分类"
    ]

    empty = await client.get(
        f"/api/v1/dashboard/summary?dept_id={dept_ids['HR']}", headers=headers
    )
    assert empty.status_code == 200, empty.text
    empty_data = empty.json()["data"]
    assert empty_data["metrics"]["total_assets"] == 0
    assert empty_data["metrics"]["contract_expiring"] == 0
    assert empty_data["category_distribution"] == []

