"""회의 요약표(작업폴더/결과/회의요약표.md)가 요청한 조건을 지켰는지 검사한다.

사용법: python check.py [검사할 폴더]      (폴더를 적지 않으면 작업폴더/결과)
모델을 부르지 않으므로 키도 요금도 필요 없다. 모두 통과하면 종료 코드 0, 아니면 1.

이 파일과 풀이 폴더는 작업폴더 밖에 있다. 코딩 에이전트에는 작업폴더만 열어 준다.
작업폴더 안에 두면 에이전트가 검사 기준을 읽고 결과를 거기에 맞출 수 있다.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLUMNS = ['날짜', '주제', '결정', '액션', '담당', '기한']
# 회의록 10건의 날짜. 원문에서 직접 확인한 값이다.
MEETING_DATES = ['2026-08-17'] * 2 + ['2026-08-18'] * 2 + ['2026-08-19'] * 2 + ['2026-08-20'] * 2 + ['2026-08-21'] * 2
# 행을 찾는 데 쓰는 주제의 낱말
TOPICS = {
    '야간조': ['야간조', '인수인계'],
    '주간회의': ['주간회의', '주간 회의'],
    'A-7': ['A-7', 'A7', '레시피'],
    '안전점검': ['안전점검', '안전 점검'],
    '5호기': ['5호기', 'E-201'],
    '품질팀': ['품질'],
    '신입교육': ['신입'],
    '폐액라벨': ['폐액'],
    '주간마감': ['마감', '스탠드업'],
    '협력사': ['협력사'],
}
# 담당과 기한이 원문에 모두 적혀 있는 회의. 이 행의 담당, 기한 칸에는 "미기재"가 없어야 한다.
COMPLETE = ['야간조', 'A-7', '안전점검', '신입교육']


def read_table(text):
    """마크다운 표의 (머리글, 데이터 행 목록)을 돌려준다. 칸은 앞뒤 공백을 뗀 문자열이다."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        if all(re.fullmatch(r':?-{2,}:?', cell) for cell in cells):
            continue                                   # 구분선
        rows.append(cells)
    return (rows[0], rows[1:]) if rows else ([], [])


def find_row(rows, key):
    """주제 칸에 낱말이 들어 있는 행을 돌려준다. 없으면 None."""
    for row in rows:
        if len(row) > 1 and any(word in row[1] for word in TOPICS[key]):
            if key == '주간회의' and any(word in row[1] for word in TOPICS['주간마감']):
                continue
            return row
    return None


def cell(row, name):
    index = COLUMNS.index(name)
    return row[index] if row and len(row) > index else ''


def outside_parentheses(text):
    return re.sub(r'\([^)]*\)', '', text)


def run(folder):
    """검사 여덟 가지를 실행해 (이름, 통과 여부, 설명) 목록을 돌려준다."""
    path = Path(folder) / '회의요약표.md'
    if not path.exists():
        return [(f'{number}. 검사하지 못함', False, f'{path} 파일이 없습니다') for number in range(1, 9)]
    text = path.read_text(encoding='utf-8-sig')
    header, rows = read_table(text)
    below = text.split('|')[-1]                        # 표의 마지막 칸 뒤에 적힌 글
    results = []

    def add(name, ok, detail=''):
        results.append((name, bool(ok), detail))

    add('1. 열이 날짜, 주제, 결정, 액션, 담당, 기한 순서다', header == COLUMNS, f'머리글 {header}')
    add('2. 회의 하나에 한 행으로 10행이다', len(rows) == 10, f'{len(rows)}행')
    dates = sorted(re.match(r'\d{4}-\d{2}-\d{2}', cell(row, '날짜')).group(0)
                   for row in rows if re.match(r'\d{4}-\d{2}-\d{2}', cell(row, '날짜')))
    add('3. 날짜 열이 2026-08-17 형식이고 회의록의 날짜와 같다', dates == MEETING_DATES, f'읽은 날짜 {len(dates)}개')
    slashed = [cell(row, '주제') for row in rows
               if re.search(r'\d{1,2}/\d{1,2}', outside_parentheses(cell(row, '기한')))]
    add('4. 기한 칸에 8/28처럼 줄여 쓴 날짜가 괄호 밖에 남아 있지 않다', rows and not slashed, f'남은 행 {slashed}')
    a7 = cell(find_row(rows, 'A-7'), '기한')
    add('5. "다음 주 화요일"이 2026-08-25로 바뀌고 원문이 괄호에 남았다',
        '2026-08-25' in a7 and re.search(r'\([^)]*다음 주 화요일[^)]*\)', a7), f'A-7 행의 기한: {a7}')
    partner = ' '.join(find_row(rows, '협력사') or [])
    alarm = ' '.join(find_row(rows, '5호기') or [])
    add('6. "9월 첫째 주"와 "캘리 끝날 때까지"는 날짜로 바꾸지 않았다',
        '9월 첫째 주' in partner and '2026-09-0' not in partner and '캘리 끝날 때까지' in alarm,
        '협력사 행과 5호기 행을 봅니다')
    quality, label = find_row(rows, '품질팀'), find_row(rows, '폐액라벨')
    filled = [key for key in COMPLETE
              if '미기재' in cell(find_row(rows, key), '담당') + cell(find_row(rows, key), '기한')]
    add('7. 원문에 없는 담당(품질팀 협의)과 기한(폐액 라벨)은 "미기재"이고, 담당과 기한이 모두 적힌 회의 4건의 칸은 채웠다',
        '미기재' in cell(quality, '담당') and '미기재' in cell(label, '기한') and not filled
        and all(find_row(rows, key) for key in COMPLETE),
        f'품질팀 담당: {cell(quality, "담당")}, 폐액 라벨 기한: {cell(label, "기한")}, 잘못 비운 회의 {filled}')
    counted = sum(one.count('미기재') for row in rows for one in row)
    read_count = re.search(r'회의록[^\n\d]*(\d+)', below)      # "읽은 회의록 수: 10", "회의록 10건" 모두 읽는다
    blank_count = re.search(r'미기재[^\n\d]*(\d+)', below)
    add('8. 표 아래에 적은 회의록 수가 10이고, "미기재" 칸 수가 표에서 센 수와 같다',
        read_count and read_count.group(1) == '10' and blank_count and int(blank_count.group(1)) == counted,
        f'표에서 센 "미기재" {counted}번, 표 아래에 적힌 수 {blank_count.group(1) if blank_count else "없음"}')
    return results


def weekly_report_counts(folder):
    """주간 보고 초안의 3번 표 행 수와 4번 항목 수를 센다. 파일이 없으면 None."""
    path = Path(folder) / '주간보고_초안.md'
    if not path.exists():
        return None
    text = path.read_text(encoding='utf-8-sig')
    sections = re.split(r'(?m)^\s*(?:#+\s*)?(\d)\.\s', text)      # ['앞', '1', '내용', '2', '내용', ...]
    body = {sections[index]: sections[index + 1] for index in range(1, len(sections) - 1, 2)}
    _, todo_rows = read_table(body.get('3', ''))
    checks = [line for line in body.get('4', '').splitlines() if re.match(r'\s*([-*]|\d+[.)])\s+\S', line)]
    return len(todo_rows), len(checks), [number for number in '12345' if number in body]


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / '작업폴더' / '결과'
    results = run(folder)
    for name, ok, detail in results:
        print('통과' if ok else '실패', name, '' if ok else f'→ {detail}')
    passed = sum(ok for _, ok, _ in results)
    print(f'결과 {passed}/{len(results)} 통과 ({folder})')
    counts = weekly_report_counts(folder)
    if counts:
        print(f'주간 보고 초안: 3번 표의 할 일 {counts[0]}행, 4번 항목 {counts[1]}개, 찾은 제목 번호 {counts[2]}')
    sys.exit(0 if passed == len(results) else 1)


if __name__ == '__main__':
    main()
