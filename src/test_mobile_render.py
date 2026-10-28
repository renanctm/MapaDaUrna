import subprocess, os, sys, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.stdout.reconfigure(encoding='utf-8')

web_dir = r'C:\Projetos\MapaDaUrna\web'
test_harness = os.path.join(web_dir, '_iframe_mobile_test.html')

harness_html = """<!DOCTYPE html>
<html>
<body>
<iframe id="f320" src="index.html" style="width:320px;height:800px;border:0;"></iframe>
<iframe id="f360" src="index.html" style="width:360px;height:800px;border:0;"></iframe>
<iframe id="f390" src="index.html" style="width:390px;height:800px;border:0;"></iframe>
<script>
window.addEventListener('load', () => {
  const report = [];
  ['f320', 'f360', 'f390'].forEach(fid => {
    const win = document.getElementById(fid).contentWindow;
    const doc = win.document;
    const vw = doc.documentElement.clientWidth;
    const docSw = doc.documentElement.scrollWidth;
    report.push(`=== IFRAME VIEWPORT ${vw}px (docScrollWidth=${docSw}px) ===`);
    
    const tabs = doc.querySelectorAll('.tab-btn');
    tabs.forEach((btn, idx) => {
      btn.click();
      const panelId = btn.dataset.tab;
      const panel = doc.getElementById(panelId);
      const pRect = panel.getBoundingClientRect();
      const bodySw = doc.body.scrollWidth;
      const htmlSw = doc.documentElement.scrollWidth;
      report.push(`  TAB ${idx+1} (${panelId}): panelWidth=${Math.round(pRect.width)}px, panelScrollW=${panel.scrollWidth}px, htmlScrollW=${htmlSw}px`);
      
      const allEls = doc.querySelectorAll('header, header *, .kpi-grid, .kpi-grid *, .callout, .callout *, .tabs, #' + panelId + ', #' + panelId + ' *');
      allEls.forEach(el => {
        if (el.closest('.table-wrapper') && el !== el.closest('.table-wrapper')) return;
        if (el.closest('.tabs') && el !== el.closest('.tabs')) return;
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return;
        if (r.right > vw + 1 || r.left < -1 || (el.scrollWidth > el.clientWidth + 2 && !el.classList.contains('table-wrapper') && !el.classList.contains('tabs') && el.tagName !== 'SELECT')) {
          report.push(`    [ISSUE] <${el.tagName.toLowerCase()} class="${el.className}" id="${el.id}"> rect=[${Math.round(r.left)}..${Math.round(r.right)}] clientW=${el.clientWidth} scrollW=${el.scrollWidth} text="${(el.innerText||'').slice(0,45).replace(/\\n/g,' ')}"`);
        }
      });
    });
  });
  const pre = document.createElement('pre');
  pre.id = 'mobile-audit-report';
  pre.textContent = report.join('\\n');
  document.body.appendChild(pre);
});
</script>
</body>
</html>
"""

with open(test_harness, 'w', encoding='utf-8') as f:
    f.write(harness_html)

os.chdir(web_dir)
server = ThreadingHTTPServer(('127.0.0.1', 0), SimpleHTTPRequestHandler)
port = server.server_address[1]
t = threading.Thread(target=server.serve_forever, daemon=True)
t.start()

try:
    browser = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    out = subprocess.check_output([
        browser, '--headless', '--disable-gpu', '--window-size=1400,900', '--dump-dom',
        f'http://127.0.0.1:{port}/_iframe_mobile_test.html'
    ], stderr=subprocess.DEVNULL).decode('utf-8', errors='replace')

    start = out.find('<pre id="mobile-audit-report">')
    end = out.find('</pre>', start)
    if start != -1 and end != -1:
        print(out[start+30:end])
    else:
        print("Report not found")
finally:
    server.shutdown()
    if os.path.exists(test_harness):
        os.remove(test_harness)
