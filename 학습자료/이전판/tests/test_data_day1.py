"""1일차 파트 2 재료 검사. tools/make_data_day1.py가 만든 파일의 정답이 맞는지 확인한다."""
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / '노트북' / 'data' / '1일차'

# 정답 파일과 별개로, 안전 항목인 줄을 키워드로 찾는다. 정답 파일을 만든 목록과는 독립된 검사다.
SAFETY_WORDS = r'액체 흔적|비상구|손 끼임|인터락 해제|가스 캐비닛|산소 농도|폐액 라벨|케이블 트레이|비상정지|배기 덕트|보안경|소화기|브레이크|커버 열린'


def read(name):
    return (DATA / name).read_text(encoding='utf-8')


def diary_rows():
    rows = []
    for line in read('교대일지_4주.txt').splitlines()[1:]:
        number, when, content = line.split(' | ', 2)
        rows.append((int(number), when, content))
    return rows


def test_diary_has_400_numbered_lines_and_is_marked_fictional():
    assert '가상 자료' in read('교대일지_4주.txt').splitlines()[0]
    assert [number for number, _, _ in diary_rows()] == list(range(1, 401))


def test_safety_answer_matches_keywords_and_has_decoys():
    key = read('교대일지_안전항목.txt').splitlines()[2:]
    key_rows = [line.split(' | ', 3) for line in key]
    assert len(key_rows) == 14
    by_number = {number: (when, content) for number, when, content in diary_rows()}
    for number, when, category, content in key_rows:
        assert by_number[int(number)] == (when, content)
        assert category in ('사람의 안전', '설비 안전장치', '화학물질·환경', '소방')
    keyword_hits = {number for number, _, content in diary_rows() if re.search(SAFETY_WORDS, content)}
    assert keyword_hits == {int(number) for number, *_ in key_rows}
    # 안전 항목으로 오해하기 쉬운 "알람 1회, 재시작 후 정상" 줄이 충분히 있다
    decoys = [content for _, _, content in diary_rows() if '알람' in content and '재시작 후 정상' in content]
    assert len(decoys) >= 8


def test_dictation_has_26_speech_lines():
    lines = read('회의_받아쓰기_8월2주차.txt').splitlines()
    assert lines[0].startswith('[8월 2주차')
    assert len([line for line in lines[1:] if re.match(r'\(.+?\) ', line)]) == 26


def alarm_lines():
    lines = read('알람로그_10건.txt').splitlines()[1:]
    assert len(lines) == 10
    return {int(number): text for number, text in (line.split('. ', 1) for line in lines)}


def needs_action(number, lines):
    """알람_분류기준.txt의 세 기준을 코드로 옮긴 것. 정답 파일과 맞는지 확인하는 데 쓴다."""
    text = lines[number]
    equipment = re.search(r'\d호기', text).group()
    kind = re.search(r'E-\d+|챔버 압력 상승 경보|RF 반사파', text)
    repeated = bool(kind) and sum(
        1 for other in lines.values() if equipment in other and kind.group() in other) >= 2
    count = re.search(r'(\d+)회(?!째)', text)
    repeated = repeated or bool(count and int(count.group(1)) >= 2)
    value = re.search(r'\((\d+)도 / 상한 (\d+)도\)', text)
    near_limit = bool(value) and int(value.group(1)) / int(value.group(2)) >= 0.9
    return repeated or near_limit or '원인 미상' in text


def test_alarm_answer_follows_the_rule():
    lines = alarm_lines()
    answer = {}
    for line in read('알람로그_정답.txt').splitlines()[2:]:
        number, label, _ = line.split(' | ', 2)
        answer[int(number)] = label
    assert sorted(answer) == list(range(1, 11))
    computed = {number: '조치 필요' if needs_action(number, lines) else '모니터링' for number in lines}
    assert computed == answer
    assert list(answer.values()).count('조치 필요') == 7
    # 같은 설비가 두 번 나오는 쌍이 둘 있어, 표에서 행을 합치면 개수가 어긋난다
    assert sorted(n for n, text in lines.items() if '5호기 E-201' in text) == [1, 4]
    assert sorted(n for n, text in lines.items() if '챔버 압력 상승 경보' in text) == [2, 9]


def test_rule_file_mentions_three_criteria():
    rule = read('알람_분류기준.txt')
    assert all(f'{number}. ' in rule for number in (1, 2, 3))
