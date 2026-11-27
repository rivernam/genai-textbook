# 보고서 초안 검사 (drafting-chamber-report의 검증 기준). 사용: python tools/check_report.py out/report.md ETCH-04 2026-07
#   다섯 절 제목, 수치표 출처 칸, NG 건수가 runs에서 센 값과 같은지, 개인 이름 여부를 코드로 셉니다
import os, re, sqlite3, sys
from _common import show, path

SECTION_HEADS = ['1. 요약', '2. 수치', '3. 전월 대비', '4. 관련 사내 규정', '5. 확인 필요 사항']
USAGE = 'python tools/check_report.py out/report.md ETCH-04 2026-07'


def last_cell(line):
    """마크다운 표 한 줄을 받아 마지막 칸(출처 열)의 글자를 돌려줍니다."""
    return line.rstrip(' |').split('|')[-1].strip()


# 1. 인자 확인
if len(sys.argv) < 4:
    show({'error': f'보고서 파일 · 챔버 · 연월 세 가지가 필요합니다. 예: {USAGE}'})
    sys.exit(0)
report_file, chamber, year_month = sys.argv[1], sys.argv[2], sys.argv[3]

# 2. 파일 확인
if not os.path.exists(report_file):
    show({'error': f'보고서 파일을 찾지 못했습니다: {report_file} · 저장한 파일 이름을 확인해 주세요'})
    sys.exit(0)
text = open(report_file, encoding='utf-8').read()

# 3. DB 조회: 그 달 그 챔버의 NG 건수를 runs에서 셉니다
db = sqlite3.connect(f'file:{path("data", "slfab.db")}?mode=ro', uri=True)
run_count, ng_count = db.execute(
    "SELECT COUNT(*), SUM(result='NG') FROM runs WHERE chamber=? AND start_ts LIKE ?",
    (chamber, year_month + '%')).fetchone()

# 4. 수치표: '2. 수치' 절(다음 ## 제목 전까지)의 표에서 출처 열이 빈 행을 셉니다
section2 = text.split('2. 수치')[1].split('##')[0] if '2. 수치' in text else ''
table_lines = [line for line in section2.splitlines() if line.strip().startswith('|')]
# 구분선(|---|)을 빼고, 첫 줄(머리글)도 뺍니다
body_rows = [line for line in table_lines if not re.match(r'\|\s*:?-', line.strip())][1:]
rows_without_source = [line for line in body_rows if not last_cell(line)]
has_source_column = bool(table_lines) and '출처' in table_lines[0]
source_check = f'있음 · 빈 칸 {len(rows_without_source)}행' if has_source_column else '없음'

# 5. NG 건수: NG와 같은 줄(표, 본문 어디든)에 그 숫자가 앞뒤 숫자 없이 통째로 적혔는지 봅니다
ng_lines = [line for line in text.splitlines() if 'NG' in line]
ng_written = any(re.search(rf'(?<!\d){ng_count}(?!\d)', line) for line in ng_lines)

# 6. 결과
show({'절 제목 (양식 다섯 절)': f"{sum(head in text for head in SECTION_HEADS)}/5",
      '수치표 출처 열': source_check,
      f'NG 건수 {ng_count}건 (runs 기준)': '적힘' if ng_written else '없음',
      '개인 이름 의심': re.findall(r'[김이박최정강조윤장임]\S{1,2}\s?(?:님|씨|책임|선임|프로)', text)})
