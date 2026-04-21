import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection

# --- 1. 系統設定與 Google Sheets 連線 ---
st.set_page_config(page_title="專業排班管理系統", layout="wide", page_icon="📅")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="工作表1", ttl="0s")
        if df is not None and not df.empty:
            df['日期'] = pd.to_datetime(df['日期']).dt.date
        return df
    except Exception:
        return pd.DataFrame(columns=["日期", "員工", "開始", "結束"])

def save_data(df):
    try:
        conn.update(worksheet="Sheet1", data=df)
        st.success("數據已成功同步至雲端！")
    except Exception as e:
        st.error(f"雲端同步失敗：{e}")

if 'roster_df' not in st.session_state:
    st.session_state.roster_df = load_data()

# --- 2. 核心功能：生成單日 HTML 班表 ---
def build_single_day_html(df, day, names):
    start_h, end_h = 10, 23
    slots = np.arange(start_h, end_h + 0.5, 0.5)
    
    # 確保資料日期格式一致
    df_copy = df.copy()
    df_copy['日期'] = pd.to_datetime(df_copy['日期']).dt.date
    day_df = df_copy[df_copy["日期"] == day]
    
    html = f'<h3 style="font-family:sans-serif; margin-top:30px;">📍 日期：{day}</h3>'
    html += '<table style="width:100%; border-collapse:collapse; text-align:center; border:2px solid #333; font-family:sans-serif; margin-bottom:50px;">'
    html += '<tr style="background-color:#2C3E50; color:white;">'
    html += '<th style="border:1px solid #333; padding:10px; width:120px;">姓名 \\ 時間</th>'
    for h in range(start_h, end_h + 1):
        html += f'<th colspan="2" style="border:1px solid #333;">{h}</th>'
    html += '</tr>'
    
    for name in names:
        html += f'<tr><td style="border:1px solid #333; font-weight:bold; background-color:#ECF0F1; padding:10px;">{name}</td>'
        person_shifts = day_df[day_df["員工"] == name]
        for h in slots:
            is_work = any((row["開始"] <= h < row["結束"]) for _, row in person_shifts.iterrows())
            is_start = any((row["開始"] == h) for _, row in person_shifts.iterrows())
            bg = "#D6EAF8" if is_work else "white"
            txt = "●──" if is_start else ("───" if is_work else "")
            line = "2px solid #333" if h % 1 == 0 else "none"
            html += f'<td style="border-left:{line}; border-bottom:1px solid #333; background-color:{bg}; font-size:11px; height:35px;">{txt}</td>'
        html += '</tr>'
    return html + '</table>'

# --- 3. 側邊欄控制面板 ---
st.sidebar.header("⚙️ 系統控制台")
selected_date = st.sidebar.date_input("1. 選擇檢視日期", datetime.now().date())

st.sidebar.markdown("---")
employee_raw = st.sidebar.text_area("2. 員工名單 (一行一個名字)", "員工甲\n員工乙\n員工丙", height=150)
employee_list = [n.strip() for n in employee_raw.split("\n") if n.strip()]

with st.sidebar.form("add_form"):
    st.write("📝 3. 新增排班紀錄")
    name = st.selectbox("選擇員工", options=employee_list)
    c1, c2 = st.columns(2)
    s_t = c1.number_input("開始", 10.0, 23.0, 10.0, 0.5)
    e_t = c2.number_input("結束", 10.0, 23.0, 18.0, 0.5)
    if st.form_submit_button("儲存並同步"):
        new_data = pd.DataFrame({"日期": [selected_date], "員工": [name], "開始": [s_t], "結束": [e_t]})
        st.session_state.roster_df = pd.concat([st.session_state.roster_df, new_data], ignore_index=True)
        save_data(st.session_state.roster_df)
        st.rerun()

# 區間輸出設定
st.sidebar.markdown("---")
st.sidebar.write("### 📂 區間報表輸出設定")
date_start = st.sidebar.date_input("起始日期", selected_date)
date_end = st.sidebar.date_input("結束日期", selected_date)

# --- 4. 主畫面顯示 ---
st.title("📅 專業自動化排班管理系統")
st.markdown(build_single_day_html(st.session_state.roster_df, selected_date, employee_list), unsafe_allow_html=True)

# --- 5. 區間輸出與影印邏輯 ---
st.markdown("---")
st.subheader("🖨️ 報表輸出中心")

# 生成多日 HTML 內容
range_html_content = ""
curr = date_start
while curr <= date_end:
    range_html_content += build_single_day_html(st.session_state.roster_df, curr, employee_list)
    if curr != date_end:
        range_html_content += '<div style="page-break-after: always;"></div>'
    curr = curr + pd.Timedelta(days=1)
    if hasattr(curr, 'date'): curr = curr.date()

# 處理安全字串
safe_range_html = range_html_content.replace('"', "'").replace("\n", "")

print_js = f"""
<script>
function printRange() {{
    var win = window.open('', '_blank');
    win.document.write('<html><head><title>NCUT_Range_Roster</title>');
    win.document.write('<style>@page {{ size: landscape; margin: 10mm; }} body {{ font-family: sans-serif; padding: 20px; }} table {{ width:100%; border-collapse:collapse; }} th, td {{ border:1px solid black; text-align:center; font-size:10px; }}</style></head><body>');
    win.document.write('<h1 style="text-align:center;">員工排班總表</h1>');
    win.document.write('<p style="text-align:center;">查詢區間：{date_start} ~ {date_end}</p>');
    win.document.write("{safe_range_html}");
    win.document.write('</body></html>');
    win.document.close();
    setTimeout(function(){{ win.print(); win.close(); }}, 1000);
}}
</script>
<button onclick="printRange()" style="background-color:#2ECC71; color:white; padding:15px 30px; border:none; border-radius:8px; cursor:pointer; font-size:18px; font-weight:bold;">
    🖨️ 輸出指定區間 PDF (橫向分頁)
</button>
"""
components.html(print_js, height=120)

with st.expander("🔍 檢視雲端原始數據"):
    st.dataframe(st.session_state.roster_df)