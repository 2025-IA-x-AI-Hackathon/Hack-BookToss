import streamlit as st
import html
import os
from typing import Optional, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_REST_KEY = os.getenv("KAKAO_REST_KEY")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
TIMEOUT = 5


st.set_page_config(
    page_title="Book Toss - 도서관 검색",
    page_icon="📚",
)


@st.cache_data(show_spinner=False)
def geocode_address(address: str, rest_key: str) -> Optional[Tuple[float, float]]:
    """카카오 주소 검색 API로 좌표 조회"""
    if not rest_key:
        raise ValueError("REST API 키가 설정되지 않았습니다.")

    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {rest_key}"}
    params = {"query": address}

    response = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    documents = response.json().get("documents", [])
    if not documents:
        return None

    document = documents[0]
    lng = float(document["x"])
    lat = float(document["y"])
    return lat, lng


def generate_user_map_html(lat: float, lng: float, address: str) -> str:
    """사용자 위치만 마커로 표시하는 카카오맵 HTML 생성"""
    if not KAKAO_REST_KEY:
        raise ValueError("JavaScript SDK 키가 설정되지 않았습니다.")

    safe_address = html.escape(address)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <script type="text/javascript"
            src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_REST_KEY}&libraries=services">
        </script>
    </head>
    <body style="margin:0">
        <div id="map" style="width:100%;height:400px;border-radius:15px;"></div>
        <script>
            var mapContainer = document.getElementById('map');
            var mapOption = {{
                center: new kakao.maps.LatLng({lat}, {lng}),
                level: 3
            }};
            var map = new kakao.maps.Map(mapContainer, mapOption);
            var markerPosition  = new kakao.maps.LatLng({lat}, {lng});
            var marker = new kakao.maps.Marker({{
                position: markerPosition,
                map: map
            }});
            var infowindow = new kakao.maps.InfoWindow({{
                content: '<div style="padding:8px 12px;">📍 {safe_address}</div>'
            }});
            infowindow.open(map, marker);
        </script>
    </body>
    </html>
    """


# 헤더
st.markdown(
    """
<div class="main-header">
    <div class="main-title">📚 Book Toss</div>
    <div class="subtitle">내 근처 공공 도서관을 쉽게 찾아보세요</div>
</div>
""",
    unsafe_allow_html=True,
)


# 검색 폼
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    address = st.text_input(
        "📍 내 주소",
        placeholder="서울특별시 강남구 개포로 416",
    )

with col2:
    book_name = st.text_input(
        "📖 찾고 싶은 도서",
        placeholder="트렌드 코리아 2026",
    )

with col3:
    search_btn = st.button("🔍 검색하기", use_container_width=True)


# 검색 실행
if search_btn:
    if not address.strip():
        st.warning("📍 주소를 입력해주세요")
        st.stop()
    elif not book_name.strip():
        st.warning("📖 도서명을 입력해주세요")
        st.stop()
    else:
        st.session_state["address"] = address.strip()
        st.session_state["book_name"] = book_name.strip()


# 결과 표시
stored_address = st.session_state.get("address")
stored_book = st.session_state.get("book_name")

if stored_address and stored_book:
    st.markdown(
        f"""
        <div class="result-card" style="margin-top:1.5rem; padding:1.2rem 1.5rem; border-radius:16px; background:#f7f8ff;">
            <h3 style="margin:0;">📖 {stored_book}</h3>
            <p style="margin:0.6rem 0 0 0; opacity:0.85;">입력한 주소를 기준으로 지도를 표시합니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not KAKAO_REST_KEY:
        st.error("카카오 REST API 키가 설정되어 있지 않아 주소 좌표를 찾을 수 없습니다.")
    else:
        try:
            coords = geocode_address(stored_address, KAKAO_REST_KEY)
        except ValueError as exc:
            st.error(str(exc))
            coords = None
        except requests.RequestException as exc:
            st.error(f"주소 좌표 조회 중 문제가 발생했습니다: {exc}")
            coords = None

        if coords is None:
            st.warning("입력한 주소를 찾을 수 없었습니다. 조금 더 정확한 주소로 다시 시도해주세요.")
        else:
            user_lat, user_lng = coords

            st.markdown(
                f"<div style='margin-top:1rem; color:#4a5568;'>📍 {stored_address}</div>",
                unsafe_allow_html=True,
            )

            if not KAKAO_REST_KEY:
                st.info("카카오 지도 JavaScript 키가 없어 텍스트 정보만 표시합니다.")
            else:
                map_html = generate_user_map_html(user_lat, user_lng, stored_address)
                st.components.v1.html(map_html, height=420)
