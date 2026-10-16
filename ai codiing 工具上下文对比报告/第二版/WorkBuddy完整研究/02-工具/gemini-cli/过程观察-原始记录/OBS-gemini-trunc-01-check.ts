/**
 * OBS-gemini-trunc-01 · 函数级真实执行检查器（正向）
 *
 * 目的：对 **官方已发布快照** 的出货源码做**函数级真实执行**（只读导入，不修改快照），
 *       验证 Gemini CLI 的"单条工具输出治理"与"token 本地估算"链路里**出货常量与公式**是否与源码一致。
 *
 * 运行：bun run OBS-gemini-trunc-01-check.ts
 * 判据：全部断言通过 → 打印 "ALL PASS" 且退出码 0；任一断言失败 → 打印 FAIL 明细且退出码 1。
 *
 * 快照：workbuddy-sources/gemini-cli/ @ 42c51822084ac25cd5d97ac0023822c5235f88c8
 * 说明：只读导入快照 `.ts`（bun 直接执行 TS，无需 node_modules）；不改动快照。
 *       期望值**由源码常量/公式独立推导**（注释给出推导），非从运行结果反填。
 * 不能证明：本观察**不**证明产品端到端行为（未安装 `gemini`、未调用真实模型、未跑压缩/恢复流程）。
 */

import {
  MIN_TARGET_TOKENS,
  MIN_CHARS_FOR_TRUNCATION,
  TEXT_TRUNCATION_PREFIX,
  TOOL_TRUNCATION_PREFIX,
  estimateCharsFromTokens,
  truncateProportionally,
  normalizeFunctionResponse,
} from '/Users/junjielong/workspace/agent-context-research/workbuddy-sources/gemini-cli/packages/core/src/context/truncation.ts';
import {
  ASCII_TOKENS_PER_CHAR,
  NON_ASCII_TOKENS_PER_CHAR,
  estimateTokenCountSync,
} from '/Users/junjielong/workspace/agent-context-research/workbuddy-sources/gemini-cli/packages/core/src/utils/tokenCalculation.ts';
import {
  DEFAULT_TOKEN_LIMIT,
  GEMMA_4_TOKEN_LIMIT,
  tokenLimit,
} from '/Users/junjielong/workspace/agent-context-research/workbuddy-sources/gemini-cli/packages/core/src/core/tokenLimits.ts';

let failures = 0;
function check(name: string, actual: unknown, expected: unknown): void {
  const ok = actual === expected;
  if (!ok) failures++;
  console.log(
    `${ok ? 'PASS' : 'FAIL'} | ${name} | actual=${JSON.stringify(actual)} expected=${JSON.stringify(expected)}`,
  );
}

console.log('=== A. truncation.ts 出货常量（源码常量）===');
// 源码 truncation.ts:14-19
check('MIN_TARGET_TOKENS', MIN_TARGET_TOKENS, 10);
check('MIN_CHARS_FOR_TRUNCATION', MIN_CHARS_FOR_TRUNCATION, 100);
check(
  'TEXT_TRUNCATION_PREFIX',
  TEXT_TRUNCATION_PREFIX,
  '[Message Normalized: Exceeded size limit]',
);
check(
  'TOOL_TRUNCATION_PREFIX',
  TOOL_TRUNCATION_PREFIX,
  '[Message Normalized: Tool output exceeded size limit]',
);

console.log('=== B. tokenCalculation.ts 出货常量与估算公式 ===');
// 源码 tokenCalculation.ts:14-19
check('ASCII_TOKENS_PER_CHAR', ASCII_TOKENS_PER_CHAR, 0.33);
check('NON_ASCII_TOKENS_PER_CHAR', NON_ASCII_TOKENS_PER_CHAR, 1.5);
// 默认 charsPerToken=4 → ascii 每字符 1/4=0.25；floor 结尾（tokenCalculation.ts:40-57,120-147）
check('est([a*100])', estimateTokenCountSync([{ text: 'a'.repeat(100) }]), 25); // 100*0.25=25
check('est([中*4])', estimateTokenCountSync([{ text: '中'.repeat(4) }]), 6); // 4*1.5=6
check('est([])', estimateTokenCountSync([{ text: '' }]), 0);
check('est([ab]) 边界<1', estimateTokenCountSync([{ text: 'ab' }]), 0); // floor(2*0.25)=floor(0.5)=0

console.log('=== C. tokenLimits.ts 出货常量 ===');
// 源码 tokenLimits.ts:20-39
check('DEFAULT_TOKEN_LIMIT', DEFAULT_TOKEN_LIMIT, 1048576);
check('GEMMA_4_TOKEN_LIMIT', GEMMA_4_TOKEN_LIMIT, 256000);
check('tokenLimit(gemini-2.5-pro)', tokenLimit('gemini-2.5-pro'), 1048576);
check('tokenLimit(gemma-4-31b-it 未知→默认)', tokenLimit('__unknown__'), 1048576);

console.log('=== D. estimateCharsFromTokens 公式（truncation.ts:26-49）===');
// 全 ASCII：avg=0.33 → floor(250/0.33)=757
check('chars(ascii1000,250t)', estimateCharsFromTokens('a'.repeat(1000), 250), 757);
// 全 CJK：avg=1.5 → floor(300/1.5)=200（整除，无浮点歧义）
check('chars(cjk1000,300t)', estimateCharsFromTokens('中'.repeat(1000), 300), 200);
check('chars(empty,100)', estimateCharsFromTokens('', 100), 0);

console.log('=== E. truncateProportionally 头尾比例 + 边界（truncation.ts:55-75）===');
const s = 'ABCDEFGHIJ'.repeat(10); // 100 chars
const out = truncateProportionally(s, 50, '[P]', 0.2);
// overhead=3+5+1=9; available=41; head=floor(41*0.2)=8; tail=41-8=33; 总长=3+1+8+5+33=50
check('len(out)', out.length, 50);
check('out startsWith [P]\\n', out.startsWith('[P]\n'), true);
check('out includes \\n...\\n', out.includes('\n...\n'), true);
check('head preserved(8)', out.slice(4, 12), s.slice(0, 8));
check('tail preserved(33)', out.slice(-33), s.slice(-33));
check('omitted chars', s.length - 8 - 33, 59);
// 边界①：不到线（str.length <= targetChars）原样返回
check('under-target unchanged', truncateProportionally('short', 50, '[P]'), 'short');
// 边界②：availableChars<=0 → 仅返回 prefix（truncation.ts:67-69）
check('tiny target → prefix only', truncateProportionally(s, 5, '[P]'), '[P]');

console.log('=== F. normalizeFunctionResponse 小值不动 / 大值截断（truncation.ts:81-142）===');
const smallPart = {
  functionResponse: { name: 'read_file', response: { output: 'x'.repeat(50) } },
};
check(
  'small(<100) unchanged',
  normalizeFunctionResponse(smallPart as never, 0.5) === (smallPart as never),
  true,
);
const bigPart = {
  functionResponse: { name: 'read_file', response: { output: 'y'.repeat(5000) } },
};
const bigOut = normalizeFunctionResponse(bigPart as never, 0.5, 0.2, '/tmp/full.txt');
const bigText = (bigOut.functionResponse as { response: { output: string } })
  .response.output;
check('big truncated contains prefix', bigText.includes(TOOL_TRUNCATION_PREFIX), true);
check('big truncated contains saved path', bigText.includes('Full output saved to: /tmp/full.txt'), true);
check('big shorter than original', bigText.length < 5000, true);

console.log('=== G. 派生：自动压缩触发线（源码常量 + 官方 settings 默认）===');
// chatCompressionService.ts:45 DEFAULT_COMPRESSION_TOKEN_THRESHOLD=0.5（源码常量，未能导入，见证据卡 gemini-trigger-02）
// 官方 settings 默认 model.compressionThreshold=0.5（docs/cli/settings.md:107）
// 触发线 = 0.5 × tokenLimit(model)；1M 窗口 → 524,288
check('threshold(1M)=0.5*1048576', Math.floor(0.5 * tokenLimit('gemini-2.5-pro')), 524288);

console.log('');
if (failures === 0) {
  console.log('ALL PASS');
  process.exit(0);
} else {
  console.log(`FAILED: ${failures} assertion(s)`);
  process.exit(1);
}
