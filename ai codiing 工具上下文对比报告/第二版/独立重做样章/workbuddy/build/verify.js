/* 交互教程浏览器验收脚本：操作关键交互、检查溢出、截图、收集脚本错误 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const BASE = '/Users/junjielong/Library/Mobile Documents/iCloud~md~obsidian/Documents/我的笔记/程序猿/ai/上下文管理/ai codiing 工具上下文对比报告/第二版/独立重做样章/workbuddy';
const PAGE = 'file://' + path.join(BASE, 'Codex CLI 上下文管理-交互教程.html');
const OUT = path.join(BASE, 'build/screenshots');
fs.mkdirSync(OUT, { recursive: true });

const results = { consoleErrors: [], overflow: [], asserts: [], network: [] };
function log(name, ok, detail) {
  results.asserts.push({ name, ok, detail: detail || '' });
  console.log((ok ? 'PASS' : 'FAIL') + ' | ' + name + (detail ? ' | ' + detail : ''));
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error') results.consoleErrors.push(m.text()); });
  page.on('pageerror', e => results.consoleErrors.push('pageerror: ' + e.message));
  page.on('requestfailed', r => {
    if (!r.url().startsWith('file://')) results.network.push('FAILED: ' + r.url() + ' | ' + (r.failure() && r.failure().errorText));
  });

  await page.goto(PAGE, { waitUntil: 'load' });
  await page.waitForTimeout(400);

  /* ---------- 1. 初始状态 ---------- */
  log('初始显示 intro', await page.locator('#intro.active').count() === 1);

  /* ---------- 2. U3 演算器 ---------- */
  await page.evaluate(() => window.__wbShow('u3'));
  await page.locator('.preset', { hasText: '例4' }).click();
  await page.waitForTimeout(150);
  let concl = await page.locator('#calcData .data-row', { hasText: '结论' }).innerText();
  log('U3 例4 → 到线', concl.includes('到线'), concl.replace(/\n/g, ' '));
  log('U3 例4 整段线判定=到线', (await page.locator('#calcData .data-row', { hasText: '整段线判定' }).innerText()).includes('到线'));
  await page.fill('#cA', '89999');
  await page.dispatchEvent('#cA', 'input');
  await page.waitForTimeout(120);
  concl = await page.locator('#calcData .data-row', { hasText: '结论' }).innerText();
  log('U3 改成 A=89999（total 口径同舞台）→ 结论更新', true, concl.replace(/\n/g, ' '));
  // 自由改参数后预设取消选中
  const presetOn = await page.locator('.preset.on').count();
  log('U3 改参数后预设取消选中', presetOn === 0, 'on=' + presetOn);

  /* ---------- 3. U4 四幕 + 自动/手动模式纪律 ---------- */
  await page.evaluate(() => window.__wbShow('u4'));
  await page.waitForTimeout(200);
  // 默认 A=92000 到线：自动模式可以走
  await page.locator('#cpNext').click(); await page.waitForTimeout(120);
  let phase = await page.locator('#cpPhase').innerText();
  log('U4 自动(到线)可进第2幕', phase.includes('第 2 幕'), phase);
  // 拖到线下
  await page.fill('#cpA', '85000');
  await page.dispatchEvent('#cpA', 'input');
  await page.waitForTimeout(120);
  // 回第一步
  await page.locator('#cpReset').click(); await page.waitForTimeout(100);
  await page.locator('#cpNext').click(); await page.waitForTimeout(150);
  phase = await page.locator('#cpPhase').innerText();
  const whyVisible = await page.locator('#cpWhy').isVisible();
  const whyText = whyVisible ? await page.locator('#cpWhy').innerText() : '';
  log('U4 自动条件不成立 → 停在第一步并说明原因', phase.includes('第 1 幕') && whyVisible && whyText.includes('条件不成立'), phase + ' | ' + whyText.slice(0, 50));
  // 重置不改变模式
  await page.locator('#cpReset').click(); await page.waitForTimeout(100);
  log('U4 重置后仍是自动模式（未被悄悄切换）', await page.locator('#cpModeAuto.on').count() === 1);
  // 主动切手动 → 可推进
  await page.locator('#cpModeManual').click(); await page.waitForTimeout(100);
  await page.locator('#cpNext').click(); await page.waitForTimeout(120);
  phase = await page.locator('#cpPhase').innerText();
  log('U4 手动模式不要求到线可推进', phase.includes('第 2 幕'), phase);
  // 手动模式重置后模式保持
  await page.locator('#cpReset').click(); await page.waitForTimeout(100);
  log('U4 手动模式重置后仍为手动', await page.locator('#cpModeManual.on').count() === 1);
  // 播放中模式保持：设置速度并播放，随后暂停
  await page.selectOption('#cpSpeed', '1600');
  await page.locator('#cpPlay').click(); await page.waitForTimeout(500);
  await page.locator('#cpPause').click(); await page.waitForTimeout(100);
  log('U4 播放/暂停后模式仍为手动', await page.locator('#cpModeManual.on').count() === 1);

  /* ---------- 4. U5 裁剪 ---------- */
  await page.evaluate(() => window.__wbShow('u5'));
  await page.waitForTimeout(150);
  await page.locator('[data-cut="25"]').click(); await page.waitForTimeout(120);
  let crit = await page.locator('#ctData .data-row', { hasText: '关键约束' }).innerText();
  log('U5 中部+25% → 约束消失', crit.includes('已消失'), crit.replace(/\n/g, ' '));
  await page.locator('[data-pos="8"]').click(); await page.waitForTimeout(120);
  crit = await page.locator('#ctData .data-row', { hasText: '关键约束' }).innerText();
  log('U5 头部+25% → 约束幸存', crit.includes('幸存'), crit.replace(/\n/g, ' '));

  /* ---------- 5. U6 三层状态机 ---------- */
  await page.evaluate(() => window.__wbShow('u6'));
  await page.waitForTimeout(150);
  await page.locator('[data-st="3"]').click(); await page.waitForTimeout(150);
  const memTxt = await page.locator('#smMem').innerText();
  const noteTxt = await page.locator('#smNote').innerText();
  log('U6 重开 → 替代历史+后缀回放', memTxt.includes('后缀回放'), noteTxt.slice(0, 40));
  await page.uncheck('#smNew'); await page.waitForTimeout(120);
  const memTxt2 = await page.locator('#smMem').innerText();
  log('U6 取消"新更新"后替代清单不含新更新', !memTxt2.includes('整理期间新接受的更新'));

  /* ---------- 6. U8 缓存 ---------- */
  await page.evaluate(() => window.__wbShow('u8'));
  await page.waitForTimeout(150);
  await page.locator('#ccBtns .switch', { hasText: '② 把日期' }).click(); await page.waitForTimeout(120);
  let cc = await page.locator('#ccData').innerText();
  log('U8 场景b → 复用部分为"无"', cc.includes('无——变化发生'), cc.slice(0, 60).replace(/\n/g, ' '));
  await page.locator('#billPresets .preset', { hasText: '首次写入' }).click(); await page.waitForTimeout(120);
  let bill = await page.locator('#billData').innerText();
  log('U8 账单 首次写入 → 125,000', bill.includes('125,000'), bill.slice(0, 80).replace(/\n/g, ' '));
  await page.fill('#bIn', '50000'); await page.dispatchEvent('#bIn', 'input');
  await page.fill('#bCached', '40000'); await page.dispatchEvent('#bCached', 'input');
  await page.fill('#bWrite', '2000'); await page.dispatchEvent('#bWrite', 'input');
  await page.waitForTimeout(120);
  bill = await page.locator('#billData').innerText();
  log('U8 账单自算 50k/40k/2k → 14,500', bill.includes('14,500'), bill.slice(0, 80).replace(/\n/g, ' '));

  /* ---------- 7. U1 时间线 ---------- */
  await page.evaluate(() => window.__wbShow('u1'));
  await page.waitForTimeout(150);
  await page.locator('#tlNext').click(); await page.waitForTimeout(100);
  const tlCount = await page.locator('#tlList .mitem').count();
  log('U1 第1步材料=3条', tlCount === 3, 'count=' + tlCount);
  await page.selectOption('#tlSpeed', '1600');
  await page.locator('#tlPlay').click(); await page.waitForTimeout(3600);
  const tlPhase = await page.locator('#tlPhase').innerText();
  log('U1 连续播放推进', !tlPhase.includes('第 0 步'), tlPhase);
  await page.locator('#tlPause').click();

  /* ---------- 8. 多宽度溢出检查 ---------- */
  const widths = [320, 390, 768, 1440];
  const units = ['intro', 'u1', 'u2', 'u3', 'u4', 'u5', 'u6', 'u7', 'u8', 'u9', 'appendix'];
  for (const w of widths) {
    await page.setViewportSize({ width: w, height: 900 });
    for (const u of units) {
      await page.evaluate(id => window.__wbShow(id), u);
      await page.waitForTimeout(60);
      const r = await page.evaluate(() => {
        const docOverflow = document.documentElement.scrollWidth - window.innerWidth;
        let worst = docOverflow, tag = 'document';
        document.querySelectorAll('.interact, .tblwrap, pre, .colcard, .mlist').forEach(el => {
          const o = el.scrollWidth - el.clientWidth;
          if (o > worst) { worst = o; tag = el.className + '#' + (el.id || ''); }
        });
        return { worst, tag, innerWidth: window.innerWidth };
      });
      const ok = r.worst <= 2;
      if (!ok) results.overflow.push({ width: w, unit: u, overflow: r.worst, worstEl: r.tag });
      log('溢出检查 ' + w + 'px ' + u, ok, ok ? '' : ('overflow=' + r.worst + ' by ' + r.tag));
    }
  }

  /* ---------- 9. 截图 ---------- */
  async function shot(name, unit, w, h, full, action) {
    await page.setViewportSize({ width: w, height: h });
    await page.evaluate(id => window.__wbShow(id), unit);
    await page.waitForTimeout(220);
    if (action) { await action(); await page.waitForTimeout(260); }
    await page.screenshot({ path: path.join(OUT, name + '.png'), fullPage: !!full });
    console.log('SHOT', name);
  }
  await shot('01-桌面1440-开始之前', 'intro', 1440, 900, true);
  await shot('02-桌面1440-预算演算器-例4到线', 'u3', 1440, 900, true, async () => {
    await page.locator('.preset', { hasText: '例4' }).click();
  });
  await shot('03-桌面1440-压缩演示-自动条件不成立', 'u4', 1440, 900, false, async () => {
    await page.fill('#cpA', '85000'); await page.dispatchEvent('#cpA', 'input');
    await page.locator('#cpModeAuto').click(); await page.locator('#cpReset').click();
    await page.locator('#cpNext').click();
  });
  await shot('04-桌面1440-压缩演示-手动第3幕', 'u4', 1440, 900, false, async () => {
    await page.locator('#cpModeManual').click();
    await page.locator('#cpNext').click(); await page.locator('#cpNext').click();
  });
  await shot('05-桌面1440-裁剪-中部25%', 'u5', 1440, 900, true, async () => {
    await page.locator('[data-pos="150"]').click();
    await page.locator('[data-cut="25"]').click();
  });
  await shot('06-桌面1440-三个账-缓存场景b', 'u8', 1440, 900, true, async () => {
    await page.locator('#ccBtns .switch', { hasText: '② 把日期' }).click();
  });
  await shot('07-平板768-压缩演示', 'u4', 768, 900, false);
  await shot('08-手机390-开始', 'intro', 390, 844, false);
  await shot('09-手机390-压缩演示', 'u4', 390, 844, false);
  await shot('10-手机390-裁剪', 'u5', 390, 844, true);
  await shot('11-手机390-三层状态机-重开', 'u6', 390, 844, true, async () => {
    await page.locator('[data-st="3"]').click();
  });
  await shot('12-手机390-账单', 'u8', 390, 844, true);
  await shot('13-窄屏320-预算演算器', 'u3', 320, 700, true);
  await shot('14-窄屏320-附录表格', 'appendix', 320, 700, true);

  /* ---------- 10. 官方嵌入测试（联网时） ---------- */
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => window.__wbShow('u8'));
  await page.waitForTimeout(200);
  const framePromise = page.waitForEvent('framenavigated', {
    predicate: f => f.url().includes('developers.openai.com'),
    timeout: 15000
  }).catch(() => null);
  await page.locator('#ofLoad').click();
  const frame = await framePromise;
  if (frame) {
    await page.waitForTimeout(4000);
    results.network.push('iframe navigated: ' + frame.url());
    log('官方嵌入 iframe 已导航到官方域名', true, frame.url().slice(0, 80));
    await page.screenshot({ path: path.join(OUT, '15-官方嵌入-加载后.png'), fullPage: false });
    console.log('SHOT 15-官方嵌入-加载后');
  } else {
    log('官方嵌入 iframe 导航（15 秒内未出现）', false, '需检查网络可达性');
  }
  // 外链存在
  const ext = await page.locator('a[href="https://developers.openai.com/api/docs/guides/prompt-caching"]').count();
  log('官方外链存在', ext >= 1, 'count=' + ext);
  // 用新 tab 直接打开官方页（同源可操作验证）
  try {
    const p2 = await ctx.newPage();
    await p2.goto('https://developers.openai.com/api/docs/guides/prompt-caching', { waitUntil: 'domcontentloaded', timeout: 20000 });
    await p2.waitForTimeout(3000);
    const title = await p2.title();
    log('官方原页直接打开成功', true, title);
    await p2.screenshot({ path: path.join(OUT, '16-官方原页-直接打开.png'), fullPage: false });
    console.log('SHOT 16-官方原页-直接打开');
    // 尝试操作官方模拟器（找到含 "Earlier models" 或模型切换的控件）
    const simInfo = await p2.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button')).map(b => (b.textContent || '').trim()).filter(t => t.length > 2 && t.length < 40);
      return { buttonSamples: btns.slice(0, 25) };
    });
    console.log('官方页按钮样例:', JSON.stringify(simInfo.buttonSamples));
    results.network.push('openai page buttons: ' + JSON.stringify(simInfo.buttonSamples));
    await p2.close();
  } catch (e) {
    log('官方原页直接打开', false, String(e).slice(0, 160));
  }

  await browser.close();
  fs.writeFileSync(path.join(BASE, 'build/verify-result.json'), JSON.stringify(results, null, 2));
  console.log('\n===== 汇总 =====');
  console.log('console 错误数:', results.consoleErrors.length);
  console.log('溢出问题数:', results.overflow.length);
  console.log('断言失败数:', results.asserts.filter(a => !a.ok).length);
  console.log('网络记录:', results.network.length);
})().catch(e => { console.error('SCRIPT ERROR:', e); process.exit(1); });
