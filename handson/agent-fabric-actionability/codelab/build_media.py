"""録画のときに撮ったスクショ (video/out/shots/。video/labs の台本の s.shot で撮る) から、原稿が使う画像を media/ に作る。灰色の枠を付ける。

秘密の欄 (AWS のキー、client ID / secret) は、撮る時点でぼかしてある (video/rec-driver.js の s.blur)。

使い方: python build_media.py [shots のフォルダ]   (省くと ../video/out/shots)
"""
import os, re, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'video', 'out', 'shots')
DST = os.path.join(HERE, 'media')

names = sorted(set(re.findall(r'media/([\w-]+)\.png', open(os.path.join(HERE, 'actionability.md'), encoding='utf-8').read())))
os.makedirs(DST, exist_ok=True)
for name in names:
    img = Image.open(os.path.join(SRC, name + '.png')).convert('RGB')
    d = ImageDraw.Draw(img)
    w, h = img.size
    for i in range(3):
        d.rectangle([i, i, w - 1 - i, h - 1 - i], outline=(180, 180, 180))
    img.save(os.path.join(DST, name + '.png'))
print(len(names), 'images ->', DST)
