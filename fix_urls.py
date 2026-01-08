import sqlite3
import os

DB_NAME = "smtf_memory.db"


def fix_urls():
    if not os.path.exists(DB_NAME):
        print("❌ Database not found.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print(f"[*] Analyzing {DB_NAME} for missing URLs...")

    # 1. 查找所有 URL 为空 的记录
    # 注意：根据你的迁移情况，url 可能是 NULL 或者 空字符串
    cursor.execute("SELECT post_id, original_text FROM processed_posts WHERE url IS NULL OR url = ''")
    rows = cursor.fetchall()

    if not rows:
        print("    -> No missing URLs found!")
        return

    print(f"    -> Found {len(rows)} records without URLs. Attempting to reconstruct...")

    updated_count = 0
    skipped_count = 0

    for row in rows:
        post_id = str(row[0])
        reconstructed_url = ""

        # --- 策略 A: X (Twitter) ---
        if post_id.startswith("x_"):
            if "hash" not in post_id:
                # ID 格式: x_123456789
                real_id = post_id.replace("x_", "")
                if real_id.isdigit():
                    reconstructed_url = f"https://x.com/i/status/{real_id}"

        # --- 策略 B: Weibo ---
        elif post_id.startswith("wb_"):
            if "hash" not in post_id:
                # ID 格式: wb_Lc8dD...
                real_id = post_id.replace("wb_", "")
                # 微博有一个通用的详情页跳转链接
                # 也可以用 m.weibo.cn/detail/{id}
                reconstructed_url = f"https://weibo.com/detail/{real_id}"

        # --- 策略 C: Reddit ---
        elif post_id.startswith("reddit_"):
            # ID 格式: reddit_t3_1abcde
            # Reddit 短链接格式: https://redd.it/1abcde (去掉 t3_ 前缀)
            clean_id = post_id.replace("reddit_", "")
            if "_" in clean_id:
                # 如果是 t3_xxxxx，取后半部分
                short_id = clean_id.split("_")[1]
                reconstructed_url = f"https://redd.it/{short_id}"
            else:
                reconstructed_url = f"https://redd.it/{clean_id}"

        # --- 执行更新 ---
        if reconstructed_url:
            cursor.execute("UPDATE processed_posts SET url = ? WHERE post_id = ?", (reconstructed_url, post_id))
            updated_count += 1
            print(f"    [Fixed] {post_id[:15]}... -> {reconstructed_url}")
        else:
            skipped_count += 1
            # print(f"    [Skip] Cannot reconstruct: {post_id}")

    conn.commit()
    conn.close()

    print("-" * 50)
    print(f"✅ URL Repair Complete.")
    print(f"    - Fixed: {updated_count}")
    print(f"    - Skipped (Hash IDs): {skipped_count}")


if __name__ == "__main__":
    fix_urls()