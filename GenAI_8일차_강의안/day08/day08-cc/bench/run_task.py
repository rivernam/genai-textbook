# 예제 2-4, 강사 터미널 시연. 상한을 걸고 한 번 실행하고, 요청마다 로그 한 줄을 남깁니다
# 사용: python bench/run_task.py --max-turns 8 --budget 200000 "요청 문장"
#   --max-turns: 이 단계 수에 이르면 Claude Code가 멈춥니다(공식 옵션)
#   --budget: 토큰 예산. 다 쓴 뒤에 넘었는지 보고 넘었으면 「사람에게 넘김」으로 적습니다
#   로그: results/agent_log.jsonl (요청 앞 24자, 실행한 도구, 단계, 토큰, 걸린 초, 끝난 이유)
import json, os, sys
from _cc import run, path

OPTIONS = ('--max-turns', '--budget')
STOP_LABELS = {'success': '답이 나옴', 'error_max_turns': '(단계 상한) 멈춤'}


def option_value(args, name):
    """인자 목록에서 name 바로 뒤의 값을 정수로 돌려줍니다(없으면 None)."""
    if name not in args:
        return None
    return int(args[args.index(name) + 1])


# 1. 명령줄 인자: 옵션 이름과 그 값을 뺀 나머지가 요청 문장입니다
args = sys.argv[1:]
max_turns = option_value(args, '--max-turns')
budget = option_value(args, '--budget')
question = ' '.join(word for i, word in enumerate(args)
                    if word not in OPTIONS and (i == 0 or args[i - 1] not in OPTIONS))

# 2. 단계 상한을 걸고 한 번 실행하고, 토큰 예산을 넘었는지 봅니다
result = run(question, max_turns=max_turns)
over_budget = budget is not None and result['tokens'] > budget
stop = STOP_LABELS.get(result['stop'], result['stop'])

# 3. 로그 한 줄을 붙입니다(요청 앞 24자, 도구는 앞 40자)
record = {'q': question[:24], 'tools': [call['what'][:40] for call in result['calls']],
          'turns': result['turns'], 'tokens': result['tokens'], 'sec': result['sec'],
          'stop': stop, 'budget': budget, 'over_budget': over_budget}
os.makedirs(path('results'), exist_ok=True)
with open(path('results', 'agent_log.jsonl'), 'a', encoding='utf-8') as log_file:
    log_file.write(json.dumps(record, ensure_ascii=False) + '\n')

# 4. 답 앞 1500자와 요약 한 줄을 보여 줍니다
print(result['reply'][:1500])
print('---')
tool_count = len(result['calls'])
summary = f"단계 {result['turns']} · 도구 {tool_count}회 · 토큰 {result['tokens']:,} · {stop}"
if over_budget:
    summary += ' · 예산 초과 · 사람에게 넘김'
print(summary)
print('로그 한 줄 추가 · results/agent_log.jsonl')
