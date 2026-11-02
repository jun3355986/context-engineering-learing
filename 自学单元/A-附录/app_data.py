# 附录用的数据：Codex / Claude Code 两列（按第四版已核对的事实写）、术语、Codex 参数、Claude Code 参数
# 每个单元格是 (HTML 文本, 等级 'h'|'m'|'l', 依据说明 HTML)

CH_FILE = {
    2: "02-一次请求里装了什么.html",
    3: "03-命令输出几万行.html",
    4: "04-压缩之后还记得什么.html",
    5: "05-缓存省的是什么.html",
    6: "06-工具多了会怎样.html",
    7: "07-子代理省了什么.html",
    8: "08-回退分叉恢复.html",
    9: "09-新会话怎么记得我.html",
    10: "10-窗口满了会怎样.html",
    11: "11-怎么证明更好.html",
    12: "12-给场景设计策略.html",
}


def ch(n, anchor=""):
    return '<a href="%s%s">第 %d 章</a>' % (CH_FILE[n], anchor, n)


# 16 类的新顺序（按第四版章节），数字是第三版总表里的行序号 0–15
ORDER = [0, 1, 3, 5, 6, 7, 4, 12, 2, 9, 10, 11, 13, 15, 14, 8]

# 每类的第四版名字、哪章讲、一句话白话
CATS = {
    0: ("请求组装", "请求里装了什么、按什么顺序放", [2]),
    1: ("规则文件", "项目里写给 agent 的长期指令怎么找、怎么合并、有没有上限", [2]),
    3: ("会话中途的变化", "会话进行中，设置、环境、规则变了，请求里怎么跟上", [2]),
    5: ("单次工具输出", "一条命令输出特别长时，进请求之前怎么截", [3]),
    6: ("旧工具输出的清理", "不调模型，直接把旧的工具输出换成占位符或删掉", [3]),
    7: ("压缩", "窗口快满时，把旧历史写成摘要", [4]),
    4: ("token 计量", "怎么知道用了多少、离窗口还有多远", [4, 10]),
    12: ("缓存", "请求开头不变的部分怎么让服务器复用", [5]),
    2: ("工具按需加载", "工具定义不全放进请求，用到再找", [6]),
    9: ("子代理", "把一部分活派给另一个会话，窗口里留什么", [7]),
    10: ("回退、分叉、恢复", "会话记录怎么存，怎么撤销和接着聊", [8]),
    11: ("跨会话记忆", "新开一个会话，怎么还记得以前的事", [9]),
    13: ("窗口满了之后", "请求超窗、压缩也失败时怎么办", [10]),
    15: ("评估和可观测", "怎么量出一种做法好不好", [11]),
    14: ("扩展点", "钩子、插件能改上下文管理的哪一步", [4]),
    8: ("多模态", "图片怎么进上下文、怎么省", []),
}

# Codex 和 Claude Code 两列：键是第三版行序号；没有键的类别沿用第三版（待核实）
CODEX = {
    0: ("gpt-6.1-sol（思考级别 low）：没有 <code>instructions</code> 字段、没有顶层 <code>tools</code>；<code>input</code> 7 条：工具定义 → 系统提示词 → 技能目录和权限 → 子代理说明 → 子代理开关 → AGENTS.md 和环境信息 → 你的话。gpt-5.5（low）：9 个工具放在顶层 <code>tools</code>，<code>input</code> 4 条。没有 system 角色。", "h", [2]),
    1: ("<code>AGENTS.md</code>：项目根（缺省以 <code>.git</code> 为标记）到当前目录每级取一份，<code>AGENTS.override.md</code> 优先；全局 <code>~/.codex/AGENTS.md</code> 排最前；项目文件合计 32,768 字节，尾部静默截断；文件里的 <code>@</code> 不展开。", "h", [2]),
    3: ("会话设置（权限、协作模式、子代理、AGENTS.md、环境信息）按状态比较：没变不加，变了在末尾追加，不改前面。全局 AGENTS.md 每次请求前重读，项目 AGENTS.md 一个会话读一次（这两条只读了源码和自带测试）；<code>resume</code> 接旧线程时和存档基线比，不同就追加（实验）。", "m", [2, 8]),
    5: ("最多四道闸，取最紧的：进程缓冲 1 MiB（头尾各 512 KiB）→ <code>exec_command</code> 缺省 10,000 token → <code>exec</code> 缺省 10,000 token（只有 gpt-6.1-sol）→ 写入历史按 12,000 token（基数 10,000 × 1.2）。截法是头尾各留一半；被截掉的原文哪里都不存。", "h", [3]),
    6: ("没找到清理旧工具输出的机制（搜索源码，未穷尽）；一条约 1.2 万 token 的输出，之后每次请求都重发。", "m", [3]),
    7: ("压缩线 = min(<code>model_auto_compact_token_limit</code>, 窗口 × 90%)。OpenAI 官方通道走远端压缩（服务器回加密摘要，保留 64,000 token；只读了源码），其他通道走本地压缩（保留你亲手发的消息，预算 20,000 token，加一段摘要）。<code>/compact</code> 不带参数。", "h", [4]),
    4: ("用量 = 上次服务器报的 <code>total_tokens</code> + 之后新增条目的估算（UTF-8 字节 ÷ 4 向上取整，是本地估算，不是真实分词）。有效窗口 = 窗口 × 95%（gpt-6.1-sol：272,000 → 258,400）。", "h", [4, 10]),
    12: ("OpenAI 文档（2026-11-02）：GPT-5.6 及之后缺省缓存。Codex 的 <code>prompt_cache_key</code> = 会话 id，不传 <code>prompt_cache_options</code>；WebSocket 下同进程只发新增条目；换模型、关工具时追加说明而不改前缀。真实命中率没测。", "h", [5]),
    2: ("MCP 工具按模型表 <code>supports_search_tool</code> 登记：true 延后，false 直连。延后时 gpt-5.5 用顶层 <code>tool_search</code> 找，gpt-6.1-sol 在 <code>exec</code> 脚本里过滤 <code>ALL_TOOLS</code>。接 30 个 MCP 工具，gpt-6.1-sol 的请求逐字不变。", "h", [6]),
    9: ("gpt-6.1-sol（V2）请求里固定多 8,514 字节子代理相关内容；<code>fork_turns</code> 缺省 <code>all</code>，子代理带走父的全部历史；最终回答整份回到父会话，无上限；总数缺省 4（含 root），层数不限。gpt-5.5（V1）缺省不带历史。", "h", [7]),
    10: ("每个会话一个 <code>.jsonl</code> 存档，只追加。回退（TUI 里 Esc 两下）= 另存新文件并换指针，旧文件不动，不还原你的文件；分叉（<code>/fork</code>）= 新线程引用旧前缀；恢复时 AGENTS.md 与存档基线比对。压缩可被回退撤销。", "h", [8]),
    11: ("<code>memories</code> 缺省关。打开后后台先用 gpt-5.6-luna（low）提炼旧会话，再用 gpt-5.6-terra（medium）合并成一份摘要，放进新会话的第三条输入；摘要超过 2,500 token 从中间截；一个 <code>CODEX_HOME</code> 一份，不按项目分。", "h", [9]),
    13: ("主请求被拒（流里 <code>response.failed</code> + <code>context_length_exceeded</code>）：只报错，不压缩、不重发。本地压缩请求被拒：从最旧的一条删起再发。HTTP 400 不认。小窗口下每步都压，没有次数上限（搜索，未穷尽）。", "h", [10]),
    15: ("<code>codex-rs/</code> 里没有名字带 eval / bench 的包（只看了目录名），没找到评测框架。存档里每个响应一条 <code>token_usage_record</code>（压缩请求也有），可算请求数、输入、命中、压缩次数；<code>codex exec --json</code> 只有会话累计；<code>--ephemeral</code> 不写存档。", "h", [11]),
    14: ("钩子 <code>PreCompact</code> / <code>PostCompact</code> 只能叫停；压缩后排一次 <code>SessionStart</code>，输出作为额外上下文；<code>compact_prompt</code> 可换本地压缩的提示词，远端压缩不适用。都只读了源码，没实验。", "m", [4]),
    8: ("本版只核对到：本地压缩截短原话时去掉图片（读了源码）。", "m", [4]),
}

CLAUDE = {
    1: ("当前目录及以上每一级的 <code>CLAUDE.md</code> 启动时加载（单个超过 4 MiB 整份跳过）；子目录的在读写那个目录里的文件时才加载，单个文件上限 40,000 字符（20 万 token 窗口）；<code>CLAUDE.md</code> 里写 <code>@路径</code> 导入别的文件，最多 4 跳。", "m", [2]),
    5: ("成功的命令约 30,000 字符内直接给；超过就存成文件，给路径加前 2,000 字符预览。失败的命令约 10,000 字符，超过给头尾摘录。", "m", [3]),
    6: ("文档提到会「清理旧工具结果」并算作预期的缓存重建，没写触发条件和规则。", "m", [5]),
    7: ("压缩后从磁盘重读根目录 <code>CLAUDE.md</code>、不带 <code>paths:</code> 的规则、自动记忆、计划；最近的文件最多重读 5 个（超过 5,000 token 只给路径）；用过的技能每个最多 5,000、合计 25,000 token。<code>/compact focus on …</code> 可指定摘要重点。原生 100 万窗口约在 96.7 万 token 压。", "m", [4]),
    12: ("三层缓存（系统提示词和工具定义 → 项目上下文 → 对话）；缺省存 5 分钟，订阅额度内主对话 1 小时；缓存标记最多 4 个；文档列出会断缓存的操作；<code>/usage</code> 有一行 Prompt cache (main)。", "m", [5]),
    2: ("工具搜索缺省开：开局只载入工具名和服务器 instructions，用到再找。<code>ENABLE_TOOL_SEARCH</code> 取 <code>true</code> / <code>auto</code> / <code>auto:N</code> / <code>false</code>；instructions 和直连工具的描述各截 4,096 字符，搜索加载的描述 16,384 字符。", "m", [6]),
    9: ("缺省空白上下文（fork 除外），Explore 和 Plan 不带 <code>CLAUDE.md</code>；嵌套 3 层，并发 20，累计无上限；在 <code>permissions.deny</code> 里写 <code>Agent(名字)</code> 或 <code>Agent</code> 可关闭。", "m", [7]),
    10: ("<code>/rewind</code> 或 Esc 两下，四种动作（代码和对话 / 只对话 / 只代码 / 摘要）；只追踪编辑工具改的文件，shell 单独改的不追踪；最近 100 个检查点，约 30 天清理。<code>/branch</code>、<code>--fork-session</code> 分叉；<code>--continue</code> / <code>--resume</code> 恢复，压缩过的从最后一次压缩接上。", "m", [8]),
    11: ("自动记忆（auto memory）本地缺省开，模型在会话里当场写到 <code>~/.claude/projects/&lt;project&gt;/memory/</code>；<code>MEMORY.md</code> 前 200 行或 25 KB 开局载入，主题文件按需读；子代理不带（fork 除外）。", "m", [9]),
    13: ("交互里提示 <code>Context limit reached · /compact or /clear to continue</code>；自动压缩先摘要最旧几轮，一整轮都摘要不了时留最新 prompt 原文、其余全摘要；压完又立刻被填满数次，报 <code>Autocompact is thrashing</code> 并停止重试（文档没写次数）。", "m", [10]),
}

# ---------------------------------------------------------------------------
# 参数
# Codex：(配置项, 写在哪, 缺省, 作用, 章, 等级)
CODEX_PARAMS = [
    ("<code>project_doc_max_bytes</code>", "<code>config.toml</code> 顶层", "32,768 字节", "项目 AGENTS.md 合计上限，从尾部截，只写日志", [2], "h"),
    ("<code>tool_output_token_limit</code>", "<code>config.toml</code> 顶层", "不设时取模型表的基数 10,000 token；写入历史时 × 1.2", "写入历史前每条工具输出的上限", [3], "h"),
    ("<code>model_context_window</code>", "<code>config.toml</code> 顶层", "取模型表（gpt-6.1-sol 源码自带表 272,000）", "改窗口大小；实验里设 14,000 看小窗口反复压缩", [10], "h"),
    ("<code>model_auto_compact_token_limit</code>", "<code>config.toml</code> 顶层", "取模型表；压缩线 = min(它, 窗口 × 90%)", "自动压缩的触发线", [4], "h"),
    ("<code>model_post_turn_compact_threshold_percent</code>", "<code>config.toml</code> 顶层", "0（不压）；取值 0–100，超过 100 启动报错", "一轮最终回答之后，用量 ≥ 有效窗口 × 这个百分比就压", [12], "h"),
    ("<code>compact_prompt</code> / <code>experimental_compact_prompt_file</code>", "<code>config.toml</code> 顶层", "内置的 9 行提示词", "换本地压缩的提示词；远端压缩不用", [4], "m"),
    ("<code>effective_context_window_percent</code>", "模型表的字段，不在 <code>config.toml</code> 里", "95", "有效窗口 = 窗口 × 这个百分比", [10], "h"),
    ("<code>stream_max_retries</code>", "通道配置 <code>[model_providers.&lt;名字&gt;]</code>", "5", "流式请求出错后重试次数；被拒的压缩请求也按它重试", [10], "h"),
    ("<code>supports_websockets</code>", "通道配置 <code>[model_providers.&lt;名字&gt;]</code>", "自定义通道只走 HTTP", "设为 <code>true</code> 才走 WebSocket", [5], "h"),
    ("<code>[agents] enabled</code>", "<code>config.toml</code>", "true", "设为 <code>false</code>：三块子代理内容全无，gpt-6.1-sol 的请求少 8,516 字节", [7], "h"),
    ("<code>[agents] max_threads</code>", "<code>config.toml</code>", "V2：总数 4（含 root；设 N 则总数 N+1）；V1：6（只读源码，没实验）", "同时存在的子代理数", [7], "h"),
    ("<code>[features.multi_agent_v2]</code> 下 <code>root_agent_usage_hint_text</code> / <code>multi_agent_mode_hint_text</code>", "<code>config.toml</code>", "使用内置文字（2,575 / 410 字节）", "设为 <code>\"\"</code> 去掉对应那条说明", [7], "h"),
    ("<code>[features] memories</code>", "<code>config.toml</code>", "false", "打开跨会话记忆", [9], "h"),
    ("<code>[memories] use_memories</code> / <code>generate_memories</code>", "<code>config.toml</code>", "都是 true（前提是 <code>memories</code> 已打开）", "是否读记忆 / 是否让新会话被提炼", [9], "h"),
    ("<code>[memories] max_rollout_age_days</code> / <code>min_rollout_idle_hours</code> / <code>max_rollouts_per_startup</code>", "<code>config.toml</code>", "10（0–90）/ 6（1–48）/ 2（1–128）", "只提炼更新时间在 10 天内、已空闲 6 小时以上的旧会话，每次最多取 2 个", [9], "h"),
    ("<code>[memories] max_unused_days</code>", "<code>config.toml</code>", "30（0–365）", "合并时只选最近引用（没引用过则看自己的活动时间）在 30 天内的；过期且上次没用过的，启动时删除", [9], "h"),
    ("<code>[memories] extract_model</code> / <code>consolidation_model</code>", "<code>config.toml</code>", "不设：提炼 gpt-5.6-luna（low），合并 gpt-5.6-terra（medium）", "换提炼、合并用的模型", [9], "h"),
    ("<code>[memories] min_rate_limit_remaining_percent</code>", "<code>config.toml</code>", "25（0–100）", "额度窗口剩余低于它，后台记忆任务不启动（只读源码，没实验）", [9], "m"),
    ("<code>enabled_tools</code> / <code>disabled_tools</code>", "MCP 服务器配置 <code>[mcp_servers.&lt;名字&gt;]</code>", "不设：该服务器全部工具", "只注册这些 / 在其后排除；实验里 10 个工具 → 2 个，定义 3,592 → 930 字节", [6], "h"),
    ("<code>tool_input_schema_max_bytes</code>", "MCP 服务器配置", "5,000 字节（只读了注释）", "单个工具的输入 schema 超过它就压缩", [6], "m"),
    ("<code>default_tools_approval_mode</code>", "MCP 服务器配置", "不设则按批准策略", "实验里设为 <code>\"approve\"</code>，才能直接调没搜过的工具", [6], "h"),
]

# 写死的数：(数, 是什么, 章, 等级)
CODEX_FIXED = [
    ("1 MiB", "进程输出缓冲，头尾各 512 KiB", [3], "h"),
    ("10,000 token", "<code>exec_command</code> 和 <code>exec</code> 的缺省输出上限（模型可以传更大的，写入历史时仍被截回）", [3], "h"),
    ("20,000 token", "本地压缩保留你亲手发的消息的预算，从新到旧", [4], "h"),
    ("64,000 token", "远端压缩保留的预算（别的代理消息单条 ≤ 10,000）；只读源码", [4], "m"),
    ("12,000 token", "界面「X% left」公式里当作固定开头的数；只读源码，没在终端看过", [10], "m"),
    ("1,048,576 字符", "单条用户输入上限（TUI 输入框和 app-server 检查，<code>codex exec</code> 没查）", [10], "h"),
    ("2,500 token", "记忆摘要读路径的上限（字节 ÷ 4），超出从中间截", [9], "h"),
    ("6 小时 / 1 小时", "记忆合并成功后的冷却 / 失败后重试间隔", [9], "h"),
    ("8", "<code>tool_search</code> 一次返回的工具数缺省值（gpt-5.5，模型可传 <code>limit</code>）", [6], "h"),
]

# Claude Code：(参数, 值, 作用, 章)  —— 官方文档 2026-11-02 抓取
CLAUDE_PARAMS = [
    ("<code>CLAUDE.md</code> 里的 <code>@路径</code> 导入", "最多 4 跳", "导入别的文件", [2]),
    ("启动时加载的单个 <code>CLAUDE.md</code>", "超过 4 MiB 整份跳过", "范围是当前目录及以上每一级", [2]),
    ("子目录 <code>CLAUDE.md</code>", "单个文件 40,000 字符（20 万 token 窗口）", "超出只给开头并提示用 Read 工具读剩下的", [2]),
    ("成功命令的输出", "约 30,000 字符内直接给；超过存文件 + 路径 + 前 2,000 字符预览", "失败的命令约 10,000 字符，超过给头尾摘录", [3]),
    ("压缩后重读文件", "最多 5 个最近的；超过 5,000 token 只给路径", "技能正文每个最多 5,000、合计 25,000 token", [4]),
    ("自动压缩的触发", "原生 100 万窗口约 96.7 万 token；其他多数情况到窗口上限", "输入框里 <code>/autocompact 500k</code> 可提前", [4]),
    ("缓存存活", "5 分钟；订阅额度内主对话 1 小时", "设置 <code>promptCacheTtl</code> 可选；缓存标记最多 4 个", [5]),
    ("工具搜索", "缺省开；<code>ENABLE_TOOL_SEARCH</code> = <code>auto</code> 时工具定义低于窗口 10% 直连", "instructions 和直连工具描述各 4,096 字符，搜索加载的 16,384 字符", [6]),
    ("子代理", "嵌套 3 层，并发 20，累计无上限", "<code>permissions.deny</code> 里写 <code>Agent(名字)</code> 关闭", [7]),
    ("<code>/rewind</code> 检查点", "最近 100 个，约 30 天清理", "只追踪编辑工具改的文件", [8]),
    ("自动记忆 <code>MEMORY.md</code>", "开局载入前 200 行或 25 KB", "<code>autoMemoryEnabled</code>、<code>CLAUDE_CODE_DISABLE_AUTO_MEMORY=1</code> 可关", [9]),
    ("请求体", "32 MB 上限，与窗口无关", "报 <code>Request too large</code>", [10]),
]

# Claude Code 非官方源码 v2.1.88 与官方文档的差别（第三版记的）
CLAUDE_CONFLICTS = [
    ("<code>CLAUDE.md</code> 导入跳数", "5 跳", "4 跳", "本版 2026-11-02 重新抓文档核对：4 跳"),
    ("技能列表里单条描述的长度", "250 字符", "1,536 字符处截断", "没重新抓"),
    ("通用工具结果落盘阈值", "50,000 字符（Bash 30,000、Grep 20,000）", "通用 10,000 字符；Bash 30,000", "Bash 的 30,000 本版重新核对一致；通用那项没重新抓"),
    ("图片体积限制", "2000×2000、base64 5 MB", "缩放后超过 500 KB 转 JPEG", "没重新抓"),
]

# ---------------------------------------------------------------------------
# 术语表：分组 -> [(中文, 英文/代码名, 一句话定义, 首次讲解 HTML)]
def C(n, extra=""):
    return ch(n) + extra


TERMS = [
    ("容量与计量", [
        ("token", "token", "模型读写和计价的单位，不等于字或词。Codex 本地估算用「UTF-8 字节数 ÷ 4 向上取整」，不是真实分词。", "第 1 章（待写）；第 2 章起用估算"),
        ("上下文窗口", "context window", "一次请求里输入和输出共享的最大 token 数。gpt-6.1-sol：源码自带表是 272,000。", "第 1 章（待写）；数字见 " + C(4)),
        ("有效窗口", "effective context window", "Codex 实际当作上限的数：窗口 × 95%，gpt-6.1-sol 是 258,400。", C(10)),
        ("压缩线", "auto-compact limit", "用量到这条线就触发压缩：min(<code>model_auto_compact_token_limit</code>, 窗口 × 90%)，gpt-6.1-sol 缺省 244,800。", C(4)),
        ("用量", "usage", "服务器每次响应里报的输入、缓存命中、输出 token 数。Codex 判断要不要压，用「上次报的总数 + 之后新增条目的估算」。", C(4)),
    ]),
    ("一次请求里有什么", [
        ("输入条目", "input item", "Responses 接口里 <code>input</code> 数组的一项：一条消息、一次工具调用、一个工具输出……本书按每条的 <code>json.dumps</code> 字节数算大小。", C(2)),
        ("developer / user", "role", "请求里的两种消息角色：developer 是应用（这里是 Codex）写给模型的指令，user 是来自用户这边的内容。Codex 的请求没有 system 角色。", C(2)),
        ("工具定义", "tool definition", "告诉模型有哪些工具、参数怎么填的说明，也占 token。gpt-6.1-sol 放在 <code>input</code> 第一条，gpt-5.5 放在顶层 <code>tools</code>。", C(2)),
        ("系统提示词", "base instructions", "定义 agent 身份和行为的长指令。gpt-6.1-sol 里是 <code>input</code> 的第二条。", C(2)),
        ("规则文件", "AGENTS.md / CLAUDE.md", "写在项目里、每个会话都要遵守的指令文件：Codex 读 <code>AGENTS.md</code>，Claude Code 读 <code>CLAUDE.md</code>。", C(2)),
        ("技能目录", "skills list", "请求里列出可用技能的一段目录，放在会话配置那一条里，和权限、协作模式在一起。", C(2)),
        ("会话设置的追加", "context update", "每次请求前，Codex 把权限、协作模式、环境信息等和上次比较，没变不加，变了在末尾追加一条，不改前面。", C(2)),
        ("假服务器", "mock server", "本机起的假 Responses 服务器，按剧本回复，用来抓 Codex 发出的请求；不联网、不花额度。所以本书的实验证明「请求里有什么」，不证明「模型答得好不好」。", C(2)),
    ]),
    ("工具和输出", [
        ("截断", "truncation", "超过上限时切掉一部分。Codex 的截法是头尾各留一半，中间换成一行说明。", C(3)),
        ("四道闸", "—", "命令输出到进请求之间最多四处截断：进程缓冲 1 MiB → <code>exec_command</code> → <code>exec</code> → 写入历史；结果取最紧的那道。", C(3)),
        ("代码工具", "<code>exec</code>（code mode）", "gpt-6.1-sol 不直接调命令工具，而是写一段 JavaScript 交给 <code>exec</code> 运行，JS 里再调 <code>exec_command</code> 和别的工具。", C(3)),
        ("存档", "rollout", "<code>~/.codex/sessions/</code> 下每个会话一个 <code>.jsonl</code> 文件，只追加。存的是第四道之前的工具输出文本。", C(3)),
        ("MCP", "Model Context Protocol", "把外部工具接进 agent 的协议。接上的工具，定义进不进请求，由下面的「延后 / 直连」决定。", C(6)),
        ("延后 / 直连", "Deferred / Direct", "MCP 工具的两种登记方式：延后 = 定义不进请求，用到再搜；直连 = 定义直接放进请求。由模型表的 <code>supports_search_tool</code> 决定，true 延后。", C(6)),
        ("工具搜索", "<code>tool_search</code>", "gpt-5.5 用来找延后工具的顶层工具（BM25 搜索）。gpt-6.1-sol 没有它，改在 <code>exec</code> 脚本里过滤 <code>ALL_TOOLS</code>。", C(6)),
    ]),
    ("压缩", [
        ("压缩", "compaction", "让模型把一段历史写成摘要，再用摘要加保留的原话替换原历史。", C(4)),
        ("本地压缩 / 远端压缩", "local / remote compaction", "本地：Codex 自己发一次请求让模型写摘要（自定义通道）。远端：服务器返回加密摘要，保留 64,000 token（OpenAI 官方通道和 Azure）。", C(4)),
        ("原话预算", "—", "本地压缩时保留你亲手发的消息，预算 20,000 token，从新到旧，装不下的截短后停。", C(4)),
        ("摘要", "summary", "模型写的一段文字，带固定前缀，作为用户消息放在新历史末尾。写摘要必然丢信息。", C(4)),
        ("轮末压缩", "post-turn compaction", "一轮的最终回答之后，用量 ≥ 有效窗口 × <code>model_post_turn_compact_threshold_percent</code> 就压；缺省 0 = 不压。", C(12)),
        ("/compact", "—", "输入框里手动压缩的斜杠命令。Codex 的不带参数；Claude Code 的可以写 <code>/compact focus on …</code> 指定重点。", C(4)),
    ]),
    ("缓存", [
        ("前缀", "prefix", "从请求第一个 token 起必须逐字相同的部分；一处不同，后面的都接不上缓存。", C(5)),
        ("前缀缓存", "prompt cache", "服务器复用相同前缀已经算过的结果，命中的部分按更低的价算。省钱和等待，不省窗口。", C(5)),
        ("缓存键", "<code>prompt_cache_key</code>", "Codex 每次请求带的标识，值是会话 id（子代理沿用父的）。", C(5)),
        ("缓存存活时间", "TTL", "缓存保留多久。OpenAI 文档（GPT-5.6 及之后）缺省 30 分钟，Claude Code 缺省 5 分钟、订阅额度内主对话 1 小时。", C(5)),
        ("WebSocket 增量发送", "<code>previous_response_id</code>", "官方通道下，同一进程里后面的请求只发新增条目，不重发整份。", C(5)),
        ("增量工具", "<code>incremental_tools</code>", "换模型、关工具时追加一条说明，不改写前面的内容，保住缓存前缀。", C(5)),
    ]),
    ("子代理", [
        ("子代理", "subagent", "主会话派出去干活的另一个会话；它的最终回答整份回到主会话。", C(7)),
        ("V1 / V2", "multi_agent v1 / v2", "Codex 的两套子代理实现。gpt-6.1-sol 用 V2：请求里多两条说明，子代理缺省带走父的全部历史；gpt-5.5 用 V1。", C(7)),
        ("fork_turns", "<code>fork_turns</code>", "派子代理时带多少父会话的历史：缺省 <code>all</code> 全带，<code>\"none\"</code> 空白开始。", C(7)),
    ]),
    ("会话和记忆", [
        ("线程", "thread", "一个会话的编号，就是存档文件名里那串 UUID。", C(8)),
        ("回退", "revert / rewind", "Codex：撤销最近几轮，另存一个新文件并换指针，不还原你的文件。Claude Code：<code>/rewind</code> 可选连代码一起还原。", C(8)),
        ("分叉", "fork", "从某一轮复制出新线程，原会话不动。", C(8)),
        ("恢复", "resume", "重新打开旧会话接着聊。被回退的轮次不回来；AGENTS.md 与基线比对。", C(8)),
        ("基线", "baseline", "存档里记着的「上次给模型看过的环境状态」（含 AGENTS.md 全文），恢复时拿它和现在比。", C(8)),
        ("检查点", "checkpoint", "Claude Code 在每次编辑前存的文件快照，<code>/rewind</code> 靠它还原。", C(8)),
        ("跨会话记忆", "memories", "Codex 的 <code>memories</code> 功能（缺省关）：后台先提炼旧会话、再合并成一份摘要，新会话开头多塞这份摘要。", C(9)),
        ("提炼 / 合并", "phase 1 / phase 2", "第一阶段：模型把单个旧会话写成一小段；第二阶段：另一个模型把许多小段合并成全局摘要。", C(9)),
        ("引用", "<code>oai-mem-citation</code>", "回答末尾带的标记。Codex 据此给被用到的旧会话记次数，次数决定淘汰。", C(9)),
    ]),
    ("窗口满了和评估", [
        ("超窗", "<code>context_length_exceeded</code>", "请求超出窗口被服务器拒绝。Codex 只认流里 <code>response.failed</code> 带这个 code 的，HTTP 400 不认。", C(10)),
        ("标记已满", "<code>set_total_tokens_full</code>", "主请求被拒后，Codex 把「上次用量」记成 max(有效窗口 − 会话累计用量, 0)；累计已超窗时等于没标。", C(10)),
        ("反复压缩", "thrashing", "固定部分占满窗口时每一步都压缩。Codex 没有次数上限；Claude Code 报 <code>Autocompact is thrashing</code> 后停止重试。", C(10)),
        ("配对对照", "paired A/B", "同一批任务、同一个起点，各跑两个配置，看每个任务上的差，不比两组均值。", C(11)),
        ("不一致率", "discordant rate, d", "两个配置在同一任务上「一个成功一个失败」的占比。它决定要多少任务才分得出两个配置。", C(11)),
        ("符号检验", "sign test", "只数「A 成功 B 失败」和「B 成功 A 失败」各多少，看是不是明显偏向一边。", C(11)),
        ("A/A", "A/A test", "两个完全一样的配置各跑一遍，量一量噪声有多大。", C(11)),
        ("每成功任务成本", "CPS", "总成本 ÷ 成功任务数；失败任务的成本也算进分子。", C(11)),
        ("复现性", "reproducibility", "同一任务重跑，请求里哪些字段会变：UUID、开始时间戳、工具输出里的耗时；工作目录路径和 <code>CODEX_HOME</code> 路径写进请求，换了前缀就在那里断。", C(11)),
    ]),
]

# 其他 agent 的专有名词（第三版记的，待核实）
OTHER_TERMS = [
    ("微压缩", "microcompact", "Claude Code 里只清理旧工具结果、不做摘要的轻量路径；第三版读到的 v2.1.88 源码里缺省关。"),
    ("历史转图", "snapcompact", "oh-my-pi 压缩方法链（remote → snapcompact → handoff → shake → soft，逐级回退）里的一种：把被丢弃的历史渲染成 PNG 交给视觉模型读。"),
    ("机械省略", "shake", "oh-my-pi 压缩方法链里的一种：不调模型，把大块工具结果换成占位符和可恢复的指针。"),
    ("整段替换", "full-replace", "Grok Build 的压缩形态：用一条摘要加保留的尾部，整体替换旧历史。"),
    ("可见面", "surface", "DeepSeek Harness 的术语：日志里进入模型请求的那一层有序视图。"),
    ("代码模式", "Code Mode", "opencode v2：MCP 工具不进工具定义，靠 <code>execute</code> 间接调用。和 Codex 的 <code>exec</code> 是不是同一类做法，本版没核对。"),
]

# 易混词：(词, 区别, 章)
CONFUSABLE = [
    ("窗口 / 有效窗口 / 压缩线", "窗口是模型的总容量（gpt-6.1-sol 源码自带表 272,000）；有效窗口是 Codex 留出 5% 后的上限（258,400，界面「X% left」按它算）；压缩线更早（244,800）。用量到压缩线就压。压缩线和有效窗口之间只剩 13,600 token，约等于一条最大的工具输出。", [4, 10, 12]),
    ("回退 / 分叉 / 恢复", "回退：同一个线程，撤销最近几轮。分叉：新线程，原线程不动。恢复：打开旧线程接着聊，被回退的轮次不回来。三者都不还原你磁盘上的文件（Claude Code 的 <code>/rewind</code> 可选还原编辑工具改过的文件）。", [8]),
    ("存档 / 记忆", "存档：每个会话一个文件，完整、只追加，恢复会话靠它。记忆：后台从旧会话提炼出的一份摘要，新会话开头多塞，缺省关，最多约 1 万字节。", [8, 9]),
    ("截断 / 压缩", "截断改的是一条工具输出，不调模型，原文哪里都不存。压缩改的是整段历史，要调一次模型写摘要。Codex 没有「只清理旧工具输出」这一级（搜索源码，未穷尽）。", [3, 4]),
]
