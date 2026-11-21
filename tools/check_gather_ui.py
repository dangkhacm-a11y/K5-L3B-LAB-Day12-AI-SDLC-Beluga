"""Check the real Canvas basket/stock renderer in Chrome, without dependencies.

    python3 tools/check_gather_ui.py [--chrome /path/to/chrome]
"""

import argparse
import html
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


CHECK = r"""
<script>
const results = [];
const labels = [], paints = [], textBounds = [];
const originalText = ctx.fillText.bind(ctx), originalRect = ctx.fillRect.bind(ctx);
ctx.fillText = (s, x, y, ...args) => {
  labels.push(String(s));
  const bounds = ctx.measureText(s);
  textBounds.push({label: String(s), top: y - bounds.actualBoundingBoxAscent, bottom: y + bounds.actualBoundingBoxDescent});
  originalText(s, x, y, ...args);
};
ctx.fillRect = (...args) => { paints.push(ctx.fillStyle); originalRect(...args); };
const items = [
  {id: 'I1', kind: 'ca_loc', fresh: 75},
  {id: 'I2', kind: 'bong_sung', fresh: 60},
  {id: 'I3', kind: 'bong_sung', fresh: 80}
];
for (const width of [1280, 900, 390]) {
  for (const hold of [items, ['ca_loc', 'bong_sung', 'bong_sung'], []]) {
    labels.length = paints.length = textBounds.length = 0;
    snap = {mode: 'gather', hold, hold_capacity: 10, time_left_ticks: 600, meta: {}};
    drawGather(width, 720, 1000);
    const label = labels.find(s => s.startsWith('Giỏ '));
    const summary = labels.join(' ').toLowerCase().replace(/\s+/g, '');
    const summaryBounds = textBounds.find(entry => entry.label.includes('×'));
    const controlsBounds = textBounds.find(entry => entry.label.startsWith('WASD:'));
    const ok = hold.length ? summary.includes('cálóc×1') && summary.includes('bôngsúng×2')
      && paints.includes('#4a6b32') && paints.includes('#ec407a')
      && summaryBounds.bottom < controlsBounds.top : label.includes('0/10');
    results.push((ok ? 'PASS ' : 'FAIL ') + width + ' basket: ' + label);
  }
  for (const stock of [items, {ca_loc: 1, bong_sung: 2}, [], {}]) {
    labels.length = 0;
    snap = {mode: 'quan', stock, time_left_ticks: 600, meta: {}};
    drawQuan(width, 720, 1000);
    const label = labels.find(s => s.includes('Kho nguyên liệu:'));
    const empty = Array.isArray(stock) ? !stock.length : !Object.keys(stock).length;
    const summary = label.toLowerCase().replace(/\s+/g, '');
    const ok = empty ? summary.includes('(trống)') : summary.includes('cálóc×1') && summary.includes('bôngsúng×2');
    results.push((ok ? 'PASS ' : 'FAIL ') + width + ' stock: ' + label);
  }
}
document.getElementById('result').textContent = results.join('\n');
</script>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chrome", default=shutil.which("google-chrome") or
                        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "chonoi/web/index.html"
    # Disable scheduling/network only; render using the app's real functions and Canvas.
    setup = "<pre id='result'>ERROR: checks did not finish</pre><script>" + \
        "window.fetch = () => new Promise(() => {}); window.requestAnimationFrame = () => {};" + \
        "</script>"
    page = source.read_text(encoding="utf-8").replace("<script>", setup + "<script>", 1)
    page = page.replace("</body>", CHECK + "</body>")
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "check.html"
        target.write_text(page, encoding="utf-8")
        result = subprocess.run([
            args.chrome, "--headless", "--no-first-run", "--no-default-browser-check",
            "--disable-background-networking", "--disable-extensions",
            "--user-data-dir=" + str(Path(tmp) / "profile"), "--dump-dom", target.as_uri(),
        ], capture_output=True, text=True, timeout=30)
    match = re.search(r'<pre id="result">(.*?)</pre>', result.stdout, re.S)
    report = html.unescape(match[1]) if match else result.stderr
    print(report)
    return int(result.returncode != 0 or not match or "FAIL" in report or "ERROR" in report)


if __name__ == "__main__":
    raise SystemExit(main())
