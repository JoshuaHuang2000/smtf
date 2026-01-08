import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import markdown  # <--- 新增


class Editor:
    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # 初始化 Jinja2 模板引擎
        self.env = Environment(loader=FileSystemLoader('templates'))

    def generate_report(self, db_records):
        """
        生成 HTML 报告
        :param db_records: 数据库取出的原始元组列表 (text, verdict, summary, time)
        :return: 生成的 HTML 内容字符串
        """
        # 1. 整理数据格式，方便模板渲染
        posts = []
        for record in db_records:
            # record[2] 是数据库里的 summary 字段 (Markdown 文本)
            # 我们把它转换成 HTML
            html_summary = markdown.markdown(record[2])

            posts.append({
                "original_text": record[0],
                "verdict": record[1],
                "summary": html_summary,  # <--- 这里存的是转换后的 HTML 代码
                "processed_at": record[3]
            })

        # 2. 加载模板
        template = self.env.get_template('digest_template.html')

        # 3. 渲染
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        html_content = template.render(posts=posts, date_str=date_str)

        # 4. 保存到本地文件 (Web Report)
        filename = f"daily_digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        file_path = os.path.join(self.output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"    [Editor] Report generated: {file_path}")
        return html_content, file_path

    def send_email(self, html_content, recipient_email):
        """
        发送邮件 (需要配置 .env)
        """
        sender_email = os.getenv("EMAIL_SENDER")
        email_password = os.getenv("EMAIL_PASSWORD")  # Gmail App Password
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))

        if not sender_email or not email_password:
            print("    [!] Email credentials not found in .env. Skipping email.")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Truth Digest - {datetime.now().strftime('%Y-%m-%d')}"
        msg["From"] = sender_email
        msg["To"] = recipient_email

        # 附加 HTML 内容
        msg.attach(MIMEText(html_content, "html"))

        try:
            print(f"    [Email] Connecting to SMTP server {smtp_server}...")
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()  # 启用安全加密
            server.login(sender_email, email_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            server.quit()
            print(f"    [Email] Sent successfully to {recipient_email}")
        except Exception as e:
            print(f"    [!] Email failed: {e}")