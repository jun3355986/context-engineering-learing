// OBS-dsh-meter-01: 出货代码函数级真实执行（只读快照，不修改）
// 目标：验证 token-meter 固定启发式的真实数值（4 字符/token + block/role 开销）
// 判据：退出码（0=全部符合预期；1=有偏差）；含负例脚本 obs-meter-negative.ts
// 快照：571902028a75c64c1d767f4ae5fd099485f0ddf0
import { estimateMessage, estimateToolsTokens, ROLE_OVERHEAD } from '/Users/junjielong/workspace/agent-context-research/workbuddy-sources/deepseek-harness/packages/llm/token-meter/src/estimate.ts'

type AnyMsg = Parameters<typeof estimateMessage>[0]
const msg = (role: string, text: string) => ({ role, content: [{ type: 'text', text }] }) as unknown as AnyMsg

const cases: Array<[string, number, number]> = [
  ['user 400 ASCII 字符', estimateMessage(msg('user', 'a'.repeat(400))), 108],
  ['user 400 汉字', estimateMessage(msg('user', '中'.repeat(400))), 108],
  ['system 400 ASCII 字符', estimateMessage(msg('system', 'a'.repeat(400))), 104],
  ['estimateToolsTokens(undefined)', estimateToolsTokens(undefined), 0],
]

let failed = 0
console.log('ROLE_OVERHEAD =', ROLE_OVERHEAD)
for (const [name, got, want] of cases) {
  const ok = got === want
  if (!ok) failed += 1
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}: got=${got} want=${want}`)
}
console.log(failed === 0 ? 'RESULT: ALL PASS' : `RESULT: ${failed} FAILED`)
process.exit(failed === 0 ? 0 : 1)
