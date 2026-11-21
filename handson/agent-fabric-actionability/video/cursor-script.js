// ページ内に描画する仮想マウスカーソル(実OSカーソルではなく、録画に映るための矢印カーソル)
const CURSOR_INIT_SCRIPT = `
(function () {
  function ensureCursor() {
    let c = document.getElementById('pw-cursor');
    if (!c) {
      c = document.createElement('div');
      c.id = 'pw-cursor';
      c.innerHTML =
        '<svg width="26" height="26" viewBox="0 0 26 26" xmlns="http://www.w3.org/2000/svg">' +
        '<path d="M2 1 L2 20 L7.2 15.8 L10.4 23 L13.6 21.6 L10.4 14.4 L17 14.4 Z" ' +
        'fill="black" stroke="white" stroke-width="1.4" stroke-linejoin="round"/>' +
        '</svg>';
      document.documentElement.appendChild(c);
    }
    return c;
  }
  function ensureStyle() {
    if (document.getElementById('pw-cursor-style')) return;
    const style = document.createElement('style');
    style.id = 'pw-cursor-style';
    style.textContent =
      '#pw-cursor{position:fixed;top:0;left:0;width:26px;height:26px;' +
      'margin-left:0;margin-top:0;' +
      'pointer-events:none;z-index:2147483647;' +
      'filter:drop-shadow(0 1px 2px rgba(0,0,0,0.6));' +
      'transition:transform 0.03s linear;}' +
      '#pw-cursor.pw-click svg{transform:scale(0.85);}' +
      '#pw-cursor svg{transform-origin:2px 1px;display:block;}';
    document.documentElement.appendChild(style);
  }
  function init() {
    ensureStyle();
    ensureCursor();
    document.addEventListener('mousemove', function (e) {
      const cur = ensureCursor();
      cur.style.transform = 'translate(' + e.clientX + 'px,' + e.clientY + 'px)';
    }, true);
    document.addEventListener('mousedown', function () {
      ensureCursor().classList.add('pw-click');
    }, true);
    document.addEventListener('mouseup', function () {
      ensureCursor().classList.remove('pw-click');
    }, true);
  }
  document.addEventListener('DOMContentLoaded', init);
  if (document.readyState !== 'loading') init();
})();
`;

async function moveMouseTo(page, x, y, steps = 30) {
  await page.mouse.move(x, y, { steps });
}

async function moveAndClick(page, locator, { pauseBefore = 400, pauseAfter = 300 } = {}) {
  await locator.scrollIntoViewIfNeeded().catch(() => {});
  const box = await locator.boundingBox();
  if (box) {
    const x = box.x + box.width / 2;
    const y = box.y + box.height / 2;
    await moveMouseTo(page, x, y);
    await page.waitForTimeout(pauseBefore);
  }
  try {
    await locator.click({ force: true, timeout: 5000 });
  } catch (e) {
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    } else {
      throw e;
    }
  }
  await page.waitForTimeout(pauseAfter);
}

async function moveAndType(page, locator, text, { pauseBefore = 400 } = {}) {
  await moveAndClick(page, locator, { pauseBefore, pauseAfter: 200 });
  await page.keyboard.type(text, { delay: 90 });
}

// タイムスタンプ付きログ + SRT字幕自動生成用のロガー。
// step() を呼ぶたびに [経過秒, ラベル] を記録し、動画の実尺が分かった後に
// buildSrt() で自動的に .srt を組み立てる(手動でのタイミング計算が不要になる)。
function createTimeline() {
  const t0 = Date.now();
  const marks = [];
  function step(label) {
    const sec = (Date.now() - t0) / 1000;
    marks.push({ sec, label });
    console.log(`[t=${sec.toFixed(2)}s] ${label}`);
    return sec;
  }
  function toSrtTimestamp(totalSeconds) {
    const ms = Math.max(0, Math.round(totalSeconds * 1000));
    const h = String(Math.floor(ms / 3600000)).padStart(2, '0');
    const m = String(Math.floor((ms % 3600000) / 60000)).padStart(2, '0');
    const s = String(Math.floor((ms % 60000) / 1000)).padStart(2, '0');
    const msec = String(ms % 1000).padStart(3, '0');
    return `${h}:${m}:${s},${msec}`;
  }
  // videoDurationSec: 実際の録画ファイルの長さ(秒)。ffprobe/ffmpegで取得した値を渡す。
  function buildSrt(videoDurationSec) {
    const entries = marks.filter(m => m.label.trim().length > 0);
    let out = '';
    entries.forEach((m, i) => {
      const start = m.sec;
      const end = i + 1 < entries.length ? entries[i + 1].sec : videoDurationSec;
      out += `${i + 1}\n${toSrtTimestamp(start)} --> ${toSrtTimestamp(end)}\n${m.label}\n\n`;
    });
    return out;
  }
  return { step, buildSrt, marks };
}

module.exports = { CURSOR_INIT_SCRIPT, moveMouseTo, moveAndClick, moveAndType, createTimeline };
