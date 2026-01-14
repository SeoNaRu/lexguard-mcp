"""
동적 MCP 툴 생성기
api_crawler의 메타데이터를 기반으로 MCP 툴을 동적으로 생성
"""
from typing import List, Dict, Any, Optional
from ..tools.api_metadata_loader import get_metadata_loader


class DynamicToolGenerator:
    """동적으로 MCP 툴을 생성하는 클래스"""
    
    def __init__(self):
        self.metadata_loader = get_metadata_loader()
    
    def generate_tool_schema(self, api_info: Dict) -> Dict:
        """
        API 정보를 기반으로 MCP 툴 스키마를 생성합니다
        
        Args:
            api_info: api_index.json의 API 정보
            
        Returns:
            MCP 툴 스키마 딕셔너리
        """
        api_id = api_info.get("id")
        api_name = api_info.get("api_name", "")
        file_name = api_info.get("file", "")
        
        # API 상세 정보 로드
        api_detail = self.metadata_loader.load_api_detail(api_id)
        if not api_detail:
            return None
        
        request_parameters = api_detail.get("request_parameters", [])
        
        # 툴 이름 생성 (영문, 소문자, 언더스코어)
        tool_name = self._generate_tool_name(api_name, api_id)
        
        # 입력 스키마 생성
        properties = {}
        required = []
        
        for param in request_parameters:
            param_name = param.get("name", "")
            param_type = param.get("type", "string")
            param_required = param.get("required", False)
            param_desc = param.get("description", "")
            
            # target, type 등은 자동으로 설정되므로 제외
            if param_name in ["target", "type"]:
                continue
            
            # OC는 API 키이므로 제외 (별도 처리)
            if param_name == "OC":
                continue
            
            # JSON 스키마 타입 변환
            json_type = self._convert_type_to_json_schema(param_type)
            
            properties[param_name] = {
                "type": json_type,
                "description": param_desc
            }
            
            # 기본값이 있는 경우 추가
            if "default" in param:
                properties[param_name]["default"] = param.get("default")
            
            # 필수 파라미터
            if param_required:
                required.append(param_name)
        
        # API ID는 항상 포함 (내부적으로 사용)
        properties["_api_id"] = {
            "type": "integer",
            "description": "API ID (내부 사용)",
            "default": api_id
        }
        
        tool_schema = {
            "name": tool_name,
            "description": f"{api_name} API를 호출합니다",
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
        
        return tool_schema
    
    def generate_all_tools(self, limit: Optional[int] = None) -> List[Dict]:
        """
        모든 API에 대한 MCP 툴 스키마를 생성합니다
        
        Args:
            limit: 생성할 툴 개수 제한 (None이면 전체)
            
        Returns:
            MCP 툴 스키마 리스트
        """
        apis = self.metadata_loader.get_all_apis()
        
        if limit:
            apis = apis[:limit]
        
        tools = []
        for api_info in apis:
            tool_schema = self.generate_tool_schema(api_info)
            if tool_schema:
                tools.append(tool_schema)
        
        return tools
    
    def generate_tools_by_category(self, category: str) -> List[Dict]:
        """카테고리별로 툴을 생성합니다"""
        apis = self.metadata_loader.get_apis_by_category(category)
        tools = []
        for api_info in apis:
            tool_schema = self.generate_tool_schema(api_info)
            if tool_schema:
                tools.append(tool_schema)
        return tools
    
    def _generate_tool_name(self, api_name: str, api_id: int) -> str:
        """
        API 이름을 기반으로 툴 이름을 생성합니다
        예: "현행법령(시행일) 목록 조회" -> "call_api_1" 또는 "law_list_effective"
        """
        # 간단한 방식: api_call_{id}
        return f"call_api_{api_id}"
    
    def _convert_type_to_json_schema(self, param_type: str) -> str:
        """파라미터 타입을 JSON 스키마 타입으로 변환"""
        type_mapping = {
            "string": "string",
            "char": "string",
            "int": "integer",
            "integer": "integer",
            "float": "number",
            "number": "number",
            "bool": "boolean",
            "boolean": "boolean"
        }
        
        param_type_lower = param_type.lower()
        return type_mapping.get(param_type_lower, "string")
    
    def get_tool_by_api_id(self, api_id: int) -> Optional[Dict]:
        """API ID로 툴 스키마를 가져옵니다"""
        apis = self.metadata_loader.get_all_apis()
        for api_info in apis:
            if api_info.get("id") == api_id:
                return self.generate_tool_schema(api_info)
        return None


# 싱글톤 인스턴스
_tool_generator: Optional[DynamicToolGenerator] = None


def get_tool_generator() -> DynamicToolGenerator:
    """DynamicToolGenerator 싱글톤 인스턴스를 반환합니다"""
    global _tool_generator
    if _tool_generator is None:
        _tool_generator = DynamicToolGenerator()
    return _tool_generator

