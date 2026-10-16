// OBS-dsh-meter-01 负例：验证判据能报错（应判 FAIL）
// 断言（刻意错误）：CJK 400 汉字 应比 ASCII 400 字符 贵 —— 期望被推翻
// 期望退出码 = 1（若为 0，说明判据恒真/无效，观察作废）
import { estimateMessage } from '/Users/junjielong/workspace/agent-context-research/workbuddy-sources/deepseek-harness/packages/llm/token-meter/src/estimate.ts'

type AnyMsg = Parameters<typeof estimateMessage>[0]
const msg = (text: string) => ({ role: 'user', content: [{ type: 'text', text }] }) as unknown as AnyMsg

const ascii = estimateMessage(msg('a'.repeat(400)))
const cjk = estimateMessage(msg('中'.repeat(400)))
const claim = cjk > ascii // 刻意错误的主张
console.log(`ascii=${ascii} cjk=${cjk} claim(cjk>ascii)=${claim}`)
console.log(claim ? 'NEGATIVE-NOT-DETECTED (判据无效)' : 'NEGATIVE-DETECTED (判据有效：CJK 未更贵)')
process.exit(claim ? 0 : 1)
