"""tool_schemas 패키지 — 18개 MCP 도구 스키마를 모듈별로 분리하고 TOOLS_LIST로 통합."""
from . import integrated, law, lookup, extended, utility

TOOLS_LIST = (
    integrated.SCHEMAS
    + law.SCHEMAS
    + lookup.SCHEMAS
    + extended.SCHEMAS
    + utility.SCHEMAS
)

__all__ = ["TOOLS_LIST"]
