import os
import typing
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")


class ContentFilter:
    def __init__(self):
        self.client = genai.Client(api_key=API_KEY)
        self.fast_model = "gemini-3-flash-preview"
        self.smart_model = "gemini-3-pro-preview"

    def analyze_post(self, post_text: str, image_path: str = None) -> dict:
        if not image_path:
            if not self._is_worth_checking(post_text):
                return {
                    "original_text": post_text,
                    "is_relevant": False,
                    "verdict": "NOISE",
                    "summary": "Filtered by Stage 1 (Irrelevant/Spam)"
                }
        return self._perform_deep_audit(post_text, image_path)

    def _is_worth_checking(self, text: str) -> bool:
        prompt = f"""
        Analyze this post. Return ONLY 'YES' if it contains factual claims, news, or meaningful opinions/discussions.
        Return 'NO' if it is obvious spam, simple greeting, or pure emotion without context.
        Post: "{text}"
        """
        try:
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=prompt
            )
            return "YES" in response.text.strip().upper()
        except:
            return True

    def _perform_deep_audit(self, text: str, image_path: str = None) -> dict:
        today_str = datetime.now().strftime("%Y-%m-%d")
        print(f"    -> Auditing (Date: {today_str}, Img: {bool(image_path)})...")

        contents = []
        has_image = False

        if image_path and os.path.exists(image_path):
            try:
                image = Image.open(image_path)
                contents.append(image)
                has_image = True
            except Exception as e:
                print(f"    [!] Image load failed: {e}")

        # --- 基础指令 ---
        base_instructions = f"""
        Current Date: {today_str}
        ROLE: OSINT Analyst.
        TASK: Verify the content veracity strictly.
        """

        if has_image:
            base_instructions += """
            PHASE 1: VISUAL EVIDENCE EXTRACTION
            - **TRANSCRIPTION**: If the image contains text, transcribe it EXACTLY.
            - **ANALYSIS**: Describe visual context.
            """
        else:
            base_instructions += """
            PHASE 1: CLAIM EXTRACTION
            - Identify the core claim. Is it a subjective feeling or a checkable fact?
            """

        # --- [核心修改] 逻辑微调 ---
        base_instructions += """
        PHASE 2: CROSS-VERIFICATION (Google Search)
        - Search for the CORE CLAIM found in Phase 1.
        - **Critical Nuance**: 
          * If the post is "My friend said [Technical/Scientific/Historical Fact]", verify the FACT. If the fact is correct, the post is TRUE.
          * If the post is "My friend said [Private Gossip/Subjective Feeling]", this is unverifiable. Mark as MIXED.

        PHASE 3: FINAL VERDICT
        Output EXACTLY one label at the start:

        - [VERDICT: TRUE]: 
          * Confirmed Facts / News.
          * **Technical/Scientific claims** (even if presented as anecdotes) that are verified by search.

        - [VERDICT: FALSE]: 
          * Proven Misinformation / Fake News / Hoax.

        - [VERDICT: MIXED]: 
          * **Purely Personal Stories**: Relationship drama, "today I ate...", feelings.
          * **Unverifiable Rumors**: No evidence found either way.
          * **Subjective Opinions**: Without factual basis.

        Then provide your reasoning.
        """

        prompt = f"{base_instructions}\n\nPost Text Metadata: \"{text}\""
        contents.append(prompt)

        try:
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )

            res_text = response.text if response.text else "No response."

            # 结果解析
            verdict = "MIXED"
            if "[VERDICT: TRUE]" in res_text:
                verdict = "TRUE"
            elif "[VERDICT: FALSE]" in res_text:
                verdict = "FALSE"
            elif "[VERDICT: MIXED]" in res_text:
                verdict = "MIXED"
            else:
                upper = res_text.upper()
                if "FALSE" in upper:
                    verdict = "FALSE"
                elif "TRUE" in upper and "NOT TRUE" not in upper:
                    verdict = "TRUE"

            if response.candidates and response.candidates[0].grounding_metadata:
                if response.candidates[0].grounding_metadata.search_entry_point:
                    res_text += "\n\n(🔍 Verified via Google Search)"

            return {
                "original_text": text,
                "is_relevant": True,
                "verdict": verdict,
                "summary": res_text
            }
        except Exception as e:
            return {
                "original_text": text,
                "is_relevant": True,
                "verdict": "MIXED",
                "summary": f"Error: {str(e)}"
            }

    # ... (Analyst / Chat 保持不变) ...
    def generate_daily_briefing(self, posts_text_list: list[str]) -> str:
        if not posts_text_list: return "No content to summarize."

        today_str = datetime.now().strftime("%Y-%m-%d")

        # 拼接所有帖子
        raw_data = "\n\n".join(posts_text_list)

        prompt = f"""
        Current Date: {today_str}
        ROLE: Chief Intelligence Analyst.

        INPUT DATA FORMAT:
        Each item starts with a status tag: [TRUE], [FALSE], or [MIXED], followed by the platform and text.

        TASK: 
        Write a structured "Daily Intelligence Briefing" based on the input.

        GUIDELINES:
        1. **Categorize by Topic**: Group similar posts (e.g., Tech, Politics, Culture).
        2. **Status Awareness (CRITICAL)**:
           - Use items marked **[TRUE]** as the foundation for factual updates.
           - Use items marked **[FALSE]** to create a specific "⚠️ Misinformation Watch" section (debunk them briefly).
           - Use items marked **[MIXED]** to reflect public sentiment, rumors, or unverified discussions.
        3. **Citations**: When mentioning a specific event, link to the source if available in the text.
        4. **Tone**: Professional, objective, insightful.
        5. **Structure**:
           # 📅 Daily Intelligence Briefing ({today_str})

           ## 🌍 Key Developments (Factual)
           ...

           ## 🗣️ Public Sentiment & Discussions (Mixed/Anecdotal)
           ...

           ## 🛡️ Misinformation Watch (Debunked)
           ... (Only if [FALSE] items exist)

        INPUT DATA:
        {raw_data}
        """

        try:
            # 简报生成依然建议用 Pro，逻辑能力更强
            return self.client.models.generate_content(model=self.smart_model, contents=prompt).text
        except Exception as e:
            return f"Error generating briefing: {str(e)}"

    def answer_user_question(self, context_text: str, question: str) -> str:
        today_str = datetime.now().strftime("%Y-%m-%d")
        prompt = f"Current Date: {today_str}\nContext:\n{context_text}\n\nQuestion: {question}"
        try:
            return self.client.models.generate_content(model=self.smart_model, contents=prompt).text
        except Exception as e:
            return str(e)