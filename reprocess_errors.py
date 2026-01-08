import sqlite3
import time
from logic.filter import ContentFilter

DB_NAME = "smtf_memory.db"


def reprocess():
    print("[*] Starting Error Reprocessing...")

    # 1. 初始化过滤器
    try:
        filter_engine = ContentFilter()
        print(f"    -> Engine loaded. Model: {filter_engine.fast_model}")
    except Exception as e:
        print(f"    [!] Failed to load engine: {e}")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 2. 查找脏数据 [修正SQL]
    # 我们只检查 summary 列，因为数据库里没有 fact_check_notes 列
    cursor.execute('''
        SELECT post_id, original_text, image_path 
        FROM processed_posts 
        WHERE summary LIKE '%Error%' 
           OR summary LIKE '%404%'
    ''')
    rows = cursor.fetchall()

    if not rows:
        print("✅ No error records found. Database is clean.")
        return

    print(f"[*] Found {len(rows)} records to re-process.")

    # 3. 重新跑 AI 分析
    updated_count = 0
    for i, (post_id, text, img_path) in enumerate(rows):
        print(f"[{i + 1}/{len(rows)}] Reprocessing {post_id}...")

        try:
            # 调用 filter.py 重新分析
            analysis = filter_engine.analyze_post(text, image_path=img_path)

            # 获取新的分析结果
            # 注意：filter返回的是 'fact_check_notes'，我们要把它存入数据库的 'summary' 列
            new_summary = analysis.get('fact_check_notes', '')

            # 简单的错误检查
            if "Error" not in new_summary and "404" not in new_summary:
                verdict = "TRUE" if analysis['fact_check_passed'] else "WARNING"
                if not analysis['is_relevant']:
                    verdict = "NOISE"

                # [修正SQL] 更新语句只更新存在的列
                cursor.execute('''
                    UPDATE processed_posts 
                    SET verdict = ?, summary = ?
                    WHERE post_id = ?
                ''', (verdict, new_summary, post_id))

                conn.commit()
                print(f"    ✅ Fixed.")
                updated_count += 1
            else:
                # 如果还是报错，可能是 API 问题或者网络问题
                fail_reason = new_summary[:50].replace('\n', ' ')
                print(f"    ❌ Still failing: {fail_reason}...")

        except Exception as e:
            print(f"    [!] Script Crash: {e}")

        time.sleep(1)

    conn.close()
    print(f"\n[Done] Reprocessed. Successfully fixed {updated_count} records.")


if __name__ == "__main__":
    reprocess()