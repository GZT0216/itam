from httpx import AsyncClient

from tests.helpers import auth_headers, login


async def _category(client: AsyncClient, headers: dict[str, str], code: str) -> dict:
    response = await client.get("/api/v1/asset-categories/tree", headers=headers)
    tree = response.json()["data"]

    def walk(nodes):
        for node in nodes:
            if node["code"] == code:
                return node
            found = walk(node["children"])
            if found:
                return found
        return None

    category = walk(tree)
    assert category is not None
    return category


async def _dept(client: AsyncClient, headers: dict[str, str], code: str) -> dict:
    response = await client.get("/api/v1/departments/tree", headers=headers)
    tree = response.json()["data"]

    def walk(nodes):
        for node in nodes:
            if node["code"] == code:
                return node
            found = walk(node["children"])
            if found:
                return found
        return None

    dept = walk(tree)
    assert dept is not None
    return dept


async def test_global_search_assets_users_depts(client: AsyncClient):
    tokens = await login(client)
    headers = auth_headers(tokens["access_token"])
    laptop = await _category(client, headers, "HW-LAPTOP")
    it_dept = await _dept(client, headers, "IT")

    created = await client.post(
        "/api/v1/assets",
        json={
            "name": "全局搜索测试笔记本",
            "category_id": laptop["id"],
            "serial_no": "SN-SEARCH-9001",
            "dept_id": it_dept["id"],
            "custom_fields": {},
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    asset = created.json()["data"]

    by_serial = await client.get(
        "/api/v1/search", params={"keyword": "SN-SEARCH-9001"}, headers=headers
    )
    assert by_serial.status_code == 200, by_serial.text
    items = by_serial.json()["data"]["items"]
    asset_items = [item for item in items if item["type"] == "asset"]
    assert len(asset_items) == 1
    assert asset_items[0]["id"] == asset["id"]
    assert asset_items[0]["keyword"] == asset["asset_no"]
    assert "全局搜索测试笔记本" in asset_items[0]["title"]

    by_username = await client.get(
        "/api/v1/search", params={"keyword": "admin"}, headers=headers
    )
    user_items = [
        item for item in by_username.json()["data"]["items"] if item["type"] == "user"
    ]
    assert user_items
    assert user_items[0]["keyword"] == "admin"

    by_dept = await client.get(
        "/api/v1/search", params={"keyword": "信息技术"}, headers=headers
    )
    dept_items = [
        item for item in by_dept.json()["data"]["items"] if item["type"] == "dept"
    ]
    assert dept_items
    assert dept_items[0]["title"] == "信息技术部"

    missing = await client.get(
        "/api/v1/search", params={"keyword": "NOT-EXIST-XYZ"}, headers=headers
    )
    assert missing.status_code == 200
    assert missing.json()["data"]["items"] == []

    wildcard = await client.get(
        "/api/v1/search", params={"keyword": "%"}, headers=headers
    )
    assert wildcard.status_code == 200
    assert wildcard.json()["data"]["items"] == []

    invalid = await client.get("/api/v1/search", headers=headers)
    assert invalid.status_code == 422

    removed = await client.delete(f"/api/v1/assets/{asset['id']}", headers=headers)
    assert removed.status_code == 200, removed.text
