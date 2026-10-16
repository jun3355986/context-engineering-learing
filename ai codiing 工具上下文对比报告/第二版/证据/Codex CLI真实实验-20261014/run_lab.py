#!/usr/bin/env python3
"""Bounded live Codex CLI app-server experiments. No credentials are copied/logged."""
import argparse,asyncio,datetime,hashlib,json,os,re,subprocess,time,signal
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MODEL=os.environ.get('CODEX_LAB_MODEL','gpt-5.6-sol')
RUNTIME=Path(os.environ['CODEX_LAB_HOME']).expanduser().resolve() if os.environ.get('CODEX_LAB_HOME') else None

def clean_env(home):
 e=os.environ.copy();e['CODEX_HOME']=str(home)
 for k in ['OPENAI_API_KEY','CODEX_API_KEY','OPENAI_BASE_URL','CODEX_ACCESS_TOKEN']:e.pop(k,None)
 e['RUST_LOG']='warn'
 return e

def safe(value):
 if isinstance(value,dict):return {k:safe(v) for k,v in value.items() if k.lower() not in ['access_token','refresh_token','authorization','api_key','encrypted_content']}
 if isinstance(value,list):return [safe(x) for x in value]
 if isinstance(value,str):return re.sub(r'\b(sk-[A-Za-z0-9_-]{12,}|eyJ[A-Za-z0-9_.-]{30,})\b','[REDACTED]',value)
 return value

class Client:
 def __init__(self,home,artifacts):self.home=home;self.artifacts=artifacts;self.messages=[];self.pending={};self.next_id=0;self.new=asyncio.Event();self.errors=[]
 async def start(self):
  self.artifacts.mkdir(parents=True,exist_ok=True)
  self.proc=await asyncio.create_subprocess_exec('codex','app-server','--stdio','--strict-config',env=clean_env(self.home),start_new_session=True,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,limit=2*1024*1024)
  self.log=(self.artifacts/'events.jsonl').open('w');self.err=(self.artifacts/'stderr.txt').open('w')
  self.reader=asyncio.create_task(self.read());self.stderr=asyncio.create_task(self.read_stderr())
  self.initialized=await self.call('initialize',{'clientInfo':{'name':'context_lab','title':'Context learning lab','version':'20261014'},'capabilities':{'experimentalApi':True}})
  await self.send({'method':'initialized'})
 async def read(self):
  while line:=await self.proc.stdout.readline():
   try:m=json.loads(line)
   except:continue
   record={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'message':safe(m)};self.log.write(json.dumps(record,ensure_ascii=False)+'\n');self.log.flush();self.messages.append(record)
   if 'id' in m and ('result' in m or 'error' in m):
    f=self.pending.pop(str(m['id']),None)
    if f and not f.done():f.set_result(m)
   elif 'id' in m and 'method' in m:
    # No model approval or dynamic tool requests should be needed by this read-only lab.
    await self.send({'id':m['id'],'error':{'code':-32601,'message':'No approvals or dynamic tools in this bounded lab'}})
   if m.get('method')=='error':self.errors.append(safe(m.get('params')))
   self.new.set()
 async def read_stderr(self):
  while line:=await self.proc.stderr.readline():self.err.write(safe(line.decode(errors='replace')));self.err.flush()
 async def send(self,m):
  self.log.write(json.dumps({'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'direction':'send','message':safe(m)},ensure_ascii=False)+'\n');self.log.flush()
  self.proc.stdin.write((json.dumps(m,ensure_ascii=False)+'\n').encode());await self.proc.stdin.drain()
 async def call(self,method,params,timeout=45):
  self.next_id+=1;i=self.next_id;f=asyncio.get_running_loop().create_future();self.pending[str(i)]=f
  await self.send({'id':i,'method':method,'params':params})
  m=await asyncio.wait_for(f,timeout)
  if 'error' in m:raise RuntimeError(json.dumps(m['error'],ensure_ascii=False))
  return m['result']
 async def wait_turn(self,thread,start,timeout=180):
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   for r in self.messages[start:]:
    m=r['message'];p=m.get('params',{})
    if m.get('method')=='turn/completed' and p.get('threadId')==thread:return p['turn']
   self.new.clear()
   await asyncio.wait_for(self.new.wait(),max(.1,deadline-time.monotonic()))
  raise TimeoutError('turn deadline')
 async def turn(self,thread,text):
  start=len(self.messages);res=await self.call('turn/start',{'threadId':thread,'effort':'low','input':[{'type':'text','text':text}]});done=await self.wait_turn(thread,start)
  segment=self.messages[start:]
  usages=[r['message']['params']['tokenUsage'] for r in segment if r['message'].get('method')=='thread/tokenUsage/updated']
  items=[r['message']['params'].get('item',{}) for r in segment if r['message'].get('method')=='item/completed']
  info={'turn':safe(done),'usage':usages,'items':safe(items),'events_count':len(segment)}
  print('turn',done.get('status'),'last',usages[-1].get('last') if usages else None,'items',[x.get('type') for x in items],flush=True)
  return info
 async def close(self):
  if self.proc.returncode is None:
   self.proc.stdin.close()
   try:await asyncio.wait_for(self.proc.wait(),3)
   except asyncio.TimeoutError:os.killpg(self.proc.pid,signal.SIGTERM)
  try:await asyncio.wait_for(self.proc.wait(),5)
  except asyncio.TimeoutError:os.killpg(self.proc.pid,signal.SIGKILL);await self.proc.wait()
  try:await asyncio.wait_for(asyncio.gather(self.reader,self.stderr,return_exceptions=True),5)
  except asyncio.TimeoutError:
   try:os.killpg(self.proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
  self.log.close();self.err.close()

async def run(mode):
 if RUNTIME is None or not (RUNTIME/'.context-lab-runtime').is_file():
  raise SystemExit('请先设置 CODEX_LAB_HOME 并运行 setup_runtime.py；不使用个人全局目录。')
 home=RUNTIME;out=ROOT/'artifacts'/mode;client=Client(home,out);await client.start();result={'mode':mode,'cli_version':subprocess.check_output(['codex','--version'],text=True).strip(),'model':MODEL,'runs':[]}
 try:
  configs={'model_context_window':100000,'model_auto_compact_token_limit_scope':'total','model_auto_compact_token_limit':22000 if mode=='automatic' else 90000,'tool_output_token_limit':256 if mode=='truncation-config' else 10000,'model_reasoning_effort':'low','check_for_update_on_startup':False}
  start=await client.call('thread/start',{'cwd':str(ROOT/'workspace'),'model':MODEL,'approvalPolicy':'never','sandbox':'read-only','ephemeral':False,'historyMode':'legacy','config':configs,'threadSource':'cli'})
  thread=start['thread']['id'];result['start']=safe(start);result['requested_config']=configs
  print('thread',mode,thread,'model',start.get('model'),'instructions',start.get('instructionSources'),flush=True)
  if mode=='cache':
   prompts=['不要使用工具。请记住这项任务硬约束：RETURN_BY=16:00、BUDGET_CNY=1280、MEETING_POINT=东门。只输出包含这三项的JSON，不要其它文字。','不要使用工具。重述本任务的三项硬约束，仍只输出JSON。','不要使用工具。再核对一次三项硬约束，只输出JSON。']
  elif mode=='automatic':
   prompts=['这是自动压缩复现实验。硬约束RETURN_BY=16:00、BUDGET_CNY=1280、MEETING_POINT=东门。严格依次使用shell读取context-A.txt、context-B.txt、context-C.txt，每次只读取一个文件并等待结果，不能合并命令、不能使用并行工具。每次用cat完整输出，若工具支持max_output_tokens，设为6500。不得写文件、不得读取其它资料。读完三份后给出简短JSON：read_files、三项硬约束、三个TAIL标记。只根据结果判断；如果程序整理上下文，请继续尚未完成的步骤，不重做已完成读取。']
  else:
   limit=128 if mode=='truncation-call' else 60000
   prompts=[f'这是工具输出裁剪复现实验。只用一次shell工具执行 cat long-output.txt，必须设置max_output_tokens={limit}（若当前工具不支持此参数，明确报告）。不能读取其它文件，不得使用grep或定点重读，不得猜测。工具返回后只输出JSON：head_marker、middle_marker、tail_marker、saw_truncation_marker。只填写本次工具结果中实际看到的完整标记；看不到的写UNKNOWN。']
  for prompt in prompts:
   info=await client.turn(thread,prompt);result['runs'].append(info)
   if info['turn'].get('status')!='completed':break
  result['read']=safe(await client.call('thread/read',{'threadId':thread,'includeTurns':True}))
  (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
  thread_path=start['thread'].get('path')
  if thread_path:
   path=Path(thread_path)
   if path.is_file() and path.is_relative_to(home):
    (out/'rollout.jsonl').write_text(''.join(json.dumps(safe(json.loads(line)),ensure_ascii=False)+'\n' for line in path.read_text().splitlines() if line.strip()))
    print('rollout captured',path.name,flush=True)
  print('done',mode,flush=True)
  if any(r['turn'].get('status')!='completed' for r in result['runs']):
   raise RuntimeError('至少一个模型任务未完成；请按 results.json 判读，不能算实验通过。')
 except Exception as e:
  result['runner_error']=str(e);(out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('runner error:',str(e),flush=True);raise SystemExit(1)
 finally:await client.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['cache','automatic','truncation-call','truncation-config']);a=p.parse_args();asyncio.run(run(a.mode))
