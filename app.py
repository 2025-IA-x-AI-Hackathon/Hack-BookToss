import streamlit as st

st.set_page_config(
    page_title="Book Toss - 도서관 검색",
    page_icon="📚",
)

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
        st.session_state["address"] = address
        st.session_state["book_name"] = book_name
