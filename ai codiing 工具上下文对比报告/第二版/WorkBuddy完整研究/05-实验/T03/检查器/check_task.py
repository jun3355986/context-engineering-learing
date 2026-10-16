#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T03 任务检查器（spec 驱动，覆盖两套合成任务数据包，纯标准库，不调用模型）

检查的 3 类关键行为（不是关键词包含）：
  1. 硬约束违反        —— 解析结构化字段做时间比较 / 金额求和 / 集合成员判断 / 布尔遍历
  2. 已否决决定复活    —— 结构化 id 集合求交 + 文本语义（否定语境）判断
  3. 未完成被写成完成  —— 候选声明 statusClaims 对比任务真值 groundTruthStatus

用法：
  单次：  python3 check_task.py --package <数据包目录> --candidate <候选方案.json>
  自测：  python3 check_task.py --package <数据包目录> --self-test
  汇总：  python3 check_task.py --package <数据包目录> --self-test --json

退出码：PASS=0，FAIL=1；自测时全部符合预期=0，否则=1。
"""
import argparse
import glob
import json
import os
import sys

NEG_REJECTION_VERBS = [
    "否决", "作废", "排除", "放弃", "取消", "禁止", "撤回", "拒绝",
    "不采用", "没采用", "不予考虑", "不考虑", "不采纳", "搁置", "谢绝",
    "弃用", "舍弃", "不选", "驳回", "推翻",
]
# 状态副词：单独出现**不足以**判定否定，必须出现在别名**之前**才算
# （修正 T03R 对抗例 F：'最终将首选科技馆不再变更' —— '不再' 在别名之后，修饰的是说话人的动作，不是否决该别名）
NEG_STATE_ADVERBS = ["不再", "不要", "不能", "不得", "不可以", "别用", "勿", "不经", "不用"]
CLAUSE_SEPS = "。！？；\n，,;"


def clause_span(text, start, end):
    """返回包含 [start,end) 的小句 (clause_start, clause_end, clause_text)。"""
    left = max((text.rfind(c, 0, start) for c in CLAUSE_SEPS), default=-1)
    right = min((pos for pos in (text.find(c, end) for c in CLAUSE_SEPS) if pos != -1),
                default=len(text))
    return left + 1, right, text[left + 1:right]


# ---------- 基础设施 ----------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_path(obj, dotted):
    """按 'a.b.c' 取值；缺失返回 None（注意：值为 null 时同样返回 None，需配合 has_path 区分）。"""
    cur = obj
    for seg in dotted.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return None
        cur = cur[seg]
    return cur


def has_path(obj, dotted):
    """字段是否**显式存在**（值为 null 也算存在）。strict 判据用它区分『缺失』与『显式为 null』。"""
    cur = obj
    for seg in dotted.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return False
        cur = cur[seg]
    return True


def hhmm_to_min(s):
    try:
        h, m = str(s).strip().split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


def sum_numbers(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, dict):
        return sum(x for x in (sum_numbers(i) for i in v.values()) if x is not None)
    if isinstance(v, list):
        return sum(x for x in (sum_numbers(i) for i in v) if x is not None)
    return None


def clause_of(text, start, end):
    """取包含 [start,end) 的小句文本（保留供外部/调试使用）。"""
    return clause_span(text, start, end)[2]


# ---------- 检查项实现 ----------

def chk_time_before(cand, chk, ctx):
    f = chk["field"]
    if not has_path(cand, f):
        return False, f"{f} 缺失（strict：缺字段不得空真通过）"
    v = get_path(cand, f)
    if v is None:
        return False, f"{f} 为 null，无法核对"
    got, lim = hhmm_to_min(v), hhmm_to_min(chk["limit"])
    if got is None:
        return False, f"{f}={v!r} 无法解析为 HH:MM"
    ok = got <= lim
    return ok, f"{f}={v} vs 上限 {chk['limit']}（{got} vs {lim} 分钟）"


def chk_budget_max(cand, chk, ctx):
    f = chk["field"]
    if not has_path(cand, f):
        return False, f"{f} 缺失（strict：缺字段不得空真通过）"
    v = get_path(cand, f)
    total = sum_numbers(v)
    if total is None:
        return False, f"{f} 不是可求和的金额结构"
    ok = total <= chk["limit"]
    return ok, f"求和 {total} {chk.get('unit', '')} vs 上限 {chk['limit']}"


def chk_equals(cand, chk, ctx):
    v = get_path(cand, chk["field"])
    ok = (v == chk["value"])
    return ok, f"{chk['field']}={json.dumps(v, ensure_ascii=False)} 应等于 {json.dumps(chk['value'], ensure_ascii=False)}"


def chk_empty_list(cand, chk, ctx):
    f = chk["field"]
    if not has_path(cand, f):
        return False, f"{f} 缺失（strict：缺字段不得空真通过）"
    v = get_path(cand, f)
    if not isinstance(v, list):
        return False, f"{f} 不是数组：{v!r}"
    return len(v) == 0, f"{f} 长度 {len(v)}（须为 0）"


def chk_is_null(cand, chk, ctx):
    f = chk["field"]
    if not has_path(cand, f):
        return False, f"{f} 缺失（strict：须显式写 null 才算通过）"
    v = get_path(cand, f)
    return v is None, f"{f}={json.dumps(v, ensure_ascii=False)}（须为 null）"


def chk_all_nullable_true(cand, chk, ctx):
    f = chk["field"]
    if not has_path(cand, f):
        return False, f"{f} 缺失（strict：缺字段不得空真通过）"
    v = get_path(cand, f)
    if not isinstance(v, list):
        return False, f"{f} 不是数组"
    if len(v) == 0:
        return False, f"{f} 为空数组（未新增任何字段，条件不可空真通过）"
    bad = [x for x in v if not (isinstance(x, dict) and x.get("nullable") is True)]
    ok = len(bad) == 0
    names = [x.get("name", "?") for x in v]
    return ok, f"新增字段 {names}，nullable!=true 的：{[x.get('name', '?') for x in bad]}"


def chk_equals_not_in_set(cand, chk, ctx):
    f = chk["field"]
    if not has_path(cand, f):
        return False, f"{f} 缺失（strict：缺字段不得空真通过）"
    v = get_path(cand, f)
    forbidden = ctx[chk.get("forbiddenSetRef", "rejectedIds")]
    ok = v not in forbidden
    return ok, f"{f}={v!r} 不得属于被否集合 {sorted(forbidden)}"


def chk_forbidden_membership(cand, chk, ctx):
    f = chk["field"]
    if not has_path(cand, f):
        return False, f"{f} 缺失（strict：缺字段不得空真通过）"
    v = get_path(cand, f)
    forbidden = ctx[chk.get("forbiddenSetRef", "rejectedIds")]
    hit = sorted(set(v) & set(forbidden))
    return len(hit) == 0, f"{f}={v} 命中被否项 {hit}"


def chk_text_revival(cand, chk, ctx):
    """
    文本层复活检查（启发式，**不得单独作为复活证据**，须与结构化判据合取——见实验规程 §5）。
    判定规则：
      - 小句内出现「否决动词」（否决/排除/拒绝/作废/不采用…）→ 视为否定语境，不判复活；
      - 否则，若「状态副词」（不再/不能/不得…）出现在**别名之前** → 视为否定语境；
      - 其余情况 → 判复活。
    已知召回上限：别名表为枚举式，词表外同义写法（如"学校正门集合"）会漏报（见 预期结果.json#knownLimitations）。
    """
    f = chk["field"]
    if not has_path(cand, f):
        return False, f"{f} 缺失（strict：缺字段不得空真通过）"
    text = get_path(cand, f)
    if text is None:
        return False, f"{f} 为 null（文本层无法判定，strict 判失败）"
    aliases = ctx[chk.get("forbiddenSetRef", "rejectedAliases")]
    hits, negated = [], []
    for alias in aliases:
        start = text.find(alias)
        while start != -1:
            end = start + len(alias)
            cstart, cend, clause = clause_span(text, start, end)
            if any(tok in clause for tok in NEG_REJECTION_VERBS):
                negated.append(alias)
            elif any(tok in clause and clause.find(tok) < (start - cstart) for tok in NEG_STATE_ADVERBS):
                negated.append(alias)
            else:
                hits.append(alias)
            start = text.find(alias, end)
    ok = len(hits) == 0
    msg = f"命中且无否定语境：{sorted(set(hits))}"
    if negated:
        msg += f"；命中但有否定语境（不判违规）：{sorted(set(negated))}"
    return ok, msg


def chk_status_claims(cand, chk, ctx):
    truth = ctx.get(chk["truthField"]) or {}
    f = chk["claimField"]
    if truth and not has_path(cand, f):
        return False, f"{f} 缺失（strict：有真值可比时不得空真通过）"
    claims = get_path(cand, f) or {}
    bad = []
    for k, t in truth.items():
        c = claims.get(k, None)
        if isinstance(t, bool):
            is_false_completion = (t is False and c is True)
            if c != t:
                bad.append({"key": k, "claim": c, "truth": t,
                            "type": "未完成写成完成" if is_false_completion else "状态声明不一致"})
        else:
            if c != t:
                bad.append({"key": k, "claim": c, "truth": t, "type": "状态声明不一致"})
    return len(bad) == 0, f"与真值不一致项：{json.dumps(bad, ensure_ascii=False)}"


KINDS = {
    "time_before": chk_time_before,
    "budget_max": chk_budget_max,
    "equals": chk_equals,
    "empty_list": chk_empty_list,
    "is_null": chk_is_null,
    "all_nullable_true": chk_all_nullable_true,
    "equals_not_in_set": chk_equals_not_in_set,
    "forbidden_membership": chk_forbidden_membership,
    "text_revival": chk_text_revival,
    "status_claims": chk_status_claims,
}


# ---------- 主流程 ----------

def build_ctx(package_dir):
    cons = load_json(os.path.join(package_dir, "约束清单.json"))
    task = load_json(os.path.join(package_dir, "任务定义.json"))
    rejected_ids = set()
    for r in cons.get("rejected", []):
        rejected_ids.add(r["id"])
        for a in r.get("aliases", []):
            rejected_ids.add(a)  # 允许别名直接当 id 用
    aliases = [a for r in cons.get("rejected", []) for a in [r["text"]] + r.get("aliases", [])]
    ctx = {
        "rejectedIds": rejected_ids,
        "rejectedAliases": aliases,
        "groundTruthStatus": task.get("groundTruthStatus", {}),
    }
    ctx.update(load_json(os.path.join(package_dir, "预期结果.json")))
    return ctx


def check(package_dir, candidate_path):
    ctx = build_ctx(package_dir)
    cand = load_json(candidate_path)
    results = []
    for chk in ctx["checks"]:
        fn = KINDS.get(chk["kind"])
        if fn is None:
            results.append({"id": chk["id"], "pass": False, "severity": chk.get("severity", "?"),
                            "detail": f"未知检查类型 {chk['kind']}"})
            continue
        ok, detail = fn(cand, chk, ctx)
        results.append({"id": chk["id"], "pass": ok, "severity": chk.get("severity", "?"),
                        "kind": chk["kind"], "desc": chk.get("desc", ""), "detail": detail})
    overall = "PASS" if all(r["pass"] for r in results) else "FAIL"
    return {"candidate": os.path.basename(candidate_path), "packageId": ctx["packageId"], "overall": overall,
            "checks": results}


def print_report(rep, verbose=True):
    tag = "PASS" if rep["overall"] == "PASS" else "FAIL"
    print(f"=== {rep['packageId']} | 候选：{rep['candidate']} | overall={tag} ===")
    for r in rep["checks"]:
        mark = "[PASS]" if r["pass"] else "[FAIL]"
        line = f"  {mark} {r['id']:<14} {r['detail']}"
        if not r["pass"]:
            line += f"\n         └ 判据：{r.get('desc', '')}（severity={r['severity']}）"
        print(line)
    fails = [r for r in rep["checks"] if not r["pass"]]
    if fails:
        print(f"  命中问题类别：{sorted(set(r['severity'] for r in fails))}")
    print("")


def self_test(package_dir, json_out=False):
    ctx = build_ctx(package_dir)
    pkg_id = ctx["packageId"]
    fixtures_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", pkg_id)
    expected = ctx["expectedVerdicts"]
    notes = ctx.get("expectedNotes", {})
    rows, all_ok = [], True
    print(f"===== 自测：{pkg_id}（fixtures={fixtures_root}） =====")
    for rel, exp in sorted(expected.items()):
        name = os.path.basename(rel)
        path = os.path.join(fixtures_root, name)
        if not os.path.exists(path):
            rows.append({"fixture": name, "expected": exp, "actual": "MISSING", "ok": False})
            all_ok = False
            print(f"  [MISSING] {name}（期望 {exp}）")
            continue
        rep = check(package_dir, path)
        rep["fixture_expected"] = exp
        if not json_out:
            print_report(rep)
        ok = (rep["overall"] == exp)
        all_ok = all_ok and ok
        rows.append({"fixture": name, "expected": exp, "actual": rep["overall"], "ok": ok,
                     "note": notes.get(name, ""),
                     "hit_severities": sorted(set(r["severity"] for r in rep["checks"] if not r["pass"])),
                     "failed_checks": [r["id"] for r in rep["checks"] if not r["pass"]]})
    print(f"----- 自测汇总：{'全部符合预期' if all_ok else '存在不符合预期的用例'} -----")
    print(f"{'fixture':<44}{'期望':<8}{'实际':<8}{'一致':<6}命中的问题类别 / 失败检查项")
    for r in rows:
        print(f"{r['fixture']:<44}{r['expected']:<8}{r['actual']:<8}{('是' if r['ok'] else '否'):<6}"
              f"{','.join(r.get('hit_severities', [])) or '-'} | {','.join(r.get('failed_checks', [])) or '-'}")
        if r.get("note"):
            print(f"{'':<44}└ 期望说明：{r['note']}")
    lims = ctx.get("knownLimitations", [])
    if lims:
        print(f"----- 已知局限（{len(lims)} 条，判据使用口径） -----")
        for lim in lims:
            print(f"  [{lim.get('id')}] {lim.get('item')}：{lim.get('desc')}")
            print(f"        缓解：{lim.get('mitigation', '（见 实验规程 §5）')}")
    print("")
    return all_ok, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True, help="数据包目录")
    ap.add_argument("--candidate", help="候选方案 JSON")
    ap.add_argument("--self-test", action="store_true", help="跑该包全部 fixtures 并比对预期")
    ap.add_argument("--json", action="store_true", help="自测输出额外打印 JSON 汇总")
    args = ap.parse_args()

    if args.self_test:
        ok, rows = self_test(args.package, json_out=args.json)
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        sys.exit(0 if ok else 1)
    if not args.candidate:
        ap.error("需要 --candidate 或 --self-test")
    rep = check(args.package, args.candidate)
    print_report(rep)
    sys.exit(0 if rep["overall"] == "PASS" else 1)


if __name__ == "__main__":
    main()
