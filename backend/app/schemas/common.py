"""Общие схемы для API ответов."""
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: Optional[str] = None
    has_more: bool = False
    total: Optional[int] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[Any] = None
