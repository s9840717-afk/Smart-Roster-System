import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit.components.v1 as components
from google.cloud import firestore
from google.oauth2 import service_account
import json

# --- 1. 系統設定 ---
st.set_page_config(page_title="專業排班管理系統", layout="wide", page_icon="📅")

# --- 2. Firebase 連線初始化 ---
def init_connection():
    try:
        # 從 Streamlit Secrets 讀取 Firebase 金鑰
        key_dict = json.loads(st.secrets["textkey"])
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return firestore.Client(credentials=creds, project=key_dict['project_id'])
    except Exception as e:
        st.error(f"等待 Firebase 金鑰設定中... {e}")
        return None

db = init_connection()

# 讀取資料
def load_data():
    if db is None: return pd.DataFrame(columns=["日期", "員工", "開始", "結束", "id"])
    try:
        # 從 Firestore 的 'roster' 集合抓取所有資料
        docs = db.collection("roster").stream()
        data = []
        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id # 保存 Firestore 的文件 ID 用於修改/刪除
            data.append(d)
        df = pd.DataFrame(data)
        if not df.empty:
            df['日期'] = pd.to_datetime(df['日期']).dt.date
        else:
            df = pd.DataFrame(columns=["日期", "員工", "開始", "結束", "id"])
        return df
    except:
        return pd.DataFrame(columns=["日期", "員工", "開始", "結束", "id"])

# 寫入資料
def add_data(date_obj, name, start, end):
    if db:
        db.collection("roster").add({
            "日期": str(date_obj),
            "員工": name,
            "開始": float(start),
            "結束": float(end)
        })

# 更新資料
def update_data(doc_id, name, start, end):
    if db and doc_id:
        db.collection("roster").document(doc_id).update({
            "員工": name,
            "開始": float(start),
            "結束": float(end)
        })

# 刪除資料
def delete_data(doc_id):
    if db and doc_id:
        db.collection("roster").document(doc_id).delete()

# 初始化 Session State
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = load_data()

# --- 3. 核心功能：生成 HTML 班表 ---
def build_html(df, day, names):
    start_h, end_h = 10, 23
    slots = np.arange(start_h, end_h + 0.5, 0.5)
    day_df = df[df["日期"] == day] if not df.empty else pd.DataFrame()
    
    html = f'<h3 style="font-family:sans-serif;">📍 日期：{day}</h3>'
    html += '<table style="width:100%; border-collapse:collapse; text-align:center; border:2px solid #333; font-family:sans-serif;">'
    html += '<tr style="background-color:#2C3E50; color:white;"><th>姓名 \\ 時間</th>'
    for h in range(start_h, end_h + 1): html += f'<th colspan="2">{h}</th>'
    html += '</tr>'
    
    for name in names:
        html += f'<tr><td style="font-weight:bold; background-color:#f4f4f4; border:1px solid #333; padding:10px;">{name}</td>'
        person_shifts = day_df[day_df["員工"] == name] if not day_df.empty else pd.DataFrame()
        for h in slots:
            is_work = any((row["開始"] <= h < row["結束"]) for _, row in person_shifts.iterrows()) if not person_shifts.empty else False
            is_start = any((row["開始"] == h) for _, row in person_shifts.iterrows()) if not person_shifts.empty else False
            bg = "#D6EAF8" if is_work else "white"
            txt = "●──" if is_start else ("───" if is_work else "")
            line = "2px solid #333" if h % 1 == 0 else "none"
            html += f'<td style="border-left:{line}; border-bottom:1px solid #333; background-color:{bg}; font-size:11px; height:35px;">{txt}</td>'
        html += '</tr>'
    return html + '</table>'

# --- 4. 介面控制面板 ---
st.sidebar.header("⚙️ Firebase 同步系統")
selected_date = st.sidebar.date_input("1. 選擇檢視日期", datetime.now().date())
employee_raw = st.sidebar.text_area("2. 員工名單 (一行一個)", "員工甲\n員工乙\n員工丙", height=100)
employee_list = [n.strip() for n in employee_raw.split("\n") if n.strip()]

mode = st.sidebar.selectbox("3. 操作模式", ["新增排班", "修改/刪除"])

if mode == "新增排班":
    st.sidebar.markdown("---")
    name = st.sidebar.selectbox("選擇員工", options=employee_list)
    c1, c2 = st.sidebar.columns(2)
    s = c1.number_input("開始", 10.0, 23.0, 10.0, 0.5)
    e = c2.number_input("結束", 10.0, 23.0, 18.0, 0.5)
    if st.sidebar.button("🚀 儲存並同步至雲端"):
        add_data(selected_date, name, s, e)
        st.session_state.roster_df = load_data() # 重新抓取
        st.rerun()
else:
    st.sidebar.write("🔍 選取該日班次進行修改")
    day_shifts = st.session_state.roster_df[st.session_state.roster_df["日期"] == selected_date].copy()
    if not day_shifts.empty:
        day_shifts['display'] = day_shifts.apply(lambda r: f"{r['員工']} ({r['開始']}-{r['結束']})", axis=1)
        target_idx = st.sidebar.selectbox("選取項目", options=day_shifts.index, format_func=lambda x: day_shifts.loc[x, 'display'])
        doc_id = day_shifts.loc[target_idx, 'id']
        
        new_n = st.sidebar.selectbox("修正員工", options=employee_list, index=employee_list.index(day_shifts.loc[target_idx, '員工']) if day_shifts.loc[target_idx, '員工'] in employee_list else 0)
        c1, c2 = st.sidebar.columns(2)
        new_s = c1.number_input("修正開始", 10.0, 23.0, float(day_shifts.loc[target_idx, '開始']), 0.5)
        new_e = c2.number_input("修正結束", 10.0, 23.0, float(day_shifts.loc[target_idx, '結束']), 0.5)
        
        b1, b2 = st.sidebar.columns(2)
        if b1.button("✅ 更新"):
            update_data(doc_id, new_n, new_s, new_e)
            st.session_state.roster_df = load_data()
            st.rerun()
        if b2.button("🗑️ 刪除"):
            delete_data(doc_id)
            st.session_state.roster_df = load_data()
            st.rerun()
    else:
        st.sidebar.info("選中日期無資料")

# --- 5. 主畫面與輸出 ---
st.title("📅 跨設備排班同步系統")
st.markdown(build_html(st.session_state.roster_df, selected_date, employee_list), unsafe_allow_html=True)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 手動刷新資料 (跨設備同步)"):
    st.session_state.roster_df = load_data()
    st.rerun()

# 區間輸出
st.markdown("---")
st.subheader("🖨️ 報表輸出")
d1, d2 = st.columns(2)
date_s = d1.date_input("輸出起始日期", selected_date)
date_e = d2.date_input("輸出結束日期", selected_date)

range_html = ""
curr = date_s
while curr <= date_e:
    range_html += build_html(st.session_state.roster_df, curr, employee_list)
    if curr != date_e: range_html += '<div style="page-break-after: always;"></div>'
    curr = curr + pd.Timedelta(days=1)
    if hasattr(curr, 'date'): curr = curr.date()

safe_print = range_html.replace('"', "'").replace("\n", "")
print_js = f"""<script>function p(){{ var w=window.open('','_blank'); w.document.write('<html><head><style>@page{{size:landscape;}}table{{width:100%;border-collapse:collapse;}}th,td{{border:1px solid black;text-align:center;font-size:10px;}}</style></head><body><h1 style="text-align:center;">排班總表</h1>'); w.document.write("{safe_print}"); w.document.write('</body></html>'); w.document.close(); setTimeout(function(){{w.print();w.close();}},1000); }}</script><button onclick="p()" style="background-color:#2ECC71;color:white;padding:15px 30px;border:none;border-radius:8px;cursor:pointer;font-size:18px;">🖨️ 輸出 PDF 報表</button>"""
components.html(print_js, height=100)