// T17 交互教材验收脚本：多宽度溢出检查 + 交互实质变化断言 + 控制台错误
// 运行：NODE_PATH=<...>/node_modules node verify.js
const { chromium } = require("playwright-core");
const path = require("path");
const { pathToFileURL } = require("url");

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const FILE = pathToFileURL(path.resolve(__dirname, "..", "交互教材.html")).href;
const WIDTHS = [320, 390, 768, 1440];
const UNITS = ["intro", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "appendix"];

let pass = 0, fail = 0;
const results = [];
function ok(name, cond, extra) {
  if (cond) { pass++; results.push("PASS  " + name); }
  else { fail++; results.push("FAIL  " + name + (extra ? "  → " + extra : "")); }
}

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const consoleErrors = [];
  page.on("console", m => { if (m.type() === "error") consoleErrors.push(m.text()); });
  page.on("pageerror", e => consoleErrors.push("pageerror: " + e.message));

  await page.goto(FILE, { waitUntil: "load" });

  // ---------- 1) 多宽度溢出检查 ----------
  let overflow = 0, checked = 0;
  for (const w of WIDTHS) {
    await page.setViewportSize({ width: w, height: 900 });
    for (const u of UNITS) {
      await page.evaluate(id => { document.querySelectorAll(".unit").forEach(el => el.classList.remove("active")); document.getElementById(id).classList.add("active"); }, u);
      await page.waitForTimeout(60);
      const res = await page.evaluate(() => {
        const de = document.documentElement;
        const docOver = de.scrollWidth > de.clientWidth + 1;
        const sels = [".interact", ".tblwrap", "pre", ".colcard", ".mlist", ".seg", ".logbox", ".calc-grid", ".threecol", "table"];
        let worst = 0, worstSel = "";
        sels.forEach(s => document.querySelectorAll(s).forEach(el => {
          const o = el.scrollWidth - el.clientWidth;
          if (o > worst) { worst = o; worstSel = s; }
        }));
        return { docOver, worst, worstSel, docW: de.scrollWidth, clientW: de.clientWidth };
      });
      checked++;
      if (res.docOver || res.worst > 1) { overflow++; results.push(`OVERFLOW  ${w}px · ${u} · docOver=${res.docOver} worst=${res.worst}(${res.worstSel})`); }
    }
  }
  ok(`多宽度溢出检查（${WIDTHS.length} 宽 × ${UNITS.length} 单元 = ${checked} 项）`, overflow === 0, `${overflow} 项溢出`);

  await page.setViewportSize({ width: 1440, height: 900 });

  // ---------- 2) 交互断言 ----------
  const goto = async id => { await page.evaluate(i => { document.querySelectorAll(".unit").forEach(el => el.classList.remove("active")); document.getElementById(i).classList.add("active"); }, id); await page.waitForTimeout(60); };

  // ① 预算演算器
  await goto("b1");
  await page.click("#calcReset");
  await page.click("#calcRun");
  let v = await page.evaluate(() => document.querySelector("#calcTable").textContent);
  ok("①默认样例 → 到线", /到线/.test(v) && !/未到线/.test(v.split("判定理由")[1] || ""), v.slice(0, 120));
  await page.fill("#calcA", "89999");
  await page.dispatchEvent("#calcA", "input");
  v = await page.evaluate(() => document.querySelector("#calcTable").textContent);
  ok("①改 A=89999 → 未到线", /未到线/.test(v), v.slice(0, 120));
  await page.click('[data-preset="ex3"]');
  v = await page.evaluate(() => document.querySelector("#calcOut").textContent);
  ok("①dsh 预设 → 触发线 118,464", /118,464/.test(v), v.slice(0, 160));
  await page.selectOption("#calcTool", "claude");
  v = await page.evaluate(() => document.querySelector("#calcTable").textContent);
  ok("①② Claude → 无法判定（默认未公布）", /未公布/.test(v), v.slice(0, 120));
  await page.click('#calcPredict [data-guess="yes"]');
  v = await page.evaluate(() => document.querySelector("#calcFb").textContent);
  ok("①预测题有反馈", /无法判定/.test(v) || /到线/.test(v), v.slice(0, 100));

  // ② 裁剪器
  await goto("b2");
  await page.click("#trReset");
  for (let k = 0; k < 5; k++) await page.click("#trNext");
  v = await page.evaluate(() => document.querySelector("#trTable").textContent);
  ok("②中部默认 → 已消失（中段）", /已消失/.test(v), v.slice(0, 160));
  await page.selectOption("#trPos", "head");
  v = await page.evaluate(() => document.querySelector("#trTable").textContent);
  ok("②头部 → 幸存（头部保留区）", /幸存/.test(v), v.slice(0, 160));
  const headVal = () => page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("#trTable .data-row"));
    const r = rows.find(x => { const k = x.querySelector(".k"); return k && k.textContent.indexOf("头部保留 / 尾部保留") >= 0; });
    return r ? r.querySelector(".v").textContent : "";
  });
  await page.fill("#trBudget", "6000");
  await page.dispatchEvent("#trBudget", "input");
  v = await headVal();
  ok("②预算 6,000 → 头部保留 163 行（解析自「头部保留/尾部保留」行前段）", /^163 行/.test(v), v.slice(0, 80));
  await page.fill("#trBudget", "1000");
  await page.dispatchEvent("#trBudget", "input");
  v = await headVal();
  ok("②预算 1,000 → 头部保留 27 行（预算越大保留越多）", /^27 行/.test(v), v.slice(0, 80));

  // ③ 压缩四幕
  await goto("b3");
  await page.click("#cmpReset");
  v = await page.evaluate(() => document.querySelector("#cmpPhase").textContent);
  ok("③起始在第 0 幕", /第 0 幕/.test(v), v);
  await page.click("#cmpNext");
  v = await page.evaluate(() => document.querySelector("#cmpPhase").textContent);
  ok("③下一步 → 第 1 幕（筛候选）", /第 1 幕/.test(v), v);
  await page.click("#cmpPlay");
  await page.waitForTimeout(2500);
  await page.click("#cmpPause");
  v = await page.evaluate(() => document.querySelector("#cmpStatus").textContent);
  ok("③播放→暂停，模式提示正确", /已暂停/.test(v), v);
  await page.click('[data-sample="b"]');
  await page.evaluate(() => { document.querySelector("#cmpDots").querySelectorAll("[data-jump]")[3].click(); });
  const d3 = await page.evaluate(() => ({
    note: document.querySelector("#cmpNote").textContent,
    after: document.querySelector("#cmpAfter").textContent,
    table: document.querySelector("#cmpTable").textContent
  }));
  const all3 = d3.note + " || " + d3.after + " || " + d3.table;
  // 母稿自测②：装 M3 7,000 剩 13,000；M2 16,000 > 13,000 → 边界条目=M2，截短 ≈13,000；M1 不补缝
  ok("③样例B 第3幕 → 边界条目=M2（16,000 > 13,000）、截短≈13,000 tokens",
    /M2（16,000 > 13,000）/.test(d3.table) && /> 剩余 13,000/.test(d3.note) && /约 13,000 tokens/.test(all3),
    all3.slice(0, 260));
  ok("③样例B 第3幕 → 全程无负值", !/-\d/.test(all3), all3.slice(0, 260));
  ok("③样例B 第3幕 → 更旧的 M1 未以「已装原样」出现（不补缝）", !/M1 原样/.test(all3), all3.slice(0, 260));
  ok("③样例B 第3幕 → 已装含 M3（7,000）原样", /M3 原样/.test(d3.after), d3.after.slice(0, 160));
  await page.click('#cmpPredict [data-guess="no"]');
  v = await page.evaluate(() => document.querySelector("#cmpFb").textContent);
  ok("③预测题「不补缝」反馈正确", /猜对了/.test(v), v.slice(0, 120));

  // ④ 状态机
  await goto("b4");
  await page.click('[data-state="post"]');
  v = await page.evaluate(() => document.querySelector("#smDisk").textContent + "|" + document.querySelector("#smNote").textContent);
  ok("④压缩后 → 磁盘追加检查点", /检查点/.test(v), v.slice(0, 120));
  await page.click('[data-state="resume"]');
  v = await page.evaluate(() => document.querySelector("#smMem").textContent);
  ok("④重开 → 替代历史 + 后缀回放", /后缀回放/.test(v), v.slice(0, 120));
  await page.click('[data-state="closed"]');
  v = await page.evaluate(() => document.querySelector("#smMem").textContent);
  ok("④关闭 → 内存态消失", /消失/.test(v), v.slice(0, 80));

  // ⑤ 检索 / 记忆
  await goto("b5");
  await page.click("#retReset");
  await page.click("#retNext"); await page.click("#retNext");
  v = await page.evaluate(() => document.querySelector("#retPhase").textContent);
  ok("⑤第 3 步 → read 取正文", /read/.test(v), v);
  await page.click("#retMode");
  v = await page.evaluate(() => document.querySelector("#retList").textContent);
  ok("⑤切全量装填 → 出现「桌子装不下」", /装不下/.test(v), v.slice(0, 100));
  await page.click('[data-tool="ohmy"]');
  v = await page.evaluate(() => document.querySelector("#memQ1").textContent);
  ok("⑤三问卡 ④oh-my-pi → 关（默认 off）", /关/.test(v), v);

  // ⑥ 账单器
  await goto("b6");
  await page.click('[data-scen="b"]');
  v = await page.evaluate(() => document.querySelector("#billTable").textContent);
  ok("⑥账②失效 → 当量 125,000", /125,000/.test(v), v.slice(0, 160));
  await page.click('[data-scen="d"]');
  v = await page.evaluate(() => document.querySelector("#billTable").textContent);
  ok("⑥自算 → 当量 14,500", /14,500/.test(v), v.slice(0, 200));
  await page.click('[data-scen="c"]');
  v = await page.evaluate(() => document.querySelector("#billTable").textContent);
  ok("⑥账③压缩周转 → 当量 92,000", /92,000/.test(v), v.slice(0, 200));
  await page.click('#billPredict [data-guess="no"]');
  v = await page.evaluate(() => document.querySelector("#billFb").textContent);
  ok("⑥预测题「都不变」反馈正确", /猜对了/.test(v), v.slice(0, 80));

  // ⑦ 时间线
  await goto("b7");
  await page.click("#tlReset");
  v = await page.evaluate(() => document.querySelector("#tlData").textContent);
  ok("⑦起点材料 1 条", /1 条/.test(v), v.slice(0, 80));
  await page.click("#tlNext");
  v = await page.evaluate(() => document.querySelector("#tlData").textContent);
  ok("⑦第1步 → 材料 4 条 + 模型调用 1 次", /4 条/.test(v), v.slice(0, 100));
  await page.click("#tlPlay"); await page.waitForTimeout(2200); await page.click("#tlPause");
  v = await page.evaluate(() => document.querySelector("#tlStatus").textContent);
  ok("⑦播放→暂停", /已暂停/.test(v), v);

  // 新增：逐步/暂停控件与 ④⑤⑦ 预测题
  await goto("b1");
  await page.click("#calcReset");
  await page.click("#calcNext"); await page.click("#calcNext");
  v = await page.evaluate(() => document.querySelector("#calcStatus").textContent);
  ok("①逐步控件 → 第 2 / 5 步", /第 2 \/ 5 步/.test(v), v);
  await page.click("#calcPlay"); await page.waitForTimeout(1800); await page.click("#calcPause");
  v = await page.evaluate(() => document.querySelector("#calcStatus").textContent);
  ok("①连续播放→暂停", /已暂停/.test(v), v);

  await goto("b2");
  await page.click("#trReset"); await page.click("#trNext");
  v = await page.evaluate(() => document.querySelector("#trStatus").textContent);
  ok("②逐步控件 → 第 1 / 5 步", /第 1 \/ 5 步/.test(v), v);
  await page.click("#trPlay"); await page.waitForTimeout(1800); await page.click("#trPause");
  v = await page.evaluate(() => document.querySelector("#trStatus").textContent);
  ok("②连续播放→暂停", /已暂停/.test(v), v);

  await goto("b4");
  await page.click("#smReset"); await page.click("#smNext");
  v = await page.evaluate(() => document.querySelector("#smStatus").textContent);
  ok("④逐步控件 → 第 2 / 4 态", /第 2 \/ 4 态/.test(v), v);
  await page.click("#smPlay"); await page.waitForTimeout(2300); await page.click("#smPause");
  v = await page.evaluate(() => document.querySelector("#smStatus").textContent);
  ok("④连续播放→暂停", /已暂停/.test(v), v);
  await page.click('#smPredict [data-guess="no"]');
  v = await page.evaluate(() => document.querySelector("#smFb").textContent);
  ok("④预测题「不包含」反馈正确", /猜对了/.test(v), v.slice(0, 80));

  await goto("b5");
  await page.click("#retReset"); await page.click("#retPlay");
  await page.waitForTimeout(2000); await page.click("#retPause");
  v = await page.evaluate(() => document.querySelector("#retStatus").textContent);
  ok("⑤连续播放→暂停", /已暂停/.test(v), v);
  await page.click('#retPredict [data-guess="no"]');
  v = await page.evaluate(() => document.querySelector("#retFb").textContent);
  ok("⑤预测题「只拿到路径候选」反馈正确", /猜对了/.test(v), v.slice(0, 80));

  await goto("b6");
  await page.click("#billReset"); await page.click("#billNext");
  v = await page.evaluate(() => document.querySelector("#billStatus").textContent);
  ok("⑥逐账控件 → 第 2 / 4 账", /第 2 \/ 4 账/.test(v), v);
  await page.click("#billPlay"); await page.waitForTimeout(2400); await page.click("#billPause");
  v = await page.evaluate(() => document.querySelector("#billStatus").textContent);
  ok("⑥连续播放→暂停", /已暂停/.test(v), v);

  await goto("b7");
  await page.click('#tlPredict [data-guess="0"]');
  v = await page.evaluate(() => document.querySelector("#tlFb").textContent);
  ok("⑦预测题「0 次」反馈正确", /猜对了/.test(v), v.slice(0, 80));

  // 导航
  await page.click('#navlist [data-go="b6"]');
  v = await page.evaluate(() => document.getElementById("b6").classList.contains("active") && document.getElementById("where").textContent);
  ok("导航切换到 ⑥ 账单器", /账单器/.test(String(v)), String(v));

  // ---------- 3) 控制台错误 ----------
  ok("控制台错误 = 0", consoleErrors.length === 0, consoleErrors.slice(0, 3).join(" | "));

  await browser.close();

  console.log(results.join("\n"));
  console.log(`\n==== 合计：PASS ${pass} / FAIL ${fail} ====`);
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error("脚本异常：", e); process.exit(2); });
