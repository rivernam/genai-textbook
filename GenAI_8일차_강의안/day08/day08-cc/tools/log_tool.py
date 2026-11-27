# 도구 실행 로그 (예제 2-5, settings.json의 PostToolUse 훅이 도구를 실행할 때마다 호출합니다)
#   Claude Code가 표준 입력으로 넘겨 주는 JSON에서 필요한 칸만 골라 logs/tool_log.jsonl에 한 줄씩 쌓습니다
#   명령 원문은 앞 80자만 남깁니다(로그에 데이터, 개인정보가 통째로 남지 않게). 대신 집계에 쓸 칸(조회한 표 이름)은 table 칸에 따로 남깁니다
#   Desktop이 안에서 쓰는 도구(mcp__ccd_…, 계획 표시, 마무리)는 기록하지 않습니다
import json, os, re, sys, time
from _common import path

# 1. 훅이 넘겨 준 JSON을 읽습니다: Windows 기본 cp949 대신 UTF-8로 읽습니다
event = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace'))
tool = event.get('tool_name') or ''
if tool.startswith('mcp__ccd_'):
    sys.exit(0)

# 2. 기록할 칸을 고릅니다: query_db 명령이면 SQL의 FROM, JOIN 뒤 표 이름도 모읍니다(없으면 빈칸)
tool_input = event.get('tool_input', {})
command = str(tool_input.get('command') or '')
tables = []
if 'query_db' in command:
    for table_name in re.findall(r'\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)', command, re.I):
        if table_name not in tables:
            tables.append(table_name)
what = (command or tool_input.get('file_path') or tool_input.get('skill')
        or tool_input.get('subagent_type') or '')
record = {'time': time.strftime('%Y-%m-%d %H:%M:%S'),
          'session': event.get('session_id', '')[:8],
          'tool': tool,
          'what': str(what)[:80],          # 앞 80자만 남깁니다
          'table': ' · '.join(tables)}

# 3. logs/tool_log.jsonl에 한 줄 덧붙입니다
os.makedirs(path('logs'), exist_ok=True)
with open(path('logs', 'tool_log.jsonl'), 'a', encoding='utf-8') as log_file:
    log_file.write(json.dumps(record, ensure_ascii=False) + '\n')
