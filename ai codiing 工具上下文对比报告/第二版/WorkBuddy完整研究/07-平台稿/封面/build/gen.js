// T20 封面生成器：基图 + SVG 文字合成
// 输出：../ 下 *.svg（35 张）
const fs = require("fs");
const path = require("path");
const OUT = path.resolve(__dirname, "..");

const FONT = `"PingFang SC","Hiragino Sans GB","Heiti SC","Microsoft YaHei","Noto Sans SC",sans-serif`;
const INK = "#10203a";
const ACCENT = "#2952cc";
const TEAL = "#0d9488";
const SUB = "#5b6b82";

// ---- 文本宽度估算（单位 em）----
function unit(ch) {
  const c = ch.codePointAt(0);
  if (ch === " ") return 0.30;
  if (c >= 0x2e80 && c <= 0x9fff) return 1.0;   // CJK 汉字
  if (c >= 0xff00 && c <= 0xffef) return 1.0;   // 全角标点
  if (c >= 0x3000 && c <= 0x303f) return 1.0;
  if (ch === "—" || ch === "≠" || ch === "≥" || ch === "≤") return 1.0;
  if (ch === "·") return 0.40;
  if (ch === "×") return 0.62;
  if (c < 128) return 0.56;                     // ASCII
  return 0.9;
}
function textUnits(s) {
  let u = 0;
  for (const ch of s) u += unit(ch);
  return u;
}
// 在最优位置切成两行：优先在标点后断行，再取最均衡
const BREAK_PUNCT = " ：:，,、。？?！!—…；;·";
function splitTwo(s) {
  const chars = [...s];
  const cands = [];
  for (let i = 1; i < chars.length; i++) {
    if (chars[i - 1] === "—") continue;                 // 不在破折号内部断行
    const a = textUnits(chars.slice(0, i).join(""));
    const b = textUnits(chars.slice(i).join(""));
    const isPunct = BREAK_PUNCT.includes(chars[i - 1]) || chars[i] === "—";
    cands.push({ i, max: Math.max(a, b), isPunct });
  }
  const punctCands = cands.filter((c) => c.isPunct);
  const pool = punctCands.length ? punctCands : cands;
  pool.sort((x, y) => x.max - y.max);
  const best = pool[0];
  return [chars.slice(0, best.i).join("").trim(), chars.slice(best.i).join("").trim()];
}
// 计算 1~2 行 + 自适应字号
function fit(title, innerW, base, min) {
  const total = textUnits(title);
  const oneLineSize = Math.floor(innerW / total);
  let lines, size;
  // 单行只要不用缩得太狠，就保持单行
  if (oneLineSize >= base) {
    lines = [title]; size = base;
  } else if (oneLineSize >= base * 0.72 && oneLineSize >= min) {
    lines = [title]; size = oneLineSize;
  } else {
    lines = splitTwo(title);
    const maxU = Math.max(...lines.map(textUnits));
    size = Math.min(base, Math.floor(innerW / maxU));
    if (size < min) size = min;
  }
  return { lines, size };
}
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function pill(x, y, w, h, fill, txt, color, size, weight) {
  return `
  <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${h / 2}" fill="${fill}"/>
  <text x="${x + w / 2}" y="${y + h / 2}" text-anchor="middle" dominant-baseline="central"
        font-family='${FONT}' font-size="${size}" font-weight="${weight}" fill="${color}">${esc(txt)}</text>`;
}

// 通用封面
function cover({ W, H, base, badgeL, badgeR, title, subtitle, footer, align, panelTop, baseSize, minSize }) {
  const pad = Math.round(W * 0.065);
  const panelW = W - pad * 2;
  const innerW = panelW - Math.round(W * 0.06) * 2;
  const cx = W / 2;
  const textX = align === "center" ? cx : pad + Math.round(W * 0.06);
  const anchor = align === "center" ? "middle" : "start";

  const f = fit(title, innerW, baseSize, minSize);
  const lineGap = Math.round(f.size * 1.32);
  const titleBlockH = f.lines.length * lineGap;
  const subH = subtitle ? Math.round(f.size * 0.52) + Math.round(f.size * 0.55) : 0;
  const panelH = titleBlockH + subH + Math.round(H * 0.095);
  const panelY = panelTop;
  const titleStartY = panelY + Math.round(H * 0.062) + Math.round(f.size * 0.82);

  let titleSvg = "";
  f.lines.forEach((ln, i) => {
    titleSvg += `
  <text x="${textX}" y="${titleStartY + i * lineGap}" text-anchor="${anchor}"
        font-family='${FONT}' font-size="${f.size}" font-weight="800" fill="${INK}">${esc(ln)}</text>`;
  });
  let subSvg = "";
  if (subtitle) {
    subSvg = `
  <text x="${textX}" y="${titleStartY + f.lines.length * lineGap + Math.round(f.size * 0.25)}"
        text-anchor="${anchor}" font-family='${FONT}' font-size="${subH ? Math.round(f.size * 0.5) : 30}"
        font-weight="500" fill="${SUB}">${esc(subtitle)}</text>`;
  }

  const footerH = Math.round(H * 0.10);
  const badgeH = Math.round(H * 0.058);
  const badgeY = Math.round(H * 0.055);
  const badgeSize = Math.round(badgeH * 0.50);
  const blW = Math.round(textUnits(badgeL) * badgeSize * 0.86) + badgeH;
  const brW = Math.round(textUnits(badgeR) * badgeSize * 0.86) + badgeH;

  return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <defs>
    <clipPath id="clip"><rect x="0" y="0" width="${W}" height="${H}" rx="0"/></clipPath>
  </defs>
  <g clip-path="url(#clip)">
    <image x="0" y="0" width="${W}" height="${H}" preserveAspectRatio="xMidYMid slice"
           xlink:href="bases/${base}"/>
  </g>
${pill(pad, badgeY, blW, badgeH, "rgba(255,255,255,0.92)", badgeL, ACCENT, badgeSize, 700)}
${pill(W - pad - brW, badgeY, brW, badgeH, ACCENT, badgeR, "#ffffff", badgeSize, 700)}
  <rect x="${pad}" y="${panelY}" width="${panelW}" height="${panelH}" rx="${Math.round(H * 0.03)}"
        fill="rgba(255,255,255,0.90)" stroke="rgba(41,82,204,0.16)" stroke-width="2"/>
  <rect x="${pad}" y="${panelY + Math.round(H * 0.028)}" width="${Math.round(W * 0.011)}"
        height="${panelH - Math.round(H * 0.056)}" rx="${Math.round(W * 0.006)}" fill="${ACCENT}"/>
${titleSvg}${subSvg}
  <rect x="0" y="${H - footerH}" width="${W}" height="${footerH}" fill="rgba(255,255,255,0.94)"/>
  <rect x="0" y="${H - footerH}" width="${W}" height="2" fill="rgba(13,148,136,0.55)"/>
  <text x="${cx}" y="${H - footerH + footerH / 2}" text-anchor="middle" dominant-baseline="central"
        font-family='${FONT}' font-size="${Math.round(footerH * 0.34)}" font-weight="600"
        fill="${SUB}">${esc(footer)}</text>
</svg>
`;
}

// ---------------- 数据 ----------------
const GW = 1200, GH = 800;      // 公众号：3:2
const BW = 1200, BH = 630;      // 博客 OG：标准 OG 尺寸 1.91:1（标题区上下留白，裁剪安全）
const XW = 1080, XH = 1440;     // 小红书：3:4
const FOOTER = "八工具实测 · 有来源可查";

const gongzhong = [
  "AI 明明“记得”，为什么这次回答没用上？",
  "一次回答，AI 到底看了哪些材料？",
  "AI 的“容量”怎么算？三条线，到线才整理",
  "实测篇①：压缩阈值到底在哪？八个工具实测一遍",
  "旧历史被压成一段摘要：丢了什么？",
  "实测篇②：连续压三次，约束还在吗？",
  "AI 读了大文件，为什么只看到一小段？",
  "实测篇③：落盘的文件，真能一个字不差找回来吗？",
  "关掉再打开，AI 还记得多少？",
  "为什么第二次问同样的问题更便宜？",
  "AI 的“记忆”“子代理”“交接”：它到底记不记得住？",
  "AI 会自己去找资料，还是你全塞给它？",
  "源码深挖①：跟着真实代码走一遍——压缩在哪一行被触发？",
  "源码深挖②：换一个工具再走一遍——同一机制，不同实现",
  "如果换你来设计：一个 Agent 的上下文流程怎么排？",
  "怎么判断一个上下文方案好不好？（收官）",
];

const xhs = [
  "AI 说忘了？记录其实还在",
  "一次回答，看了哪五块料",
  "三条线：到线才整理",
  "90% 不是统一压缩阈值",
  "阈值写 85%，实测 72%？",
  "压一次，约束丢没丢？",
  "连压三次，硬约束丢了",
  "摘要会越压越长？",
  "大文件，AI 只看到一小段？",
  "落盘就一定能全找回？",
  "关掉重开，AI 还记得吗？",
  "恢复会把命令再跑一遍吗？",
  "第二次问更便宜：缓存",
  "缓存 ≠ 摘要 ≠ 记忆",
  "清掉旧输出，账单 ×2.9",
  "AI 的记忆，默认开还是关？",
  "有检索工具，就一定会用吗？",
  "换你设计：先写一个反例",
];

const pad2 = (n) => String(n).padStart(2, "0");

let made = [];
// 公众号：基图 B1，左上 badge 系列，右上 第NN篇
gongzhong.forEach((t, i) => {
  const svg = cover({
    W: GW, H: GH, base: "B1-公众号系列.png",
    badgeL: "上下文管理 · 八工具实测", badgeR: `第${pad2(i + 1)}篇`,
    title: t, footer: FOOTER, align: "start",
    panelTop: Math.round(GH * 0.235), baseSize: 72, minSize: 42,
  });
  const name = `公众号-第${pad2(i + 1)}篇.svg`;
  fs.writeFileSync(path.join(OUT, name), svg);
  made.push(name);
});
// 小红书：基图 B2/B3/B4 轮转，居中
xhs.forEach((t, i) => {
  const bases = ["B2-小红书A.png", "B3-小红书B.png", "B4-小红书C.png"];
  const svg = cover({
    W: XW, H: XH, base: bases[i % 3],
    badgeL: "上下文管理 · 八工具实测", badgeR: `第${pad2(i + 1)}条`,
    title: t, footer: FOOTER, align: "center",
    panelTop: Math.round(XH * 0.30), baseSize: 96, minSize: 60,
  });
  const name = `小红书-第${pad2(i + 1)}条.svg`;
  fs.writeFileSync(path.join(OUT, name), svg);
  made.push(name);
});
// 博客 OG：基图 B5；标准 OG 1200×630（1.91:1），标题区上下留白保证裁剪安全
{
  const svg = cover({
    W: BW, H: BH, base: "B5-博客OG.png",
    badgeL: "博客 · 阅读入口", badgeR: "OG",
    title: "AI 上下文管理 · 完整教程入口",
    subtitle: "为什么 AI 明明“记得”，这次却没把材料用上",
    footer: FOOTER, align: "start",
    panelTop: Math.round(BH * 0.33), baseSize: 70, minSize: 44,
  });
  fs.writeFileSync(path.join(OUT, "博客-OG.svg"), svg);
  made.push("博客-OG.svg");
}

console.log("生成 SVG：", made.length);
made.forEach((m) => console.log(" -", m));
