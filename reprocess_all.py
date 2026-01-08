import sqlite3
import time
import os
from logic.filter import ContentFilter

# --- [核心修改] 获取当前脚本所在的绝对路径 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 拼接数据库的完整路径
DB_PATH = os.path.join(BASE_DIR, "smtf_memory.db")


def reprocess_all():
    print("[*] Starting Full Database Standardization (TRUE/FALSE/MIXED)...")
    print(f"    -> Connecting to DB at: {DB_PATH}")  # 打印出来让你确认路径对不对

    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database file not found at {DB_PATH}")
        return

    try:
        filter_engine = ContentFilter()
    except Exception as e:
        print(f"    [!] Engine Init Failed: {e}")
        return

    conn = sqlite3.connect(DB_PATH)  # 使用绝对路径连接
    cursor = conn.cursor()

    # ... 后面的代码保持不变 ...
    # 1. 选取所有非噪音数据
    try:
        cursor.execute('''
            SELECT post_id, original_text, image_path 
            FROM processed_posts 
            WHERE verdict != 'NOISE'
        ''')
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"❌ Database Error: {e}")
        print("Tip: Are you sure 'smtf_memory.db' is in the same folder as this script?")
        return

    print(f"[*] Found {len(rows)} records to standardize.")

    updated_count = 0
    for i, (post_id, text, img_path) in enumerate(rows):
        print(f"[{i + 1}/{len(rows)}] Auditing {post_id}...")

        try:
            # 调用新逻辑
            analysis = filter_engine.analyze_post(text, image_path=img_path)

            new_verdict = analysis.get('verdict', 'MIXED')
            new_summary = analysis.get('summary', '')

            # 更新数据库
            cursor.execute('''
                UPDATE processed_posts 
                SET verdict = ?, summary = ?
                WHERE post_id = ?
            ''', (new_verdict, new_summary, post_id))

            conn.commit()
            print(f"    -> Result: {new_verdict}")
            updated_count += 1

        except Exception as e:
            print(f"    [!] Error: {e}")

        # 稍微快一点
        time.sleep(0.5)

    conn.close()
    print(f"\n[✅] Standardization Complete. Updated {updated_count} records.")


if __name__ == "__main__":
    reprocess_all()