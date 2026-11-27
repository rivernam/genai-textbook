"""1일차 파트 2 실습의 테스트.

    check_classify(texts)                   실습 2. 분류 응답 세 개의 형식, 일관성, 정확도를 확인한다.
    check_chain(table_text, count_rows, classified)   실습 3. 표의 행 수와 로그 번호를 확인한다.

check_classify는 응답 텍스트만 받으므로 API를 부르지 않는다. 실습 노트북이 응답을 받아 넘긴다.
"""
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data' / '1일차'
LINE = re.compile(r'^\s*(\d+)\s*\|\s*(조치 필요|모니터링)\s*$')
ROW = re.compile(r'^\s*\|\s*(\d+)\s*\|')
SAMPLE_TABLE = '''다음은 정리한 표입니다.

| 로그 번호 | 설비 | 알람 | 발생 시각 |
| --- | --- | --- | --- |
| 1 | 5호기 | E-201 | 02:14 |
| 4 | 5호기 | E-201 | 03:30 |
| 8 | 6호기 | 칠러 유량 저하 | 05:45 |
'''


def load_answer():
    """알람로그_정답.txt를 {줄 번호: 분류}로 읽는다."""
    rows = (DATA / '알람로그_정답.txt').read_text(encoding='utf-8').splitlines()[2:]
    return {int(row.split(' | ')[0]): row.split(' | ')[1] for row in rows}


def parse(text):
    """응답에서 "번호 | 분류" 줄을 읽어 {번호: 분류}로 돌려준다. 형식에 맞지 않는 줄은 무시한다."""
    return {int(found.group(1)): found.group(2) for line in text.splitlines() if (found := LINE.match(line))}


def table_numbers(text):
    """마크다운 표의 데이터 줄에서 첫 칸의 번호를 순서대로 모은다."""
    return [int(found.group(1)) for line in text.splitlines() if (found := ROW.match(line))]


def _report(results, passed_message):
    for number, (ok, title) in enumerate(results, 1):
        print(f'{number}. {"통과" if ok else "실패"} {title}')
    if all(ok for ok, _ in results):
        print(passed_message)
    return results


def check_classify(texts):
    """네 가지를 확인해 결과를 출력한다. [(통과 여부, 설명), ...]을 돌려준다."""
    answer = load_answer()
    texts = list(texts) if isinstance(texts, (list, tuple)) else []
    parsed = [parse(text) for text in texts]
    only_lines = bool(texts) and all(
        text.strip() and all(LINE.match(line) for line in text.strip().splitlines()) for text in texts)
    same = bool(parsed) and len({tuple(sorted(rows.items())) for rows in parsed}) == 1
    # 힌트 2가 분류가 바뀐 줄을 찾게 하므로, 실패하면 그 줄과 세 번의 분류를 함께 보여 준다
    changed = sorted(number for number in set().union(*parsed) if len({rows.get(number) for rows in parsed}) > 1)
    changed_note = ', '.join(f'{number}번 ' + '/'.join(str(rows.get(number)) for rows in parsed) for number in changed)
    matched = [sum(rows.get(number) == label for number, label in answer.items()) for rows in parsed]
    results = [
        (len(texts) == 3 and all(len(rows) == 10 for rows in parsed), '세 번 모두 10건의 분류를 읽을 수 있다'),
        (only_lines, '응답에 "번호 | 분류" 줄 외의 말이나 코드 블록 표시가 없다'),
        (same, '세 번의 분류가 모두 같다' + ('' if same or not changed else f'(분류가 바뀐 줄: {changed_note})')),
        (bool(matched) and all(count >= 9 for count in matched), f'세 번 모두 정답과 9건 이상 일치한다(일치한 건수: {matched})'),
    ]
    return _report(results, '실습 2 통과')


def check_chain(table_text, count_rows, classified):
    """네 가지를 확인해 결과를 출력한다. count_rows는 학습자가 작성한 표의 행 수를 세는 함수다."""
    answer = load_answer()
    expected = sorted(number for number, label in answer.items() if label == '조치 필요')
    try:
        sample_ok = count_rows(SAMPLE_TABLE) == 3
    except Exception:
        sample_ok = False
    try:
        counted = count_rows(table_text)
    except Exception:
        counted = None
    numbers = sorted(table_numbers(table_text))
    classified_rows = parse(classified)
    classified_count = list(classified_rows.values()).count('조치 필요')
    classified_right = sum(classified_rows.get(number) == label for number, label in answer.items())
    results = [
        (sample_ok, 'count_table_rows가 머리글과 구분선을 빼고 데이터 줄 3개를 센다'),
        (counted == len(expected), f'표의 행 수가 조치 필요 {len(expected)}건과 같다(센 값: {counted})'),
        (numbers == expected, f'표의 로그 번호가 정답의 조치 필요 번호와 같다(표의 번호: {numbers})'),
        (counted == classified_count, f'표의 행 수가 1단 분류에서 센 조치 필요 건수와 같다({classified_count}건)'),
    ]
    reported = _report(results, '실습 3 통과')
    if classified_right != len(answer):
        # 1단이 틀리면 표를 바르게 만들어도 테스트 2~4번 가운데 하나는 실패하므로, 원인이 2단이 아님을 알린다
        print(f'참고: 1단(실습 2)의 분류가 정답과 {classified_right}/{len(answer)}건만 일치합니다. '
              '실습 2의 분류부터 고칩니다.')
    return reported
