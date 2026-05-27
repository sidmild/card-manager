import streamlit as st
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# --- [1] 구글 시트 연결 설정 ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
client = gspread.authorize(creds)

spreadsheet_name = "카드출납대장(현천고)"
doc = client.open(spreadsheet_name)

record_sheet = doc.worksheet("출납기록")
card_sheet = doc.worksheet("카드목록")

# --- [2] 데이터 불러오기 및 필터링 ---
# 1. 카드 목록 가져오기
card_list_data = card_sheet.col_values(2)[1:] 
card_list = [card for card in card_list_data if card]

# 2. 전체 출납 기록 가져오기
all_records = record_sheet.get_all_values()

checked_out_list = []
if len(all_records) > 1:
    for idx, row in enumerate(all_records[1:], start=2):
        if len(row) >= 6 and row[5] == "수령":
            display_text = f"👤 {row[2]} | 💳 {row[3]} ({row[0]} 수령)"
            checked_out_list.append({
                "row_num": idx,
                "display": display_text,
                "row_data": row
            })

# --- [3] 웹 화면 구성 ---
st.set_page_config(page_title="카드 출납 관리", layout="centered")
st.title("💳 법인카드 출납 관리 시스템")

# 탭을 3개로 확장 (관리자 페이지 추가)
tab1, tab2, tab3 = st.tabs(["▶️ 카드 수령하기", "◀️ 카드 반납하기", "⚙️ 관리자 페이지"])

# --- [ 탭 1: 카드 수령 화면 ] ---
with tab1:
    st.header("카드 수령 등록")
    user_name = st.text_input("사용자 이름", placeholder="홍길동", key="sh_user")
    card_selection = st.selectbox("수령할 카드 선택", card_list, key="sh_card")
    purpose_content = st.text_input("품의 내용 / 사용 목적", placeholder="행정실 소모품 구입 등", key="sh_purpose")
    
    if st.button("수령 확인 버튼 누르기", type="primary", key="btn_sh"):
        if user_name and purpose_content:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = [current_time, "", user_name, card_selection, purpose_content, "수령"]
            record_sheet.append_row(new_row)
            st.success(f"✅ 수령 등록 완료! 구글 시트에 안전하게 저장되었습니다.")
            st.rerun()  # 화면을 즉시 새로고침하여 데이터 갱신
        else:
            st.warning("⚠️ 이름과 품의 내용을 모두 입력해 주세요.")

# --- [ 탭 2: 카드 반납 화면 ] ---
with tab2:
    st.header("카드 반납 등록")
    return_method = st.radio("반납 방식 선택", ["미반납 목록에서 선택", "직접 작성하여 반납"], horizontal=True)
    
    if return_method == "미반납 목록에서 선택":
        if not checked_out_list:
            st.info("🎉 현재 미반납된 카드가 없습니다! 모두 장부에 반납되어 있습니다.")
        else:
            options_display = [item["display"] for item in checked_out_list]
            selected_display = st.selectbox("반납할 수령 기록을 고르세요", options_display)
            selected_item = next(item for item in checked_out_list if item["display"] == selected_display)
            return_note = st.text_input("반납 메모 (선택)", placeholder="특이사항이 있다면 적어주세요.")
            
            if st.button("반납 완료 버튼 누르기", type="primary", key="btn_ret_select"):
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row_num = selected_item["row_num"]
                record_sheet.update_cell(row_num, 2, current_time)
                record_sheet.update_cell(row_num, 6, "반납")
                if return_note:
                    existing_purpose = selected_item["row_data"][4]
                    record_sheet.update_cell(row_num, 5, f"{existing_purpose} [{return_note}]")
                st.success("✅ 반납 처리가 완료되었습니다!")
                st.rerun()

    else:
        st.subheader("직접 정보 입력 반납")
        return_user = st.text_input("반납자 이름", placeholder="홍길동", key="ret_user")
        return_card = st.selectbox("반납할 카드 선택", card_list, key="ret_card")
        return_purpose = st.text_input("품의 내용 / 사용 목적", placeholder="기록이 누락되어 직접 반납 처리함", key="ret_purpose")
        
        if st.button("반납 완료 버튼 누르기", type="primary", key="btn_ret_manual"):
            if return_user and return_purpose:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = ["", current_time, return_user, return_card, return_purpose, "반납"]
                record_sheet.append_row(new_row)
                st.success("✅ 직접 입력 반납 처리가 완료되었습니다!")
                st.rerun()
            else:
                st.warning("⚠️ 이름과 품의 내용을 모두 입력해 주세요.")

# --- [ 탭 3: 관리자 페이지 화면 ] ---
with tab3:
    st.header("⚙️ 시스템 관리자 전용")
    
    # 간단한 보안을 위한 비밀번호 입력창 (원하는 비밀번호로 수정 가능)
    password = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if password == "1234":  # 초기 비밀번호는 1234입니다.
        st.success("🔒 인증에 성공했습니다.")
        
        # 관리자 기능별 접이식 메뉴(Expander) 구성
        admin_menu = st.radio("원하는 작업을 선택하세요", ["📊 카드 사용 현황 조회", "➕ 새 카드 등록", "✏️ 출납 기록 수정/삭제"], horizontal=True)
        
        # 1. 카드 사용 현황 조회 (9번 요구사항)
        if admin_menu == "📊 카드 사용 현황 조회":
            st.subheader("전체 출납 내역 대장")
            if len(all_records) > 1:
                # 엑셀처럼 표 형태로 예쁘게 보여주기 위해 Pandas 데이터프레임 사용
                df = pd.DataFrame(all_records[1:], columns=all_records[0])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("아직 기록된 출납 내역이 없습니다.")
                
        # 2. 새 카드 등록 (8번 요구사항)
        elif admin_menu == "➕ 새 카드 등록":
            st.subheader("새로운 카드 등록")
            new_card_name = st.text_input("등록할 카드 이름을 입력하세요", placeholder="교무실 국민카드 (4321)")
            
            if st.button("카드 등록 실행", type="primary"):
                if new_card_name:
                    if new_card_name in card_list:
                        st.error("❌ 이미 존재하는 카드 이름입니다.")
                    else:
                        # 카드목록 시트의 A열에는 순번, B열에는 카드이름 추가
                        next_num = len(card_list) + 1
                        card_sheet.append_row([str(next_num), new_card_name])
                        st.success(f"✅ '{new_card_name}' 카드가 성공적으로 등록되었습니다!")
                        st.rerun()
                else:
                    st.warning("⚠️ 카드 이름을 입력해 주세요.")
                    
        # 3. 카드 사용 내용 수정 (8번 요구사항)
        elif admin_menu == "✏️ 출납 기록 수정/삭제":
            st.subheader("잘못 입력된 기록 수정")
            if len(all_records) > 1:
                # 수정할 행 고르기 목록 생성
                edit_options = [f"📄 {i}번 행 | {row[2]} | {row[3]} | {row[5]}" for i, row in enumerate(all_records[1:], start=2)]
                selected_edit = st.selectbox("수정할 장부의 행을 선택하세요", edit_options)
                
                # 선택한 행 번호 추출
                row_num_to_edit = int(selected_edit.split(" ")[1].replace("번", ""))
                current_row_data = all_records[row_num_to_edit - 1]
                
                # 기존 데이터를 입력창에 미리 채워둠
                st.write(f"🔧 **현재 데이터:** {current_row_data}")
                edit_user = st.text_input("사용자 이름 수정", value=current_row_data[2])
                edit_card = st.selectbox("카드 수정", card_list, index=card_list.index(current_row_data[3]) if current_row_data[3] in card_list else 0)
                edit_purpose = st.text_input("품의 내용 수정", value=current_row_data[4])
                edit_status = st.selectbox("상태 수정", ["수령", "반납"], index=0 if current_row_data[5] == "수령" else 1)
                
                if st.button("장부 내용 수정 반영하기", type="primary"):
                    # 구글 시트의 해당 칸(Cell)들을 직접 찾아가 수정
                    record_sheet.update_cell(row_num_to_edit, 3, edit_user)     # C열: 사용자
                    record_sheet.update_cell(row_num_to_edit, 4, edit_card)     # D열: 카드번호
                    record_sheet.update_cell(row_num_to_edit, 5, edit_purpose)  # E열: 품의내용
                    record_sheet.update_cell(row_num_to_edit, 6, edit_status)   # F열: 상태
                    st.success(f"✅ {row_num_to_edit}번 행의 기록이 성공적으로 수정되었습니다!")
                    st.rerun()
            else:
                st.info("수정할 기록이 없습니다.")
                
    elif password != "":
        st.error("❌ 비밀번호가 일치하지 않습니다.")