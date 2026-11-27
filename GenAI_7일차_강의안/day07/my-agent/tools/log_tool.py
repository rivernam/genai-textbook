# 도구 실행 로그 · settings.json의 PostToolUse 훅이 도구를 실행할 때마다 호출합니다
#   Claude Code가 표준 입력으로 넘겨 주는 JSON에서 필요한 칸만 골라 logs/agent_log.jsonl에 한 줄씩 쌓습니다
#   명령 원문은 앞 80자만 남깁니다(로그에 데이터가 통째로 남지 않게)
import json, os, sys, time
from _common import path

event = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace'))  # Windows 기본 cp949 대신 UTF-8로 읽습니다
tool_input = event.get('tool_input', {})
record = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'session': event.get('session_id', '')[:8],
          'tool': event.get('tool_name'),
          'what': str(tool_input.get('command') or tool_input.get('file_path') or tool_input.get('skill') or tool_input.get('subagent_type') or '')[:80]}
os.makedirs(path('logs'), exist_ok=True)
with open(path('logs', 'agent_log.jsonl'), 'a', encoding='utf-8') as log_file:
    log_file.write(json.dumps(record, ensure_ascii=False) + '\n')
