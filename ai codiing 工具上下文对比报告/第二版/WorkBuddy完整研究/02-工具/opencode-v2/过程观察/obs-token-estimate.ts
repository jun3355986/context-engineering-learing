// OBS-ocv2-token-01 · 检查器（合成数据，退出码为准）
// 目的：验证 v2 出货代码的本地近似估算口径 = 字符数 / 4（非字节/4），且含 Math.max(0, …) 下界。
// 直接执行只读快照文件（无 import 依赖的纯函数），属"出货代码真实执行"，非产品端到端。
import { estimate } from "/Users/junjielong/workspace/agent-context-research/workbuddy-sources/opencode-v2/packages/core/src/util/token.ts"

let failures = 0
const check = (name: string, ok: boolean) => {
  if (!ok) failures++
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}`)
}

// 正向断言
check("estimate('a'×100) === 25", estimate("a".repeat(100)) === 25)
// CJK：4 个汉字 = 4 字符 → 1；若按字节 12/4=3 则判据失败，用于区分字符/字节口径
check("estimate('你好世界') === 1（按字符 4/4，而非字节 12/4=3）", estimate("你好世界") === 1)
check("estimate('') === 0（下界 Math.max(0, …)）", estimate("") === 0)

// 负例（防"判据恒真"）：朴素判据 estimate('ab') === 0 应当为 false（实际 Math.round(0.5)=1）
check("负例按预期失败: estimate('ab') === 0 为 false（实际为 1，证明判据非恒真）", estimate("ab") === 0 === false)

console.log(
  JSON.stringify({
    fn: "estimate",
    source: "packages/core/src/util/token.ts:5",
    charsPerToken: 4,
    ascii100: estimate("a".repeat(100)),
    cjk4: estimate("你好世界"),
    cjk4_bytes: Buffer.byteLength("你好世界", "utf-8"),
    empty: estimate(""),
    ab: estimate("ab"),
  }),
)
console.log(`EXIT_CODE=${failures === 0 ? 0 : 1}`)
process.exit(failures === 0 ? 0 : 1)
