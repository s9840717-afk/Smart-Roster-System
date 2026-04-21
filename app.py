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
        df = conn.read(worksheet="Sheet1", ttl="0s")
        if df is not None and not df.empty:
            df['日期'] = pd.to_datetime(df['日期']).dt.date
        return df
    except Exception:
        return pd.DataFrame(columns=["日期", "員工", "開始", "結束"])

def save_data(df):
    try:
        conn.update(worksheet="Sheet1", data=df)
        st.success("數據已同步至雲端！")
    except Exception as e:
        st.error(f"同步失敗：{e}")

if 'roster_df' not in st.session_state:
    st.session_state.roster_df = load_data()

# --- 2. 核心功能：生成 HTML 班表 ---
def build_single_day_html(df, day, names):
    start_h, end_h = 10, 23
    slots = np.arange(start_h, end_h + 0.5, 0.5)
    
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

# --- 3. 側邊欄：管理面板 ---
st.sidebar.header("⚙️ 系統控制台")
selected_date = st.sidebar.date_input("1. 選擇檢視日期", datetime.now().date())

st.sidebar.markdown("---")
employee_raw = st.sidebar.text_area("2. 員工名單管理", "員工甲\n員工乙\n員工丙", height=100)
employee_list = [n.strip() for n in employee_raw.split("\n") if n.strip()]

# 功能切換：新增 vs 修改/刪除
mode = st.sidebar.radio("3. 選擇操作模式", ["新增班次", "修改/刪除班次"])

if mode == "新增班次":
    with st.sidebar.form("add_form"):
        st.write("📝 新增排班")
        n = st.selectbox("選擇員工", options=employee_list)
        c1, c2 = st.columns(2)
        s = c1.number_input("開始", 10.0, 23.0, 10.0, 0.5)
        e = c2.number_input("結束", 10.0, 23.0, 18.0, 0.5)
        if st.form_submit_button("儲存並同步"):
            new_row = pd.DataFrame({"日期": [selected_date], "員工": [n], "開始": [s], "結束": [e]})
            st.session_state.roster_df = pd.concat([st.session_state.roster_df, new_row], ignore_index=True)
            save_data(st.session_state.roster_df)
            st.rerun()

else:
    # 修改/刪除邏輯
    st.sidebar.write("🔍 選取該日班次進行修改")
    day_shifts = st.session_state.roster_df[st.session_state.roster_df["日期"] == selected_date].copy()
    
    if not day_shifts.empty:
        day_shifts['display'] = day_shifts.apply(lambda r: f"{r['員工']} ({r['開始']}-{r['結束']})", axis=1)
        target_idx = st.sidebar.selectbox("選取項目", options=day_shifts.index, format_func=lambda x: day_shifts.loc[x, 'display'])
        
        with st.sidebar.form("edit_form"):
            st.write("✏️ 修改選取項目")
            new_n = st.selectbox("修正員工", options=employee_list, index=employee_list.index(day_shifts.loc[target_idx, '員工']) if day_shifts.loc[target_idx, '員工'] in employee_list else 0)
            c1, c2 = st.columns(2)
            new_s = c1.number_input("修正開始", 10.0, 23.0, float(day_shifts.loc[target_idx, '開始']), 0.5)
            new_e = c2.number_input("修正結束", 10.0, 23.0, float(day_shifts.loc[target_idx, '結束']), 0.5)
            
            col_save, col_del = st.columns(2)
            if col_save.form_submit_button("✅ 更新"):
                st.session_state.roster_df.loc[target_idx, ["員工", "開始", "結束"]] = [new_n, new_s, new_e]
                save_data(st.session_state.roster_df)
                st.rerun()
            if col_del.form_submit_button("🗑️ 刪除"):
                st.session_state.roster_df = st.session_state.roster_df.drop(target_idx)
                save_data(st.session_state.roster_df)
                st.rerun()
    else:
        st.sidebar.warning("該日期尚無班次紀錄")

# --- 4. 區間輸出與主畫面 ---
st.sidebar.markdown("---")
st.sidebar.write("### 📂 區間報表輸出")
date_start = st.sidebar.date_input("起始日期", selected_date)
date_end = st.sidebar.date_input("結束日期", selected_date)

st.title("📅 專業自動化排班管理系統")
st.markdown(build_single_day_html(st.session_state.roster_df, selected_date, employee_list), unsafe_allow_html=True)

# 影印功能
range_html = ""
curr = date_start
while curr <= date_end:
    range_html += build_single_day_html(st.session_state.roster_df, curr, employee_list)
    if curr != date_end: range_html += '<div style="page-break-after: always;"></div>'
    curr = curr + pd.Timedelta(days=1)
    if hasattr(curr, 'date'): curr = curr.date()

safe_print = range_html.replace('"', "'").replace("\n", "")
print_js = f"""
<script>
function printR() {{
    var w = window.open('', '_blank');
    w.document.write('<html><head><style>@page{{size:landscape;margin:10mm;}}table{{width:100%;border-collapse:collapse;}}th,td{{border:1px solid black;text-align:center;font-size:10px;}}</style></head><body>');
    w.document.write('<h1 style="text-align:center;">排班總表 ({date_start} ~ {date_end})</h1>');
    w.document.write("{safe_print}");
    w.document.write('</body></html>'); w.document.close();
    setTimeout(function(){{ w.print(); w.close(); }}, 1000);
}}
</script>
<button onclick="printR()" style="background-color:#2ECC71; color:white; padding:15px 30px; border:none; border-radius:8px; cursor:pointer; font-size:18px;">🖨️ 輸出 PDF 報表</button>
"""
components.html(print_js, height=120)