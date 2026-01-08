import asyncio
from playwright.async_api import async_playwright
import os


class RedditHarvester:
    def __init__(self, user_data_dir="browser_data", headless=False):
        self.headless = headless
        self.source_prefix = "reddit"

    async def harvest(self, max_posts=5):
        print(f"[*] [Reddit] Connecting to Canary (Port 9222)...")

        async with async_playwright() as p:
            try:
                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                default_context = browser.contexts[0]
            except Exception as e:
                print(f"    [!] Connection failed: {e}")
                return []

            # 寻找或新建 Reddit 标签页
            page = None
            for p_tab in default_context.pages:
                if "reddit.com" in p_tab.url:
                    page = p_tab
                    print("    -> Found existing Reddit tab, reusing...")
                    # await page.bring_to_front()
                    break

            if not page:
                print("    -> Opening new Reddit tab...")
                page = await default_context.new_page()
                await page.goto("https://www.reddit.com/")

            # 刷新以获取新内容
            await page.reload()

            try:
                await page.wait_for_selector('shreddit-post', state="visible", timeout=8000)
            except:
                print("    [!] Reddit content not found. Waiting...")
                await page.wait_for_selector('shreddit-post', timeout=0)

            print("    -> Scraping Reddit feed...")
            posts_data = []
            seen_ids = set()

            for i in range(3):
                posts = await page.locator('shreddit-post').all()
                print(f"       (Scroll {i + 1}) Found {len(posts)} posts.")

                for post in posts:
                    if len(posts_data) >= max_posts: break
                    try:
                        raw_id = await post.get_attribute("id")
                        is_promoted = await post.get_attribute("promoted")
                        if is_promoted == "true": continue

                        title = await post.get_attribute("post-title")
                        permalink = await post.get_attribute("permalink")

                        unique_id = f"{self.source_prefix}_{raw_id}"
                        if unique_id in seen_ids: continue

                        full_text = f"[Reddit] {title}\n(Link: https://www.reddit.com{permalink})"

                        seen_ids.add(unique_id)
                        posts_data.append({
                            "id": unique_id,
                            "text": full_text,
                            "url": f"https://www.reddit.com{permalink}"
                        })
                    except:
                        continue

                if len(posts_data) >= max_posts: break
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(2)

            print(f"    -> [Reddit] Harvest complete.")
            await browser.close()  # 断开连接
            return posts_data


if __name__ == "__main__":
    r = RedditHarvester()
    data = asyncio.run(r.harvest(3))
    print(data)