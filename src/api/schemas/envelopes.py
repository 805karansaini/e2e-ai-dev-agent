"""Common API envelope helpers."""

from __future__ import annotations

from typing import Generic, Literal, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel

PayloadT = TypeVar("PayloadT")


class Success(BaseModel, Generic[PayloadT]):
    """Standard success envelope."""

    status: Literal["ok"] = "ok"
    data: PayloadT


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    status: Literal["error"] = "error"
    message: str


def success(data: PayloadT, status_code: int = 200) -> JSONResponse:
    """Wrap data in a success envelope JSON response."""

    return JSONResponse(
        # mode="json" ensures non-JSON-native types (e.g., datetime) are serialized
        # to JSON-friendly representations.
        content=Success[PayloadT](data=data).model_dump(mode="json"),
        status_code=status_code,
    )
