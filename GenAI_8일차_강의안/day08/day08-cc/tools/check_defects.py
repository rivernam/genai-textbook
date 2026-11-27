# 결함 원인 상위 표 검사 (예제 1-5). 사용: python tools/check_defects.py out/defect_CVD-01_2026-07.md CVD-01 2026-07
#   표의 결함 코드 상위 3개 순서, 코드별 결함 수와 런 수, 비중(%), 그 달 런 수와 NG 건수 줄을
#   DB(runs, defects)에서 다시 센 값과 맞춥니다. 비중 = 그 코드 결함 수 / 그 달 전체 결함 수 × 100(소수 첫째 자리)
import os, re, sqlite3, sys
from collections import namedtuple
from _common import show, path

Expected = namedtuple('Expected', 'code defect_count run_count percent')   # DB에서 다시 센 코드 하나
CODE_PATTERN = r'\b(ARC|BRIDGE|PARTICLE|SCRATCH|VOID)\b'


def numbers_in(line):
    """표 한 줄에서 숫자를 모두 찾아 float 목록으로 돌려줍니다(천 단위 쉼표는 뗍니다)."""
    return [float(x) for x in re.findall(r'(?<![\w.])\d+(?:\.\d+)?', line.replace(',', ''))]


def mentions_run_and_ng(line, run_count, ng_count):
    """줄에 런 수와 NG 건수가 온전한 수로 'NG' 글자와 함께 들어 있으면 True를 돌려줍니다."""
    has_runs = re.search(rf'(?<!\d){run_count}(?!\d)', line)
    has_ng = re.search(rf'(?<!\d){ng_count}(?!\d)', line)
    return bool(has_runs and has_ng and 'NG' in line)


# 1. 인자 확인
if len(sys.argv) < 4:
    usage = '표 파일 · 챔버 · 연월 세 가지가 필요합니다. 예: python tools/check_defects.py out/defect_CVD-01_2026-07.md CVD-01 2026-07'
    show({'error': usage})
    sys.exit(0)
report_file, chamber, ym = sys.argv[1], sys.argv[2], sys.argv[3]

# 2. 표 파일 확인
if not os.path.exists(report_file):
    show({'error': f'표 파일을 찾지 못했습니다: {report_file} · 저장한 파일 이름을 확인해 주세요'})
    sys.exit(0)
text = open(report_file, encoding='utf-8-sig').read()

# 3. DB에서 다시 셉니다: 그 달 런 수와 NG 건수, 코드별 결함 수(많은 순)와 런 수
db = sqlite3.connect(f'file:{path("data", "slfab.db")}?mode=ro', uri=True)
month_filter = (chamber, ym + '%')
run_count, ng_count = db.execute(
    "SELECT COUNT(*), SUM(result='NG') FROM runs WHERE chamber=? AND start_ts LIKE ?", month_filter).fetchone()
rows = db.execute("""SELECT d.defect_code, SUM(d.defect_cnt), COUNT(DISTINCT d.run_id)
                     FROM defects d JOIN runs r ON r.run_id = d.run_id
                     WHERE r.chamber=? AND r.start_ts LIKE ?
                     GROUP BY d.defect_code ORDER BY 2 DESC, 1""", month_filter).fetchall()
if not run_count:
    show({'error': f'{chamber} {ym} 런이 DB 에 없습니다 · 챔버 이름과 연월(예: 2026-07)을 확인해 주세요'})
    sys.exit(0)

# 4. 상위 3개 코드: 비중 = 그 코드 결함 수 / 그 달 전체 결함 수 × 100(소수 첫째 자리)
total_defects = sum(defect_count for _, defect_count, _ in rows)
expected = []
for code, defect_count, code_run_count in rows[:3]:
    percent = round(defect_count / total_defects * 100, 1)
    expected.append(Expected(code, defect_count, code_run_count, percent))

# 5. 표에서 결함 코드가 든 줄을 처음 나온 순서대로 읽습니다(구분선 |---| 은 건너뜁니다)
table_rows = []   # (코드, 그 코드가 든 줄)
for raw_line in text.splitlines():
    line = raw_line.strip()
    if not line.startswith('|') or re.fullmatch(r'[\s|:\-]+', line):
        continue
    found = re.search(CODE_PATTERN, line)
    if found and found.group(1) not in [code for code, _ in table_rows]:
        table_rows.append((found.group(1), line))

# 6. DB 값과 비교
order_ok = [code for code, _ in table_rows[:3]] == [item.code for item in expected]
count_mismatches, percent_mismatches = [], []
for item in expected:
    line = next((line for code, line in table_rows if code == item.code), '')
    numbers = numbers_in(line)
    if not (item.defect_count in numbers and item.run_count in numbers):
        count_mismatches.append(f'{item.code} 결함 {item.defect_count} · 런 {item.run_count}')
    if not any(abs(x - item.percent) <= 0.1 for x in numbers):   # 반올림 차이는 0.1 까지 허용
        percent_mismatches.append(f'{item.code} {item.percent}%')
run_line_ok = any(mentions_run_and_ng(line, run_count, ng_count) for line in text.splitlines())

# 7. 결과 출력
checks = [('상위 3 결함 코드와 순서', order_ok),
          ('코드별 결함 수 · 런 수', not count_mismatches),
          ('비중(%) · 그 달 결함 합계 기준', not percent_mismatches),
          (f'그 달 런 {run_count}건 · NG {ng_count}건 줄', run_line_ok)]
top3_summary = [f'{item.code} 결함 {item.defect_count} · 런 {item.run_count} · {item.percent}%'
                for item in expected]
show({'대상': f'{chamber} {ym}',
      'DB 상위 3': top3_summary,
      '그 달 결함 합계': total_defects,
      '표에서 읽은 코드 순서': [code for code, _ in table_rows],
      '맞지 않은 값': count_mismatches + percent_mismatches,
      '검사': [f"{'통과' if ok else '실패'} · {name}" for name, ok in checks],
      '점수': f'{sum(ok for _, ok in checks)}/{len(checks)}'})
