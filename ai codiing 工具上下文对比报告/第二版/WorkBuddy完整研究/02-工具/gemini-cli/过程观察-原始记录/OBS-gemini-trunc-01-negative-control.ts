/**
 * OBS-gemini-trunc-01 · 负例对照（negative control）
 *
 * 目的：证明**判据本身能报错**（防"退出码恒 0、看着通过"陷阱）。
 *       本脚本故意断言**错误的**期望值，运行后**必须 FAIL 且退出码为 1**。
 *       若本脚本退出码为 0，说明检查器判据失效，OBS-gemini-trunc-01 的正向结果不可信。
 *
 * 运行：bun run OBS-gemini-trunc-01-negative-control.ts
 * 预期：打印 FAIL 明细，退出码 1。
 *
 * 快照：workbuddy-sources/gemini-cli/ @ 42c51822084ac25cd5d97ac0023822c5235f88c8（只读导入）
 */

import { estimateTokenCountSync } from '/Users/junjielong/workspace/agent-context-research/workbuddy-sources/gemini-cli/packages/core/src/utils/tokenCalculation.ts';
import { MIN_TARGET_TOKENS } from '/Users/junjielong/workspace/agent-context-research/workbuddy-sources/gemini-cli/packages/core/src/context/truncation.ts';

let failures = 0;
function check(name: string, actual: unknown, expected: unknown): void {
  const ok = actual === expected;
  if (!ok) failures++;
  console.log(
    `${ok ? 'PASS' : 'FAIL'} | ${name} | actual=${JSON.stringify(actual)} expected=${JSON.stringify(expected)}`,
  );
}

// ① 'ab' 实测为 0（floor(2*0.25)=0），这里故意断言为 1 → 应 FAIL
check('负例① est([ab]) 故意断言=1', estimateTokenCountSync([{ text: 'ab' }]), 1);
// ② MIN_TARGET_TOKENS 实测为 10，这里故意断言为 11 → 应 FAIL
check('负例② MIN_TARGET_TOKENS 故意断言=11', MIN_TARGET_TOKENS, 11);

console.log('');
console.log(`负例合计 FAIL 数=${failures}（期望 2）`);
if (failures > 0) {
  console.log('NEGATIVE-CONTROL OK: 判据能报错');
  process.exit(1); // 负例脚本以非零退出表示"判据有效"
} else {
  console.log('NEGATIVE-CONTROL BROKEN: 判据失效');
  process.exit(0);
}
