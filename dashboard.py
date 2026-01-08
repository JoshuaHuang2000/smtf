import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
import os
import hashlib
from logic.filter import ContentFilter

st.set_page_config(page_title="SMTF Command Center", page_icon="🕵️", layout="wide")

DB_NAME = "smtf_memory.db"


# --- Backend Functions ---

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def load_data(start_date, end_date):
    conn = get_connection()
    s_str = f"{start_date} 00:00:00"
    e_str = f"{end_date} 23:59:59"

    # [关键] 确保选择了 image_path, url, verdict, manual_verdict
    query = f"""
        SELECT post_id, original_text, verdict, manual_verdict, summary, url, image_path, processed_at 
        FROM processed_posts
        WHERE processed_at BETWEEN '{s_str}' AND '{e_str}'
        ORDER BY processed_at DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def update_manual_verdict(post_id, new_verdict):
    conn = get_connection()
    conn.execute(
        "UPDATE processed_posts SET manual_verdict = ? WHERE post_id = ?",
        (new_verdict, post_id)
    )
    conn.commit()
    conn.close()
    st.rerun()


def get_cached_briefing(date_key, current_context_hash):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT content, context_hash FROM briefings WHERE date_key = ?", (date_key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        content, saved_hash = row
        return content, (saved_hash == current_context_hash)
    return None, False


def save_briefing(date_key, content, context_hash):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO briefings (date_key, content, context_hash, created_at) VALUES (?, ?, ?, ?)",
        (date_key, content, context_hash, datetime.now())
    )
    conn.commit()
    conn.close()


# --- UI Logic ---

st.title("🕵️ SMTF Truth Radar")

# ==========================================
# 1. Sidebar Filters
# ==========================================
with st.sidebar:
    st.header("🔍 Filters")
    today = datetime.now().date()
    default_start = today - timedelta(days=2)
    date_range = st.date_input("Select Date Range", value=(default_start, today), max_value=today)

    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range[0]

    st.caption(f"Range: {start_date} to {end_date}")

    # [更新] 平台筛选
    sel_platforms = st.multiselect("Platform", ["x", "reddit", "wb"], default=["x", "reddit", "wb"])

    # [更新] 状态筛选 (适配新的三态逻辑 + 噪音)
    # 默认选 TRUE, FALSE, MIXED (不看噪音)
    all_verdicts = ["TRUE", "FALSE", "MIXED", "NOISE"]
    sel_verdicts = st.multiselect("Verdict", all_verdicts, default=["TRUE", "FALSE", "MIXED"])

    search_q = st.text_input("Search Keyword", "")

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# Load & Process Data
if os.path.exists(DB_NAME):
    df = load_data(start_date, end_date)
else:
    st.error("Database not found!")
    st.stop()

# 计算最终状态 (人工覆盖 AI)
df['final_verdict'] = df['manual_verdict'].combine_first(df['verdict'])


# 平台标签处理
def get_platform_label(pid):
    pid = str(pid)
    if pid.startswith("x_"): return "x"
    if pid.startswith("reddit_"): return "reddit"
    if pid.startswith("wb_"): return "wb"
    return "unknown"


df['platform'] = df['post_id'].apply(get_platform_label)

# --- Apply Filters ---
filtered_df = df[df['platform'].isin(sel_platforms)]
filtered_df = filtered_df[filtered_df['final_verdict'].isin(sel_verdicts)]
if search_q:
    filtered_df = filtered_df[filtered_df['original_text'].str.contains(search_q, case=False)]

# ==========================================
# 2. Main Layout (Tabs)
# ==========================================

tab1, tab2 = st.tabs(["📊 Explorer & Briefing", "💬 Chat with Data"])

# --- TAB 1: Explorer ---
with tab1:
    # A. Briefing Section
    st.markdown(f"### 🧠 AI Analyst Briefing")

    # 生成唯一的 Key
    platforms_hash = hashlib.md5("".join(sorted(sel_platforms)).encode()).hexdigest()[:6]
    verdicts_hash = hashlib.md5("".join(sorted(sel_verdicts)).encode()).hexdigest()[:6]
    search_hash = hashlib.md5(search_q.encode()).hexdigest()[:6] if search_q else "nosearch"
    report_key = f"report_{start_date}_{end_date}_{platforms_hash}_{verdicts_hash}_{search_hash}"

    if not filtered_df.empty:
        ids_str = "".join(sorted(filtered_df['post_id'].astype(str).tolist()))
        current_hash = hashlib.md5(ids_str.encode()).hexdigest()
        cached_content, is_fresh = get_cached_briefing(report_key, current_hash)

        col_ai_1, col_ai_2 = st.columns([5, 1])
        with col_ai_2:
            btn_label = "✨ Generate"
            if cached_content and not is_fresh:
                btn_label = "🔄 Refresh"
            elif cached_content:
                btn_label = "🔄 Regenerate"

            if st.button(btn_label, key="gen_briefing"):
                with st.spinner(f"Reading {len(filtered_df)} items..."):
                    # 简报不仅给文本，也给状态，让 AI 知道哪些是谣言
                    texts = []
                    for _, r in filtered_df.iterrows():
                        status = r['final_verdict']
                        url = r['url'] or 'N/A'
                        texts.append(f"[{status}] [{r['platform']}] {r['original_text']} (Src: {url})")

                    summary = ContentFilter().generate_daily_briefing(texts)
                    save_briefing(report_key, summary, current_hash)
                    st.rerun()

        with col_ai_1:
            if cached_content:
                if not is_fresh: st.warning("Data changed since generation.")
                st.markdown(cached_content)
            else:
                st.info("Ready to summarize based on current filters.")
    else:
        st.write("No data to summarize.")

    st.divider()

    # B. List Section
    st.markdown(f"### 🔍 Records ({len(filtered_df)})")

    for index, row in filtered_df.iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                p_map = {"x": "🐦 X", "reddit": "🤖 Reddit", "wb": "🇨🇳 Weibo", "unknown": "❓"}
                p_label = p_map.get(row['platform'], row['platform'])

                # [修改点] 增加显示 ID (使用单引号包裹显示为代码块，方便复制)
                st.markdown(f"**{p_label}** | `{row['processed_at']}` | 🆔 `{row['post_id']}`")

                # 正文 (带链接)
                txt = row['original_text'].replace('\n', '  \n')
                if row['url']:
                    st.markdown(f"[{txt}]({row['url']})")
                else:
                    st.markdown(txt)

                # --- 多模态图片显示 ---
                if row['image_path'] and os.path.exists(row['image_path']):
                    st.image(row['image_path'], caption="Snapshot", width=400)
                # --------------------

                if row['summary']:
                    with st.expander("AI Notes"):
                        st.markdown(row['summary'])

            with c2:
                # [更新] 状态颜色逻辑
                curr_v = row['manual_verdict'] if row['manual_verdict'] else row['verdict']

                if curr_v == 'TRUE':
                    st.success("TRUE")
                elif curr_v == 'FALSE':
                    st.error("FALSE")  # 红色
                elif curr_v == 'MIXED':
                    st.warning("MIXED")  # 黄色
                else:
                    st.info("NOISE")  # 蓝色/灰色

                # [更新] 编辑菜单
                new_v = st.selectbox("Edit", all_verdicts,
                                     index=all_verdicts.index(curr_v) if curr_v in all_verdicts else 0,
                                     key=f"v_{row['post_id']}", label_visibility="collapsed")
                if new_v != curr_v:
                    if new_v != row['manual_verdict']:
                        update_manual_verdict(row['post_id'], new_v)

# --- TAB 2: Chat Interface ---
with tab2:
    st.header("💬 Ask the Intelligence Database")
    st.caption(f"Context: Analyzing {len(filtered_df)} filtered records from {start_date} to {end_date}")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask something (e.g., 'What are the main rumors today?')"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        if not filtered_df.empty:
            # 构建上下文：包含 Verdict，这样 AI 能回答"有哪些假新闻"
            context_list = []
            for _, r in filtered_df.iterrows():
                context_list.append(
                    f"ID: {r['post_id']} | Status: {r['final_verdict']} | Platform: {r['platform']} | Content: {r['original_text']}")
            context_data = "\n".join(context_list)
        else:
            context_data = "No data found matching current filters."

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                ai_engine = ContentFilter()
                response = ai_engine.answer_user_question(context_data, prompt)
                st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})