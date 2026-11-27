# 회의록 10건 요약 보고서 검사 (1-1 비교, 5분 체험). 사용: python tools/check_summary.py out/mtg_summary.md
#   보고서의 표 행을 회의 ID(MTG-2025-W01 ~ W10)별로 세어 원문 회의록의 논의 사항 수와 맞추고,
#   행에 적힌 숫자가 그 회의 원문에 있는 숫자인지 대조합니다(원문에 없는 숫자 = 지어냈거나 잘못 옮긴 값)
import json, re, sys
from _common import show, path

MEETING_IDS = [f'MTG-2025-W{i:02d}' for i in range(1, 11)]


def numbers_in(text):
    """글 속 숫자를 모두 찾아 앞의 0을 뗀 집합으로 돌려줍니다(07과 7을 같은 값으로 봅니다)."""
    return {number.lstrip('0') or '0' for number in re.findall(r'\d+', text)}


# 1. 인자 확인
if len(sys.argv) < 2:
    show({'error': '보고서 파일이 필요합니다. 예: python tools/check_summary.py out/mtg_summary.md'})
    sys.exit(0)
report_file = sys.argv[1]

# 2. 보고서 파일 읽기
try:
    report = open(report_file, encoding='utf-8').read()
except OSError:
    show({'error': f'보고서 파일을 찾지 못했습니다: {report_file} · 저장한 파일 이름을 확인해 주세요'})
    sys.exit(0)

# 3. 원문 회의록: 회의마다 본문을 합치고 "1. "처럼 번호가 붙은 논의 사항 수를 셉니다
chunks = json.load(open(path('data', 'chunks6.json'), encoding='utf-8'))
source_text = {}
item_count = {}
for meeting_id in MEETING_IDS:
    texts = [chunk['text'] for chunk in chunks if chunk['doc_id'] == meeting_id]
    source_text[meeting_id] = '\n\n'.join(texts)
    item_count[meeting_id] = len(re.findall(r'^\d+\. ', source_text[meeting_id], re.M))

# 4. 보고서 표 행: 회의별로 세고, 행에 적힌 숫자를 원문 숫자와 대조합니다
row_count = {meeting_id: 0 for meeting_id in MEETING_IDS}
invented = []
for line in report.splitlines():
    is_divider = re.fullmatch(r'[\s|:\-]+', line)        # |---|---| 구분선
    if not line.strip().startswith('|') or is_divider:
        continue
    week = re.search(r'W\s*0?(\d{1,2})\b', line)         # W01, W 1, W10 같은 표기
    if not week or not 1 <= int(week.group(1)) <= 10:
        continue
    meeting_id = MEETING_IDS[int(week.group(1)) - 1]
    row_count[meeting_id] += 1
    # 회의 ID에 든 숫자(주차, 2025)는 대조에서 뺍니다
    body = line.replace(week.group(0), ' ').replace('MTG-2025-', ' ')
    bad_numbers = sorted(numbers_in(body) - numbers_in(source_text[meeting_id]))
    if bad_numbers:
        invented.append({'회의': meeting_id, '원문에 없는 숫자': bad_numbers, '행': line.strip()[:60]})

# 5. 비교
missing = [meeting_id for meeting_id in MEETING_IDS if row_count[meeting_id] == 0]
short = []
for meeting_id in MEETING_IDS:
    rows, items = row_count[meeting_id], item_count[meeting_id]
    if rows and rows != items:
        short.append(f'{meeting_id} {rows}/{items}')
checks = [('회의 10건이 모두 표에 있음', not missing),
          ('회의마다 논의 사항 수와 표 행 수가 같음', not missing and not short),
          ('원문에 없는 숫자 0건', not invented)]
check_lines = [f"{'통과' if ok else '실패'} · {name}" for name, ok in checks]
passed = sum(ok for _, ok in checks)

# 6. 결과 출력: 원문에 없는 숫자는 앞 5건만 보여 줍니다
show({'원문 논의 사항': sum(item_count.values()), '표 행': sum(row_count.values()),
      '빠진 회의': missing, '행 수가 다른 회의': short, '원문에 없는 숫자': invented[:5],
      '검사': check_lines, '점수': f'{passed}/{len(checks)}'})
