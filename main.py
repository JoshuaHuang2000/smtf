import asyncio
import os
import argparse
import time
from logic.filter import ContentFilter
# 导入各个 Harvester
from harvester import Harvester as XHarvester
from weibo_harvester import WeiboHarvester
# Reddit 暂时还没更新多模态，先留着
from reddit_harvester import RedditHarvester
from database import Database
from editor import Editor


class SocialMediaTruthFilter:
    def __init__(self, headless=False):
        self.db = Database()
        self.filter_engine = ContentFilter()
        self.editor = Editor()

        # 注册收割者
        self.harvesters = [
            ("X (Twitter)", XHarvester(headless=headless)),
            ("Weibo", WeiboHarvester(headless=headless)),
            ("Reddit", RedditHarvester(headless=headless))
        ]

    async def run_pipeline(self, is_cron=False):
        print(f"\n[{'CRON' if is_cron else 'MANUAL'}] Starting SMTF Pipeline...")

        all_new_insights = []
        limit = 10 if is_cron else 5

        # 1. 轮询平台
        for platform_name, harvester in self.harvesters:
            print(f"\n[A] Harvesting {platform_name}...")

            try:
                # 统一调用 harvest 接口
                raw_posts = await harvester.harvest(max_posts=limit)

                if not raw_posts:
                    print(f"    -> No posts from {platform_name}.")
                    continue

                print(f"[B] Auditing {len(raw_posts)} posts from {platform_name}...")

                for post in raw_posts:
                    # 统一 ID 格式 (X 已经加了前缀，Weibo 也加了，Reddit 需要确认)
                    # 简单起见，这里做个双重保险
                    raw_id = str(post['id'])
                    if platform_name == "X (Twitter)" and not raw_id.startswith("x_"):
                        final_id = f"x_{raw_id}"
                    elif platform_name == "Reddit" and not raw_id.startswith("reddit_"):
                        final_id = f"reddit_{raw_id}"
                    else:
                        final_id = raw_id  # Weibo 自带 wb_ 前缀

                    post['id'] = final_id

                    # 查库去重
                    if self.db.is_processed(final_id):
                        continue

                    # AI 分析 (传入文本和图片路径)
                    print(f"    -> Analyzing: {final_id[:15]}...")

                    img_path = post.get('image_path')
                    analysis = self.filter_engine.analyze_post(post['text'], image_path=img_path)

                    # 存库
                    self.db.save_result(post, analysis)

                    # [核心修改] 适配新的 Verdict 显示逻辑
                    verdict = analysis.get('verdict', 'MIXED')
                    is_rel = analysis.get('is_relevant', False)

                    if is_rel and verdict != 'NOISE':
                        print(f"    [✅ {verdict}] {platform_name}")
                        all_new_insights.append(analysis)
                    else:
                        print(f"    [❌ {verdict}] {analysis.get('relevance_reason', 'Dropped')}")

                    # 礼貌等待
                    time.sleep(1)

            except Exception as e:
                print(f"    [!] Error harvesting {platform_name}: {e}")
                # 打印详细堆栈方便调试，生产环境可去掉
                # import traceback; traceback.print_exc()

        # 2. 生成报告 (Legacy HTML Report)
        # Dashboard 已经是主力了，这个 HTML 报告作为备用
        should_report = len(all_new_insights) > 0 or (not is_cron)

        if should_report:
            print("\n[C] Updating Digest Cache...")
            # 实际上 V2/V3 主要靠 Dashboard 看了，这里就不强制弹窗了
            # 如果你还想弹 HTML，可以保留下面的代码
            # recent_data = self.db.get_recent_digests(limit=20)
            # if recent_data:
            #     html, path = self.editor.generate_report(recent_data)
            #     if not is_cron:
            #         os.system(f"open '{path}'")
        else:
            print("    -> No new insights. Silent mode.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cron", action="store_true")
    args = parser.parse_args()

    app = SocialMediaTruthFilter(headless=args.cron)
    try:
        asyncio.run(app.run_pipeline(is_cron=args.cron))
    finally:
        app.db.close()