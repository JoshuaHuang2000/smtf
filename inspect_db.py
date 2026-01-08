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
        print("\n" + "=" * 110)
        print(f"📊 SMTF DATABASE INSPECTOR: {DB_NAME}")
        print("=" * 110)

        # 1. 总体统计
        cursor.execute("SELECT count(*) FROM processed_posts")
        total_count = cursor.fetchone()[0]

        print(f"\n[Stats]")
        print(f"Total Records: {total_count}")

        # 按 Verdict 分类统计
        print("Breakdown by Verdict:")
        cursor.execute("SELECT verdict, count(*) FROM processed_posts GROUP BY verdict")
        stats = cursor.fetchall()
        for verdict, count in stats:
            bar = "█" * (count // 2 + 1)
            print(f"  - {verdict:<10} : {count:<3} {bar}")

        # 2. 最近记录详情 (增加了 URL 列)
        limit = 20
        print(f"\n[Recent {limit} Records] (Ordered by Processing Time)")
        print("-" * 110)

        # 调整表头，给 URL 留位置
        header = f"{'ID':<18} | {'VERDICT':<9} | {'TIME':<19} | {'URL':<30} | {'CONTENT SUMMARY'}"
        print(header)
        print("-" * 110)

        # --- 修改点：SQL 查询增加 url 字段 ---
        # 注意：这里假设你已经运行过 migrate_v2.py，数据库里有 url 列
        # 如果有些老数据没有 url，sqlite 会返回 None
        cursor.execute('''
            SELECT post_id, verdict, processed_at, url, original_text 
            FROM processed_posts 
            ORDER BY processed_at DESC 
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        for row in rows:
            p_id, verdict, time_str, url, text = row

            # 1. 处理 ID
            clean_id = str(p_id)
            if len(clean_id) > 16:
                clean_id = clean_id[:14] + ".."

            # 2. 处理 URL (处理 None 和过长的情况)
            clean_url = str(url) if url else ""
            if len(clean_url) > 28:
                clean_url = clean_url[:25] + "..."
            elif clean_url == "":
                clean_url = "[No URL]"

            # 3. 处理时间
            time_str = str(time_str)[:19]

            # 4. 处理正文
            clean_text = text.replace('\n', ' ').strip()
            if len(clean_text) > 35:
                clean_text = clean_text[:35] + "..."

            print(f"{clean_id:<18} | {verdict:<9} | {time_str:<19} | {clean_url:<30} | {clean_text}")

        print("-" * 110)

    except sqlite3.OperationalError as e:
        print(f"❌ Error: {e}")
        print("Tip: Did you run 'migrate_v2.py' to add the 'url' column?")
    finally:
        conn.close()


if __name__ == "__main__":
    inspect()