from httpx import AsyncClient

from tests.helpers import auth_headers, login


async def _it_dept(client: AsyncClient, headers: dict[str, str]) -> dict:
    response = await client.get("/api/v1/departments/tree", headers=headers)
    assert response.status_code == 200, response.text
    tree = response.json()["data"]

    def walk(nodes):
        for node in nodes:
            if node["code"] == "IT":
                return node
            found = walk(node["children"])
            if found:
                return found
        return None

    dept = walk(tree)
    assert dept is not None
    return dept


async def test_department_crud_and_optimistic_lock(client: AsyncClient):
    tokens = await login(client)
    headers = auth_headers(tokens["access_token"])
    it_dept = await _it_dept(client, headers)

    created = await client.post(
        "/api/v1/departments",
        json={
            "name": "测试部",
            "code": "TEST",
            "parent_id": it_dept["id"],
            "leader": "张三",
            "sort": 99,
            "status": 1,
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    dept = created.json()["data"]
    assert dept["path"] == f"{it_dept['path']}{dept['id']}/"
    assert dept["level"] == it_dept["level"] + 1
    assert dept["version"] >= 1

    updated = await client.put(
        f"/api/v1/departments/{dept['id']}",
        json={
            "name": "测试部（改名）",
            "code": "TEST",
            "parent_id": it_dept["id"],
            "sort": 98,
            "status": 1,
            "version": dept["version"],
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["version"] == dept["version"] + 1

    stale = await client.put(
        f"/api/v1/departments/{dept['id']}",
        json={
            "name": "过期更新",
            "code": "TEST",
            "parent_id": it_dept["id"],
            "sort": 97,
            "status": 1,
            "version": 1,
        },
        headers=headers,
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == 40900

    duplicated = await client.post(
        "/api/v1/departments",
        json={"name": "重复编码", "code": "TEST"},
        headers=headers,
    )
    assert duplicated.status_code == 409
    assert duplicated.json()["code"] == 40910

    removed = await client.delete(f"/api/v1/departments/{dept['id']}", headers=headers)
    assert removed.status_code == 200, removed.text


async def test_user_lifecycle_and_soft_delete(client: AsyncClient):
    tokens = await login(client)
    headers = auth_headers(tokens["access_token"])
    it_dept = await _it_dept(client, headers)

    roles_response = await client.get("/api/v1/roles/options/all", headers=headers)
    roles = roles_response.json()["data"]
    employee_role = next(role for role in roles if role["code"] == "EMPLOYEE")

    created = await client.post(
        "/api/v1/users",
        json={
            "username": "zhangsan",
            "password": "Init@12345",
            "real_name": "张三",
            "dept_id": it_dept["id"],
            "employee_no": "E1001",
            "email": "zhangsan@example.com",
            "role_ids": [employee_role["id"]],
            "status": 1,
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    user = created.json()["data"]
    assert user["must_change_password"] is True
    assert user["dept_name"] == it_dept["name"]
    assert [role["code"] for role in user["roles"]] == ["EMPLOYEE"]

    duplicate = await client.post(
        "/api/v1/users",
        json={
            "username": "zhangsan",
            "password": "Init@12345",
            "real_name": "张三二号",
            "dept_id": it_dept["id"],
            "role_ids": [employee_role["id"]],
        },
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == 40920

    listed = await client.get(
        "/api/v1/users",
        params={"keyword": "zhangsan", "dept_id": it_dept["id"]},
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    page = listed.json()["data"]
    assert page["total"] == 1
    assert page["items"][0]["username"] == "zhangsan"

    new_tokens = await client.post(
        "/api/v1/auth/login",
        json={"username": "zhangsan", "password": "Init@12345"},
    )
    assert new_tokens.status_code == 200
    assert new_tokens.json()["data"]["must_change_password"] is True

    detail = await client.get(f"/api/v1/users/{user['id']}", headers=headers)
    assert detail.status_code == 200
    current = detail.json()["data"]
    assert current["version"] >= user["version"]

    disabled = await client.put(
        f"/api/v1/users/{user['id']}/status",
        json={"status": 0, "version": current["version"]},
        headers=headers,
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["data"]["status"] == 0

    blocked = await client.post(
        "/api/v1/auth/login",
        json={"username": "zhangsan", "password": "Init@12345"},
    )
    assert blocked.status_code == 401

    enabled = await client.put(
        f"/api/v1/users/{user['id']}/status",
        json={"status": 1, "version": disabled.json()["data"]["version"]},
        headers=headers,
    )
    assert enabled.status_code == 200, enabled.text

    reset = await client.post(
        f"/api/v1/users/{user['id']}/reset-password",
        json={"new_password": "Reset@12345", "version": enabled.json()["data"]["version"]},
        headers=headers,
    )
    assert reset.status_code == 200, reset.text

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "zhangsan", "password": "Init@12345"},
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "zhangsan", "password": "Reset@12345"},
    )
    assert new_login.status_code == 200
    assert new_login.json()["data"]["must_change_password"] is True

    deleted = await client.delete(f"/api/v1/users/{user['id']}", headers=headers)
    assert deleted.status_code == 200, deleted.text

    login_after_delete = await client.post(
        "/api/v1/auth/login",
        json={"username": "zhangsan", "password": "Reset@12345"},
    )
    assert login_after_delete.status_code == 401

    listed_after = await client.get(
        "/api/v1/users",
        params={"keyword": "zhangsan"},
        headers=headers,
    )
    assert listed_after.json()["data"]["total"] == 0

    self_detail = await client.get(
        f"/api/v1/users/{tokens['user']['id']}",
        headers=headers,
    )
    self_disable = await client.put(
        f"/api/v1/users/{tokens['user']['id']}/status",
        json={"status": 0, "version": self_detail.json()["data"]["version"]},
        headers=headers,
    )
    assert self_disable.status_code == 400
