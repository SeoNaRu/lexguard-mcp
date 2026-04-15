"""Repository 레이어 - 데이터 접근 로직"""
from .law_repository import LawRepository
from .base import BaseLawRepository
from .law_search import LawSearchRepository
from .law_detail import LawDetailRepository
from .law_misc_repository import LawMiscRepository
from .law_history_repository import LawHistoryRepository
from .law_link_repository import LawLinkRepository
from .law_form_repository import LawFormRepository
from .law_interpretation_repository import LawInterpretationRepository

__all__ = [
    "LawRepository",
    "BaseLawRepository",
    "LawSearchRepository",
    "LawDetailRepository",
    "LawMiscRepository",
    "LawHistoryRepository",
    "LawLinkRepository",
    "LawFormRepository",
    "LawInterpretationRepository",
]

