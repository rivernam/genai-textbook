# 도구 실행 로그. settings.json의 PostToolUse 훅이 도구를 실행할 때마다 호출합니다
#   Claude Code가 표준 입력으로 넘겨 주는 JSON에서 필요한 칸만 골라 logs/agent_log.jsonl에 한 줄씩 쌓습니다
#   명령 원문은 앞 80자만 남깁니다(로그에 데이터, 개인정보가 통째로 남지 않게). 대신 집계에 쓸 칸(조회한 표 이름)은 table 칸에 따로 남깁니다
#   answers 폴더의 md에 답을 쓴 줄에는 그 답의 제목 번호(「## Q4」 → Q4)를 q 칸에 따로 남깁니다(미션 1 검사가 질문과 세션을 짝짓는 데 씁니다)
#   Desktop이 안에서 쓰는 도구(mcp__ccd_…, 계획 표시, 마무리)는 기록하지 않습니다
import json, os, re, sys, time
from _common import path

ev = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace'))   # Windows 기본 cp949 대신 UTF-8로 읽습니다
tool = ev.get('tool_name') or ''
if tool.startswith('mcp__ccd_'):
    sys.exit(0)
inp = ev.get('tool_input', {})
cmd = str(inp.get('command') or '')
tables = []
if 'query_db' in cmd:     # SQL의 FROM, JOIN 뒤 표 이름(없으면 빈칸)
    for t in re.findall(r'\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)', cmd, re.I):
        if t not in tables:
            tables.append(t)

QH = re.compile(r'(?:^|\\n|`n|\n|[\'"])\s*#{1,4}\s*(Q\d+)\b')         # 답 제목 「## Q4」(줄 첫머리, \n, `n, 따옴표 뒤)
ANS = r'answers[\\/][^\s;|&<>\'"]*\.md'                               # answers\d8m1.md, answers/d8m1.md
WRITE = re.compile(r'(>>?|\btee\b(\s+-a)?)\s*[\'"]?[^\s;|&<>\'"]*' + ANS                      # >, >>, tee
                   + r'|\b(Add-Content|Set-Content|Out-File)\b[^;|\n]*' + ANS                  # PowerShell
                   + r'|open\(\s*[rRbB]?[\'"][^\'"]*' + ANS + r'[\'"]\s*,\s*[\'"][aw]', re.I)   # python open(..., 'a')


def heads(s):
    out = []
    for q in QH.findall(s or ''):
        if q not in out:
            out.append(q)
    return out


q = []
fp = str(inp.get('file_path') or '')
if tool in ('Write', 'Edit', 'MultiEdit') and re.search(ANS + r'$', fp):
    if tool == 'Write':
        q = heads(inp.get('content'))
    else:
        pairs = [(inp.get('old_string') or '', inp.get('new_string') or '')] + \
                [(e.get('old_string') or '', e.get('new_string') or '') for e in inp.get('edits') or []]
        new = [h for o, n in pairs for h in heads(n)]
        old = [h for o, n in pairs for h in heads(o)]
        q = [h for h in dict.fromkeys(new) if h not in old] or list(dict.fromkeys(new))   # 새로 붙인 제목(없으면 고친 제목)
elif tool in ('Bash', 'PowerShell') and WRITE.search(cmd):
    q = heads(cmd)

rec = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'session': ev.get('session_id', '')[:8],
       'tool': tool,
       'what': str(cmd or inp.get('file_path') or inp.get('skill') or inp.get('subagent_type') or '')[:80],
       'table': ' · '.join(tables)}
if q:
    rec['q'] = ' '.join(q)
os.makedirs(path('logs'), exist_ok=True)
with open(path('logs', 'agent_log.jsonl'), 'a', encoding='utf-8') as f:
    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
