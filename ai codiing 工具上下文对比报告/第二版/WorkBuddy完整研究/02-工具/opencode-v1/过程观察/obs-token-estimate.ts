// OBS-ocv1-token-01 观察运行器（只读导入快照出货代码；不修改快照）
// 目的：对 OpenCode v1 出货代码中的本地 token 估算函数做**函数级真实执行**，
//       验证"字符数/4"口径（而非字节/4），并带一个"应判失败"的负例证明判据非恒真。
// 快照：/Users/junjielong/workspace/agent-context-research/workbuddy-sources/opencode-v1
//       SHA 733b2c627e5aec39cb33cc22373bdce33053ef2c (tag v1.19.0)
// 说明：该模块 `packages/core/src/util/token.ts` 无任何 import，可独立执行；
//       它是 v1 出货代码 `packages/opencode/src/util/token.ts` 的再导出目标。

import { estimate } from "/Users/junjielong/workspace/agent-context-research/workbuddy-sources/opencode-v1/packages/core/src/util/token.ts"

const ascii100 = "a".repeat(100)
const cjk = "你好世界" // 4 个 UTF-16 字符，UTF-8 共 12 字节

// 正向判据（应全部为 true）
const positive: [string, boolean][] = [
  ["estimate(100 个 ASCII 字符) === 25", estimate(ascii100) === 25],
  ["estimate('你好世界') === 1（按字符数 4/4，而非字节 12/4=3）", estimate(cjk) === 1],
  ["estimate('') === 0", estimate("") === 0],
]

// 负例判据（应判失败，即 false；用于证明判据非恒真）
const negative: [string, boolean][] = [["estimate('ab') === 0（实际为 1，此判据应失败）", estimate("ab") === 0]]

let ok = true
for (const [label, pass] of positive) {
  if (!pass) ok = false
  console.log(`${pass ? "PASS" : "FAIL"}  ${label}`)
}
for (const [label, pass] of negative) {
  // 负例必须为 false 才说明判据不是"永远通过"
  const behaved = pass === false
  if (!behaved) ok = false
  console.log(`${behaved ? "PASS" : "FAIL"}  负例按预期失败: ${label}（实测 ${pass}）`)
}

console.log(
  JSON.stringify({
    fn: "estimate",
    source: "packages/core/src/util/token.ts:3-5",
    charsPerToken: 4,
    ascii100: estimate(ascii100),
    cjk4: estimate(cjk),
    cjk4_bytes: Buffer.byteLength(cjk, "utf-8"),
    empty: estimate(""),
    ab: estimate("ab"),
  }),
)

process.exit(ok ? 0 : 1)
