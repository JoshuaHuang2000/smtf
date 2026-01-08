import sqlite3
import os

DB_NAME = "smtf_memory.db"


def migrate():
    if not os.path.exists(DB_NAME):
        print("❌ Database not found.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print(f"[*] Starting V3 migration for {DB_NAME}...")

    # 创建简报存档表
    # date_key: 日期字符串 (例如 "2025-01-01")
    # context_hash: 只要当天的帖子内容变了（比如你手动修改了 verdict），我们就重新生成，用来做缓存失效检测
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS briefings (
            date_key TEXT PRIMARY KEY,
            content TEXT,
            context_hash TEXT, 
            created_at TIMESTAMP
        )
    ''')

    print("    -> Table 'briefings' created/verified.")
    conn.commit()
    conn.close()
    print("[✅] Migration V3 complete.")


if __name__ == "__main__":
    migrate()