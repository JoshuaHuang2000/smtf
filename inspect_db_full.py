import sqlite3
import os

DB_NAME = "smtf_memory.db"


def inspect():
    if not os.path.exists(DB_NAME):
        print(f"❌ Database file '{DB_NAME}' not found!")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        print("\n" + "=" * 80)
        print(f"📊 SMTF DATABASE INSPECTOR (Full View): {DB_NAME}")
        print("=" * 80)

        # 1. 总体统计
        cursor.execute("SELECT count(*) FROM processed_posts")
        total_count = cursor.fetchone()[0]
        print(f"Total Records: {total_count}\n")

        # 2. 最近记录详情 (详细清单模式)
        limit = 10  # 显示最近10条，太多了刷屏
        print(f"[Recent {limit} Records] (Ordered by Processing Time)")

        cursor.execute('''
            SELECT post_id, verdict, processed_at, url, original_text 
            FROM processed_posts 
            ORDER BY processed_at DESC 
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        for row in rows:
            p_id, verdict, time_str, url, text = row

            # 处理空 URL
            full_url = url if url else "[No URL stored]"

            # 处理正文换行，防止太乱
            clean_text = text.replace('\n', ' ')
            if len(clean_text) > 100:
                clean_text = clean_text[:100] + "..."

            print("-" * 80)
            print(f"🆔 ID      : {p_id}")
            print(f"⚖️ VERDICT : {verdict}")
            print(f"⏰ TIME    : {str(time_str)[:19]}")
            print(f"🔗 URL     : {full_url}")  # <--- 这里会显示完整链接
            print(f"📝 TEXT    : {clean_text}")

        print("-" * 80)

    except sqlite3.OperationalError as e:
        print(f"❌ Error: {e}")
        print("Tip: Did you run 'migrate_v2.py' to add the 'url' column?")
    finally:
        conn.close()


if __name__ == "__main__":
    inspect()