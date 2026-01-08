import asyncio
from playwright.async_api import async_playwright
import os
import random
import re  # 别忘了导入 re


class Harvester:
    def __init__(self, user_data_dir="browser_data", headless=False):
        self.user_data_dir = user_data_dir
        self.headless = headless

    async def harvest(self, max_posts=5):
        return await self.harvest_x_timeline(max_posts)

    async def harvest_x_timeline(self, max_posts=5):
        print(f"[*] [X] Attempting to connect to LOCAL Chrome (Port 9222)...")

        async with async_playwright() as p:
            try:
                # 1. 连接本地 Chrome (强制 IPv4)
                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                default_context = browser.contexts[0]
            except Exception as e:
                print(f"    [!] Connection failed: {e}")
                print(
                    r"    👉 请先在终端运行: /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir='/tmp/chrome_dev_session'")
                return []

            # 2. 寻找 X 标签页
            page = None
            pages = default_context.pages

            for p_tab in pages:
                if "x.com" in p_tab.url or "twitter.com" in p_tab.url:
                    page = p_tab
                    print("    -> Found existing X tab, reusing...")
                    # [优化] 注释掉这就不会强制切屏了，让它在后台默默跑
                    # await page.bring_to_front()
                    break

            if not page:
                print("    -> No X tab found, opening new one...")
                page = await default_context.new_page()
                await page.goto("https://x.com/home")

            # [核心黑科技] CDP 强制伪装可见性
            try:
                # 使用 default_context 创建会话更稳健
                client = await default_context.new_cdp_session(page)
                # 告诉 Chrome: "嘿，你就在屏幕最中间，用户正盯着你看呢"
                await client.send("Emulation.setFocusEmulationEnabled", {"enabled": True})
                await client.send("Emulation.setCPUThrottlingRate", {"rate": 1})
                await client.send("Emulation.setAutoDarkModeOverride", {"enabled": False})
                print("    -> [Stealth] CDP visibility spoofing active.")
            except Exception as e:
                print(f"    [!] CDP Warning: {e}")

            # 3. 刷新与加载
            print("    -> Refreshing timeline...")
            try:
                await page.reload(wait_until="domcontentloaded")
                await page.wait_for_selector('[data-testid="tweet"]', state="visible", timeout=15000)
                print("    -> Timeline ready.")
            except:
                print("    [!] Timeline timeout. Please check Chrome window manually.")
                # 断开连接，不杀进程
                await browser.close()
                return []

            # 4. 抓取流程
            print("    -> Scraping timeline...")
            posts_data = []
            seen_ids = set()
            os.makedirs("assets/images", exist_ok=True)

            for i in range(3):
                tweets = await page.locator('[data-testid="tweet"]').all()
                print(f"       (Scroll {i + 1}) Visible tweets: {len(tweets)}")

                for tweet in tweets:
                    if len(posts_data) >= max_posts: break

                    try:
                        extracted_id = None
                        final_url = ""

                        # ID / URL 提取
                        links = await tweet.locator('a[href*="/status/"]').all()
                        for link in links:
                            href = await link.get_attribute("href")
                            if "/status/" in href:
                                parts = href.split("/status/")
                                if len(parts) > 1:
                                    possible_id = parts[1].split("/")[0].split("?")[0]
                                    if possible_id.isdigit():
                                        extracted_id = f"x_{possible_id}"
                                        final_url = f"https://x.com{href}"
                                        break

                        text = await tweet.inner_text()
                        clean_text = text.replace("\n", " ").strip()
                        if not extracted_id: extracted_id = f"x_hash_{hash(clean_text)}"

                        if extracted_id in seen_ids: continue

                        # 图片下载 (直接复用 Page Request)
                        image_local_path = None
                        photo_divs = await tweet.locator('[data-testid="tweetPhoto"] img').all()

                        if photo_divs:
                            img_src = await photo_divs[0].get_attribute("src")
                            if img_src:
                                # 替换为原图
                                if "name=" in img_src:
                                    high_res_src = re.sub(r"name=\w+", "name=orig", img_src)
                                else:
                                    high_res_src = img_src

                                ext = "jpg"
                                if "format=png" in high_res_src: ext = "png"
                                filename = f"assets/images/{extracted_id}.{ext}"

                                try:
                                    # 利用当前页面的 Context 下载，最安全
                                    response = await page.request.get(high_res_src)
                                    if response.status == 200:
                                        with open(filename, "wb") as f:
                                            f.write(await response.body())
                                        image_local_path = filename
                                except:
                                    pass

                        if len(clean_text) > 20 or image_local_path:
                            seen_ids.add(extracted_id)
                            posts_data.append({
                                "id": extracted_id,
                                "text": clean_text[:500],
                                "url": final_url,
                                "image_path": image_local_path
                            })

                    except Exception:
                        continue

                if len(posts_data) >= max_posts: break

                # 随机滚动模拟
                await page.mouse.wheel(0, random.randint(800, 1500))
                await asyncio.sleep(random.uniform(2.0, 4.0))

            print(f"    -> Harvested {len(posts_data)} posts.")

            # [重要] 只是断开连接，Chrome 依然在后台运行
            await browser.close()
            print("    -> Disconnected (Chrome stays open).")

            return posts_data


if __name__ == "__main__":
    h = Harvester()
    asyncio.run(h.harvest(3))
