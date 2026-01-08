import sqlite3
import os

# 获取当前脚本所在目录的绝对路径，确保和 main.py 在同一级
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "smtf_memory.db")


def check_db():
    print(f"[*] Diagnostic Tool for: {DB_PATH}")

    # 1. 检查文件是否存在
    if not os.path.exists(DB_PATH):
        print(f"❌ FILE NOT FOUND! The database file does not exist at this path.")
        return

    # 2. 检查文件大小
    size = os.path.getsize(DB_PATH)
    print(f"    -> File Size: {size / 1024:.2f} KB")

    if size == 0:
        print("❌ FILE IS EMPTY! (0 KB). This is why Python can't find any tables.")
        return

    # 3. 检查表结构
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 查询所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print(f"    -> Found {len(tables)} tables:")
        found_target = False
        for t in tables:
            print(f"       - {t[0]}")
            if t[0] == "processed_posts":
                found_target = True

        print("-" * 30)

        if found_target:
            print("✅ 'processed_posts' table EXISTS. The database structure is correct.")

            # 顺便看看有多少数据
            cursor.execute("SELECT count(*) FROM processed_posts")
            count = cursor.fetchone()[0]
            print(f"    -> Row Count: {count}")

        else:
            print("❌ 'processed_posts' table MISSING. You are connected to a wrong or corrupted DB.")

        conn.close()

    except Exception as e:
        print(f"❌ Error reading DB: {e}")


if __name__ == "__main__":
    check_db()