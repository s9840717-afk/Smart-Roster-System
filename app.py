import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. 系統基本設定 ---
st.set_page_config(page_title="NCUT 智慧排班管理系統", layout="wide", page_icon="📅")
DATA_FILE = "roster_data.csv"

# 初始化資料庫
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=["日期", "員工", "開始", "結束"]).to_csv(DATA_FILE, index=False)

def load_data():
    df = pd.read_csv(DATA_FILE)
    if not df.empty:
        df['日期'] = pd.to_datetime(df['日期']).dt.date
    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

if 'roster_df' not in st.session_state:
    st.session_state.roster_df = load_data()

# --- 2. 核心功能：生成單日 HTML 表格 ---
def build_single_day_table(input_df, target_day, full_employee_list):
    start_h = 10
    end_h = 23
    all_slots = np.arange(start_h, end_h + 0.5, 0.5)
    day_data = input_df[input_df["日期"] == target_day]
    
    html = f'<h3 style="text-align:left; margin-top:30px; font-family: sans-serif;">📍 日期：{target_day}</h3>'
    html += '<table style="width:100%; border-collapse: collapse; text-align: center; border: 2px solid #333; font-family: sans-serif; margin-bottom:40px;">'
    html += '<tr style="background-color: #2C3E50; color: white;">'
    html += '<th style="border: 1px solid #333; padding: 10px; width: 120px;">姓名 \\ 時間</th>'
    for h in range(start_h, end_h + 1):
        html += f'<th colspan="2" style="border: 1px solid #333;">{h}</th>'
    html += '</tr>'
    
    for name in full_employee_list:
        html += f'<tr><td style="border: 1px solid #333; font-weight: bold; padding: 10px; background-color: #ECF0F1;">{name}</td>'
        person_shifts = day_data[day_data["員工"] == name]
        for h in all_slots:
            is_working = any((row["開始"] <= h < row["結束"]) for _, row in person_shifts.iterrows())
            is_start = any((row["開始"] == h) for _, row in person_shifts.iterrows())
            bg_color = "#D6EAF8" if is_working else "white"
            content = "●──" if is_start else ("───" if is_working else "")
            border_l = "2px solid #333" if h % 1 == 0 else "none"
            html += f'<td style="border-left: {border_l}; border-bottom: 1px solid #333; border-right: none; background-color: {bg_color}; font-size: 11px; height: 35px;">{content}</td>'
        html += '</tr>'
    return html + '</table>'

# --- 3. 側邊欄：管理控制台 ---
st.sidebar.header("⚙️ 系統控制台")
selected_date = st.sidebar.date_input("📅 1. 檢視日期", datetime.now().date())

st.sidebar.markdown("---")
employee_raw = st.sidebar.text_area("👤 2. 員工名單管理 (斷行隔開)", "員工甲\n員工乙\n員工丙", height=150)
employee_list = [n.strip() for n in employee_raw.split("\n") if n.strip()]

with st.sidebar.form("add_shift"):
    st.write("📝 3. 新增排班紀錄")
    name = st.selectbox("選擇員工", options=employee_list)
    c1, c2 = st.columns(2)
    s_time = c1.number_input("開始(H)", 10.0, 23.0, 10.0, 0.5)
    e_time = c2.number_input("結束(H)", 10.0, 23.0, 18.0, 0.5)
    if st.form_submit_button("確認存檔"):
        new = pd.DataFrame({"日期": [selected_date], "員工": [name], "開始": [s_time], "結束": [e_time]})
        st.session_state.roster_df = pd.concat([st.session_state.roster_df, new], ignore_index=True)
        save_data(st.session_state.roster_df)
        st.rerun()

st.sidebar.markdown("---")
# 刪除功能邏輯
curr_day = st.session_state.roster_df[st.session_state.roster_df["日期"] == selected_date].copy()
if not curr_day.empty:
    st.sidebar.write("🗑️ 4. 刪除紀錄")
    curr_day['info'] = curr_day.apply(lambda r: f"{r['員工']} ({r['開始']}-{r['結束']})", axis=1)
    target = st.sidebar.selectbox("選取欲刪除項目", options=curr_day['info'].tolist())
    if st.sidebar.button("執行刪除"):
        real_idx = curr_day[curr_day['info'] == target].index[0]
        st.session_state.roster_df = st.session_state.roster_df.drop(real_idx)
        save_data(st.session_state.roster_df)
        st.rerun()

# --- 4. 主畫面展示 ---
st.title("🛡️ NCUT 智慧排班管理系統")
st.info(f"當前檢視日期：{selected_date} | 員工總數：{len(employee_list)} 人")
main_table = build_single_day_table(st.session_state.roster_df, selected_date, employee_list)
st.markdown(main_table, unsafe_allow_html=True)

# --- 5. 報表輸出 ---
st.markdown("---")
st.subheader("📂 報表輸出中心 (PDF / Print)")
d_start = st.sidebar.date_input("輸出起始日期", selected_date)
d_end = st.sidebar.date_input("輸出結束日期", selected_date)

range_html = ""
curr = d_start
while curr <= d_end:
    range_html += build_single_day_table(st.session_state.roster_df, curr, employee_list)
    if curr != d_end: range_html += '<div style="page-break-after: always;"></div>'
    curr = curr + pd.Timedelta(days=1)
    if hasattr(curr, 'date'): curr = curr.date()

safe_html = range_html.replace('"', "'").replace("\n", "")
print_script = f"""
<script>
function printPDF() {{
    var win = window.open('', '_blank');
    win.document.write('<html><head><title>NCUT_Roster</title>');
    win.document.write('<style>@page {{ size: landscape; margin: 10mm; }} body {{ font-family: sans-serif; }} table {{ width:100%; border-collapse:collapse; }} th, td {{ border:1px solid black; font-size:10px; }}</style></head><body>');
    win.document.write('<h1 style="text-align:center;">智慧排班管理系統 - 員工班表總表</h1>');
    win.document.write('<p style="text-align:center;">查詢區間：{d_start} 至 {d_end}</p>');
    win.document.write("{safe_html}");
    win.document.write('</body></html>');
    win.document.close();
    setTimeout(function(){{ win.print(); win.close(); }}, 500);
}}
</script>
<button onclick="printPDF()" style="background-color: #2ECC71; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
    🖨️ 產生區間報表 (自動分頁)
</button>
"""
components.html(print_script, height=100)