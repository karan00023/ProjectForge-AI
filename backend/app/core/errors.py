from fastapi import HTTPException, status


def not_found(entity: str = "Resource") -> HTTPException:
    # Also used for records in another tenant, so their existence is never disclosed.
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{entity} not found")


def forbidden(message: str = "Your role does not allow this action") -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, message)


def conflict(message: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, message)


def bad_request(message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, message)
