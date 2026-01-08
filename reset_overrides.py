import sqlite3
import os

DB_NAME = "smtf_memory.db"


def reset_manual():
    if not os.path.exists(DB_NAME):
        print("❌ Database not found.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print(f"[*] Resetting Manual Overrides in {DB_NAME}...")

    # 检查有多少条记录被人为修改过
    cursor.execute("SELECT count(*) FROM processed_posts WHERE manual_verdict IS NOT NULL")
    count = cursor.fetchone()[0]

    print(f"    -> Found {count} records with manual overrides.")

    if count > 0:
        # 将 manual_verdict 清空 (设为 NULL)
        cursor.execute("UPDATE processed_posts SET manual_verdict = NULL")
        conn.commit()
        print(f"    ✅ All manual overrides cleared. Dashboard will now show raw AI verdicts.")
    else:
        print("    -> No overrides found. The issue might be elsewhere.")

    conn.close()


if __name__ == "__main__":
    reset_manual()