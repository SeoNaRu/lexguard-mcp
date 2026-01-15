import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv
from src.services.situation_guidance_service import SituationGuidanceService
from src.utils.response_formatter import format_mcp_response
from src.utils.response_truncator import shrink_response_bytes, MAX_RESPONSE_SIZE


def find_sample(keyword: str) -> Path:
    sample_dir = Path("sample")
    for path in sample_dir.iterdir():
        if path.is_file() and keyword in path.name:
            return path
    raise FileNotFoundError(f"샘플 파일을 찾을 수 없습니다: {keyword}")


def run_case(name: str, text: str, auto_search: bool):
    svc = SituationGuidanceService()
    result = asyncio.run(
        svc.document_issue_analysis(
            text,
            None,
            auto_search=auto_search,
            max_clauses=3,
            max_results_per_type=3,
        )
    )
    mcp = format_mcp_response(result, "document_issue_tool")
    final = {"jsonrpc": "2.0", "id": name, "result": mcp}
    final = shrink_response_bytes(final, MAX_RESPONSE_SIZE)
    serialized = json.dumps(final, ensure_ascii=False)
    size_bytes = len(serialized.encode("utf-8"))

    content = mcp.get("content", [])
    top_text = content[0].get("text") if content else ""

    print(f"[{name}] size_bytes={size_bytes} (max={MAX_RESPONSE_SIZE})")
    print(f"  success={result.get('success')} success_search={result.get('success_search')}")
    print(f"  missing_reason={result.get('missing_reason')}")
    print(f"  citations_count={len(mcp.get('structuredContent', {}).get('citations', [])) if mcp.get('structuredContent') else 0}")
    safe_top = top_text[:120].encode("cp949", "replace").decode("cp949")
    print(f"  content_top={safe_top}")

    if size_bytes > MAX_RESPONSE_SIZE:
        raise SystemExit(f"응답 크기 초과: {size_bytes} > {MAX_RESPONSE_SIZE}")


def main():
    load_dotenv()
    lease_path = find_sample("임대차")
    terms_path = find_sample("서비스 이용 약관")

    lease_text = lease_path.read_text(encoding="utf-8")
    terms_text = terms_path.read_text(encoding="utf-8")

    run_case("case1-lease-auto", lease_text, auto_search=True)
    run_case("case2-terms-auto", terms_text, auto_search=True)
    run_case("case3-lease-no-search", lease_text, auto_search=False)


if __name__ == "__main__":
    main()

