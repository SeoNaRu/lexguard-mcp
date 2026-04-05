"""
Playwright-based article crawler for law.go.kr
Used as fallback when eflawjosub API returns no article content (타법개정 MST)

Approach: 
  1. eflaw search → get MST for the law
  2. Open lsInfoP.do with MST as lsiSeq 
  3. Wait for JS rendering
  4. Extract article text from rendered body (제N조 ~ 제N+1조)
"""
import logging
import re
import requests

logger = logging.getLogger("lexguard-mcp")

# Module-level browser instance for reuse
_pw = None
_browser = None


def _get_browser():
    """Lazy-init Playwright browser (singleton)"""
    global _pw, _browser
    if _browser is None:
        try:
            from playwright.sync_api import sync_playwright
            _pw = sync_playwright().start()
            _browser = _pw.chromium.launch(headless=True)
            logger.info("Playwright browser launched (headless chromium)")
        except Exception as e:
            logger.warning("Playwright not available: %s", e)
            return None
    return _browser


def _find_mst_for_law(law_name: str, api_key: str) -> str | None:
    """eflaw 검색으로 법령의 MST(법령일련번호) 찾기"""
    try:
        import urllib.parse
        encoded = urllib.parse.quote(law_name)
        url = f"https://www.law.go.kr/DRF/lawSearch.do?OC={api_key}&target=eflaw&type=JSON&display=10&query={encoded}&search=1&section=lawNm"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        LawSearch = data.get('LawSearch', {})
        law_list = LawSearch.get('law', [])
        if not isinstance(law_list, list):
            law_list = [law_list] if law_list else []
        
        # 현행 버전 우선, 그 다음 연혁
        for law in law_list:
            현행 = law.get('현행연혁코드', '')
            if 현행 == '현행':
                return law.get('법령일련번호', '')
        
        # 현행이 없으면 첫 번째 결과
        if law_list:
            return law_list[0].get('법령일련번호', '')
        
        return None
    except Exception as e:
        logger.warning("eflaw search failed: %s", e)
        return None


def crawl_article(law_name: str, article_number: str, api_key: str = "") -> str | None:
    """
    law.go.kr에서 Playwright로 조문을 스크래핑합니다.

    1. eflaw 검색 → MST 찾기
    2. lsInfoP.do 페이지 로드 (JS 렌더링 대기)
    3. body 텍스트에서 제N조~제N+1조 사이 내용 추출

    Args:
        law_name: 법령명 (예: '농어촌정비법')
        article_number: 조 번호 (예: '86')
        api_key: DRF API 키 (eflaw 검색용)

    Returns:
        조문 텍스트 또는 None
    """
    browser = _get_browser()
    if not browser:
        return None

    page = None
    try:
        jo_num = re.sub(r'[^0-9]', '', str(article_number))
        if not jo_num:
            return None

        # 1. MST 찾기
        mst = _find_mst_for_law(law_name, api_key)
        if not mst:
            logger.warning("Could not find MST for law: %s", law_name)
            return None

        # 2. lsInfoP.do 페이지 로드
        page = browser.new_page()
        url = f"https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq={mst}&chrClsCd=010202&urlMode=lsInfoP&ancYnChk=0&mobile=&gubun=api"
        page.goto(url, timeout=20000)
        page.wait_for_load_state('networkidle', timeout=15000)
        page.wait_for_timeout(3000)  # AJAX 렌더링 대기

        # 3. body 텍스트에서 조문 추출
        body = page.inner_text('body')
        
        # lsInfoP.do 페이지에는 목차(간단한 조문 제목 목록)와 본문(전체 조문 내용)이 모두 포함됩니다.
        # 목차에서는 각 조문이 한 줄로 요약되어 있습니다.
        # 본문에서는 항 번호(①, ②, 1., 2. 등)가 포함됩니다.
        # 
        # 전략: "제{N}조(" 패턴을 모두 찾고, 항 내용(① 또는 1.)이 포함된 것을 본문으로 선택합니다.
        
        import re as _re
        article_start_pattern = f"제{jo_num}조("
        article_pattern = article_start_pattern  # 기본값
        all_occurrences = [m.start() for m in _re.finditer(_re.escape(article_start_pattern), body)]
        
        start_idx = -1
        for pos in all_occurrences:
            # 해당 위치 이후 200자 안에 ① 또는 "1."이 있으면 본문으로 판단
            chunk = body[pos:pos+200]
            if '①' in chunk or '\n1.' in chunk or '\n1. ' in chunk:
                start_idx = pos
                break
        
        # 본문을 못 찾으면 마지막 발생 위치 사용 (보통 본문이 뒤에 있음)
        if start_idx < 0 and all_occurrences:
            start_idx = all_occurrences[-1]
        
        # 대체 패턴
        if start_idx < 0:
            article_pattern = f"제{jo_num}조"
            all_occurrences2 = [m.start() for m in _re.finditer(_re.escape(article_pattern), body)]
            for pos in all_occurrences2:
                chunk = body[pos:pos+200]
                if '①' in chunk or '\n1.' in chunk:
                    start_idx = pos
                    break
            if start_idx < 0 and all_occurrences2:
                start_idx = all_occurrences2[-1]
        
        if start_idx < 0:
            logger.info("Article %s not found in lsInfoP page for %s", jo_num, law_name)
            return None

        # 다음 조문 찾기 (종료점)
        next_num = int(jo_num) + 1
        end_patterns = [f"제{next_num}조(", f"제{next_num}조"]
        
        end_idx = len(body)
        for ep in end_patterns:
            idx = body.find(ep, start_idx + len(article_pattern))
            if idx > 0 and idx < end_idx:
                end_idx = idx

        content = body[start_idx:end_idx].strip()
        
        if content and len(content) > 20:
            logger.info("Playwright crawled article %s (%d chars)", article_number, len(content))
            return content

        return None

    except Exception as e:
        logger.warning("Playwright crawl failed for %s art %s: %s", law_name, article_number, e)
        return None
    finally:
        if page:
            try:
                page.close()
            except Exception:
                pass


def shutdown():
    """Clean up Playwright resources"""
    global _pw, _browser
    try:
        if _browser:
            _browser.close()
        if _pw:
            _pw.stop()
    except Exception:
        pass
    _browser = None
    _pw = None
