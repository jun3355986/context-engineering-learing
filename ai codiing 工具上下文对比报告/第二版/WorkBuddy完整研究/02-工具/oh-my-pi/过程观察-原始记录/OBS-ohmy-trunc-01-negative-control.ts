// 负例控制运行（T08R 后补录）：复现"检查器能失败/返回 1"的判据自检。
// 用途：证明判据非"恒 0"——当期望值与出货代码行为不符时，harness 如实报 [FAIL] 并 exit 1。
// 注意：本脚本**不是**首轮真实失败那一跑的原始复现，而是对同一失败模式的**控制性重演**
//       （首版 CJK 用例输入未到线、期望值却写"应截断"）。仅合成数据。
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

// 复现首轮失败模式：CJK 输入"未到线"，却把期望值写成"应截断"（错误期望）。
const cjkLines = Array.from({ length: 200 }, (_, i) => `中文行-${i}-` + "汉".repeat(8)).join("\n");
const bytes = Buffer.byteLength(cjkLines, "utf-8");
const lines = cjkLines.split("\n").length;
const r = truncateHead(cjkLines);
check(
  "CJK under-limit but expected to truncate (deliberately wrong expectation)",
  r.truncated === true, // ← 错误期望：未到线时 truncated 为 undefined/false
  `inputLines=${lines} inputBytes=${bytes} truncated=${r.truncated} truncatedBy=${r.truncatedBy}`,
);

console.log(failures === 0 ? "RESULT: ALL_PASS" : `RESULT: ${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
