# T06 过程观察 · 原始记录（合成数据，无真实项目数据）

## 环境探测（只读命令）

```
$ pi --version
1.2.0
$ pi auth check --model deepseek-v4.1-flash --provider opencode-go --json --no-refresh
{"status":"ready","provider":"opencode-go","authType":"api_key"}
```

## 运行 1（默认设置解析）命令与输出
```
$ cd /tmp/pi-t06-obs/proj && pi -p "..." --session-dir /tmp/pi-t06-obs/sessions --mode json
退出码: 1
--- stderr ---
Warning: Invalid settings file /Users/junjielong/.pi/agent/settings.json: EEXIST: file already exists, mkdir '/Users/junjielong/.pi/agent/settings.json.lock'
Credential store read failed for opencode-go: EEXIST: file already exists, mkdir '/Users/junjielong/.pi/agent/auth.json.lock'
--- stdout(raw.jsonl 全部) ---
{"type":"session","version":3,"id":"01a13b39-d500-7433-8bea-6c1102d49b7e","timestamp":"2026-10-14T16:23:28.257Z","cwd":"/private/tmp/pi-t06-obs/proj"}
```

## 运行 2（显式 --provider/--model 绕过默认设置解析）命令与输出
```
$ cd /tmp/pi-t06-obs/proj && pi -p "..." --provider opencode-go --model deepseek-v4.1-flash --session-dir /tmp/pi-t06-obs/sessions --mode json
退出码: 1（stderr 见下）
--- stderr ---
Warning: Invalid settings file /Users/junjielong/.pi/agent/settings.json: EEXIST: file already exists, mkdir '/Users/junjielong/.pi/agent/settings.json.lock'
Credential store read failed for opencode-go: EEXIST: file already exists, mkdir '/Users/junjielong/.pi/agent/auth.json.lock'
--- stdout(raw.jsonl 全部) ---
{"type":"session","version":3,"id":"01a13b39-d500-7433-8bea-6c1102d49b7e","timestamp":"2026-10-14T16:23:28.257Z","cwd":"/private/tmp/pi-t06-obs/proj"}
```

## 锁目录状态（只读查看，未修改）
```
/Users/junjielong/.pi/agent/auth.json.lock:
total 0
drwxr-xr-x  2 junjielong staff  64 2026-10-15 00:22 .
drwxr-xr-x 19 junjielong staff 608 2026-10-15 00:22 ..

/Users/junjielong/.pi/agent/models-store.json.lock:
total 0
drwxr-xr-x  2 junjielong staff  64 2026-10-15 00:22 .
drwxr-xr-x 19 junjielong staff 608 2026-10-15 00:22 ..

/Users/junjielong/.pi/agent/settings.json.lock:
total 0
drwxr-xr-x  2 junjielong staff  64 2026-10-14 23:41 .
drwxr-xr-x 19 junjielong staff 608 2026-10-15 00:22 ..
（三个 .lock 均为空目录，创建时间 2026-10-14 23:41 ~ 2026-10-15 00:22）
```
