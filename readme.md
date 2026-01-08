# 🕵️ SMTF: Social Media Truth Filter

**A local-first, AI-powered intelligence command center.**

SMTF 是一个基于 **"Vibe Coding"** 理念构建的个人情报系统。它能够自动抓取社交媒体（X/Twitter, Weibo, Reddit）的时间线，利用 Google Gemini (Multimodal) 进行多维度的真实性核查、去噪和摘要，最终生成一份可视化的情报日报。

## ✨ Core Features

*   **🛡️ 不死鸟采集 (Anti-Anti-Scraping)**:
    *   **CDP 挂载模式**: 利用 Chrome DevTools Protocol 直接接管本地已登录的浏览器，完美复用真实用户 Session。
    *   **抗干扰机制**: 支持后台静默运行（绕过 Chrome 后台资源节流），支持 **JS 注入下载** + **截图兜底** 双重策略，无视 418/403 防盗链。
*   **🧠 双重 AI 大脑**:
    *   **Stage 1**: Gemini Flash 快速过滤广告和情绪垃圾。
    *   **Stage 2**: Gemini Pro + **Google Search Grounding** 进行深度事实核查。
    *   **Visual Analysis**: 原生多模态支持，自动读取图片/截图中的文字和细节，对抗“开局一张图”的谣言。
*   **📊 指挥中心 (Dashboard)**:
    *   基于 Streamlit 的交互式面板。
    *   支持按日期、平台、真伪状态筛选。
    *   **Chat with Data**: 直接向 AI 提问关于当前情报库的问题（如“今天有哪些关于 AI 的假新闻？”）。
    *   **One-Click Briefing**: 自动生成结构化的每日/每周情报简报。

## 🛠️ Tech Stack

*   **Language**: Python 3.10+
*   **Browser Automation**: Playwright (CDP Mode)
*   **AI Model**: Google Gemini 2.0/3.0 Preview (via `google-genai` SDK)
*   **Frontend**: Streamlit
*   **Database**: SQLite3 (Local storage with WAL mode)

## 🚀 Installation

1.  **Clone the repo**
    ```bash
    git clone https://github.com/yourusername/smtf.git
    cd smtf
    ```

2.  **Install Dependencies**
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    playwright install
    ```

3.  **Configuration**
    在项目根目录创建一个 `.env` 文件，填入你的 Google API Key：
    ```env
    GEMINI_API_KEY=AIzaSyDxxxxxxxxx
    ```

## 🖥️ Usage Guide

### Step 1: 启动“大脑”浏览器 (The Host)
SMTF 需要接管一个开启了远程调试端口的 Chrome (强烈推荐使用 **Chrome Canary** 以实现与日常浏览器的物理隔离)。

请在终端运行启动命令（建议保存为 `start_browser.sh` 并赋予执行权限）：

```bash
# macOS 示例 (Chrome Canary)
# 注意：这些参数对于防止后台运行时被降速至关重要
"/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" \
  --remote-debugging-port=9222 \
  --user-data-dir="/tmp/canary_dev_session" \
  --disable-backgrounding-occluded-windows \
  --disable-renderer-backgrounding \
  --disable-background-timer-throttling \
  --disable-features=CalculateNativeWinOcclusion
```
启动后，请在弹出的浏览器中手动登录 X (Twitter), Weibo, Reddit。

### Step 2: 运行采集 (The Harvester)
保持上面的浏览器开启（可以移动到其他虚拟桌面，但不要关闭），然后运行：

```bash
python main.py
```
程序会自动连接 9222 端口，控制浏览器进行滚动抓取、下载高清原图，并将数据存入 smtf_memory.db。

### Step 3: 启动指挥中心 (The Dashboard)
查看报告、生成简报或手动修正数据：


```Bash
python -m streamlit run dashboard.py
````
* 📂 Project Structure
    * **main.py**: 主程序入口，调度 Harvester 和 Auditor。
    * **harvester.py**: X (Twitter) 采集逻辑 (CDP 挂载 + 原图下载)。
    * **weibo_harvester.py**: 微博采集逻辑 (抗反爬 + 截图兜底)。
    * **reddit_harvester.py**: Reddit 采集逻辑。
    * **logic/filter.py**: AI 核心逻辑 (Prompt Engineering & API Call)。
    * **dashboard.py**: Streamlit 前端界面。
    * **database.py**: SQLite 封装。
    * **backfill_images.py**: 用于补全历史缺失图片的工具脚本。
    * **reprocess_all.py**: 用于批量重新清洗/分析历史数据的工具。

## ⚠️ Disclaimer
本项目仅供学习与研究使用。数据完全存储于本地。请遵守相关法律法规及目标网站的使用条款 (ToS)。不要进行高频、大规模的数据抓取。