import asyncio
from playwright.async_api import async_playwright
import os

# --- 请把那个抓取失败的微博链接填在这里 ---
TARGET_URL = "https://weibo.com/7378302827/QlihkkM95"


# 如果你不知道具体是哪条，可以去数据库查一下 url 字段，或者填博主主页
# TARGET_URL = "https://weibo.com/u/1642088277"

async def probe():
    print(f"[*] Probing URL: {TARGET_URL}")

    async with async_playwright() as p:
        # 使用有头模式，这样你能看到发生了什么
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        await page.goto(TARGET_URL, wait_until="domcontentloaded")
        print("    -> Page loaded. Waiting 5s for render...")
        await asyncio.sleep(5)

        # 1. 截图看 Playwright 到底看见了什么
        await page.screenshot(path="debug_view.png")
        print("    -> Screenshot saved to 'debug_view.png'. Check if image is visible there.")

        # 2. 扫描所有 IMG 标签
        imgs = await page.locator("img").all()
        print(f"\n    -> Found {len(imgs)} <img> tags. Analyzing candidates...\n")

        print(f"{'INDEX':<5} | {'WIDTH':<6} | {'HEIGHT':<6} | {'SRC (truncated)'}")
        print("-" * 80)

        for i, img in enumerate(imgs):
            try:
                # 获取关键属性
                src = await img.get_attribute("src")
                # 检查自然尺寸 (这是之前的过滤核心)
                n_width = await img.evaluate("el => el.naturalWidth")
                n_height = await img.evaluate("el => el.naturalHeight")
                # 获取可见性
                is_visible = await img.is_visible()

                # 简单的过滤显示
                if src and len(src) > 10:
                    clean_src = src[:50] + "..."
                    print(f"{i:<5} | {n_width:<6} | {n_height:<6} | {clean_src}")

                    # 针对那张你觉得应该被抓到的图，如果它尺寸很小，或者 src 很怪，这里就能看出来
                    if "sinaimg.cn" in src:
                        print(f"      [SINAIMG Detected] Visible: {is_visible}")
                        if n_width < 150:
                            print(f"      ⚠️ WARNING: Natural Width is {n_width} (Filter threshold is 150)")
                        if ".png" in src:
                            print(f"      ⚠️ WARNING: Format is PNG")

            except Exception as e:
                print(f"{i:<5} | Error: {e}")

        print("-" * 80)
        print("\nPress Ctrl+C to close browser...")
        # 挂起浏览器，让你有机会手动按 F12 检查
        await asyncio.sleep(300)


if __name__ == "__main__":
    asyncio.run(probe())