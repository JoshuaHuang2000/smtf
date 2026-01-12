import sqlite3
import os

DB_NAME = "smtf_memory.db"


def inspect_weibo():
    if not os.path.exists(DB_NAME):
        print("❌ Database not found.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print(f"[*] Inspecting Weibo Data in {DB_NAME}...\n")

    # 查询所有 wb_ 开头的记录
    cursor.execute('''
        SELECT post_id, original_text, url, processed_at
        FROM processed_posts 
        WHERE post_id LIKE 'wb_%'
        ORDER BY processed_at DESC
    ''')
    rows = cursor.fetchall()

    if not rows:
        print("No Weibo records found.")
        return

    print(f"Total Weibo Records: {len(rows)}")
    print("Legend:")
    print("  ✅ REAL : 包含字母，通常是真正的微博 MID (如 wb_L9d8K...)")
    print("  ⚠️ HASH : 没抓到 ID，用哈希兜底的 (如 wb_hash_...)")
    print("  ❌ SUSP : 纯数字长ID，极可能是抓错了，抓成了博主的 UserID (如 wb_6607420428)")

    print("\n" + "-" * 110)
    print(f"{'STATUS':<8} | {'ID':<22} | {'URL':<35} | {'CONTENT PREVIEW'}")
    print("-" * 110)

    for row in rows:
        pid, text, url, time = row
        clean_text = text.replace('\n', ' ').strip()[:40]
        url_display = str(url)[:32] + "..." if url else "[No URL]"

        # 核心判断逻辑
        if "hash" in pid:
            status = "⚠️ HASH"
        elif pid.replace("wb_", "").isdigit():
            # 如果 ID 去掉前缀后全是数字，且长度像 User ID (10位左右)
            # 真正的微博数字 ID (mid) 现在很少见了，大部分变成了 base62 (字母数字混合)
            status = "❌ SUSP"
        else:
            status = "✅ REAL"

        print(f"{status:<8} | {pid:<22} | {url_display:<35} | {clean_text}")

    print("-" * 110)
    conn.close()


if __name__ == "__main__":
    inspect_weibo()