#!/usr/bin/env python3
"""Prepare only the explicitly selected lab runtime; never reads credential text."""
import argparse,json,os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description='创建实验专用配置，复用认证软链接；不改个人全局配置。')
parser.add_argument('--cleanup',action='store_true')
args=parser.parse_args()
value=os.environ.get('CODEX_LAB_HOME')
if not value:raise SystemExit('请先 export CODEX_LAB_HOME="$(mktemp -d /tmp/codex-context-lab.XXXXXX)"')
home=Path(value).expanduser().resolve()
source=Path(os.environ.get('CODEX_AUTH_SOURCE_HOME',str(Path.home()/'.codex'))).expanduser().resolve()
if home==source or home==Path.home() or home==ROOT or home.is_relative_to(ROOT):
 raise SystemExit('CODEX_LAB_HOME 必须是公开包与个人 Codex 目录之外的独立临时目录。')
if 'Mobile Documents' in home.parts or 'CloudStorage' in home.parts:
 raise SystemExit('实验运行目录请放在本机临时目录，避免认证链接或会话进入同步公开笔记。')
marker=home/'.context-lab-runtime'
link=home/'auth.json'
if args.cleanup:
 if not marker.is_file():raise SystemExit('没有本脚本标记，不删除此目录内的文件。')
 record=json.loads(marker.read_text())
 if link.is_symlink() and str(link.resolve())==record.get('auth_link_target'):
  link.unlink();print('已移除实验 auth.json 软链接；个人认证原文件未修改。')
 else:print('没有由本脚本创建的认证软链接需要移除。')
 raise SystemExit(0)
home.mkdir(parents=True,exist_ok=True)
if list(home.iterdir()) and not marker.is_file():
 raise SystemExit('CODEX_LAB_HOME 非空且没有实验标记；请选择新临时目录。')
if marker.is_file():
 print('实验运行目录已准备；不覆盖现有实验配置。');raise SystemExit(0)
auth=source/'auth.json'
created_link=False
if auth.is_file():link.symlink_to(auth);created_link=True
# JSON quoted strings are valid TOML basic strings for these paths.
workspace=json.dumps(str(ROOT/'workspace'),ensure_ascii=False)
config='''model = "gpt-5.6-sol"
model_reasoning_effort = "low"
approval_policy = "never"
sandbox_mode = "read-only"
web_search = "disabled"
check_for_update_on_startup = false
[analytics]
enabled = false
[projects.'''+workspace+''']
trust_level = "trusted"
'''
(home/'config.toml').write_text(config)
marker.write_text(json.dumps({'workspace':str(ROOT/'workspace'),'auth_link_target':str(auth) if created_link else None},ensure_ascii=False))
print('独立配置已创建：',home)
print('仅此合成资料目录设为 trusted；sandbox 仍为 read-only。')
print('复用个人认证软链接。' if created_link else '未找到文件认证。请运行 CODEX_HOME="$CODEX_LAB_HOME" codex login，再做预检。')
