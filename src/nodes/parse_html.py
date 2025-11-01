"""
HTML 파싱 노드 모듈
"""
from __future__ import annotations
from typing import Dict, Any


def parse_html(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    HTML 파일을 파싱하여 결과를 state에 추가합니다.
    
    Args:
        state: 상태 딕셔너리 (place, title, saved_html_path 등 포함)
        
    Returns:
        업데이트된 state 딕셔너리
    """
    # TODO: 실제 HTML 파싱 로직 구현 필요
    state["parse_success"] = False
    state["parse_error"] = "parse_html 함수가 아직 구현되지 않았습니다"
    state["ok"] = False
    return state

