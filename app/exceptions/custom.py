class AppException(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UserAlreadyExistsException(AppException):
    def __init__(self, message: str = "A user with this email already exists") -> None:
        super().__init__(message=message, status_code=409)


class InvalidCredentialsException(AppException):
    def __init__(self, message: str = "Invalid email or password") -> None:
        super().__init__(message=message, status_code=401)


class InactiveUserException(AppException):
    def __init__(self, message: str = "User account is inactive") -> None:
        super().__init__(message=message, status_code=403)


class UserNotFoundException(AppException):
    def __init__(self, message: str = "User not found") -> None:
        super().__init__(message=message, status_code=404)


class SessionNotFoundException(AppException):
    def __init__(self, message: str = "Session not found") -> None:
        super().__init__(message=message, status_code=404)
