import streamlit as st
import os
import json
from typing import List, Dict, Optional, Tuple
import requests
from dotenv import load_dotenv
from math import radians, sin, cos, sqrt, atan2

load_dotenv()

KAKAO_REST_KEY = os.getenv("KAKAO_REST_KEY")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}

ALLOWED_REGION = ["강남구", "서초구", "송파구"]

LIBRARY_ADDRESS_MAP = {
    "도곡정보문화도서관": "서울특별시 강남구 도곡로18길 57",
    "개포하늘꿈도서관": "서울특별시 강남구 개포로110길 54",
    "논현도서관": "서울특별시 강남구 학동로43길 17"
}

TIMEOUT = 5   # API 요청 타임아웃 (초)
TOP_N_MAP = 1  # 지도에 표시할 도서관 개수

st.set_page_config(
    page_title="Book Toss - 도서관 검색",
    page_icon="📚",
)

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371  # 지구 반지름 (km)

    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c

def parse_jsonl(jsonl_text: str) -> List[Dict]:
    results = []
    for line in jsonl_text.strip().split('\n'):
        if line.strip():
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return results


def get_coordinates(address: str) -> Optional[Tuple[float, float, str]]:
    try:
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        params = {"query": address}
        response = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        documents = data.get("documents", [])
        
        if not documents:
            return None
            
        doc = documents[0]
        lng = float(doc["x"])
        lat = float(doc["y"])
        region = doc["address"].get("region_2depth_name", "")
        
        if not region:
            return None
        
        return (lng, lat, region)
    except Exception as e:
        st.error(f"좌표 변환 중 오류: {e}")
        return None

def get_library_with_distance(library_name: str, user_lat: float, user_lng: float) -> Optional[Dict]:
    if library_name not in LIBRARY_ADDRESS_MAP:
        return None
    
    address = LIBRARY_ADDRESS_MAP[library_name]
    coords = get_coordinates(address)
    
    if not coords:
        return None
    
    lib_lng, lib_lat, _ = coords
    straight_distance_km = calculate_distance(user_lat, user_lng, lib_lat, lib_lng)

    return {
        "name": library_name,
        "address": address,
        "lat": lib_lat,
        "lng": lib_lng,
        "straight_distance": straight_distance_km,
    }


def process_book_results(jsonl_data: str, user_lat: float, user_lng: float) -> Tuple[List[Dict], List[Dict]]:
    """도서 검색 결과 처리 및 도서관별 거리 계산"""
    results = parse_jsonl(jsonl_data)

    # 도서관별로 그룹화 (available=true만)
    available_libraries = {}
    for item in results:
        if item.get("available", False):
            lib_name = item["library"]
            if lib_name not in available_libraries:
                available_libraries[lib_name] = []
            available_libraries[lib_name].append(item)

    # 도서관 좌표 및 거리 계산
    library_coords = []
    for lib_name in available_libraries.keys():
        lib_info = get_library_with_distance(lib_name, user_lat, user_lng)
        if lib_info:
            lib_info["books"] = available_libraries[lib_name]
            library_coords.append(lib_info)
    
    # 거리순 정렬
    library_coords.sort(key=lambda x: x["straight_distance"])

    # 지도용 (상위 N개)
    map_libraries = library_coords[:TOP_N_MAP]
    
    return map_libraries, library_coords

def generate_map_html(user_lat: float, user_lng: float, 
                     library_coords: List[Dict], book_name: str) -> str:
    """카카오맵 HTML 생성"""

    user_html = f"""
        <div class="user"">
            <div>내 위치</div>
        </div>
        """

    markers_js = f"""
        var userLatLng = new kakao.maps.LatLng({user_lat}, {user_lng});
        var userMarker = new kakao.maps.Marker({{
            position: userLatLng,
            map: map,
            image: new kakao.maps.MarkerImage(
                "https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png",
                new kakao.maps.Size(24, 35)
            )
        }});
        bounds.extend(userLatLng);

        var userOverlay = new kakao.maps.CustomOverlay({{
            content: `{user_html}`,
            map: null,
            position: userMarker.getPosition()
        }});

        userOverlay.setMap(map);
        
        var overlays = [];
    """
    
    for idx, lib in enumerate(library_coords):
        info_html = f"""
        <div class="wrap">
            <div class="info">
                <div class="title">
                    {lib['name']}
                    <div class="close" onclick="closeOverlay({idx})" title="닫기"></div>
                </div>
                <div class="body">
                    <div class="desc">
                        <div class="ellipsis">📍 {lib['address']}</div>
                        <div>⏱️ 이동시간: {duration_text}</div>
                        <div>📏 이동거리: {distance_text}</div>
                        <div>⤴️ <a href='https://map.kakao.com/link/from/내위치,{user_lat},{user_lng}/to/{lib['name']},{lib['lat']},{lib['lng']}' target='_blank' class='link'>길찾기</a></div>
                    </div>
                </div>
            </div>
        </div>
        """

        markers_js += f"""
            (function(index) {{
                var libLatLng = new kakao.maps.LatLng({lib['lat']}, {lib['lng']});
                var marker = new kakao.maps.Marker({{
                    position: libLatLng,
                    map: map
                }});

                var overlay = new kakao.maps.CustomOverlay({{
                    content: `{info_html}`,
                    map: null,
                    position: marker.getPosition()
                }});
                
                overlays[index] = overlay;
                
                kakao.maps.event.addListener(marker, 'click', function() {{
                    overlay.setMap(map);
                }});
                
                bounds.extend(libLatLng);
            }})({idx});
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <script type="text/javascript"
            src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_API_KEY}&libraries=services">
        </script>
    </head>
    <body style="margin:0px">
        <div id="map" style="width:100%;height:550px;border-radius:15px;"></div>
        <script>
            var mapContainer = document.getElementById('map');
            var mapOption = {{
                center: new kakao.maps.LatLng({user_lat}, {user_lng}),
                level: 6
            }};
            var map = new kakao.maps.Map(mapContainer, mapOption);
            var bounds = new kakao.maps.LatLngBounds();
            {markers_js}
            
            function closeOverlay(index) {{
                if (overlays[index]) {{
                    overlays[index].setMap(null);
                }}
            }}
            
            map.setBounds(bounds);
        </script>
    </body>
    </html>
    """

# 헤더
st.markdown("""
    <div class="main-header">
        <div class="main-title">📚 Book Toss</div>
        <div class="subtitle">내 근처 공공 도서관을 쉽게 찾아보세요</div>
    </div>
    """, unsafe_allow_html=True)

# 검색 폼
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    address = st.text_input(
        "📍 내 주소",
        placeholder="서울특별시 강남구 개포로 416"
    )

with col2:
    book_name = st.text_input(
        "📖 찾고 싶은 도서",
        placeholder="트렌드 코리아 2026"
    )

with col3:
    st.write("")
    st.write("")
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
if ("address" in st.session_state and "book_name" in st.session_state and
    st.session_state["address"].strip() and st.session_state["book_name"].strip()):
    # st.markdown("---")
    
    with st.spinner("🔍 도서관 검색 중..."):
        # 사용자 위치 좌표 가져오기
        user_coords = get_coordinates(st.session_state["address"])

        user_lng, user_lat, user_region = user_coords
        
        jsonl_data = """
            {"title": "도서 (큰글자책) 숨결이 바람 될 때", "library": "행복한도서관", "status_raw": "대출가능", "available": true, "room": "[행복한] 큰글자책", "call_number": "큰글", "year": "2018", "cover_image": "https://image.aladin.co.kr/product/8992/81/cover500/8965961955_1.jpg", "publisher": "도서"}
            {"title": "도서 [큰글자도서] 숨결이 바람 될 때", "library": "논현도서관", "status_raw": "대출가능", "available": true, "room": "[큰글자도서] 숨결이", "call_number": "큰", "year": "2018", "cover_image": "https://image.aladin.co.kr/product/8992/81/cover500/8965961955_1.jpg", "publisher": "도서"}
            {"title": "도서 숨결이 바람 될 때", "library": "논현도서관", "status_raw": "대출불가", "available": false, "room": "[큰글자도서] 숨결이", "call_number": "큰", "year": "2018", "cover_image": "https://image.aladin.co.kr/product/8992/81/cover500/8965961955_1.jpg", "publisher": "도서"}
            {"title": "도서 (큰글씨책) 숨결이 바람 될 때", "library": "대치도서관", "status_raw": "대출불가", "available": false, "room": "[대치] 큰글씨책", "call_number": "큰글", "year": "2018", "cover_image": "https://image.aladin.co.kr/product/8992/81/cover500/8965961955_1.jpg", "publisher": "도서"}
            {"title": "도서 숨결이 바람 될 때", "library": "대치도서관", "status_raw": "status_raw": "대출가능", "available": true, "[대치] 큰글씨책", "call_number": "큰글", "year": "2018", "cover_image": "https://image.aladin.co.kr/product/8992/81/cover500/8965961955_1.jpg", "publisher": "도서"}
            {"title": "도서 WHEN BREATH BECOMES", "library": "일원본동주민도서관", "status_raw": "status_raw": "대출가능", "available": true, "room": "[일원본동문고] 일반자료실", "call_number": "848-폴872w", "year": "2016", "cover_image": "https://image.aladin.co.kr/product/8992/81/cover500/8965961955_1.jpg", "publisher": "도서"}"""
        
        map_libraries, all_libraries = process_book_results(jsonl_data, user_lat, user_lng)

        if not all_libraries:
            st.warning("⚠️ 현재 대출 가능한 도서관을 찾을 수 없습니다.")
            st.stop()

        # 결과 카드
        st.markdown(f"""
        <div class="result-card">
            <h3>📖 {st.session_state['book_name']}</h3>
            <p style="margin:0.5rem 0 0 0; opacity:0.9;">
                📍 {user_region}에서 대출 가능한 도서관 {len(all_libraries)}곳을 찾았어요!
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 지도 표시 (가장 가까운 N개)
        if map_libraries:
            st.markdown(f"### 🗺️ 가장 가까운 도서관")
            map_html = generate_map_html(
                user_lat, user_lng, map_libraries, st.session_state['book_name']
            )
            st.components.v1.html(map_html, height=570)
        
        # 전체 도서관 목록
        st.markdown("### 🏛️ 대출 가능 도서관 목록 (가까운 순)")
        for idx, lib in enumerate(all_libraries):
            is_top = idx < TOP_N_MAP
            status_class = "available" if is_top else ""
            distance_text = lib.get("straight_distance", lib["straight_distance"])

            with st.container():
                st.markdown(f"""
                <div class="library-item {status_class}">
                    <h4>
                        {'🥇' if idx == 0 else '🥈' if idx == 1 else ''} {lib['name']}
                    </h4>
                    <p style="margin:0 0; display:flex; align-items:center; gap:0.4rem;">
                        <span style="flex:0 1 auto; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                            {lib['address']}
                        </span>
                    </p>
                    <div style="margin-top:0.3rem; color:#4a5568; font-size:0.9rem;">
                        📏 {distance_text}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"📚 대출 가능 도서 {len(lib['books'])}권")
