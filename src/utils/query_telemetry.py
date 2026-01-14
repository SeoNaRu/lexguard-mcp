"""
Query Telemetry - 검색 쿼리 로그 및 측정
어떤 쿼리가 성공했는지, 0 비율, 재시도 횟수 등을 추적
"""
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger("lexguard-mcp")


class QueryTelemetry:
    """쿼리 텔레메트리"""
    
    def __init__(self):
        # 인메모리 통계 (실제로는 DB나 파일에 저장)
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "empty_results": 0,
            "retry_count": defaultdict(int),
            "synonym_expansions": defaultdict(int),
            "domain_classifications": defaultdict(int),
            "avg_results_per_query": [],
            "query_patterns": defaultdict(int)
        }
        
        # 리플레이 가능한 요청 로그 (최근 N개만 유지)
        self.request_logs = []  # 최근 100개만 유지
        self.max_logs = 100
    
    def log_query(
        self,
        query: str,
        total: int,
        attempts: int = 1,
        fallback_used: bool = False,
        issue_type: Optional[str] = None,
        classified_domains: Optional[List[str]] = None
    ):
        """
        쿼리 실행 로그 기록
        
        Args:
            query: 검색 쿼리
            total: 결과 수
            attempts: 시도 횟수
            fallback_used: fallback 사용 여부
            issue_type: 쟁점 유형
            classified_domains: 분류된 도메인 리스트
        """
        self.stats["total_queries"] += 1
        
        if total > 0:
            self.stats["successful_queries"] += 1
            self.stats["avg_results_per_query"].append(total)
        else:
            self.stats["empty_results"] += 1
        
        if attempts > 1:
            self.stats["retry_count"][attempts] += 1
        
        if fallback_used:
            self.stats["query_patterns"]["fallback_used"] += 1
        
        if issue_type:
            self.stats["domain_classifications"][issue_type] += 1
        
        if classified_domains:
            for domain in classified_domains:
                self.stats["domain_classifications"][domain] += 1
        
        # 간단한 쿼리 패턴 추출
        query_lower = query.lower()
        if "프리랜서" in query_lower or "근로자성" in query_lower:
            self.stats["query_patterns"]["labor_issue"] += 1
        elif "재산분할" in query_lower or "이혼" in query_lower:
            self.stats["query_patterns"]["divorce"] += 1
        elif "손해배상" in query_lower:
            self.stats["query_patterns"]["damages"] += 1
        
        # 리플레이 가능한 로그 저장
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "total": total,
            "attempts": attempts,
            "fallback_used": fallback_used,
            "issue_type": issue_type,
            "classified_domains": classified_domains or []
        }
        self.request_logs.append(log_entry)
        
        # 최대 로그 수 제한
        if len(self.request_logs) > self.max_logs:
            self.request_logs = self.request_logs[-self.max_logs:]
        
        # 로그 출력 (DEBUG 레벨)
        logger.debug(
            "Query telemetry | query=%r total=%d attempts=%d fallback=%s issue_type=%s",
            query[:50], total, attempts, fallback_used, issue_type
        )
    
    def get_replay_data(self, query: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        리플레이 가능한 요청 데이터 반환
        
        Args:
            query: 특정 쿼리로 필터링 (선택사항)
            limit: 반환할 최대 개수
            
        Returns:
            요청 로그 리스트
        """
        logs = self.request_logs
        
        if query:
            logs = [log for log in logs if query.lower() in log.get("query", "").lower()]
        
        return logs[-limit:]
    
    def replay_request(self, log_entry: Dict) -> Dict:
        """
        저장된 요청을 재실행하기 위한 정보 반환
        
        Args:
            log_entry: 저장된 로그 엔트리
            
        Returns:
            재실행 가능한 요청 정보
        """
        return {
            "query": log_entry.get("query"),
            "issue_type": log_entry.get("issue_type"),
            "timestamp": log_entry.get("timestamp"),
            "original_result": {
                "total": log_entry.get("total"),
                "attempts": log_entry.get("attempts"),
                "fallback_used": log_entry.get("fallback_used")
            }
        }
    
    def log_synonym_expansion(
        self,
        original_query: str,
        expanded_query: str,
        success: bool
    ):
        """동의어 확장 로그"""
        if success:
            self.stats["synonym_expansions"][expanded_query] += 1
    
    def get_stats(self) -> Dict:
        """통계 반환"""
        avg_results = 0.0
        if self.stats["avg_results_per_query"]:
            avg_results = sum(self.stats["avg_results_per_query"]) / len(self.stats["avg_results_per_query"])
        
        return {
            "total_queries": self.stats["total_queries"],
            "successful_queries": self.stats["successful_queries"],
            "empty_results": self.stats["empty_results"],
            "success_rate": (
                self.stats["successful_queries"] / self.stats["total_queries"]
                if self.stats["total_queries"] > 0 else 0.0
            ),
            "empty_rate": (
                self.stats["empty_results"] / self.stats["total_queries"]
                if self.stats["total_queries"] > 0 else 0.0
            ),
            "avg_results_per_query": avg_results,
            "retry_distribution": dict(self.stats["retry_count"]),
            "domain_classifications": dict(self.stats["domain_classifications"]),
            "query_patterns": dict(self.stats["query_patterns"]),
            "top_synonym_expansions": dict(
                sorted(
                    self.stats["synonym_expansions"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            )
        }
    
    def reset_stats(self):
        """통계 초기화"""
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "empty_results": 0,
            "retry_count": defaultdict(int),
            "synonym_expansions": defaultdict(int),
            "domain_classifications": defaultdict(int),
            "avg_results_per_query": [],
            "query_patterns": defaultdict(int)
        }


# 전역 인스턴스
_telemetry = None


def get_telemetry() -> QueryTelemetry:
    """QueryTelemetry 싱글톤 인스턴스 반환"""
    global _telemetry
    if _telemetry is None:
        _telemetry = QueryTelemetry()
    return _telemetry

