"""
pipeline_graph.py
-----------------
LangGraph 파이프라인 (단계 2: get_library_portal + search_book)

그래프:
  get_library_portal → search_book → END

역할:
- get_library_portal: catalog_index.yaml에서 해당 구(place)의 포털/카탈로그 홈 URL을 찾음
- search_book: 브라우저 자동화로 도서관 사이트에서 책 검색 및 HTML 저장

CLI 예시:
  PYTHONPATH=00_src python -m graph.pipeline_graph --place gangnam --title "어린 왕자"
"""

from __future__ import annotations
from typing import Dict, Any
import os
from datetime import datetime
import argparse

# LangGraph 기본 컴포넌트
from langgraph.graph import StateGraph, END

# 우리가 만든 노드 함수
from nodes.resolve_catalog import resolve_catalog
from nodes.search_book import search_book


def build_graph():
    """
    그래프: get_library_portal → search_book → END
    """
    graph = StateGraph(dict)  # 상태는 단순히 dict로 사용

    graph.add_node("get_library_portal", resolve_catalog)
    graph.add_node("search_book", search_book)

    graph.set_entry_point("get_library_portal")
    graph.add_edge("get_library_portal", "search_book")
    graph.add_edge("search_book", END)

    return graph.compile()

app = build_graph()


def run_once(place: str, title: str) -> Dict[str, Any]:
    """
    그래프를 한 번 실행한다.

    입력:
      - place: 'gangnam' | 'songpa' | 'seocho' ... 등
      - title: 책 제목(검색어)

    출력: 최종 state(dict)
    """
    initial_state: Dict[str, Any] = {"place": place, "title": title}

    # HTML 저장 경로 설정
    date_str = datetime.now().strftime("%Y-%m-%d")
    default_raw_dir = os.path.join("00_src", "data", "raw", date_str)
    try:
        os.makedirs(default_raw_dir, exist_ok=True)
    except Exception:
        pass

    result_state = app.invoke(initial_state)
    return result_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Library catalog portal lookup → book search")
    parser.add_argument("--place", type=str, required=True, help="예: gangnam | songpa | seocho ...")
    parser.add_argument("--title", type=str, required=True, help="검색어(도서명)")
    args = parser.parse_args()

    result = run_once(args.place, args.title)
    
    if result.get("found"):
        print(f"✓ 도서관 포털 URL: {result.get('catalog_home_url')}")
    else:
        print(f"✗ 도서관 포털을 찾을 수 없습니다: {result.get('reason', 'unknown')}")
    
    if result.get("ok"):
        print(f"✓ 검색 성공")
        saved_html_paths = result.get("saved_html_paths", [result.get("saved_html_path")])
        saved_html_paths = [p for p in saved_html_paths if p]
        if saved_html_paths:
            print(f"✓ 저장된 HTML: {len(saved_html_paths)}개")
            for idx, path in enumerate(saved_html_paths, 1):
                print(f"  [{idx}] {path}")
    elif result.get("search_error"):
        print(f"✗ 검색 실패: {result.get('search_error')}")