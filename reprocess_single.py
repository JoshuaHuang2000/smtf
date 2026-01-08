import sqlite3
import os
import sys
from logic.filter import ContentFilter

# 路径修复：确保能找到数据库
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "smtf_memory.db")


def reprocess_one(target_id):
    print(f"[*] Targeting Post ID: {target_id}")

    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database not found at {DB_PATH}")
        return

    # 1. 初始化大脑
    try:
        filter_engine = ContentFilter()
        print(f"    -> AI Engine loaded ({filter_engine.fast_model})")
    except Exception as e:
        print(f"    [!] Failed to load AI: {e}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. 获取该帖子的原始数据
    cursor.execute('SELECT original_text, image_path, url FROM processed_posts WHERE post_id = ?', (target_id,))
    row = cursor.fetchone()

    if not row:
        print(f"❌ Post ID '{target_id}' not found in database.")
        conn.close()
        return

    original_text, image_path, url = row
    print(f"    -> Text Preview: {original_text[:50]}...")
    print(f"    -> Image Path: {image_path}")

    # 3. 重新分析
    print("    -> Sending to Gemini for re-evaluation...")
    try:
        # 调用核心分析逻辑
        analysis = filter_engine.analyze_post(original_text, image_path=image_path)

        new_verdict = analysis.get('verdict', 'MIXED')
        new_summary = analysis.get('summary', '')

        print(f"\n[{new_verdict}] Analysis Result:")
        print("-" * 40)
        print(new_summary)
        print("-" * 40)

        # 4. 更新数据库
        # 注意：我们会顺便清空 manual_verdict，确保 Dashboard 显示的是这个最新的 AI 结果
        cursor.execute('''
            UPDATE processed_posts 
            SET verdict = ?, summary = ?, manual_verdict = NULL 
            WHERE post_id = ?
        ''', (new_verdict, new_summary, target_id))

        conn.commit()
        print(f"✅ Database updated successfully!")

    except Exception as e:
        print(f"❌ Analysis Failed: {e}")

    conn.close()


if __name__ == "__main__":
    # 使用方式：python reprocess_single.py <ID>
    if len(sys.argv) < 2:
        # 如果没传参数，让用户手动输入
        target_id = input("Enter Post ID to reprocess: ").strip()
    else:
        target_id = sys.argv[1].strip()

    if target_id:
        reprocess_one(target_id)
    else:
        print("No ID provided.")