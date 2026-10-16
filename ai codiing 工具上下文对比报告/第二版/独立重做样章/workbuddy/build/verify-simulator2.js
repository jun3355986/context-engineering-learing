/* 官方模拟器实际操作 v2：真实鼠标事件切换模型代际 */
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
  await page.waitForTimeout(4500);
  await page.evaluate(() => {
    const h = Array.from(document.querySelectorAll('h1,h2,h3')).find(x => /prefix matching/i.test(x.textContent || ''));
    if (h) h.scrollIntoView({ block: 'start' });
  });
  await page.waitForTimeout(1200);

  async function state() {
    return page.evaluate(() => {
      const t = document.body.innerText;
      const m = t.match(/([\d,]+)\s*Reported cached tokens/);
      // 找 Earlier models / GPT-5.6+ 的选中样式（比较 aria-selected / class 里是否含 selected/active）
      const cands = Array.from(document.querySelectorAll('button, [role="tab"], [role="button"], label, div')).filter(el => /^(Earlier models|GPT-5\.6\+)$/.test((el.textContent || '').trim()));
      const info = cands.slice(0, 6).map(el => ({
        text: (el.textContent || '').trim(),
        cls: el.className && el.className.toString ? el.className.toString().slice(0, 80) : '',
        ariaSelected: el.getAttribute('aria-selected'),
        dataState: el.getAttribute('data-state')
      }));
      let earlierLine = '';
      const idx = t.indexOf('min cacheable length (varies by model)');
      return { reported: m ? m[1] : null, cands: info };
    });
  }
  console.log('初始:', JSON.stringify(await state(), null, 1));

  /* 真实鼠标点击 Earlier models */
  const earlier = page.locator('text=Earlier models').first();
  await earlier.click({ force: true });
  await page.waitForTimeout(1800);
  const s1 = await state();
  console.log('点击 Earlier models 后:', JSON.stringify(s1, null, 1));
  await page.screenshot({ path: path.join(OUT, '21-模拟器-点击Earlier后.png') });

  /* 再点回 GPT-5.6+ */
  const gpt = page.locator('text=GPT-5.6+').first();
  await gpt.click({ force: true });
  await page.waitForTimeout(1800);
  const s2 = await state();
  console.log('点击 GPT-5.6+ 后:', JSON.stringify(s2, null, 1));
  await page.screenshot({ path: path.join(OUT, '22-模拟器-点击GPT56后.png') });

  fs.writeFileSync(path.join(BASE, 'build/verify-simulator2.json'), JSON.stringify({ s0: await state(), s1, s2 }, null, 2));
  console.log('数字变化（Earlier vs GPT-5.6+）:', s1.reported !== s2.reported, s1.reported, '→', s2.reported);
  await browser.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
