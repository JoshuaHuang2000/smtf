import sqlite3
import os

DB_NAME = "smtf_memory.db"
IMG_DIR = "assets/images"


def migrate():
    # 1. 创建存放图片的目录
    if not os.path.exists(IMG_DIR):
        os.makedirs(IMG_DIR, exist_ok=True)
        print(f"[+] Created image directory: {IMG_DIR}")

    # 2. 修改数据库
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 获取列名
    cursor.execute("PRAGMA table_info(processed_posts)")
    columns = [info[1] for info in cursor.fetchall()]

    if 'image_path' not in columns:
        print("    -> Adding column: image_path")
        cursor.execute("ALTER TABLE processed_posts ADD COLUMN image_path TEXT")
    else:
        print("    -> Column 'image_path' already exists.")

    conn.commit()
    conn.close()
    print("[✅] Migration V4 complete. Ready for Screenshots.")


if __name__ == "__main__":
    migrate()