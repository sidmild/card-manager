import streamlit as st
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json

# ==========================================
# 🚀 1. 연결 정보 캐싱 (가장 빠르고 확실한 아이디 연결 방식)
# ==========================================

def init_connection():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    key_dict = json.loads(st.secrets["google_key"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    
    sheet_id = "13OWFBm3CA37LHKt3eMPLUWZfnUrrYUEAmH1GsNANVeo"
    return client.open_by_key(sheet_id)

doc = init_connection()
record_sheet = doc.worksheet("출납기록")
card_sheet = doc.worksheet("카드목록")
user_sheet = doc.worksheet("사용자목록")
purpose_sheet = doc.worksheet("품의내용목록")

# ==========================================
# 🚀 2. 데이터 임시 저장 (속도 향상 핵심 기술)
# ==========================================
@st.cache_data(ttl=30) # 30초 동안 구글에 안 묻고 기억한 것을 0.1초만에 보여줌
def load_data():
    c_list = [c for c in card_sheet.col_values(2)[1:] if c]
    u_list = [u for u in user_sheet.col_values(1)[1:] if u]
    
    p_records = purpose_sheet.get_all_values()
    p_list = []
    if len(p_records) > 1:
        for row in p_records[1:]:
            if row[0]:
                drafter = row[1] if len(row) > 1 and row[1] else "지정안됨"
                p_list.append(f"{row[0]} (품의자: {drafter})")
                
    r_records = record_sheet.get_all_values()
    return c_list, u_list, p_list, r_records

# 함수를 실행해서 기억된 데이터를 불러옵니다.
card_list, user_list, purpose_list, all_records = load_data()

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

# --- 페이지 이동(Session State) 초기화 ---
if 'page' not in st.session_state:
    st.session_state.page = 'main'

def change_page(page_name):
    st.session_state.page = page_name

# ==========================================
# 3. 화면 구성
# ==========================================
st.set_page_config(page_title="카드 출납 관리", layout="centered")

# --- 화면 A: 메인 화면 ---
if st.session_state.page == 'main':
    st.title("💳 법인카드 출납 시스템")
    st.write("원하시는 작업을 선택해 주세요.")
    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🟩 카드 수령하기", use_container_width=True):
            change_page('checkout')
            st.rerun()
    with col2:
        if st.button("🟥 카드 반납하기", use_container_width=True):
            change_page('return')
            st.rerun()
            
    st.divider()
    if st.button("⚙️ 관리자 메뉴", use_container_width=False):
        change_page('admin')
        st.rerun()

# --- 화면 B: 카드 수령 화면 ---
elif st.session_state.page == 'checkout':
    if st.button("🔙 뒤로 가기"):
        change_page('main')
        st.rerun()
        
    st.header("🟩 카드 수령 등록")
    st.subheader("📌 현재 카드 사용 현황")
    if not checked_out_list:
        st.info("모든 카드가 반납되어 사무실에 있습니다.")
    else:
        for item in checked_out_list:
            st.warning(f"사용중: {item['display']}")
            
    st.divider()
    
    st.subheader("📝 수령 정보 입력")
    user_name = st.selectbox("사용자 이름 (수령자)", user_list)
    
    if not available_cards:
        st.error("현재 남은 카드가 없습니다!")
    else:
        card_selection = st.selectbox("수령할 카드", available_cards)
        purpose_options = purpose_list + ["기타 (직접 입력)"]
        selected_purpose = st.selectbox("품의 내용 / 품의자", purpose_options)
        
        if selected_purpose == "기타 (직접 입력)":
            purpose_content = st.text_input("직접 입력해 주세요 (예: 물품구입 / 홍길동)")
        else:
            purpose_content = selected_purpose
            
        if st.button("수령 완료", type="primary"):
            if purpose_content:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = [current_time, "", user_name, card_selection, purpose_content, "수령", "0"]
                record_sheet.append_row(new_row)
                
                # 🚀 장부를 수정했으니 기존 기억을 지우고 새로고침!
                st.cache_data.clear() 
                
                st.success(f"✅ 수령 등록 완료! 메인 화면으로 돌아갑니다.")
                change_page('main')
                st.rerun()
            else:
                st.warning("⚠️ 내용을 입력해 주세요.")

# --- 화면 C: 카드 반납 화면 ---
elif st.session_state.page == 'return':
    if st.button("🔙 뒤로 가기"):
        change_page('main')
        st.rerun()
        
    st.header("🟥 카드 반납 등록")
    if not checked_out_list:
        st.info("현재 반납할 카드가 없습니다.")
    else:
        options_display = [item["display"] for item in checked_out_list]
        selected_display = st.selectbox("반납할 카드를 고르세요", options_display)
        selected_item = next(item for item in checked_out_list if item["display"] == selected_display)
        
        return_amount = st.number_input("사용 금액 (원)", min_value=0, step=1000)
        return_note = st.text_input("반납 메모 (선택)", placeholder="영수증 제출 등 특이사항")
        
        if st.button("반납 완료", type="primary"):
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row_num = selected_item["row_num"]
            
            record_sheet.update_cell(row_num, 2, current_time) 
            record_sheet.update_cell(row_num, 6, "반납")      
            record_sheet.update_cell(row_num, 7, return_amount) 
            
            if return_note:
                existing_purpose = selected_item["row_data"][4]
                record_sheet.update_cell(row_num, 5, f"{existing_purpose} [{return_note}]")
                
            # 🚀 반납 처리 후 캐시 초기화!
            st.cache_data.clear()
            
            st.success("✅ 반납 완료! 메인 화면으로 돌아갑니다.")
            change_page('main')
            st.rerun()

# --- 화면 D: 관리자 화면 ---
elif st.session_state.page == 'admin':
    if st.button("🔙 뒤로 가기"):
        change_page('main')
        st.rerun()
        
    st.header("⚙️ 관리자 전용")
    password = st.text_input("비밀번호", type="password")
    
    if password == "1234":
        st.success("인증 성공")
        st.write("전체 출납 내역 조회 (금액 포함)")
        
        if len(all_records) > 1:
            df = pd.DataFrame(all_records[1:], columns=all_records[0])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("데이터가 없습니다.")