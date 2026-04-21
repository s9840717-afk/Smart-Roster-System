import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection

# --- 1. 系統設定與 Google Sheets 連線 ---
st.set_page_config(page_title="專業排班管理系統", layout="wide", page_icon="📅")

# 建立連線物件
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 從雲端讀取，ttl=0 代表不使用緩存，每次都抓最新的
        return conn.read(ttl="0s")
    except:
        return pd.DataFrame(columns=["日期", "員工", "開始", "結束"])

def save_data(df):
    # 將整個 DataFrame 寫回雲端
    conn.update(data=df)

if 'roster_df' not in st.session_state:
    st.session_state.roster_df = load_data()

# --- 2. 核心功能：生成 HTML 班表 ---
def build_roster_html(df, day, names):
    start_h, end_h = 10, 23
    slots = np.arange(start_h, end_h + 0.5, 0.5)
    
    # 確保日期格式一致再篩選
    df['日期'] = pd.to_datetime(df['日期']).dt.date
    day_df = df[df["日期"] == day]
    
    html = f'<h3 style="font-family:sans-serif;">📍 日期：{day}</h3>'
    html += '<table style="width:100%; border-collapse:collapse; text-align:center; border:2px solid #333; font-family:sans-serif;">'
    html += '<tr style="background-color:#2C3E50; color:white;">'
    html += '<th style="border:1px solid #333; padding:10px; width:120px;">姓名 \\ 時間</th>'
    for h in range(start_h, end_h + 1):
        html += f'<th colspan="2" style="border:1px solid #333;">{h}</th>'
    html += '</tr>'
    
    for name in names:
        html += f'<tr><td style="border:1px solid #333; font-weight:bold; background-color:#f4f4f4;">{name}</td>'
        shifts = day_df[day_df["員工"] == name]
        for h in slots:
            is_work = any((row["開始"] <= h < row["結束"]) for _, row in shifts.iterrows())
            is_start = any((row["開始"] == h) for _, row in shifts.iterrows())
            bg = "#D6EAF8" if is_work else "white"
            txt = "●──" if is_start else ("───" if is_work else "")
            line = "2px solid #333" if h % 1 == 0 else "none"
            html += f'<td style="border-left:{line}; border-bottom:1px solid #333; background-color:{bg}; font-size:11px; height:35px;">{txt}</td>'
        html += '</tr>'
    return html + '</table>'

# --- 3. 介面控制 ---
st.title("📅 專業自動化排班系統 (雲端同步版)")
st.sidebar.title("🛠️ 管理面板")
sel_date = st.sidebar.date_input("選擇檢視日期", datetime.now().date())
emp_raw = st.sidebar.text_area("員工名單 (一行一個名字)", "員工甲\n員工乙\n員工丙", height=150)
emp_list = [n.strip() for n in emp_raw.split("\n") if n.strip()]

# 側邊欄新增功能
with st.sidebar.form("add"):
    st.write("新增排班")
    n = st.selectbox("員工", options=emp_list)
    c1, c2 = st.columns(2)
    s = c1.number_input("開始", 10.0, 23.0, 10.0, 0.5)
    e = c2.number_input("結束", 10.0, 23.0, 18.0, 0.5)
    if st.form_submit_button("儲存並同步雲端"):
        new = pd.DataFrame({"日期": [sel_date], "員工": [n], "開始": [s], "結束": [e]})
        st.session_state.roster_df = pd.concat([st.session_state.roster_df, new], ignore_index=True)
        save_data(st.session_state.roster_df)
        st.success("已同步至 Google Sheets！")
        st.rerun()

# 顯示班表
main_html = build_roster_html(st.session_state.roster_df, sel_date, emp_list)
st.markdown(main_html, unsafe_allow_html=True)

# 輸出功能保持不變...
clean_html = main_html.replace('"', "'").replace("\n", "")
print_js = f"""<script>function printPDF(){{ var w = window.open('', '_blank'); w.document.write('<html><head><style>@page{{size:landscape;margin:10mm;}}table{{width:100%;border-collapse:collapse;}}th,td{{border:1px solid black;text-align:center;}}</style></head><body>'); w.document.write("{clean_html}"); w.document.write('</body></html>'); w.document.close(); setTimeout(function(){{ w.print(); w.close(); }}, 1000); }}</script><button onclick="printPDF()" style="background-color:#28A745;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;">🖨️ 輸出 PDF</button>"""
components.html(print_js, height=100)