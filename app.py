import streamlit as st
import datetime
import gspread
import pandas as pd

# ==========================================
# 1. 연결 정보 세팅
# ==========================================
def init_connection():
    key_dict = dict(st.secrets["google_credentials"])
    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
    client = gspread.service_account_from_dict(key_dict)
    sheet_id = "13OWFBm3CA37LHKt3eMPLUWZfnUrrYUEAmH1GsNANVeo"
    return client.open_by_key(sheet_id)

doc = init_connection()

record_sheet = doc.worksheet("출납기록")
card_sheet = doc.worksheet("카드목록")
user_sheet = doc.worksheet("사용자목록")

# ==========================================
# 2. 데이터 임시 저장
# ==========================================
@st.cache_data(ttl=30)
def load_data():
    c_list = [c for c in card_sheet.col_values(2)[1:] if c]
    u_list = [u for u in user_sheet.col_values(1)[1:] if u]
    r_records = record_sheet.get_all_values()
    return c_list, u_list, r_records

card_list, user_list, all_records = load_data()

# --- 데이터 필터링 ---
checked_out_list = []
if len(all_records) > 1:
    for idx, row in enumerate(all_records[1:], start=2):
        if len(row) >= 6 and row[5] == "수령":
            checked_out_list.append({
                "row_num": idx,
                "display": f"👤 {row[2]} | 💳 {row[3]}",
                "row_data": row
            })

in_use_cards = [item["row_data"][3] for item in checked_out_list]
available_cards = [c for c in card_list if c not in in_use_cards]

KST = datetime.timezone(datetime.timedelta(hours=9))

# --- 페이지 이동 초기화 ---
if 'page' not in st.session_state:
    st.session_state.page = 'main'

def change_page(page_name):
    st.session_state.page = page_name

# ==========================================
# 3. 공통 디자인 (CSS)
# ==========================================
st.set_page_config(page_title="카드 출납 관리", layout="centered")

st.markdown("""
    <style>
    .stApp {
        background-color: #ffffff !important;
        color: #31333F !important;
    }
    
    .stApp p, .stApp span, .stApp label {
        font-size: 20px !important;
    }
    
    .stSelectbox div[data-baseweb="select"] {
        font-size: 18px !important;
    }
    .stTextInput input {
        font-size: 18px !important;
    }
    
    .stRadio div[role="radiogroup"] {
        gap: 15px;
    }
    
    /* 💡 메인 화면의 큰 버튼 (무조건 흰색 고정!) */
    div[data-testid="column"] button[kind="primary"],
    div[data-testid="stColumn"] button[kind="primary"] {
        background-color: #ffffff !important; 
        color: #31333F !important; 
        border: 2px solid #e0e0e0 !important; 
        height: 140px !important;
        font-size: 32px !important;
        font-weight: 900 !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
    }
    div[data-testid="column"] button[kind="primary"]:hover,
    div[data-testid="stColumn"] button[kind="primary"]:hover {
        border-color: #ff4b4b !important;
        color: #ff4b4b !important;
        background-color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 메인 화면 ---
if st.session_state.page == 'main':
    st.markdown("<h1 style='font-size: 40px;'>💳 신용카드 사용대장</h1>", unsafe_allow_html=True)
    st.write("원하시는 작업을 선택해 주세요.")
    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🟩 카드 수령하기", use_container_width=True, type="primary"):
            change_page('checkout')
            st.rerun()
    with col2:
        if st.button("🟥 카드 반납하기", use_container_width=True, type="primary"):
            change_page('return')
            st.rerun()
            
    st.divider()
    if st.button("⚙️ 관리자 메뉴", use_container_width=True):
        change_page('admin')
        st.rerun()

# --- 수령 화면 ---
elif st.session_state.page == 'checkout':
    # 💡 수령 화면 전용: 완료 버튼 초록색 스타일 주입
    st.markdown("""
        <style>
        button[kind="primary"] {
            background-color: #03c75a !important; 
            color: white !important;
            border: none !important;
            font-size: 20px !important;
            font-weight: bold !important;
            border-radius: 10px !important;
            transition: all 0.2s ease-in-out;
        }
        button[kind="primary"]:hover {
            background-color: #00b04e !important; 
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if st.button("🔙 뒤로 가기"):
        change_page('main')
        st.rerun()
        
    st.markdown("<h2 style='font-size: 32px;'>🟩 카드 수령 등록</h2>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 24px;'>📝 수령 정보 입력</h3>", unsafe_allow_html=True)
    
    if not available_cards:
        st.error("현재 남은 카드가 없습니다!")
    else:
        # 💡 1. 수령할 카드를 가장 먼저 선택하도록 위로 배치
        card_selection = st.radio("수령할 카드", available_cards)
        
        # 💡 2. 사용자 이름을 카드 선택 밑으로 이동
        user_name = st.selectbox(
            "사용자 이름 (검색하여 선택)", 
            options=user_list, 
            index=None, 
            placeholder="🔍 이름을 입력하면 자동으로 검색됩니다"
        )
        
        # 💡 3. 메모 작성
        checkout_note = st.text_input("수령 메모 (선택)", placeholder="특이사항을 적어주세요")
        
        if st.button("수령 완료", type="primary", use_container_width=True):
            if not user_name: 
                st.warning("⚠️ 사용자 이름을 검색하여 선택해 주세요.")
            else:
                current_time = datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
                new_row = [current_time, "", user_name, card_selection, checkout_note, "수령"]
                record_sheet.append_row(new_row)
                
                st.cache_data.clear() 
                st.success(f"✅ 수령 등록 완료")
                change_page('main')
                st.rerun()

    st.divider()
    st.markdown("<h3 style='font-size: 24px;'>📌 현재 카드 사용 현황</h3>", unsafe_allow_html=True)
    if not checked_out_list:
        st.info("모든 카드가 반납되어 사무실에 있습니다.")
    else:
        for item in checked_out_list:
            st.warning(f"사용중: {item['display']}")

# --- 반납 화면 ---
elif st.session_state.page == 'return':
    # 💡 반납 화면 전용: 완료 버튼 빨간색 스타일 주입
    st.markdown("""
        <style>
        button[kind="primary"] {
            background-color: #ff4b4b !important; 
            color: white !important;
            border: none !important;
            font-size: 20px !important;
            font-weight: bold !important;
            border-radius: 10px !important;
            transition: all 0.2s ease-in-out;
        }
        button[kind="primary"]:hover {
            background-color: #ff3333 !important; 
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if st.button("🔙 뒤로 가기"):
        change_page('main')
        st.rerun()
        
    st.markdown("<h2 style='font-size: 32px;'>🟥 카드 반납 등록</h2>", unsafe_allow_html=True)
    if not checked_out_list:
        st.info("현재 반납할 카드가 없습니다.")
    else:
        options_display = [item["display"] for item in checked_out_list]
        
        selected_display = st.radio("반납할 카드를 고르세요", options_display)
        selected_item = next(item for item in checked_out_list if item["display"] == selected_display)
        
        return_note = st.text_input("반납 메모 (선택)", placeholder="특이사항을 적어주세요")
        
        if st.button("반납 완료", type="primary", use_container_width=True):
            current_time = datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
            row_num = selected_item["row_num"]
            
            record_sheet.update_cell(row_num, 2, current_time) 
            record_sheet.update_cell(row_num, 6, "반납")      
            
            if return_note:
                existing_note = selected_item["row_data"][4]
                record_sheet.update_cell(row_num, 5, f"{existing_note} [{return_note}]".strip())
                
            st.cache_data.clear()
            st.success("✅ 반납 완료")
            change_page('main')
            st.rerun()

# --- 관리자 화면 ---
elif st.session_state.page == 'admin':
    if st.button("🔙 뒤로 가기"):
        change_page('main')
        st.rerun()
        
    st.markdown("<h2 style='font-size: 32px;'>⚙️ 관리자 전용</h2>", unsafe_allow_html=True)
    password = st.text_input("비밀번호", type="password")
    
    if password == "지출줌1!":
        st.success("인증 성공")
        st.write("전체 출납 내역 조회")
        
        if len(all_records) > 1:
            df = pd.DataFrame(all_records[1:], columns=all_records[0])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("데이터가 없습니다.")