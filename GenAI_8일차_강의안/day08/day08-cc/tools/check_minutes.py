# 회의록 정리 검사 (summarizing-meeting-minutes의 검증 기준). 사용: python tools/check_minutes.py out/minutes.md MTG-2025-W01
#   표의 행 수가 원문 논의 사항 수와 같은지, 「미정」 칸 수, 담당, 기한 칸에 원문에 없는 단어가 있는지 셉니다
import json, os, re, sys
from _common import show, path

# 1. 인자, 파일 확인
if len(sys.argv) < 3:
    usage = '정리 파일 · 회의록 ID 두 가지가 필요합니다. 예: python tools/check_minutes.py out/minutes.md MTG-2025-W01'
    show({'error': usage})
    sys.exit(0)
summary_file, doc_id = sys.argv[1], sys.argv[2]
if not os.path.exists(summary_file):
    show({'error': f'정리 파일을 찾지 못했습니다: {summary_file} · 저장한 파일 이름을 확인해 주세요'})
    sys.exit(0)
summary = open(summary_file, encoding='utf-8').read()

# 2. 원문 청크를 합치고, 「논의 사항」 뒤에 오는 번호 항목(1. 2. …)을 셉니다
chunks = json.load(open(path('data', 'chunks6.json'), encoding='utf-8'))
source = '\n'.join(chunk['text'] for chunk in chunks if chunk['doc_id'] == doc_id)
discussion = source.split('논의 사항')[1] if '논의 사항' in source else source
items = re.findall(r'^\d+\.\s', discussion, flags=re.M)

# 3. 정리 파일에서 번호로 시작하는 표 행(| 1 | …)을 칸 목록으로 나눕니다
rows = []
for line in summary.splitlines():
    line = line.strip()
    if re.match(r'\|\s*\d+\s*\|', line):
        rows.append([cell.strip() for cell in line.strip('|').split('|')])

# 4. 「미정」 칸 수와, 담당, 기한(4, 5번째 칸)에 원문에 없는 단어가 든 행을 모읍니다
undecided = sum(row.count('미정') for row in rows)
invented = []
for row in rows:
    owner_and_due = row[3:5]
    made_up = [value for value in owner_and_due
               if value not in ('미정', '-') and value not in source]
    if len(row) >= 5 and made_up:
        invented.append(owner_and_due)

show({'원문 논의 사항': len(items), '표 행': len(rows), '미정 칸': undecided,
      '원문에 없는 담당·기한': invented})
