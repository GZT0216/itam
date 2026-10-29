class BizError(Exception):
    code: int = 40000
    http_status: int = 400

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        http_status: int | None = None,
        data: object | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status
        self.data = data


class AuthError(BizError):
    code = 40100
    http_status = 401


class PermissionDenied(BizError):
    code = 40300
    http_status = 403


class PasswordChangeRequired(PermissionDenied):
    code = 40310

    def __init__(self, message: str = "首次登录（或密码被重置）后必须修改密码") -> None:
        super().__init__(message)


class NotFoundError(BizError):
    code = 40400
    http_status = 404


class ConflictError(BizError):
    code = 40900
    http_status = 409


class ServiceUnavailable(BizError):
    code = 50300
    http_status = 503
