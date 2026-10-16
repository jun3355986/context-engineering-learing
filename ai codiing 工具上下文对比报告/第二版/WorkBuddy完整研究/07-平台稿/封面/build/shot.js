// T20 封面导出：SVG -> PNG（playwright-core + 系统 Chrome）
const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const OUT = path.resolve(__dirname, "..");

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

// 可选：命令行传文件名子串，仅重导匹配的 SVG（不传则全量重导）
const filter = process.argv.slice(2);
const files = fs
  .readdirSync(OUT)
  .filter((f) => f.endsWith(".svg"))
  .filter((f) => !filter.length || filter.some((s) => f.includes(s)))
  .sort();

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  for (const f of files) {
    const full = path.join(OUT, f);
    const svg = fs.readFileSync(full, "utf8");
    const m = svg.match(/width="(\d+)"\s+height="(\d+)"/);
    const W = parseInt(m[1], 10), H = parseInt(m[2], 10);
    const ctx = await browser.newContext({
      viewport: { width: W, height: H },
      deviceScaleFactor: 1,
    });
    const page = await ctx.newPage();
    await page.goto(pathToFileURL(full).href, { waitUntil: "load" });
    await page.waitForTimeout(400);
    const png = full.replace(/\.svg$/, ".png");
    await page.screenshot({ path: png });
    await ctx.close();
    console.log(`png: ${path.basename(png)}  ${W}x${H}`);
  }
  await browser.close();
})();
