import os
import sys
import argparse
from database import Database
from editor import Editor


def open_file_in_browser(file_path):
    """跨平台打开文件"""
    try:
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":  # macOS
            os.system(f"open '{file_path}'")
        else:  # Linux
            os.system(f"xdg-open '{file_path}'")
        print("    -> Browser launched.")
    except Exception as e:
        print(f"    [!] Failed to open browser: {e}")
        print(f"    Please manually open: {file_path}")


def generate_and_show(limit=20):
    print(f"[*] Generating Static Digest (Last {limit} items)...")

    # 1. 连接数据库读取数据
    db = Database()
    try:
        # 注意：这里使用的是 database.py 里现成的 get_recent_digests 方法
        # 它默认过滤掉了 NOISE，按时间倒序
        rows = db.get_recent_digests(limit=limit)
    except Exception as e:
        print(f"    [!] Database Error: {e}")
        return
    finally:
        db.close()

    if not rows:
        print("    [!] No relevant data found in database.")
        return

    print(f"    -> Found {len(rows)} records.")

    # 2. 调用 Editor 生成 HTML
    try:
        editor = Editor()
        # generate_report 会返回 (html_content, file_path)
        _, file_path = editor.generate_report(rows)
        print(f"    -> Report saved to: {file_path}")

        # 3. 弹窗显示
        open_file_in_browser(file_path)

    except Exception as e:
        print(f"    [!] Editor Error: {e}")


if __name__ == "__main__":
    # 支持命令行参数调整显示条数
    # 例如: python show_digest.py --limit 50
    parser = argparse.ArgumentParser(description="Generate and pop-up the static HTML digest.")
    parser.add_argument("--limit", type=int, default=20, help="Number of recent posts to include")
    args = parser.parse_args()

    generate_and_show(limit=args.limit)