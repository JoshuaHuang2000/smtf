from logic.filter import ContentFilter

f = ContentFilter()
# 找一个你本地 assets/images/ 下真实存在的图片路径
img_path = "assets/images/wb_QkXCeEj2b.jpg"
text = "这是一条测试微博"

print(f.analyze_post(text, img_path))