import re, json

with open("desktop_app/FewFeedV3.9.1/content.js", "r") as f:
    c = f.read()

urls = re.findall(r'https?://[^\s"\'`\\]+', c)
print("Content URLs:", set(urls))

with open("desktop_app/FewFeedV3.9.1/bg.js", "r") as f:
    b = f.read()

urls_b = re.findall(r'https?://[^\s"\'`\\]+', b)
print("BG URLs:", set(urls_b))
