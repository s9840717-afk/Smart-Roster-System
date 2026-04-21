import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="智慧排班系統 - 斷行輸入版", layout="wide")
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

# --- 2. 核心功能：生成單日 HTML 表格 (全員顯示) ---
def build_single_day_table(input_df, target_day, full_employee_list):
    start_h = 10
    end_h = 23
    all_slots = np.arange(start_h, end_h + 0.5, 0.5)
    
    day_data = input_df[input_df["日期"] == target_day]
    
    html = f'<h3 style="text-align:left; margin-top:30px; font-family: sans-serif;">📍 日期：{target_day}</h3>'
    html += '<table style="width:100%; border-collapse: collapse; text-align: center; border: 2px solid #333; font-family: sans-serif; margin-bottom:40px;">'
    html += '<tr style="background-color: #4A90E2; color: white;">'
    html += '<th style="border: 1px solid #333; padding: 10px; width: 120px;">姓名 \\ 時間</th>'
    for h in range(start_h, end_h + 1):
        html += f'<th colspan="2" style="border: 1px solid #333;">{h}</th>'
    html += '</tr>'
    
    for name in full_employee_list:
        html += f'<tr><td style="border: 1px solid #333; font-weight: bold; padding: 10px; background-color: #f9f9f9;">{name}</td>'
        person_shifts = day_data[day_data["員工"] == name]
        
        for h in all_slots:
            is_working = any((row["開始"] <= h < row["結束"]) for _, row in person_shifts.iterrows())
            is_start = any((row["開始"] == h) for _, row in person_shifts.iterrows())
            bg_color = "#E1F5FE" if is_working else "white"
            content = "●──" if is_start else ("───" if is_working else "")
            border_l = "2px solid #333" if h % 1 == 0 else "none"
            html += f'<td style="border-left: {border_l}; border-bottom: 1px solid #333; border-right: none; background-color: {bg_color}; font-size: 11px; height: 35px;">{content}</td>'
        html += '</tr>'
    
    html += '</table>'
    return html

# --- 3. 側邊欄控制區 ---
st.sidebar.title("🛠️ 管理選單")
selected_date = st.sidebar.date_input("1. 檢視單日班表", datetime.now().date())

st.sidebar.markdown("---")
# 【關鍵更新】：使用 text_area 並以斷行符號切分名單
employee_raw = st.sidebar.text_area("2. 員工名單 (請按 Enter 換行隔開)", "員工甲\n員工乙\n員工丙", height=150)
employee_list = [name.strip() for name in employee_raw.split("\n") if name.strip()]

with st.sidebar.form("add_form"):
    st.write("3. 新增班次")
    name = st.selectbox("選擇員工", options=employee_list)
    col1, col2 = st.columns(2)
    with col1: s_time = st.number_input("開始", 10.0, 23.0, 10.0, 0.5)
    with col2: e_time = st.number_input("結束", 10.0, 23.0, 18.0, 0.5)
    if st.form_submit_button("儲存班次"):
        new_row = pd.DataFrame({"日期": [selected_date], "員工": [name], "開始": [s_time], "結束": [e_time]})
        st.session_state.roster_df = pd.concat([st.session_state.roster_df, new_row], ignore_index=True)
        save_data(st.session_state.roster_df)
        st.rerun()

# 刪除功能
st.sidebar.markdown("---")
current_day_data = st.session_state.roster_df[st.session_state.roster_df["日期"] == selected_date].copy()
if not current_day_data.empty:
    st.sidebar.write("4. 刪除班次")
    current_day_data['info'] = current_day_data.apply(lambda r: f"{r['員工']} ({r['開始']}-{r['結束']})", axis=1)
    target_info = st.sidebar.selectbox("選取欲刪除項目", options=current_day_data['info'].tolist())
    if st.sidebar.button("確認刪除"):
        real_index = current_day_data[current_day_data['info'] == target_info].index[0]
        st.session_state.roster_df = st.session_state.roster_df.drop(real_index)
        save_data(st.session_state.roster_df)
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.write("### 📂 區間檔案輸出設定")
date_start = st.sidebar.date_input("起始日期", selected_date)
date_end = st.sidebar.date_input("結束日期", selected_date)

# --- 4. 主畫面展示 ---
st.title("📅 智慧視覺化排班系統")
table_html = build_single_day_table(st.session_state.roster_df, selected_date, employee_list)
st.markdown(table_html, unsafe_allow_html=True)

# --- 5. 影印功能 ---
st.markdown("---")
st.write("### 🖨️ 報表輸出中心")

range_html_content = ""
curr = date_start
while curr <= date_end:
    range_html_content += build_single_day_table(st.session_state.roster_df, curr, employee_list)
    if curr != date_end:
        range_html_content += '<div style="page-break-after: always;"></div>'
    curr = curr + pd.Timedelta(days=1)
    if hasattr(curr, 'date'): curr = curr.date()

# 預先處理 HTML 安全字串，避免 f-string 解析錯誤
safe_html = range_html_content.replace('"', "'").replace("\n", "")

print_script = f"""
<script>
function printRange() {{
    var printWindow = window.open('', '_blank');
    printWindow.document.write('<html><head><title>排班報表</title>');
    printWindow.document.write('<style>');
    printWindow.document.write('@page {{ size: landscape; margin: 10mm; }}');
    printWindow.document.write('body {{ font-family: sans-serif; padding: 20px; }}');
    printWindow.document.write('table {{ width: 100%; border-collapse: collapse; }}');
    printWindow.document.write('th, td {{ border-bottom: 1px solid black; text-align: center; font-size: 10px; }}');
    printWindow.document.write('</style></head><body>');
    printWindow.document.write('<h1 style="text-align:center;">員工排班總表</h1>');
    printWindow.document.write('<p style="text-align:center;">查詢區間：{date_start} ~ {date_end}</p>');
    printWindow.document.write("{safe_html}");
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    setTimeout(function() {{
        printWindow.focus();
        printWindow.print();
        printWindow.close();
    }}, 1000);
}}
</script>
<button onclick="printRange()" style="
    background-color: #4CAF50; color: white; padding: 15px 30px;
    border: none; border-radius: 8px; cursor: pointer; font-size: 18px; font-weight: bold;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    🖨️ 輸出區間班表 PDF
</button>
"""
components.html(print_script, height=120)