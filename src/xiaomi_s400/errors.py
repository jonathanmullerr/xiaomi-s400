"""Public errors contain fixed diagnostics, never upstream responses."""


class S400Error(Exception):
    code = "s400_error"
    message = "S400 operation failed."

    def __init__(self):
        super().__init__(self.message)


class InputError(S400Error):
    code = "invalid_input"
    message = "Invalid configuration, session import, or date range."


class AuthenticationError(S400Error):
    code = "authentication_required"
    message = "Xiaomi authentication unavailable; run xiaomi-s400 login."


class NetworkError(S400Error):
    code = "network_error"
    message = "Xiaomi network request failed."


class ProtocolError(S400Error):
    code = "protocol_error"
    message = "Xiaomi returned an unexpected response."


class PaginationError(ProtocolError):
    code = "pagination_error"
    message = "Xiaomi history is incomplete: pagination stalled or exceeded 50 pages."


class LoginExpired(AuthenticationError):
    code = "login_expired"
    message = "QR login expired; start a new login."


class LoginCancelled(AuthenticationError):
    code = "login_cancelled"
    message = "QR login cancelled."
