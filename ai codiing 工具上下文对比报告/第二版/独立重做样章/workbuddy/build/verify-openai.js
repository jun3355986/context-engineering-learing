/* 官方嵌入与外链专项验证（修复版） */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const BASE = '/Users/junjielong/Library/Mobile Documents/iCloud~md~obsidian/Documents/我的笔记/程序猿/ai/上下文管理/ai codiing 工具上下文对比报告/第二版/独立重做样章/workbuddy';
const PAGE = 'file://' + path.join(BASE, 'Codex CLI 上下文管理-交互教程.html');
const OUT = path.join(BASE, 'build/screenshots');
const results = { asserts: [], network: [], consoleErrors: [] };
function log(name, ok, detail) { results.asserts.push({ name, ok, detail: detail || '' }); console.log((ok ? 'PASS' : 'FAIL') + ' | ' + name + (detail ? ' | ' + detail : '')); }

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 } });
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error') results.consoleErrors.push(m.text()); });
  page.on('pageerror', e => results.consoleErrors.push('pageerror: ' + e.message));
  page.on('response', r => { if (r.url().includes('developers.openai.com')) results.network.push(r.status() + ' ' + r.url().slice(0, 110)); });

  await page.goto(PAGE, { waitUntil: 'load' });
  await page.waitForTimeout(300);
  await page.evaluate(() => window.__wbShow('u8'));
  await page.waitForTimeout(200);

  /* 外链存在 */
  const ext = await page.locator('a[href="https://developers.openai.com/api/docs/guides/prompt-caching"]').count();
  log('官方外链存在', ext >= 1, 'count=' + ext);

  /* 展开折叠，点击加载 */
  await page.evaluate(() => {
    const b = document.querySelector('#ofLoad');
    const d = b && b.closest('details');
    if (d) d.open = true;
  });
  await page.waitForTimeout(150);
  const framePromise = page.waitForEvent('framenavigated', {
    predicate: f => f.url().includes('developers.openai.com'),
    timeout: 20000
  }).catch(() => null);
  await page.locator('#ofLoad').click();
  const frame = await framePromise;
  if (frame) {
    log('官方 iframe 已导航到官方域名', true, frame.url().slice(0, 90));
    await page.waitForTimeout(6000);
    await page.screenshot({ path: path.join(OUT, '15-官方嵌入-加载后.png'), fullPage: false });
    console.log('SHOT 15-官方嵌入-加载后');
    /* 检查 iframe 元素区域是否渲染了非空内容（截图字节数粗判） */
    const stat = fs.statSync(path.join(OUT, '15-官方嵌入-加载后.png'));
    log('官方嵌入截图已生成', stat.size > 30000, 'size=' + stat.size);
  } else {
    log('官方 iframe 导航（20 秒内未出现）', false, '可能网络受限');
  }

  /* 直接打开官方原页并操作模拟器 */
  try {
    const p2 = await ctx.newPage();
    const resp = await p2.goto('https://developers.openai.com/api/docs/guides/prompt-caching', { waitUntil: 'domcontentloaded', timeout: 25000 });
    log('官方原页 HTTP 状态', resp && resp.status() === 200, 'status=' + (resp && resp.status()));
    await p2.waitForTimeout(3500);
    log('官方原页标题', true, await p2.title());
    await p2.screenshot({ path: path.join(OUT, '16-官方原页-顶部.png'), fullPage: false });

    /* 探索"如何匹配前缀"一节的模拟器 */
    const info = await p2.evaluate(() => {
      const out = { buttons: [], selects: [], inputRanges: 0, numbers: [] };
      document.querySelectorAll('button, [role="button"], select').forEach(el => {
        const t = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 50);
        if (t && t.length < 50) out.buttons.push(t);
      });
      out.buttons = out.buttons.slice(0, 60);
      /* 找含数字的文本（模拟器的 12,000 之类） */
      const body = document.body.innerText || '';
      const m = body.match(/\b\d{1,3}(,\d{3})+\b/g) || [];
      out.numbers = Array.from(new Set(m)).slice(0, 30);
      return out;
    });
    console.log('官方页按钮样例:', JSON.stringify(info.buttons.slice(0, 40)));
    console.log('官方页含千分位数字:', JSON.stringify(info.numbers));
    results.network.push('buttons: ' + JSON.stringify(info.buttons.slice(0, 40)));
    results.network.push('numbers: ' + JSON.stringify(info.numbers));

    /* 尝试滚动到模拟器一节并截图 */
    await p2.evaluate(() => {
      const h = Array.from(document.querySelectorAll('h1,h2,h3')).find(x => /prefix matching/i.test(x.textContent || ''));
      if (h) h.scrollIntoView({ block: 'start' });
    });
    await p2.waitForTimeout(1200);
    await p2.screenshot({ path: path.join(OUT, '17-官方原页-模拟器一节.png'), fullPage: false });
    console.log('SHOT 17-官方原页-模拟器一节');

    /* 尝试点击 "Earlier models" 类控件 */
    const clicked = await p2.evaluate(() => {
      const cands = Array.from(document.querySelectorAll('button, [role="button"], [role="tab"]')).filter(el => /earlier|model/i.test((el.textContent || '')));
      if (cands.length) { cands[0].click(); return (cands[0].textContent || '').trim().slice(0, 40); }
      return null;
    });
    if (clicked) {
      await p2.waitForTimeout(1200);
      const nums2 = await p2.evaluate(() => Array.from(new Set((document.body.innerText.match(/\b\d{1,3}(,\d{3})+\b/g) || []))).slice(0, 30));
      log('官方模拟器：点击模型类控件后数字取样', true, 'clicked="' + clicked + '" numbers=' + JSON.stringify(nums2));
      await p2.screenshot({ path: path.join(OUT, '18-官方原页-模型切换后.png'), fullPage: false });
      console.log('SHOT 18-官方原页-模型切换后');
    } else {
      log('官方模拟器：未找到模型类控件（手动查看截图 17）', false, '');
    }
    await p2.close();
  } catch (e) {
    log('官方原页操作', false, String(e).slice(0, 200));
  }

  await browser.close();
  fs.writeFileSync(path.join(BASE, 'build/verify-openai-result.json'), JSON.stringify(results, null, 2));
  console.log('\n===== 汇总 =====');
  console.log('console 错误:', results.consoleErrors.length, results.consoleErrors.slice(0, 5));
  console.log('断言失败:', results.asserts.filter(a => !a.ok).length);
})().catch(e => { console.error('SCRIPT ERROR:', e); process.exit(1); });
