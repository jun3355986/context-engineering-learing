// 生成全文搜索索引：node build-search-index.js
const fs = require("fs");
const path = require("path");

const root = process.argv[2] || process.cwd();
global.window = {};
eval(fs.readFileSync(path.join(root, "assets/js/toc.js"), "utf8"));
const toc = window.TOC;

const chapters = [];
if (toc.home) chapters.push({ ch: toc.home, group: "导读" });
for (const g of toc.groups) for (const ch of g.chapters) chapters.push({ ch, group: g.title });

const strip = (s) =>
  s
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<pre[\s\S]*?<\/pre>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/&nbsp;/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const entries = [];
for (const { ch, group } of chapters) {
  const file = ch.file;
  const abs = path.join(root, file);
  if (!fs.existsSync(abs)) continue;
  const html = fs.readFileSync(abs, "utf8");
  const art = html.match(/<article[^>]*>([\s\S]*?)<\/article>/i);
  const body = art ? art[1] : html;
  // 按 h2 切段
  const parts = body.split(/<h2([^>]*)>/i);
  let current = { id: "", heading: ch.title, text: strip(parts[0]) };
  for (let i = 1; i < parts.length; i += 2) {
    const attrs = parts[i];
    const rest = parts[i + 1] || "";
    const close = rest.indexOf("</h2>");
    const heading = strip(close >= 0 ? rest.slice(0, close) : rest);
    const after = close >= 0 ? rest.slice(close + 5) : "";
    if (current.heading) entries.push({ ch, group, ...current });
    const idm = attrs.match(/id="([^"]+)"/);
    current = { id: idm ? idm[1] : "", heading, text: strip(after) };
  }
  if (current.heading) entries.push({ ch, group, ...current });
}

const out = entries
  .filter((e) => e.heading || e.text)
  .map((e) => ({
    p: e.ch.file,
    c: e.ch.id,
    t: e.ch.title,
    g: e.group,
    a: e.id || "",
    h: e.heading,
    x: e.text.slice(0, 700),
  }));

const js =
  "/* 全文搜索索引：由 build-search-index.js 生成，勿手改 */\n" +
  "window.SEARCH_INDEX = " +
  JSON.stringify(out) +
  ";\n";
fs.writeFileSync(path.join(root, "assets/js/search-index.js"), js);
console.log("entries:", out.length, "bytes:", js.length);
