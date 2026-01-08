import sqlite3
import os

DB_NAME = "smtf_memory.db"

def migrate():
    if not os.path.exists(DB_NAME):
        print("❌ Database not found. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print(f"[*] Starting migration for {DB_NAME}...")

    # 获取当前所有列名
    cursor.execute("PRAGMA table_info(processed_posts)")
    columns = [info[1] for info in cursor.fetchall()]

    # 1. 添加 URL 字段
    if 'url' not in columns:
        print("    -> Adding column: url")
        cursor.execute("ALTER TABLE processed_posts ADD COLUMN url TEXT")
    else:
        print("    -> Column 'url' already exists.")

    # 2. 添加 manual_verdict 字段 (用于 V2 的手动修正)
    if 'manual_verdict' not in columns:
        print("    -> Adding column: manual_verdict")
        cursor.execute("ALTER TABLE processed_posts ADD COLUMN manual_verdict TEXT")
    else:
        print("    -> Column 'manual_verdict' already exists.")

    conn.commit()
    conn.close()
    print("[✅] Migration complete. Database is ready for V2.")

if __name__ == "__main__":
    migrate()