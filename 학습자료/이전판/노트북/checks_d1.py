"""1일차 실습의 테스트. API를 부르지 않는다.

    check_table(table, correct_yield)   실습 1. 사용 기준표의 형식과 계산 카드의 정답을 확인한다.

판정과 이유가 옳은지는 확인하지 않는다. 그것은 응답을 읽은 사람이 정하는 일이다.
"""
KINDS = ('정의', '원리', '계산', '최신 정보', '사내 규격')
MODELS = ('소형', '기본')
JUDGMENTS = ('맞음', '틀림', '판정 불가')
CRITERIA = ('읽고 판정해 쓴다', '검증하고 쓴다', '도구에 맡긴다', '입력하지 않는다')
CORRECT_YIELD = round(0.985 * 0.972 * 0.991 * 0.968 * 100, 2)      # 91.84


def _rows(table):
    return [table[kind] for kind in KINDS if isinstance(table.get(kind), dict)]


def check_table(table, correct_yield):
    """일곱 가지를 확인해 결과를 출력한다. [(통과 여부, 설명), ...]을 돌려준다."""
    rows = _rows(table) if isinstance(table, dict) else []
    complete = len(rows) == len(KINDS)
    results = [
        (isinstance(correct_yield, (int, float)) and abs(correct_yield - CORRECT_YIELD) < 0.005,
         '계산 카드의 정답(누적 수율, 소수 둘째 자리)을 코드로 구했다'),
        (complete, '기준표에 질문 유형 다섯 가지가 모두 있다'),
        (complete and all(row.get(model) in JUDGMENTS for row in rows for model in MODELS),
         "모델별 판정이 '맞음', '틀림', '판정 불가' 가운데 하나다"),
        (complete and all(row.get('기준') in CRITERIA for row in rows),
         '사용 기준이 네 가지 가운데 하나다'),
        (complete and all(len(str(row.get('이유', '')).strip()) >= 5 for row in rows),
         '유형마다 이유를 적었다'),
        (complete and table['계산'].get('기준') == '도구에 맡긴다',
         '계산은 모델이 맞혔더라도 도구에 맡긴다'),
        (complete and table['사내 규격'].get('기준') == '입력하지 않는다',
         '사내 규격은 입력하지 않는다'),
    ]
    for number, (ok, title) in enumerate(results, 1):
        print(f'{number}. {"통과" if ok else "실패"} {title}')
        if number == 1 and not ok:      # 정답 값은 보여 주지 않고, 확인할 계산 방법만 알려 줍니다
            print('   단계별 수율을 100으로 나누어 모두 곱한 뒤 100을 곱하고, 소수 둘째 자리로 반올림했는지 확인합니다')
    if all(ok for ok, _ in results):
        print('실습 1 통과')
    return results
