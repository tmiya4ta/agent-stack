"""録画 (out/<lab>.<タブ>.webm と out/<lab>.json) から、切り取った mp4 と字幕の srt を作る。

タブが 2 つ以上あるときは、まず json の timeline (s.tab で切り替えた時刻) の順に、前にあったタブの録画をつなぐ。

切り取るもの:
  - bad   失敗した操作の区間 (rec-driver が記録)
  - skips 待ち時間やサインインの区間 (rec-driver の s.skipStart / s.skipEnd)
  - 画面が 5 秒より長く止まっている区間 (ffmpeg の freezedetect)。先頭の 1.5 秒と、字幕を読む時間だけ残す

使い方: python process.py <ffmpeg.exe> [lab ...]   (lab を省くと全部)
出力:   out/final/<lab>.mp4、out/final/<lab>.srt
"""
import json, os, re, subprocess, sys

FF = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
FINAL = os.path.join(OUT, 'final')
FREEZE_MIN, FREEZE_KEEP = 5.0, 1.5
SUB_MAX = 8.0  # 字幕を出しておく最長の秒数


def duration(path):
    r = subprocess.run([FF, '-i', path], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def freezes(path):
    r = subprocess.run([FF, '-i', path, '-vf', f'freezedetect=n=0.002:d={FREEZE_MIN}', '-map', '0:v', '-f', 'null', '-'],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore')
    st = [float(x) for x in re.findall(r'freeze_start: ([\d.]+)', r.stderr)]
    en = [float(x) for x in re.findall(r'freeze_end: ([\d.]+)', r.stderr)]
    return list(zip(st, en + [None] * (len(st) - len(en))))


def merge(iv):
    iv = sorted((a, b) for a, b in iv if b > a)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def ts(t):
    ms = int(round(t * 1000))
    return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}'


def compose(meta):
    """タブごとの録画を、前にあったタブの順に 1 本にする (時刻は録画を始めたときから)。"""
    lab = meta['lab']
    seg = []
    for i, e in enumerate(meta['timeline']):
        b = meta['timeline'][i + 1]['sec'] if i + 1 < len(meta['timeline']) else meta['end']
        if seg and seg[-1][0] == e['tab']:
            seg[-1][2] = b
        elif b - e['sec'] > 0.04:
            seg.append([e['tab'], e['sec'], b])
    args, chains = [], []
    for k, (tab, a, b) in enumerate(seg):
        t = meta['tabs'][tab]
        args += ['-ss', f'{a - t["start"]:.3f}', '-t', f'{b - a:.3f}', '-i', os.path.join(OUT, t['file'])]
        chains.append(f'[{k}:v]fps=25,scale=1440:900,setsar=1,setpts=PTS-STARTPTS[v{k}]')
    fc = ';'.join(chains) + ';' + ''.join(f'[v{k}]' for k in range(len(seg))) + f'concat=n={len(seg)}:v=1:a=0[out]'
    dst = os.path.join(OUT, lab + '.mp4')
    subprocess.run([FF, '-y', '-loglevel', 'error'] + args + ['-filter_complex', fc, '-map', '[out]',
                    '-c:v', 'libx264', '-crf', '16', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', dst], check=True)
    # 最初のタブより前 (0 秒〜) は無いので、そのぶん時刻をずらす
    return dst, seg[0][1]


def process(lab):
    meta = json.load(open(os.path.join(OUT, lab + '.json'), encoding='utf-8'))
    if 'tabs' in meta:
        src, off = compose(meta)
        for m in meta['marks']:
            m['sec'] -= off
        for k in meta['bad'] + meta['skips']:
            k['start'] -= off
            if 'end' in k:
                k['end'] -= off
    else:
        src = os.path.join(OUT, lab + '.webm')
    dur = duration(src)
    cut = [(b['start'], b['end']) for b in meta['bad']]
    cut += [(k['start'], k.get('end', dur)) for k in meta['skips']]
    # 字幕を読む時間 (1 秒 8 文字、2.5〜9 秒) は、画面が止まっていても切らない
    read = [(m['sec'], m['sec'] + min(9.0, max(2.5, len(m['label']) / 8))) for m in meta['marks']]
    for a, b in freezes(src):
        b = dur if b is None else b
        if b - a <= FREEZE_MIN:
            continue
        a += FREEZE_KEEP
        b -= 0.3
        for ra, rb in sorted(read):
            if rb <= a or ra >= b:
                continue
            if ra > a:
                cut.append((a, ra))
            a = max(a, rb)
        if b > a:
            cut.append((a, b))
    cut = merge([(max(0, a), min(dur, b)) for a, b in cut])
    keep, t = [], 0.0
    for a, b in cut:
        if a > t + 0.05:
            keep.append((t, a))
        t = max(t, b)
    if dur > t + 0.05:
        keep.append((t, dur))

    def remap(x):
        removed = 0.0
        for a, b in cut:
            if x >= b:
                removed += b - a
            elif x > a:
                return a - removed
        return x - removed

    os.makedirs(FINAL, exist_ok=True)
    expr = '+'.join(f'between(t,{a:.3f},{b:.3f})' for a, b in keep)
    dst = os.path.join(FINAL, lab + '.mp4')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', src, '-vf', f"select='{expr}',setpts=N/FRAME_RATE/TB",
                    '-an', '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', dst], check=True)
    new_dur = duration(dst)

    marks = [(remap(m['sec']), m['label']) for m in meta['marks'] if m['label'].strip()]
    with open(os.path.join(FINAL, lab + '.srt'), 'w', encoding='utf-8') as f:
        for i, (st, label) in enumerate(marks):
            nxt = marks[i + 1][0] if i + 1 < len(marks) else new_dur
            en = min(nxt, st + SUB_MAX, new_dur)
            f.write(f'{i + 1}\n{ts(st)} --> {ts(max(en, st + 1.0))}\n{label}\n\n')
    print(f'{lab}: {dur:.0f}s -> {new_dur:.0f}s, 字幕 {len(marks)} 行')


labs = sys.argv[2:] or sorted(f[:-5] for f in os.listdir(OUT) if f.endswith('.json'))
for lab in labs:
    process(lab)
