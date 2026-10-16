const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const BASE = '/Users/junjielong/Library/Mobile Documents/iCloud~md~obsidian/Documents/我的笔记/程序猿/ai/上下文管理/ai codiing 工具上下文对比报告/第二版/独立重做样章/workbuddy';
const OUT = path.join(BASE, 'build/screenshots');
const res = { asserts: [], consoleErrors: [] };
function log(n, ok, d) { res.asserts.push({ n, ok, d: d || '' }); console.log((ok ? 'PASS' : 'FAIL') + ' | ' + n + (d ? ' | ' + d : '')); }
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', e => res.consoleErrors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') res.consoleErrors.push(m.text()); });
  await page.goto('file://' + path.join(BASE, 'Codex CLI 上下文管理-交互教程.html'), { waitUntil: 'load' });
  await page.waitForTimeout(400);

  /* U2 */
  await page.evaluate(() => window.__wbShow('u2'));
  await page.locator('#rsNext').click(); await page.locator('#rsNext').click(); await page.waitForTimeout(150);
  log('U2 到第3步', (await page.locator('#rsPhase').innerText()).includes('③'), await page.locator('#rsPhase').innerText());
  await page.locator('#rsVar').click(); await page.waitForTimeout(150);
  const rsList = await page.locator('#rsList').innerText();
  log('U2 切换"变了"→出现替换说明', rsList.includes('替换说明'), rsList.slice(0, 80).replace(/\n/g, ' '));

  /* U4 修复回归 */
  await page.evaluate(() => window.__wbShow('u4'));
  await page.waitForTimeout(150);
  await page.fill('#cpA', '85000'); await page.dispatchEvent('#cpA', 'input'); await page.waitForTimeout(150);
  let note = await page.locator('#cpNote').innerText();
  log('U4 修复：线下时第1幕说明不再自相矛盾', note.includes('未到触发线') && !note.includes('检测到已到线'), note.slice(0, 60));
  await page.locator('#cpNext').click(); await page.waitForTimeout(150);
  log('U4 修复回归：条件不成立仍停在第一步', (await page.locator('#cpPhase').innerText()).includes('第 1 幕') && await page.locator('#cpWhy').isVisible());
  await page.fill('#cpA', '92000'); await page.dispatchEvent('#cpA', 'input'); await page.waitForTimeout(150);
  log('U4 修复：拖回线上后 why 消失+说明更新',
    !(await page.locator('#cpWhy').isVisible()) && (await page.locator('#cpNote').innerText()).includes('检测到已到线'));
  // 重新生成 03 截图（修复后）
  await page.fill('#cpA', '85000'); await page.dispatchEvent('#cpA', 'input');
  await page.locator('#cpReset').click(); await page.locator('#cpNext').click(); await page.waitForTimeout(250);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.screenshot({ path: path.join(OUT, '03-桌面1440-压缩演示-自动条件不成立_v2.png'), fullPage: false });
  console.log('SHOT 03 v2');

  /* U7 */
  await page.evaluate(() => window.__wbShow('u7'));
  await page.waitForTimeout(150);
  await page.locator('#fbBtns .switch', { hasText: '验收失败' }).click(); await page.waitForTimeout(150);
  const chain = await page.locator('#fbChain').innerText();
  log('U7 验收失败 → 失败点在第③步', chain.includes('③ 验收 ✕ 失败在这里'), chain.replace(/\n/g, ' '));
  const fbData = await page.locator('#fbData').innerText();
  log('U7 状态表含"未安装"', fbData.includes('未安装'), fbData.slice(0, 60).replace(/\n/g, ' '));

  /* U9 */
  await page.evaluate(() => window.__wbShow('u9'));
  await page.waitForTimeout(150);
  await page.locator('[data-ck="0"]').check(); await page.waitForTimeout(150);
  const ck = await page.locator('#ckData').innerText();
  log('U9 勾选后进度=1/10', ck.includes('1 / 10'), ck.replace(/\n/g, ' '));

  /* 手机端 U4 截图（修复后） */
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.__wbShow('u4'));
  await page.waitForTimeout(200);
  await page.screenshot({ path: path.join(OUT, '09-手机390-压缩演示_v2.png'), fullPage: false });
  console.log('SHOT 09 v2');

  await browser.close();
  fs.writeFileSync(path.join(BASE, 'build/verify-extra-result.json'), JSON.stringify(res, null, 2));
  console.log('console 错误:', res.consoleErrors.length);
  console.log('失败数:', res.asserts.filter(a => !a.ok).length);
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
