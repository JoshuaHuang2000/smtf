import sqlite3
import json
from datetime import datetime


class Database:
    def __init__(self, db_name="smtf_memory.db"):
        # [核心修改] 增加 timeout=30 (单位：秒)
        # 这意味着如果数据库被占用，它会耐心等待30秒，而不是立刻崩溃
        self.conn = sqlite3.connect(db_name, timeout=30.0)
        # 开启 WAL 模式提高并发性能
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        """初始化数据表"""
        # 包含所有 V4 版本的字段
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_posts (
                post_id TEXT PRIMARY KEY,
                original_text TEXT,
                verdict TEXT,
                summary TEXT,
                processed_at TIMESTAMP,
                url TEXT,
                manual_verdict TEXT,
                image_path TEXT
            )
        ''')
        self.conn.commit()

    def is_processed(self, post_id_hash) -> bool:
        self.cursor.execute('SELECT 1 FROM processed_posts WHERE post_id = ?', (str(post_id_hash),))
        return self.cursor.fetchone() is not None

    def save_result(self, post_data: dict, analysis_result: dict):
        """保存处理结果 (适配 V3.3 三态逻辑)"""

        # [核心修改] 直接从 analysis_result 获取 verdict
        # 如果是 Stage 1 过滤掉的，通常 verdict 是 NOISE
        verdict = analysis_result.get('verdict', 'MIXED')

        # 再次确认：如果是被标记为不相关，强制设为 NOISE
        if not analysis_result.get('is_relevant', True):
            verdict = "NOISE"

        post_url = post_data.get('url', '')
        img_path = post_data.get('image_path', None)

        # summary 对应 filter 返回的 summary (原 fact_check_notes)
        summary = analysis_result.get('summary', 'No summary')

        try:
            self.cursor.execute('''
                INSERT INTO processed_posts (post_id, original_text, verdict, summary, processed_at, url, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(post_data['id']),
                post_data['text'],
                verdict,
                summary,
                datetime.now(),
                post_url,
                img_path
            ))
            self.conn.commit()
            print(f"    [DB] Saved {str(post_data['id'])[:8]} as {verdict}")
        except sqlite3.IntegrityError:
            print(f"    [DB] Post {str(post_data['id'])[:8]} already exists.")

    def get_recent_digests(self, limit=10):
        # 这是一个给旧版 Editor 用的接口，Dashboard 现在直接读 pandas
        self.cursor.execute('''
            SELECT original_text, verdict, summary, processed_at 
            FROM processed_posts 
            WHERE verdict != 'NOISE' 
            ORDER BY processed_at DESC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()