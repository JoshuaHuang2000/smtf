import asyncio
from playwright.async_api import async_playwright
import sqlite3
import os
import re
import random
import base64

DB_NAME = "smtf_memory.db"
USER_DATA_DIR = os.path.join(os.getcwd(), "browser_data")
IMG_DIR = "assets/images"


async def download_image_via_js(page, url):
    """
    Plan A: JS 注入下载。
    利用浏览器当前的上下文发起请求，完美继承 Referer 和 Cookie。
    """
    js_code = """
    async (url) => {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(response.statusText);
            const blob = await response.blob();
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        } catch (err) {
            return null;
        }
    }
    """
    try:
        # 执行 JS
        data_url = await page.evaluate(js_code, url)
        if data_url and "base64," in data_url:
            _, encoded = data_url.split(",", 1)
            return base64.b64decode(encoded)
    except:
        pass
    return None


async def process_page(page, url, post_id, platform):
    filename = f"{IMG_DIR}/{post_id}.jpg"

    try:
        try:
            # 1. 访问页面
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)

            # [关键] 随机行为模拟
            delay = random.uniform(1.5, 3.5)
            # print(f"       Thinking for {delay:.1f}s...")
            await asyncio.sleep(delay)

            # 滚动触发懒加载
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(1.0)
        except:
            pass

        target_img_element = None
        target_src_hd = None

        # ==========================
        # 策略 A: X (Twitter)
        # ==========================
        if platform == "x":
            try:
                await page.wait_for_selector('[data-testid="tweetPhoto"] img', timeout=5000)
                photo_divs = await page.locator('[data-testid="tweetPhoto"] img').all()
                if photo_divs:
                    target_img_element = photo_divs[0]
                    src = await target_img_element.get_attribute("src")
                    if src:
                        target_src_hd = re.sub(r"name=\w+", "name=orig", src) if "name=" in src else src
            except:
                pass

        # ==========================
        # 策略 B: Weibo (严格筛选)
        # ==========================
        elif platform == "wb":
            try:
                locators = [
                    'article .woo-picture-main img',
                    'article .pic-box img',
                    'article img'
                ]

                found_imgs = []
                for loc in locators:
                    found_imgs = await page.locator(loc).all()
                    if found_imgs: break

                for img in found_imgs:
                    try:
                        src = await img.get_attribute("src")
                        if not src: continue
                        if src.startswith("//"): src = "https:" + src

                        # 严格过滤
                        blacklist = ["tvax", "tva", "crop", "face", "icon", "avatar", "blank", "us_service", "empty",
                                     "skin"]
                        if any(x in src for x in blacklist): continue
                        if ".png" in src or ".svg" in src: continue
                        if "sinaimg.cn" not in src and "weibocdn" not in src: continue

                        width = await img.evaluate("el => el.naturalWidth")
                        if 0 < width < 200: continue

                        target_img_element = img

                        high_res = src
                        for pattern in ["/mw690/", "/orj360/", "/thumbnail/", "/bmiddle/", "/thumb180/", "/small/",
                                        "/dr/"]:
                            high_res = high_res.replace(pattern, "/large/")
                        target_src_hd = high_res
                        break
                    except:
                        continue
            except:
                pass

        # ==========================
        # 执行下载 (Plan A -> Plan B)
        # ==========================
        if target_img_element:
            downloaded = False

            # [Plan A] JS Fetch 高清图 (优先尝试)
            if target_src_hd:
                img_bytes = await download_image_via_js(page, target_src_hd)
                if img_bytes and len(img_bytes) > 2000:
                    with open(filename, "wb") as f:
                        f.write(img_bytes)
                    downloaded = True

            # [Plan B] 截图兜底 (如果 Plan A 418 或者失败)
            if not downloaded:
                try:
                    # 确保元素在视口内
                    await target_img_element.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    # 截图保存为 JPG (质量85)
                    await target_img_element.screenshot(path=filename, type="jpeg", quality=85)
                    downloaded = True
                    print(f"       📸 Plan B (Screenshot) Saved")
                except Exception:
                    pass

            if downloaded:
                return filename

    except Exception as e:
        print(f"    [!] Error: {e}")

    return None


async def run_backfill():
    if not os.path.exists(DB_NAME):
        print("❌ Database not found.")
        return

    os.makedirs(IMG_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT post_id, url FROM processed_posts 
        WHERE url IS NOT NULL 
        AND url != '' 
        AND (image_path IS NULL OR image_path = '')
        AND (post_id LIKE 'x_%' OR post_id LIKE 'wb_%')
    ''')
    rows = cursor.fetchall()

    if not rows:
        print("✅ No missing images.")
        conn.close()
        return

    print(f"[*] Found {len(rows)} posts needing image backfill...")

    async with async_playwright() as p:
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        context = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 800},
            user_agent=ua
        )
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        updated_count = 0

        for i, (post_id, url) in enumerate(rows):
            print(f"[{i + 1}/{len(rows)}] Processing {post_id} ...")

            platform = "x" if post_id.startswith("x_") else "wb"
            local_path = await process_page(page, url, post_id, platform)

            if local_path:
                print(f"    ✅ Saved.")
                conn.execute("UPDATE processed_posts SET image_path = ? WHERE post_id = ?", (local_path, post_id))
                conn.commit()
                updated_count += 1
            else:
                print(f"    ⚠️ No image captured.")

            # [重要] 循环间的随机等待
            await asyncio.sleep(random.uniform(1.0, 2.0))

        await context.close()

    conn.close()
    print(f"\n[Done] Backfill complete. Updated {updated_count} records.")


if __name__ == "__main__":
    asyncio.run(run_backfill())