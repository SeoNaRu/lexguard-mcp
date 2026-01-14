"""Repository 레이어 - 데이터 접근 로직"""
from .law_repository import LawRepository
from .base import BaseLawRepository
from .law_search import LawSearchRepository
from .law_detail import LawDetailRepository

__all__ = [
    "LawRepository",
    "BaseLawRepository",
    "LawSearchRepository",
    "LawDetailRepository"
]

