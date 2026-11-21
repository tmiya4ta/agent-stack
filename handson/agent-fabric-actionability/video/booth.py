"""イベントのブース (4K モニター) で流す版を作る。並びと見出しは booth.json、スライドは slides-booth.json。

ハンズオン版 (edit.py) との違い:
  - 3840x2160。録画は紺の背景の上の角丸の枠に入れ、枠の下に大きな見出しを 1 行と、いまの柱 (Discover〜Cost Control) を出す。
    映像の上には文字を重ねない (通りがかりの人が離れて見ても、画面と文字の両方が読めるように)
  - 場面ごとに録画の一部 (crop) をゆっくり寄せて映し、待ち時間は speed 倍で詰める
  - 最後は Thank you から黒に落として 3 秒止める (ループで流したときに、終わりと始まりがわかるように)
  - 字幕のトラックは付けない (見出しが字幕の代わり)

スライドは先に作っておく:
  powershell -File slides.ps1 <Workshop-Template.pptx> out/booth/booth-slides.pptx out/booth/slides slides-booth.json 3840
使い方: python booth.py <ffmpeg.exe> [--still]   (--still は場面ごとの静止画 out/booth/stills/ だけを作る)
出力:   out/final/actionability-booth.mp4 (途中のファイルは out/booth/parts/)
"""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FF = sys.argv[1]
STILL = '--still' in sys.argv[2:]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
FINAL = os.path.join(OUT, 'final')
BOOTH = os.path.join(OUT, 'booth')
SLIDES = os.path.join(BOOTH, 'slides')
PARTS = os.path.join(BOOTH, 'parts')
STILLS = os.path.join(BOOTH, 'stills')

W, H, FPS = 3840, 2160, 25
SRC_W, SRC_H = 1440, 900
BOX = (320, 70, 3200, 1800)        # 録画を入れる枠 (x, y, 幅, 高さ)
RADIUS = 28
BASE = '0x061238'                  # 枠の中が空いたとき (場面の切り替わり) の色
FADE = 0.5
END_BLACK = 3.0                    # 最後に黒で止める秒数
FONT_B = 'C:/Windows/Fonts/YuGothB.ttc'
FONT_M = 'C:/Windows/Fonts/YuGothM.ttc'
ACCENT = (0, 161, 224)             # #00A1E0

ENC = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-profile:v', 'high', '-level', '5.1',
       '-pix_fmt', 'yuv420p', '-r', str(FPS), '-an']


def run(args):
    subprocess.run([FF, '-v', 'error', '-y'] + args, check=True)


# ---- 重ねる画像 (PIL) ----

def frame_png(path):
    """背景のグラデーションと影。枠の中は透明にして、下の録画が見えるようにする"""
    top, bottom = (10, 30, 92), (6, 18, 56)
    bg = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        a = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(round(top[i] + (bottom[i] - top[i]) * a) for i in range(3)) + (255,))
    x, y, w, h = BOX
    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([x, y + 14, x + w, y + h + 14], RADIUS, fill=(0, 0, 0, 150))
    bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(28)))
    hole = Image.new('L', (W, H), 255)
    ImageDraw.Draw(hole).rounded_rectangle([x, y, x + w - 1, y + h - 1], RADIUS, fill=0)
    bg.putalpha(Image.composite(bg.getchannel('A'), hole, hole))
    ImageDraw.Draw(bg).rounded_rectangle([x - 1, y - 1, x + w, y + h], RADIUS + 1, outline=(255, 255, 255, 50), width=2)
    bg.save(path)


def text_png(path, pillars, sc, step):
    """枠の下: 1 行目は今の柱の札、機能の名前、手順の番号と、右に柱の並び (今のものだけ白)。2 行目は説明"""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0, x1 = BOX[0], BOX[0] + BOX[2]
    current = sc['pillar']
    chip_f = ImageFont.truetype(FONT_B, 44)
    label = pillars[current].upper()
    tw = d.textlength(label, font=chip_f)
    d.rounded_rectangle([x0, 1902, x0 + tw + 56, 1958], 28, fill=ACCENT + (255,))
    d.text((x0 + 28, 1930), label, font=chip_f, fill='white', anchor='lm')
    x = x0 + tw + 56 + 36
    if sc.get('feature'):
        f = ImageFont.truetype(FONT_B, 46)
        d.text((x, 1930), sc['feature'], font=f, fill='white', anchor='lm')
        x += d.textlength(sc['feature'], font=f) + 36
    if step:
        d.text((x, 1930), f'STEP {step[0]} / {step[1]}', font=ImageFont.truetype(FONT_M, 40),
               fill=(255, 255, 255, 170), anchor='lm')
    prog_f, prog_b = ImageFont.truetype(FONT_M, 40), ImageFont.truetype(FONT_B, 40)
    gap, x = 56, x1
    for i in reversed(range(len(pillars))):
        f = prog_b if i == current else prog_f
        w = d.textlength(pillars[i], font=f)
        x -= w
        d.text((x, 1930), pillars[i], font=f, anchor='lm',
               fill=(255, 255, 255, 255) if i == current else (255, 255, 255, 110))
        if i == current:
            d.rectangle([x, 1958, x + w, 1962], fill=ACCENT + (255,))
        x -= gap
    d.text((x0, 2040), sc['text'], font=ImageFont.truetype(FONT_B, 88), fill='white', anchor='lm')
    img.save(path)


# ---- 場面 ----

def crop_keys(sc):
    c = sc['crop']
    return (c[0], c[1]) if isinstance(c[0], list) else (c, c)


def scene(i, sc, pillars, frame, still, step):
    src = os.path.join(FINAL, f"{sc['lab']}.mp4")
    sp = sc.get('speed', 1.0)
    d = (sc['to'] - sc['from']) / sp
    (ax, ay, aw), (bx, by, bw) = crop_keys(sc)
    for x, y, w in ((ax, ay, aw), (bx, by, bw)):
        assert x + w <= SRC_W and y + w * 9 / 16 <= SRC_H, f"scene {i}: crop {x},{y},{w} が画面の外"
    txt = os.path.join(PARTS, f'{i:02}-text.png')
    text_png(txt, pillars, sc, step)
    # 寄せ方は、始めと終わりがゆっくりの cos。静止画は 6 割のところ
    p = '0.6' if still else f'(1-cos(PI*min(t/{d:.3f},1)))/2'
    k = f'({BOX[2]}/({aw}+({bw - aw})*{p}))'
    cx, cy = f'(({ax}+({bx - ax})*{p})*{k})', f'(({ay}+({by - ay})*{p})*{k})'
    # blur: 元の座標の [x, y, 幅, 高さ] をぼかす (アカウント ID や ARN など、映す範囲から外せないもの)
    vf = f"[0:v]setpts=(PTS-STARTPTS)/{sp},fps={FPS}"
    for j, (bx_, by_, bw_, bh_) in enumerate(sc.get('blur', [])):
        vf += (f"[s{j}];[s{j}]split[s{j}a][s{j}b];[s{j}b]crop={bw_}:{bh_}:{bx_}:{by_},gblur=sigma=9:steps=3[s{j}c];"
               f"[s{j}a][s{j}c]overlay={bx_}:{by_}")
    vf += (f",scale=w='trunc({SRC_W}*{k}/2)*2+2':h='trunc({SRC_H}*{k}/2)*2+2':eval=frame:flags=lanczos,"
          f"crop={BOX[2]}:{BOX[3]}:x='{cx}':y='{cy}',format=yuva420p")
    tf = '[2:v]format=rgba'
    if not still:
        vf += f',fade=t=in:st=0:d={FADE}:alpha=1,fade=t=out:st={d - FADE:.3f}:d={FADE}:alpha=1'
        tf += f',fade=t=in:st=0.2:d={FADE}:alpha=1,fade=t=out:st={d - FADE - 0.1:.3f}:d={FADE}:alpha=1'
    graph = (f"{vf}[v];color=c={BASE}:s={W}x{H}:r={FPS}[base];[base][v]overlay={BOX[0]}:{BOX[1]}:shortest=1[b1];"
             f"[b1][1:v]overlay[b2];{tf}[t];[b2][t]overlay,format=yuv420p")
    start = sc['from'] + ((sc['to'] - sc['from']) * 0.6 if still else 0)
    ins = ['-ss', f'{start:.3f}', '-t', f"{sc['to'] - start + 0.5:.3f}", '-i', src,
           '-loop', '1', '-i', frame, '-loop', '1', '-i', txt]
    if still:
        run(ins + ['-filter_complex', graph, '-frames:v', '1', os.path.join(STILLS, f'{i:02}.png')])
    else:
        dst = os.path.join(PARTS, f'{i:02}-{sc["lab"]}.mp4')
        run(ins + ['-filter_complex', graph, '-t', f'{d:.3f}'] + ENC + [dst])
        return dst


def slide(i, sl):
    d = sl['sec']
    vf = f"scale={W}:{H},format=yuv420p,fade=t=in:st=0:d={FADE}"
    if sl.get('end'):
        # 最後: 2 秒かけて黒に落とし、黒のまま止める
        vf += f",fade=t=out:st={d - 2:.3f}:d=2,tpad=stop_mode=add:stop_duration={END_BLACK}:color=black"
    else:
        vf += f",fade=t=out:st={d - FADE:.3f}:d={FADE}"
    dst = os.path.join(PARTS, f'{i:02}-slide{sl["slide"]}.mp4')
    run(['-loop', '1', '-framerate', str(FPS), '-t', str(d), '-i', os.path.join(SLIDES, f'{sl["slide"]}.png'),
         '-vf', vf] + ENC + [dst])
    return dst


def main():
    spec = json.load(open(os.path.join(HERE, 'booth.json'), encoding='utf-8'))
    os.makedirs(PARTS, exist_ok=True)
    os.makedirs(STILLS, exist_ok=True)
    frame = os.path.join(PARTS, 'frame.png')
    frame_png(frame)
    parts = []
    # 手順の番号は、同じ機能 (feature) の場面を数えて振る
    totals = {}
    for it in spec['plan']:
        if it.get('feature'):
            totals[it['feature']] = totals.get(it['feature'], 0) + 1
    seen = {}
    for i, it in enumerate(spec['plan']):
        if 'slide' in it:
            if not STILL:
                parts.append(slide(i, it))
        else:
            print(f'[{i + 1}/{len(spec["plan"])}] {it["lab"]} {it["from"]}-{it["to"]}', flush=True)
            step = None
            if it.get('feature'):
                seen[it['feature']] = seen.get(it['feature'], 0) + 1
                step = (seen[it['feature']], totals[it['feature']])
            r = scene(i, it, spec['pillars'], frame, STILL, step)
            if r:
                parts.append(r)
    if STILL:
        print('stills:', STILLS)
        return
    lst = os.path.join(PARTS, 'parts.txt')
    with open(lst, 'w', encoding='utf-8') as f:
        f.writelines(f"file '{p.replace(os.sep, '/')}'\n" for p in parts)
    dst = os.path.join(FINAL, 'actionability-booth.mp4')
    run(['-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', '-movflags', '+faststart', dst])
    print('done:', dst)


if __name__ == '__main__':
    main()
