"""Lab ごとの動画 (out/final/<lab>.mp4) とスライド (out/slides/NN.png) を、1 本の動画にまとめる。

並び: 表紙、全体の説明、事前準備、[モジュールの区切り、モジュールの説明、(ラボの区切り、ラボ) x n] x 4、締め。
ラボの動画は、labs/<lab>.js を録って process.py で切り取ったもの (out/final/)。2 回に分けて録ったラボ
(m2-lab1a + m2-lab1b など) は、ここで 1 本 (m2-lab1) につなぐ。
  - つなぎ目は、背景の紺に 0.4 秒でフェードする
  - ラボの間は録画を少し縮めて上に帯を作り、「Module 1 Discover › Lab 1-1 Agent Scanner」を出しておく
    (画面の上にかぶせると、最初に押すメニューが隠れるので)
  - 字幕は録画のときの s.step の文 (out/final/<lab>.srt) をそのまま使う。字幕のトラックとして入れた版
    (再生側でオン/オフ) と、焼き込んだ版 (-sub) の 2 本。同じ名前の .srt も出す

スライドは先に slides.ps1 で作っておく (out/slides/index.json でスライドの名前から番号を引く)。区切りごとの mp4 (out/edit/) は、元のスライドや録画より新しければ
作り直さない。edit.py のフィルタを変えたときは --all で全部作り直す。
使い方: python edit.py <ffmpeg.exe> [--all]
出力:   out/final/actionability-full.mp4 (字幕はトラック)、actionability-full-sub.mp4 (焼き込み)、actionability-full.srt
"""
import json, os, re, subprocess, sys

FF = sys.argv[1]
ALL = '--all' in sys.argv[2:]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
FINAL = os.path.join(OUT, 'final')
WORK = os.path.join(OUT, 'edit')
SLIDES = os.path.join(OUT, 'slides')
NAME = 'actionability-full'

W, H, FPS = 1920, 1080, 25
BG = '0x0A1E5C'      # 左右の余白とフェードの色 (スライドの紺に寄せる)
FADE = 0.4
FONT = 'C\\:/Windows/Fonts/YuGothM.ttc'
BAND = 60            # ラボの間の上の帯の高さ
SUB_MIN, SUB_MAX = 2.5, 8.0   # 字幕を出しておく最短と最長の秒数
# 焼き込みの字幕の見た目 (libass。srt の座標は高さ 288 として拡大されるので、12 で 1080 の約 45px)。
# 小さめの白字に、半透明の黒い帯
SUB_STYLE = ('FontName=Yu Gothic UI,FontSize=12,PrimaryColour=&H00FFFFFF,BorderStyle=3,'
             'OutlineColour=&H30000000,Outline=0.8,Shadow=0,MarginV=12')

# (種類, 中身, 秒数 または 上の帯の文字)。スライドは slides.ps1 が index.json に書いた名前
M1, M2, M3, M4 = 'Module 1 Gain Visibility', 'Module 2 Enable AI Actions', 'Module 3 Govern AI Agents', 'Module 4 Align AI Costs'
PLAN = [
    ('slide', 'cover', 5), ('slide', 'overview', 10),
    ('slide', 'lab-lab0', 3.5), ('lab', 'lab0', '事前準備  ›  Enhanced UI とビジネスグループ'),
    ('slide', 'm1', 3.5), ('slide', 'm1-white', 7),
    ('slide', 'lab-m1-lab1', 3.5), ('lab', 'm1-lab1', f'{M1}  ›  Lab 1-1  Agent Scanner'),
    ('slide', 'm2', 3.5), ('slide', 'm2-white', 8),
    ('slide', 'lab-m2-lab1', 3.5), ('lab', 'm2-lab1', f'{M2}  ›  Lab 2-1  MCP Bridge'),
    ('slide', 'lab-m2-lab2', 3.5), ('lab', 'm2-lab2', f'{M2}  ›  Lab 2-2  MCP Global Access Control'),
    ('slide', 'lab-m2-lab3', 3.5), ('lab', 'm2-lab3', f'{M2}  ›  Lab 2-3  Orchestration'),
    ('slide', 'm3', 3.5), ('slide', 'm3-white', 7),
    ('slide', 'lab-m3-lab1', 3.5), ('lab', 'm3-lab1', f'{M3}  ›  Lab 3-1  Trusted Agent Identity'),
    ('slide', 'lab-m3-lab2', 3.5), ('lab', 'm3-lab2', f'{M3}  ›  Lab 3-2  Agent Visualizer'),
    ('slide', 'm4', 3.5), ('slide', 'm4-white', 8),
    ('slide', 'lab-m4-lab1', 3.5), ('lab', 'm4-lab1', f'{M4}  ›  Lab 4-1  Semantic Routing'),
    ('slide', 'lab-m4-lab2', 3.5), ('lab', 'm4-lab2', f'{M4}  ›  Lab 4-2  Model Wallet'),
    ('slide', 'lab-m4-lab3', 3.5), ('lab', 'm4-lab3', f'{M4}  ›  Lab 4-3  Cost Optimization'),
    ('slide', 'thanks', 5),
]
# 2 回に分けて録ったラボ。この順につないで 1 本にする
JOIN = {'m2-lab1': ['m2-lab1a', 'm2-lab1b'], 'm4-lab1': ['m4-lab1a', 'm4-lab1b'], 'm4-lab2': ['m4-lab2a', 'm4-lab2b'], 'm4-lab3': ['m4-lab3a', 'm4-lab3b']}

ENC = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-an']


def run(args, cwd=None):
    subprocess.run([FF, '-v', 'error', '-y'] + args, check=True, cwd=cwd)


def fresh(dst, src):
    return not ALL and os.path.exists(dst) and os.path.getmtime(dst) > os.path.getmtime(src)


def duration(path):
    r = subprocess.run([FF, '-i', path], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def fades(d):
    return f'fade=t=in:st=0:d={FADE}:c={BG},fade=t=out:st={d - FADE:.3f}:d={FADE}:c={BG}'


def slide_png(name):
    index = json.load(open(os.path.join(SLIDES, 'index.json'), encoding='utf-8-sig'))
    return os.path.join(SLIDES, f'{index[name]}.png')


def render_slide(name, d, dst):
    run(['-loop', '1', '-framerate', str(FPS), '-t', str(d), '-i', slide_png(name),
         '-vf', f'scale={W}:{H},format=yuv420p,{fades(d)}'] + ENC + [dst])


def render_lab(lab, label, dst):
    src = os.path.join(FINAL, f'{lab}.mp4')
    d = duration(src)
    vh = H - BAND
    vw = round(1440 * vh / 900) // 2 * 2
    # 文字はファイルで渡す (日本語と記号をフィルタの書式で escape しないため)
    txt = os.path.join(WORK, f'{lab}.label.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write(label)
    vf = (f'scale={vw}:{vh},pad={W}:{H}:(ow-iw)/2:{BAND}:color={BG},fps={FPS}'
          f",drawtext=fontfile='{FONT}':textfile='{txt.replace(os.sep, '/').replace(':', chr(92) + ':')}'"
          f':fontsize=26:fontcolor=0xDCE6FF:x={(W - vw) // 2 + 4}:y=({BAND}-th)/2')
    run(['-i', src, '-vf', f'{vf},{fades(d)}'] + ENC + [dst])


def parse_srt(path):
    def sec(t):
        h, m, x = t.replace(',', '.').split(':')
        return int(h) * 3600 + int(m) * 60 + float(x)
    out = []
    for block in open(path, encoding='utf-8').read().strip().split('\n\n'):
        lines = block.strip().split('\n')
        a, b = lines[1].split(' --> ')
        out.append((sec(a), sec(b), ' '.join(lines[2:])))
    return out


def ts(t):
    ms = round(t * 1000)
    return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}'


def join(lab, parts):
    """分けて録ったラボの mp4 と srt を 1 本にする (どれも process.py の同じ設定で書き出しているので、つなぐだけ)"""
    dst = os.path.join(FINAL, f'{lab}.mp4')
    srcs = [os.path.join(FINAL, f'{p}.mp4') for p in parts]
    if not (not ALL and os.path.exists(dst) and all(os.path.getmtime(dst) > os.path.getmtime(x) for x in srcs)):
        lst = os.path.join(WORK, f'{lab}.join.txt')
        with open(lst, 'w', encoding='utf-8') as f:
            f.writelines(f"file '{x.replace(os.sep, '/')}'\n" for x in srcs)
        run(['-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', dst])
    t, n, out = 0.0, 0, []
    for p, x in zip(parts, srcs):
        for a, b, text in parse_srt(os.path.join(FINAL, f'{p}.srt')):
            n += 1
            out.append(f'{n}\n{ts(t + a)} --> {ts(t + b)}\n{text}\n')
        t += duration(x)
    with open(os.path.join(FINAL, f'{lab}.srt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))


def main():
    os.makedirs(WORK, exist_ok=True)
    for lab, parts in JOIN.items():
        have = [p for p in parts if os.path.exists(os.path.join(FINAL, f'{p}.mp4'))]
        if have:
            if len(have) < len(parts):
                print(f'  ({lab}: {", ".join(sorted(set(parts) - set(have)))} not recorded yet)')
            join(lab, have)
    parts, subs, t0 = [], [], 0.0
    for i, (kind, what, extra) in enumerate(PLAN):
        dst = os.path.join(WORK, f'{i:02}-{what}.mp4')
        print(f'[{i + 1}/{len(PLAN)}] {what}', flush=True)
        if kind == 'slide':
            if not fresh(dst, slide_png(what)):
                render_slide(what, extra, dst)
        else:
            if not os.path.exists(os.path.join(FINAL, f'{what}.mp4')):
                print(f'  (no recording for {what}, skipped)')
                continue
            if not fresh(dst, os.path.join(FINAL, f'{what}.mp4')):
                render_lab(what, extra, dst)
            d = duration(dst)
            local = [list(c) for c in parse_srt(os.path.join(FINAL, f'{what}.srt'))]
            # 短すぎるものは次の字幕の手前まで延ばし、重なりは前を切る。ラボの外にははみ出さない
            for j, c in enumerate(local):
                nxt = local[j + 1][0] if j + 1 < len(local) else d - FADE
                c[1] = min(max(min(c[1], c[0] + SUB_MAX), c[0] + SUB_MIN), nxt)
                subs.append((t0 + c[0], t0 + c[1], c[2]))
        parts.append(dst)
        t0 += duration(dst)
    lst = os.path.join(WORK, 'parts.txt')
    with open(lst, 'w', encoding='utf-8') as f:
        f.writelines(f"file '{p.replace(os.sep, '/')}'\n" for p in parts)
    srt = os.path.join(FINAL, f'{NAME}.srt')
    with open(srt, 'w', encoding='utf-8') as f:
        for n, (a, b, text) in enumerate(subs, 1):
            f.write(f'{n}\n{ts(a)} --> {ts(b)}\n{text}\n\n')
    # 字幕はトラックとして入れる (焼き込まない)。既定でオン、プレーヤーの字幕メニューで消せる
    run(['-f', 'concat', '-safe', '0', '-i', lst, '-i', srt, '-map', '0:v', '-map', '1:s',
         '-c:v', 'copy', '-c:s', 'mov_text', '-metadata:s:s:0', 'language=jpn',
         '-metadata:s:s:0', 'title=日本語', '-disposition:s:0', 'default',
         '-movflags', '+faststart', os.path.join(FINAL, f'{NAME}.mp4')])
    # 焼き込みの版。subtitles フィルタに Windows のパスを渡すと : の escape が要るので、FINAL で動かして名前だけ渡す
    print('burning subtitles', flush=True)
    run(['-i', f'{NAME}.mp4', '-vf', f"subtitles={NAME}.srt:force_style='{SUB_STYLE}'"] + ENC
        + ['-movflags', '+faststart', f'{NAME}-sub.mp4'], cwd=FINAL)
    print(f'done: {NAME}.mp4 / {NAME}-sub.mp4 {t0 / 60:.1f} min, {len(subs)} subtitles')


if __name__ == '__main__':
    main()
