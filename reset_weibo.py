import sqlite3
import os
import glob

DB_NAME = "smtf_memory.db"
IMG_DIR = "assets/images"


def reset():
    print("[*] Starting Weibo Image Cleanup...")

    # 1. 删除本地文件
    # 找到所有 wb_ 开头的图片
    pattern = os.path.join(IMG_DIR, "wb_*")
    files = glob.glob(pattern)

    print(f"    -> Found {len(files)} Weibo image files.")
    for f in files:
        try:
            os.remove(f)
        except Exception as e:
            print(f"    [!] Failed to delete {f}: {e}")

    print("    -> Local files deleted.")

    # 2. 重置数据库
    if os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # 将所有微博的 image_path 设为 NULL
        cursor.execute("UPDATE processed_posts SET image_path = NULL WHERE post_id LIKE 'wb_%'")
        changes = conn.total_changes

        conn.commit()
        conn.close()
        print(f"    -> Database updated. Reset {changes} records.")
    else:
        print("    [!] Database not found.")

    print("[✅] Cleanup complete. You can run 'backfill_images.py' now.")


if __name__ == "__main__":
    reset()