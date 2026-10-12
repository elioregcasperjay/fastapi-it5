class NotFoundError(Exception):
    """Raised when a record does not exist (HTTP 404)."""


class BusinessRuleError(Exception):
    """Raised when a library rule is broken (HTTP 400)."""