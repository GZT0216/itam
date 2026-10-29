from io import BytesIO

import pytest
from httpx import AsyncClient
from openpyxl import Workbook

from tests.helpers import auth_headers, login

XLSX_MEDIA = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _xlsx(headers: list[str], rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


async def _upload(
    client: AsyncClient,
    headers: dict[str, str],
    path: str,
    content: bytes,
    filename: str = "import.xlsx",
):
    return await client.post(
        path,
        files={"file": (filename, content, XLSX_MEDIA)},
        headers=headers,
    )


async def test_import_category_template_and_rows(client: AsyncClient):
    tokens = await login(client)
    headers = auth_headers(tokens["access_token"])

    template = await client.get(
        "/api/v1/imports/asset-categories/template", headers=headers
    )
    assert template.status_code == 200, template.text
    assert template.headers["content-type"] == XLSX_MEDIA
    assert "filename*=UTF-8''" in template.headers["content-disposition"]
    assert template.content[:2] == b"PK"

    content = _xlsx(
        [
            "分类编码",
            "分类名称",
            "上级分类编码",
            "分类类型",
            "排序",
            "安全库存",
            "状态",
            "备注",
        ],
        [
            ["IMP-NB", "导入笔记本", "IMP-HW", "", 10, 0, "启用", "子分类先出现"],
            ["IMP-HW", "导入硬件", "", "硬件", 20, 0, "启用", "根分类"],
            ["HW-LAPTOP", "重复编码", "", "硬件", 30, 0, "启用", "应失败"],
            ["IMP-ORPHAN", "孤儿分类", "NO-SUCH", "硬件", 40, 0, "启用", "上级不存在"],
            ["IMP-BAD-TYPE", "非法类型", "", "服务", 50, 0, "启用", "应失败"],
        ],
    )
    result = await _upload(
        client, headers, "/api/v1/imports/asset-categories", content
    )
    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["total"] == 5
    assert data["success"] == 2
    assert data["failed"] == 3
    rows = {item["row"] for item in data["errors"]}
    assert rows == {4, 5, 6}

    tree = await client.get("/api/v1/asset-categories/tree", headers=headers)
    codes: set[str] = set()

    def walk(nodes):
        for node in nodes:
            codes.add(node["code"])
            walk(node["children"])

    walk(tree.json()["data"])
    assert {"IMP-HW", "IMP-NB"} <= codes


async def test_import_user_template_and_rows(client: AsyncClient):
    tokens = await login(client)
    headers = auth_headers(tokens["access_token"])

    template = await client.get("/api/v1/imports/users/template", headers=headers)
    assert template.status_code == 200, template.text
    assert template.content[:2] == b"PK"

    content = _xlsx(
        [
            "用户名",
            "姓名",
            "部门编码",
            "角色编码",
            "初始密码",
            "工号",
            "邮箱",
            "手机号",
            "职位",
            "状态",
            "备注",
        ],
        [
            ["imp.zhang", "导入张三", "IT", "EMPLOYEE", "", "IMP-1001", "", "", "工程师", "启用", "正常"],
            ["imp.li", "导入李四", "NO-SUCH", "EMPLOYEE", "", "", "", "", "", "启用", "部门不存在"],
            ["admin", "重复管理员", "IT", "EMPLOYEE", "", "", "", "", "", "启用", "用户名重复"],
            ["imp.wang", "导入王五", "IT", "NO-ROLE", "", "", "", "", "", "启用", "角色不存在"],
        ],
    )
    result = await _upload(client, headers, "/api/v1/imports/users", content)
    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["success"] == 1
    assert data["failed"] == 3
    assert {item["row"] for item in data["errors"]} == {3, 4, 5}

    listed = await client.get(
        "/api/v1/users", params={"keyword": "imp.zhang"}, headers=headers
    )
    assert listed.status_code == 200, listed.text
    items = listed.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["dept_name"] == "信息技术部"

    created = items[0]
    removed = await client.delete(
        f"/api/v1/users/{created['id']}", headers=headers
    )
    assert removed.status_code == 200, removed.text


async def test_import_asset_template_and_rows(client: AsyncClient):
    tokens = await login(client)
    headers = auth_headers(tokens["access_token"])

    template = await client.get("/api/v1/imports/assets/template", headers=headers)
    assert template.status_code == 200, template.text
    assert template.content[:2] == b"PK"

    content = _xlsx(
        [
            "资产名称",
            "分类编码",
            "资产编号",
            "型号编码",
            "序列号",
            "MAC 地址",
            "购置日期",
            "供应商",
            "采购价格",
            "保修到期",
            "存放位置",
            "部门编码",
            "责任人用户名",
            "备注",
        ],
        [
            [
                "导入笔记本",
                "HW-LAPTOP",
                "",
                "LENOVO-X1-CARBON-G11",
                "SN-IMP-001",
                "AA:BB:CC:DD:EE:01",
                "2026-03-01",
                "导入供应商",
                7999,
                "2029-03-01",
                "A 座 501",
                "IT",
                "admin",
                "正常行",
            ],
            ["分类不存在", "NO-SUCH", "", "", "SN-IMP-002", "", "", "", "", "", "", "", "", ""],
            ["日期非法", "HW-LAPTOP", "", "", "SN-IMP-003", "", "2026/13/40", "", "", "", "", "", "", ""],
            ["型号不匹配", "HW-LAPTOP", "", "HPE-DL380-G11", "SN-IMP-004", "", "", "", "", "", "", "", "", ""],
        ],
    )
    result = await _upload(client, headers, "/api/v1/imports/assets", content)
    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["success"] == 1
    assert data["failed"] == 3
    assert {item["row"] for item in data["errors"]} == {3, 4, 5}

    listed = await client.get(
        "/api/v1/assets", params={"keyword": "SN-IMP-001"}, headers=headers
    )
    assert listed.status_code == 200, listed.text
    items = listed.json()["data"]["items"]
    assert len(items) == 1
    asset = items[0]
    assert asset["status"] == "PENDING_STOCK"
    assert asset["purchase_price"] == 7999
    assert asset["custodian_name"] == "系统管理员"

    removed = await client.delete(f"/api/v1/assets/{asset['id']}", headers=headers)
    assert removed.status_code == 200, removed.text


async def test_import_rejects_invalid_files(client: AsyncClient):
    tokens = await login(client)
    headers = auth_headers(tokens["access_token"])

    wrong_suffix = await _upload(
        client, headers, "/api/v1/imports/assets", b"hello", filename="data.csv"
    )
    assert wrong_suffix.status_code == 400
    assert ".xlsx" in wrong_suffix.json()["message"]

    empty = await _upload(
        client, headers, "/api/v1/imports/assets", b"", filename="empty.xlsx"
    )
    assert empty.status_code == 400

    bad_header = _xlsx(["资产名称", "分类编码"], [["无表头", "HW-LAPTOP"]])
    wrong_header = await _upload(
        client, headers, "/api/v1/imports/assets", bad_header
    )
    assert wrong_header.status_code == 400
    assert "表头缺少字段" in wrong_header.json()["message"]

    broken = await _upload(
        client, headers, "/api/v1/imports/assets", b"not-an-excel", filename="bad.xlsx"
    )
    assert broken.status_code == 400
    assert "Excel" in broken.json()["message"]


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/api/v1/imports/users/template", 200),
        ("/api/v1/imports/assets/template", 200),
        ("/api/v1/imports/asset-categories/template", 200),
    ],
)
async def test_import_templates_are_downloadable(
    client: AsyncClient, path: str, expected: int
):
    tokens = await login(client)
    headers = auth_headers(tokens["access_token"])
    response = await client.get(path, headers=headers)
    assert response.status_code == expected, response.text
    assert response.headers["content-type"] == XLSX_MEDIA
    assert response.content[:2] == b"PK"
