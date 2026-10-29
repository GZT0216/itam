from httpx import AsyncClient

TEST_PASSWORD = "Test@12345"


async def login(client: AsyncClient, password: str = TEST_PASSWORD) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": password},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == 0
    return body["data"]


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
