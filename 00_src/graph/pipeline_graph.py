"""
pipeline_graph.py
-----------------
LangGraph 파이프라인 (단계 2: get_library_portal + parse_html)

그래프:
  get_library_portal → parse_html → END

역할:
- get_library_portal: catalog_index.yaml에서 해당 구(place)의 포털/카탈로그 홈 URL을 찾음
- parse_html: 저장된 HTML을 BeautifulSoup으로 DOM 직독 파싱 → 최소 필수 필드(title, library, status_raw, available)

CLI 예시:
  PYTHONPATH=00_src python -m graph.pipeline_graph --place gangnam --title "어린 왕자" --html-path 00_src/data/raw/2025-01-01/gangnam_results.html
"""

from __future__ import annotations
from typing import Dict, Any, Optional
import os
from datetime import datetime
import argparse

# LangGraph 기본 컴포넌트
from langgraph.graph import StateGraph, END

# 우리가 만든 노드 함수
from nodes.resolve_catalog import resolve_catalog
from nodes.parse_html import parse_html


def build_graph():
    """
    그래프: get_library_portal → parse_html → END
    """
    graph = StateGraph(dict)  # 상태는 단순히 dict로 사용

    graph.add_node("get_library_portal", resolve_catalog)
    graph.add_node("parse_html", parse_html)

    graph.set_entry_point("get_library_portal")
    graph.add_edge("get_library_portal", "parse_html")
    graph.add_edge("parse_html", END)

    return graph.compile()

app = build_graph()


def run_once(place: str, title: str, html_path: Optional[str] = None) -> Dict[str, Any]:
    """
    그래프를 한 번 실행한다.

    입력:
      - place: 'gangnam' | 'songpa' | 'seocho' ... 등
      - title: 책 제목(검색어)
      - html_path: 저장된 HTML 파일 경로

    출력: 최종 state(dict)
    """
    initial_state: Dict[str, Any] = {"place": place, "title": title}

    # parse_html을 위한 출력 경로 설정
    date_str = datetime.now().strftime("%Y-%m-%d")
    default_parsed_dir = os.path.join("00_src", "data", "parsed", date_str)
    try:
        os.makedirs(default_parsed_dir, exist_ok=True)
    except Exception:
        pass

    default_jsonl = os.path.join(default_parsed_dir, f"{place}_results.jsonl")
    default_json = os.path.join(default_parsed_dir, f"{place}_results.json")

    env_out_jsonl = os.environ.get("TEST_OUT_JSONL")
    env_out_json = os.environ.get("TEST_OUT_JSON")

    if env_out_jsonl:
        initial_state["out_jsonl"] = env_out_jsonl
    else:
        initial_state["out_jsonl"] = default_jsonl

    if env_out_json:
        initial_state["out_json"] = env_out_json
    else:
        initial_state["out_json"] = default_json

    # HTML 경로 설정
    if html_path:
        initial_state["saved_html_path"] = html_path

    result_state = app.invoke(initial_state)
    return result_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Library catalog portal lookup → HTML parse")
    parser.add_argument("--place", type=str, required=True, help="예: gangnam | songpa | seocho ...")
    parser.add_argument("--title", type=str, required=True, help="검색어(도서명)")
    parser.add_argument("--html-path", type=str, help="저장된 HTML 경로")
    parser.add_argument("--out-jsonl", type=str, help="JSONL 저장 경로")
    parser.add_argument("--out-json", type=str, help="JSON 저장 경로")
    args = parser.parse_args()

    if args.out_jsonl:
        os.environ["TEST_OUT_JSONL"] = args.out_jsonl
    if args.out_json:
        os.environ["TEST_OUT_JSON"] = args.out_json

    result = run_once(args.place, args.title, html_path=args.html_path)
    
    if result.get("found"):
        print(f"✓ 도서관 포털 URL: {result.get('catalog_home_url')}")
    else:
        print(f"✗ 도서관 포털을 찾을 수 없습니다: {result.get('reason', 'unknown')}")