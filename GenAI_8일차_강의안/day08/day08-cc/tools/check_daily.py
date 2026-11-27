# 하루 NG 보고서 검사 (예제 3-6). 사용: python tools/check_daily.py out/daily_ng_20260731.md 2026-07-31
#   그날 NG가 1건 이상인 챔버 목록, 챔버별 런 수와 NG 건수, 「NG 합계 N건」 줄을 runs에서 다시 센 값과 맞춥니다
import os, re, sqlite3, sys
from _common import show, path

USAGE = 'python tools/check_daily.py out/daily_ng_20260731.md 2026-07-31'

# 1. 인자, 파일 확인
if len(sys.argv) < 3:
    show({'error': f'보고서 파일과 날짜 두 가지가 필요합니다. 예: {USAGE}'})
    sys.exit(0)
report_file, day = sys.argv[1], sys.argv[2]
if not os.path.exists(report_file):
    show({'error': f'보고서 파일을 찾지 못했습니다: {report_file} · 저장한 파일 이름을 확인해 주세요'})
    sys.exit(0)
text = open(report_file, encoding='utf-8').read()

# 2. DB 조회: 그날 챔버별 런 수와 NG 건수(NG 1건 이상만)
db = sqlite3.connect(f'file:{path("data", "slfab.db")}?mode=ro', uri=True)
truth = {c: (n, ng) for c, n, ng in db.execute(
    "SELECT chamber, COUNT(*), SUM(result='NG') FROM runs WHERE start_ts LIKE ? "
    "GROUP BY chamber HAVING SUM(result='NG') > 0", (day + '%',))}
total = sum(ng for _, ng in truth.values())

# 3. 표 읽기: 챔버 이름이 든 표 줄에서 숫자 두 개(런 수, NG 건수)를 차례로 읽습니다
rows = {}
for line in text.splitlines():
    if not line.strip().startswith('|'):
        continue
    m = re.search(r'\b([A-Z]+-\d{2})\b', line)
    if not m:
        continue
    nums = [int(x) for x in re.findall(r'(?<![\w.-])(\d+)(?![\w.%-])', line.replace(m.group(1), ''))]
    if len(nums) >= 2:
        rows[m.group(1)] = (nums[0], nums[1])

missing = sorted(set(truth) - set(rows))
extra = sorted(set(rows) - set(truth))
wrong = sorted(c for c in set(truth) & set(rows) if rows[c] != truth[c])
header = next((l for l in text.splitlines() if l.strip().startswith('|') and '챔버' in l), '')

# 4. 결과
show({f'챔버 목록 (runs 기준 {len(truth)}개)': '일치' if not missing and not extra else f'빠짐 {missing} · 더함 {extra}',
      '챔버별 런 수 · NG 건수': '모두 일치' if rows and not wrong else f'다름 {wrong}',
      f'합계 줄 「NG 합계 {total}건」': '적힘' if re.search(rf'NG\s*합계\s*{total}\s*건', text) else '없음',
      '출처 열': '있음' if '출처' in header else '없음'})
