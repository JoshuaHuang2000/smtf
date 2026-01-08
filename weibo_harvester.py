import asyncio
from playwright.async_api import async_playwright
import os
import random
import base64
import re


class WeiboHarvester:
    def __init__(self, user_data_dir="browser_data", headless=False):
        # 挂载模式下，user_data_dir 由外部浏览器决定，这里仅作兼容
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
        """Plan A: 使用浏览器内部 JS Fetch 下载，完美继承 Referer 和 Cookie"""
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
                # [核心] 连接现有浏览器
                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                default_context = browser.contexts[0]
            except Exception as e:
                print(f"    [!] Connection failed. Is Canary running with --remote-debugging-port=9222? {e}")
                return []

            # [核心] 寻找或新建标签页
            page = None
            for p_tab in default_context.pages:
                if "weibo.com" in p_tab.url:
                    page = p_tab
                    print("    -> Found existing Weibo tab, reusing...")
                    # await page.bring_to_front()
                    break

            if not page:
                print("    -> Opening new Weibo tab...")
                page = await default_context.new_page()
                # 访问第一个目标作为初始化
                await page.goto(self.target_urls[0])

            # 注入防检测
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            all_posts = []
            os.makedirs("assets/images", exist_ok=True)

            # 1. 简单检查登录
            try:
                # 稍微等一下页面反应
                await page.wait_for_selector('article', timeout=5000)
            except:
                print("    [!] Waiting for content/login...")
                # 如果没刷出来，可能是没登录，或者页面卡顿，给点时间
                try:
                    await page.wait_for_selector('article', timeout=5000)
                except:
                    print("    [!] Login check failed or timeout. Skipping Weibo.")
                    await browser.close()
                    return []

            # 2. 循环抓取
            for url in self.target_urls:
                if len(all_posts) >= max_posts * len(self.target_urls): break
                print(f"    -> Visiting: {url}")

                try:
                    if page.url != url:
                        await page.goto(url, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(2, 4))
                        try:
                            await page.mouse.wheel(0, 800)
                            await asyncio.sleep(1.5)
                            await page.wait_for_selector('article', timeout=8000)
                        except:
                            continue

                    # 自动展开
                    try:
                        expand_btns = await page.get_by_text("展开", exact=True).all()
                        for btn in expand_btns[:3]:
                            if await btn.is_visible():
                                await btn.click()
                                await asyncio.sleep(0.5)
                    except:
                        pass

                    articles = await page.locator('article').all()
                    print(f"       Found {len(articles)} posts.")

                    user_posts_count = 0
                    for article in articles:
                        if user_posts_count >= max_posts: break
                        try:
                            # --- ID/URL 提取 ---
                            found_id = None
                            found_url = ""
                            links = await article.locator("a").all()
                            for link in links:
                                href = await link.get_attribute("href")
                                if href and ("/status/" in href or "weibo.com/" in href) and len(href) > 20:
                                    if href.startswith("//"):
                                        found_url = "https:" + href
                                    elif href.startswith("/"):
                                        found_url = "https://weibo.com" + href
                                    else:
                                        found_url = href
                                    parts = href.split("?")[0].split("/")
                                    if len(parts) > 0:
                                        candidate = parts[-1]
                                        if len(candidate) > 5:
                                            found_id = candidate
                                            break

                            content_text = await article.inner_text()
                            clean_text = content_text.replace("\n", " ").strip()
                            if found_id:
                                unique_id = f"{self.source_prefix}_{found_id}"
                            else:
                                unique_id = f"{self.source_prefix}_hash_{hash(clean_text[:50])}"

                            if unique_id in [p['id'] for p in all_posts]: continue

                            # --- 图片下载 (Plan A/B) ---
                            image_local_path = None

                            # 1. 寻找最佳图片候选者
                            target_img_element = None
                            target_src_hd = None

                            # 限定容器，防止抓到侧边栏
                            locators = ['.woo-picture-main img', '.pic-box img', 'img']

                            found_imgs = []
                            for loc in locators:
                                found_imgs = await article.locator(loc).all()
                                if found_imgs: break

                            for img in found_imgs:
                                try:
                                    src = await img.get_attribute("src")
                                    if not src: continue
                                    if src.startswith("//"): src = "https:" + src

                                    # 过滤垃圾
                                    blacklist = ["tvax", "tva", "crop", "face", "icon", "avatar", "blank", "us_service",
                                                 "empty", "skin"]
                                    if any(x in src for x in blacklist): continue
                                    if ".png" in src or ".svg" in src: continue
                                    if "sinaimg.cn" not in src and "weibocdn" not in src: continue

                                    # 尺寸检查
                                    try:
                                        width = await img.evaluate("el => el.naturalWidth")
                                        if 0 < width < 150: continue
                                    except:
                                        pass

                                    target_img_element = img

                                    # 构造高清链接
                                    high_res = src
                                    for pattern in ["/mw690/", "/orj360/", "/thumbnail/", "/bmiddle/", "/thumb180/",
                                                    "/small/", "/dr/"]:
                                        high_res = high_res.replace(pattern, "/large/")
                                    target_src_hd = high_res
                                    break
                                except:
                                    continue

                            # 2. 执行下载 (Plan A -> Plan B)
                            if target_img_element:
                                filename = f"assets/images/{unique_id}.jpg"
                                downloaded = False

                                # [Plan A] JS Fetch
                                if target_src_hd:
                                    img_bytes = await self._download_image_via_js(page, target_src_hd)
                                    if img_bytes and len(img_bytes) > 2000:
                                        with open(filename, "wb") as f:
                                            f.write(img_bytes)
                                        image_local_path = filename
                                        downloaded = True

                                # [Plan B] Screenshot Fallback
                                if not downloaded:
                                    try:
                                        await target_img_element.scroll_into_view_if_needed()
                                        await asyncio.sleep(0.5)  # 等待渲染
                                        await target_img_element.screenshot(path=filename, type="jpeg", quality=80)
                                        image_local_path = filename
                                        downloaded = True
                                    except Exception:
                                        pass
                            # -----------------------------------

                            if len(clean_text) < 10 and not image_local_path: continue

                            all_posts.append({
                                "id": unique_id,
                                "text": f"[Weibo] {clean_text[:600]}",
                                "url": found_url,
                                "image_path": image_local_path
                            })
                            user_posts_count += 1
                        except:
                            continue
                except:
                    continue

            print(f"    -> [Weibo] Harvest complete.")
            # 断开连接，不关闭浏览器
            await browser.close()
            return all_posts


if __name__ == "__main__":
    wb = WeiboHarvester(headless=False)
    data = asyncio.run(wb.harvest(3))
    for item in data:
        print(f"ID: {item['id']}")
        print(f"Img: {item.get('image_path')}")
        print(f"Text: {item['text'][:50]}...\n")