/* 官方模拟器实际操作：切换模型代际，验证数字变化 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const BASE = '/Users/junjielong/Library/Mobile Documents/iCloud~md~obsidian/Documents/我的笔记/程序猿/ai/上下文管理/ai codiing 工具上下文对比报告/第二版/独立重做样章/workbuddy';
const OUT = path.join(BASE, 'build/screenshots');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 950 } });
  const page = await ctx.newPage();
  await page.goto('https://developers.openai.com/api/docs/guides/prompt-caching', { waitUntil: 'domcontentloaded', timeout: 25000 });
  await page.waitForTimeout(4000);
  await page.evaluate(() => {
    const h = Array.from(document.querySelectorAll('h1,h2,h3')).find(x => /prefix matching/i.test(x.textContent || ''));
    if (h) h.scrollIntoView({ block: 'start' });
  });
  await page.waitForTimeout(1500);

  async function readReported() {
    return page.evaluate(() => {
      const t = document.body.innerText;
      const m = t.match(/([\d,]+)\s*Reported cached tokens/);
      const b = t.match(/([\d,]+)\s*Last matched breakpoint/);
      return { reported: m ? m[1] : null, breakpoint: b ? b[1] : null };
    });
  }
  const before = await readReported();
  console.log('切换前（默认视图）:', JSON.stringify(before));

  /* 点 GPT-5.6+（若默认在 Earlier models 它应变化；反之亦然） */
  const clicked1 = await page.evaluate(() => {
    const tabs = Array.from(document.querySelectorAll('button, [role="tab"], [role="button"]'));
    const target = tabs.find(el => /GPT-5\.6\+|GPT-5.6\+/.test(el.textContent || ''));
    if (target) { target.click(); return target.textContent.trim(); }
    return null;
  });
  await page.waitForTimeout(1500);
  const after1 = await readReported();
  console.log('点击「' + clicked1 + '」后:', JSON.stringify(after1));
  await page.screenshot({ path: path.join(OUT, '19-官方模拟器-GPT56后.png') });

  const clicked2 = await page.evaluate(() => {
    const tabs = Array.from(document.querySelectorAll('button, [role="tab"], [role="button"]'));
    const target = tabs.find(el => /Earlier models/i.test(el.textContent || ''));
    if (target) { target.click(); return target.textContent.trim(); }
    return null;
  });
  await page.waitForTimeout(1500);
  const after2 = await readReported();
  console.log('点击「' + clicked2 + '」后:', JSON.stringify(after2));
  await page.screenshot({ path: path.join(OUT, '20-官方模拟器-EarlierModels后.png') });

  const result = { before, afterGpt56: after1, afterEarlier: after2, changed: (before.reported !== after1.reported) || (after1.reported !== after2.reported) };
  fs.writeFileSync(path.join(BASE, 'build/verify-simulator.json'), JSON.stringify(result, null, 2));
  console.log('数字发生变化:', result.changed);
  await browser.close();
})().catch(e => { console.error('ERR', e); process.exit(1); });
