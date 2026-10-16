// 最小观察检查器：对已发布 @oh-my-pi/pi-tui@18.10.4 的 truncateHead 出货代码做函数级真实执行。
// 判据走断言 + 退出码；含负例（应判失败/应不截断）。仅合成数据。
import {
  DEFAULT_MAX_LINES,
  DEFAULT_MAX_BYTES,
  truncateHead,
} from "@oh-my-pi/pi-tui/tools/streaming-output";

let failures = 0;
function check(name: string, cond: boolean, detail: string) {
  const tag = cond ? "PASS" : "FAIL";
  if (!cond) failures++;
  console.log(`[${tag}] ${name} :: ${detail}`);
}

console.log(`constants: DEFAULT_MAX_LINES=${DEFAULT_MAX_LINES} DEFAULT_MAX_BYTES=${DEFAULT_MAX_BYTES}`);

// 1. 负例/对照：未到线必须原样返回（若这里被截断，说明判据本身不可信）
const small = Array.from({ length: 10 }, (_, i) => `line-${i}`).join("\n");
const r1 = truncateHead(small);
check(
  "under-limit passthrough",
  !r1.truncated && r1.content === small,
  `truncated=${r1.truncated} contentUnchanged=${r1.content === small}`,
);

// 2. 到线（行）：3500 行 -> 保留前 3000 行，truncatedBy=lines
const manyLines = Array.from({ length: 3500 }, (_, i) => `l${i}`).join("\n");
const r2 = truncateHead(manyLines);
check(
  "over-lines truncates to DEFAULT_MAX_LINES",
  r2.truncated === true && r2.truncatedBy === "lines" && r2.outputLines === DEFAULT_MAX_LINES,
  `truncatedBy=${r2.truncatedBy} outputLines=${r2.outputLines} totalLines=${r2.totalLines}`,
);

// 3. 到线（字节）：单行 60000 ASCII 字节 -> 首行超限，返回空内容，firstLineExceedsLimit=true
const hugeLine = "a".repeat(60_000);
const r3 = truncateHead(hugeLine);
check(
  "single line over byte cap -> firstLineExceedsLimit",
  r3.truncated === true &&
    r3.truncatedBy === "bytes" &&
    r3.firstLineExceedsLimit === true &&
    r3.content === "" &&
    Buffer.byteLength(r3.content, "utf-8") <= DEFAULT_MAX_BYTES,
  `truncatedBy=${r3.truncatedBy} firstLineExceedsLimit=${r3.firstLineExceedsLimit} outBytes=${Buffer.byteLength(r3.content, "utf-8")}`,
);

// 4. 多字节边界：CJK 行（每字 3 字节）不得被切断成非法 UTF-8
// 600 行、每行 ~190 字节（<3000 行但 >51200 字节），强制走字节线且落点多字节处
const cjkLines = Array.from({ length: 600 }, (_, i) => `中文行-${i}-` + "汉".repeat(60)).join("\n");
const r4 = truncateHead(cjkLines);
const roundTrip = Buffer.from(r4.content, "utf-8").toString("utf-8") === r4.content;
check(
  "CJK truncation keeps valid UTF-8 and within byte budget",
  r4.truncated === true &&
    r4.truncatedBy === "bytes" &&
    roundTrip &&
    Buffer.byteLength(r4.content, "utf-8") <= DEFAULT_MAX_BYTES &&
    !r4.content.endsWith("\n"),
  `truncatedBy=${r4.truncatedBy} outBytes=${Buffer.byteLength(r4.content, "utf-8")} utf8Valid=${roundTrip}`,
);

console.log(failures === 0 ? "RESULT: ALL_PASS" : `RESULT: ${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
