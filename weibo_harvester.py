import asyncio
from playwright.async_api import async_playwright
import os
import random
import base64
import re


class WeiboHarvester:
    def __init__(self, user_data_dir="browser_data", headless=False):
        self.headless = headless
        self.source_prefix = "wb"
        self.target_urls = [
            "https://weibo.com/u/7378302827",
            "https://weibo.com/u/6607420428",
            "https://weibo.com/u/1989534434",
            "https://weibo.com/u/1642088277",
        ]

    async def harvest(self, max_posts=5):
        return await self.harvest_weibo(max_posts)

    async def _download_image_via_js(self, page, url):
        js_code = """
        async (url) => {
            try {
                const response = await fetch(url);
                if (!response.ok) return null;
                const blob = await response.blob();
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            } catch (err) { return null; }
        }
        """
        try:
            data_url = await page.evaluate(js_code, url)
            if data_url and "base64," in data_url:
                _, encoded = data_url.split(",", 1)
                return base64.b64decode(encoded)
        except:
            pass
        return None

    async def harvest_weibo(self, max_posts=5):
        print(f"[*] [Weibo] Connecting to Canary (Port 9222)...")

        async with async_playwright() as p:
            try:
                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                default_context = browser.contexts[0]
            except Exception as e:
                print(f"    [!] Connection failed: {e}")
                return []

            page = None
            for p_tab in default_context.pages:
                if "weibo.com" in p_tab.url:
                    page = p_tab
                    print("    -> Found existing Weibo tab.")
                    break

            if not page:
                print("    -> Opening new Weibo tab...")
                page = await default_context.new_page()
                await page.goto(self.target_urls[0])

            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            all_posts = []
            os.makedirs("assets/images", exist_ok=True)

            try:
                await page.wait_for_selector('article', timeout=5000)
            except:
                print("    [!] Waiting for login...")
                try:
                    await page.wait_for_selector('article', timeout=0)
                except:
                    return []

            # --- 2. 循环抓取 ---
            for url in self.target_urls:
                print(f"    -> Visiting: {url}")

                # [核心修复] 重置当前博主的计数器
                posts_from_this_user = 0

                try:
                    if page.url != url:
                        await page.goto(url, wait_until="domcontentloaded")
                        await asyncio.sleep(3)

                    last_article_count = 0

                    for scroll_round in range(3):
                        # [检查点 1] 如果这个博主已经抓够了，跳出滚动循环，直接去下一个博主
                        if posts_from_this_user >= max_posts:
                            print(f"       (Target reached for this user: {posts_from_this_user})")
                            break

                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(2.5)

                        try:
                            expand_links = await page.locator("a:has-text('展开'), span:has-text('展开')").all()
                            for link in expand_links[:3]:
                                if await link.is_visible():
                                    await link.click()
                                    await asyncio.sleep(0.2)
                        except:
                            pass

                        articles = await page.locator('article').all()
                        current_count = len(articles)
                        # print(f"       (Round {scroll_round + 1}) DOM has {current_count} articles.")

                        last_article_count = current_count

                        for i, article in enumerate(articles):
                            # [检查点 2] 再次检查当前博主是否抓够了
                            if posts_from_this_user >= max_posts: break

                            try:
                                raw_text = await article.inner_text()
                                content_preview = raw_text.replace('\n', ' ')[:15]

                                # --- ID/URL 提取 ---
                                found_id = None
                                found_url = ""
                                links = await article.locator("a").all()
                                for link in links:
                                    href = await link.get_attribute("href")
                                    if not href: continue
                                    if ("/status/" in href) or (
                                            "weibo.com/" in href and "/u/" not in href and len(href.split("/")) > 4):
                                        if href.startswith("//"):
                                            temp_url = "https:" + href
                                        elif href.startswith("/"):
                                            temp_url = "https://weibo.com" + href
                                        else:
                                            temp_url = href

                                        parts = temp_url.split("?")[0].split("/")
                                        candidate_id = parts[-1]
                                        if candidate_id.isdigit() and len(candidate_id) == 10: continue
                                        if len(candidate_id) > 5:
                                            found_id = candidate_id
                                            found_url = temp_url
                                            break

                                clean_text = raw_text.replace("\n", " ").strip()

                                if found_id:
                                    unique_id = f"{self.source_prefix}_{found_id}"
                                else:
                                    unique_id = f"{self.source_prefix}_hash_{hash(clean_text[:50])}"

                                # 去重 (仅跳过，不计入有效抓取)
                                if unique_id in [p['id'] for p in all_posts]: continue

                                # --- 图片下载 ---
                                image_local_path = None
                                target_img_element = None
                                target_src_hd = None

                                locators = ['article .woo-picture-main img', 'article .pic-box img', 'article img']
                                found_imgs = []
                                for loc in locators:
                                    found_imgs = await article.locator(loc.replace('article ', '')).all()
                                    if found_imgs: break

                                for img in found_imgs:
                                    try:
                                        src = await img.get_attribute("src")
                                        if not src: continue
                                        if src.startswith("//"): src = "https:" + src

                                        blacklist = ["tvax", "tva", "crop", "face", "icon", "avatar", "blank",
                                                     "us_service", "empty", "skin"]
                                        if any(x in src for x in blacklist): continue
                                        if ".png" in src or ".svg" in src: continue

                                        try:
                                            width = await img.evaluate("el => el.naturalWidth")
                                            if 0 < width < 150: continue
                                        except:
                                            pass

                                        target_img_element = img
                                        high_res = src
                                        for pattern in ["/mw690/", "/orj360/", "/thumbnail/", "/bmiddle/", "/thumb180/",
                                                        "/small/", "/dr/"]:
                                            high_res = high_res.replace(pattern, "/large/")
                                        target_src_hd = high_res
                                        break
                                    except:
                                        continue

                                if target_img_element:
                                    filename = f"assets/images/{unique_id}.jpg"
                                    downloaded = False

                                    if target_src_hd:
                                        img_bytes = await self._download_image_via_js(page, target_src_hd)
                                        if img_bytes and len(img_bytes) > 2000:
                                            with open(filename, "wb") as f:
                                                f.write(img_bytes)
                                            image_local_path = filename
                                            downloaded = True

                                    if not downloaded:
                                        try:
                                            await target_img_element.scroll_into_view_if_needed()
                                            await asyncio.sleep(0.3)
                                            await target_img_element.screenshot(path=filename, type="jpeg", quality=80)
                                            image_local_path = filename
                                            downloaded = True
                                        except:
                                            pass

                                if len(clean_text) < 5 and not image_local_path: continue

                                print(f"       [+] Added: {unique_id} | {content_preview}...")
                                all_posts.append({
                                    "id": unique_id,
                                    "text": f"[Weibo] {clean_text[:600]}",
                                    "url": found_url,
                                    "image_path": image_local_path
                                })
                                # [核心] 有效计数器 +1
                                posts_from_this_user += 1

                            except Exception:
                                continue

                        # 再次滚动
                        await page.mouse.wheel(0, 500)

                except Exception as e:
                    print(f"    [!] Error visiting {url}: {e}")

            print(f"    -> [Weibo] Harvest complete.")
            await browser.close()
            return all_posts


if __name__ == "__main__":
    wb = WeiboHarvester(headless=False)
    data = asyncio.run(wb.harvest(5))
    for item in data:
        print(f"ID: {item['id']}")