#!/usr/bin/env python3
"""Type the actual /compact command into a private Codex TUI PTY."""
import fcntl,json,os,pty,re,select,struct,subprocess,termios,time,signal
from pathlib import Path
from run_lab import ROOT,MODEL,RUNTIME,clean_env,safe

if RUNTIME is None or not (RUNTIME/'.context-lab-runtime').is_file():
 raise SystemExit('请先设置 CODEX_LAB_HOME 并运行 setup_runtime.py。')
cache=json.loads((ROOT/'artifacts/cache/results.json').read_text());thread=cache['start']['thread']['id'];rollout=Path(cache['start']['thread']['path']);
if not rollout.resolve().is_relative_to(RUNTIME):
 raise SystemExit('该 cache 会话不属于当前实验 CODEX_LAB_HOME；请先重新运行 cache。')
out=ROOT/'artifacts/manual-tui';out.mkdir(exist_ok=True)
def rows():
 return [json.loads(x) for x in rollout.read_text().splitlines() if x.strip()]
def checkpoints():return sum(r.get('type')=='compacted' for r in rows())
pre=rows();before_count=checkpoints();snapshot=lambda: ''.join(json.dumps(safe(x),ensure_ascii=False)+'\n' for x in rows())
(out/'before-rollout.jsonl').write_text(snapshot())
# setup_runtime.py records trust for only this synthetic workspace; unexpected prompts abort.
master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,120,0,0))
args=['codex','resume',thread,'--no-alt-screen','-m',MODEL,'-s','read-only','-a','never','--strict-config','-c','model_reasoning_effort="low"','-c','model_context_window=100000','-c','model_auto_compact_token_limit=90000','-c','model_auto_compact_token_limit_scope="total"','-c','check_for_update_on_startup=false']
env=clean_env(RUNTIME);env['TERM']='xterm-256color'
proc=subprocess.Popen(args,cwd=ROOT/'workspace',env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave)
raw=(out/'terminal.raw').open('wb');inputlog=[];began=time.monotonic();buffer=b'';plain=b'';trusted=False;skipped_update=False;sent=False;continued=False;quiet_snapshot=None;after_compact=None;task_before=None;result={'thread_id':thread,'command':args,'before_checkpoints':before_count}
def write(data,label):
 os.write(master,data);inputlog.append({'elapsed_seconds':round(time.monotonic()-began,3),'label':label,'text':data.decode(errors='replace')});print('TUI input:',label,flush=True)
try:
 while time.monotonic()-began<180:
  if select.select([master],[],[],.2)[0]:
   try:b=os.read(master,65536)
   except OSError:break
   if not b:break
   raw.write(b);raw.flush();buffer+=b
   if b'\x1b[6n' in b:os.write(master,b'\x1b[1;1R')
   plain=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',buffer)
   if not trusted and (b'Do you trust' in plain or b'Doyoutrust' in plain or b'Trust this' in plain):
    result['unexpected_trust_prompt']=True
    break
   if b'Update available' in plain or b'Updateavailable' in plain:
    result['unexpected_update_prompt']=True
    break
  elapsed=time.monotonic()-began
  if proc.poll() is not None:break
  if not sent and elapsed>8 and (b'context left' in plain or (MODEL.encode() in plain and b'/model to change' in plain)):
   write(b'/compact','type literal /compact');time.sleep(1);write(b'\r','submit literal /compact');sent=True;result['compact_input_elapsed']=round(elapsed,3)
  if sent and after_compact is None and checkpoints()>before_count:
   after_compact=time.monotonic();result['after_checkpoints']=checkpoints();(out/'after-compact-rollout.jsonl').write_text(snapshot());quiet_snapshot=rows();print('TUI compaction checkpoint installed',flush=True)
  if after_compact is not None and not continued and time.monotonic()-after_compact>6:
   quiet_now=rows();result['quiet_seconds']=6;result['quiet_record_growth']=len(quiet_now)-len(quiet_snapshot)
   result['quiet_user_message_count']=sum(r.get('type')=='event_msg' and r.get('payload',{}).get('type')=='user_message' for r in quiet_now[len(quiet_snapshot):])
   (out/'quiet-rollout.jsonl').write_text(snapshot());task_before=sum(r.get('type')=='event_msg' and r.get('payload',{}).get('type')=='task_complete' for r in quiet_now)
   write('不要使用工具。请从刚才整理后的上下文核对 RETURN_BY、BUDGET_CNY、MEETING_POINT，输出这三项的JSON。'.encode(),'type explicit new user continuation');time.sleep(1);write(b'\r','submit explicit new user continuation');continued=True
  if continued:
   now=rows();finished=sum(r.get('type')=='event_msg' and r.get('payload',{}).get('type')=='task_complete' for r in now)
   if finished>task_before:
    result['continuation_completed']=True;(out/'after-continuation-rollout.jsonl').write_text(snapshot());print('TUI new user turn completed',flush=True);break
 if after_compact is None:result['status']='no_compaction_checkpoint'
 elif not result.get('continuation_completed'):result['status']='compacted_continuation_incomplete'
 else:result['status']='completed'
 result['inputs']=inputlog;result['elapsed_seconds']=round(time.monotonic()-began,3);result['exit_before_cleanup']=proc.poll()
finally:
 if proc.poll() is None:
  try:write(b'\x03','close lab TUI');time.sleep(.2);write(b'\x03','close lab TUI again');proc.wait(timeout=3)
  except Exception:
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=3)
 raw.close();os.close(master);(out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out/'terminal-readable.txt').write_text(re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',buffer.decode(errors='replace')))
 print(json.dumps({'status':result['status'],'checkpoints':result.get('after_checkpoints'),'quiet_growth':result.get('quiet_record_growth'),'elapsed_seconds':result['elapsed_seconds']},ensure_ascii=False),flush=True)
