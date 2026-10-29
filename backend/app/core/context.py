from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
client_ip_ctx: ContextVar[str] = ContextVar("client_ip", default="")
user_agent_ctx: ContextVar[str] = ContextVar("user_agent", default="")
request_method_ctx: ContextVar[str] = ContextVar("request_method", default="")
request_path_ctx: ContextVar[str] = ContextVar("request_path", default="")


def get_request_meta() -> dict[str, str]:
    return {
        "request_id": request_id_ctx.get(),
        "ip": client_ip_ctx.get(),
        "user_agent": user_agent_ctx.get(),
        "method": request_method_ctx.get(),
        "path": request_path_ctx.get(),
    }
