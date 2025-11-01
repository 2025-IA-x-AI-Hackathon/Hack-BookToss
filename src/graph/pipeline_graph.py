# src/graph/pipeline_graph.py

from __future__ import annotations
from typing import Dict, Any, Optional
import os
import argparse
from datetime import datetime

# 아직 그래프 연결하지 않음
# from langgraph.graph import StateGraph, END

# 최소 의존: 파서만
from src.nodes.parse_html import parse_html  # state(dict) -> state(dict)

def run_once(place: str, title: str, html_path: Optional[str] = None) -> Dict[str, Any]:
    """
    v0: HTML만 주면 파싱. (그래프 도입 전)
    """
    state: Dict[str, Any] = {"place": place, "title": title}

    # 출력 경로 기본값(디버깅 안전장치)
    date_str = datetime.now().strftime("%Y-%m-%d")
    default_dir = os.path.join("data", "parsed", date_str)
    os.makedirs(default_dir, exist_ok=True)
    state["out_jsonl"] = os.environ.get("OUT_JSONL", os.path.join(default_dir, f"{place}_results.jsonl"))
    state["out_json"]  = os.environ.get("OUT_JSON",  os.path.join(default_dir, f"{place}_results.json"))

    # v0 모드: html_path 필수
    if not html_path:
        return {"ok": False, "parse_success": False, "parse_error": "html_path required in v0"}

    state["saved_html_path"] = html_path
    return parse_html(state)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--place", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--html-path", required=True, help="저장된 HTML 경로 (v0에서는 필수)")
    parser.add_argument("--out-jsonl")
    parser.add_argument("--out-json")
    args = parser.parse_args()

    if args.out_jsonl: os.environ["OUT_JSONL"] = args.out_jsonl
    if args.out_json:  os.environ["OUT_JSON"]  = args.out_json

    out = run_once(args.place, args.title, html_path=args.html_path)
    print(out.get("parse_success"), out.get("parse_error"), out.get("saved"))