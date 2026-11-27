# 틸트 등급 판정 도구 (7일차 미션 1의 완성본). 사용: python tools/grade_tilt.py PKG-B310 0.45
#   기준표는 DB에 없고 rules/spec_limits.json에 따로 있으며 제품군마다 등급 폭이 다릅니다
#   측정값이 grade_a 이하면 A, grade_b 이하면 B, upper 이하면 C, 그보다 크면 OUT
import json, sys
from _common import show, path

ROWS = json.load(open(path('rules', 'spec_limits.json'), encoding='utf-8'))

# 1. 인자 확인
if len(sys.argv) < 3:
    show({'error': '제품군과 측정값 두 가지가 필요합니다'})
    sys.exit(0)
product = sys.argv[1]
value = float(sys.argv[2])

# 2. 제품군의 틸트 기준 찾기
rule = next((row for row in ROWS if row['product'] == product and row['item'] == 'tilt'), None)
if rule is None:
    show({'error': f'{product} 의 틸트 기준이 없습니다'})
    sys.exit(0)
# 3. 작은 한계부터 차례로 비교합니다. 모두 넘으면 OUT
limits = (('A', rule['grade_a']), ('B', rule['grade_b']), ('C', rule['upper']))
grade = 'OUT'
for candidate, limit in limits:
    if value <= limit:
        grade = candidate
        break
show({'product': product, 'value': value, 'grade': grade,
      'basis': {'grade_a': rule['grade_a'], 'grade_b': rule['grade_b'], 'upper': rule['upper']}})
