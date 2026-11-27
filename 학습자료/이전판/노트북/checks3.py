"""2일차 파트 3 실습(실습 8, 9)의 테스트. 임베딩 모델도 API도 부르지 않는다."""
import csv
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parent / 'data' / '2일차'


def _report(name, results):
    for number, (label, ok) in enumerate(results, 1):
        print(f'{number}.', '통과' if ok else '실패', label)
    passed = bool(results) and all(ok for _, ok in results)   # 확인한 항목이 없으면 통과로 치지 않는다
    print(f'{name} 통과' if passed else f'{name}: 실패한 항목을 고쳐 다시 실행해 주세요')
    return passed


def _safe(function, *args):
    try:
        return function(*args)
    except Exception as error:                      # 학습자의 함수에서 난 오류는 실패로 센다
        return error


def check_search(rank_of, recall_at, search):
    """실습 8: 작은 점수 배열로 세 함수의 동작을 확인한다."""
    names = ['문서A', '문서B', '문서C', '문서D']
    scores = np.array([0.2, 0.9, 0.5, 0.7])
    tied = np.array([0.0, 0.0, 0.0, 0.0])
    results = [
        ('rank_of: 점수가 가장 높은 문서는 1위다', _safe(rank_of, scores, names, '문서B') == 1),
        ('rank_of: 점수가 가장 낮은 문서는 4위다', _safe(rank_of, scores, names, '문서A') == 4),
        ('rank_of: 점수가 모두 같으면 names의 순서대로 순위를 매긴다', _safe(rank_of, tied, names, '문서C') == 3),
        ('recall_at: 순위 [1, 2, 4, 1]의 recall@1은 50이다', _safe(recall_at, [1, 2, 4, 1], 1) == 50),
        ('recall_at: 순위 [1, 2, 4, 1]의 recall@3은 75이다', _safe(recall_at, [1, 2, 4, 1], 3) == 75),
        ('search: 상위 2건을 (문서 번호, 점수)로 점수가 높은 순으로 돌려준다',
         _safe(search, scores, names, 2) == [('문서B', 0.9), ('문서D', 0.7)]),
        ('search: 점수는 소수 셋째 자리까지 반올림한 float이다',
         _safe(search, np.array([0.12345, 0.5]), ['가', '나'], 1) == [('나', 0.5)]
         and _safe(search, np.array([0.12345, 0.05]), ['가', '나'], 1) == [('가', 0.123)]),
        ('search: k가 문서 수보다 크면 있는 만큼만 돌려준다',
         not isinstance(_safe(search, scores, names, 10), Exception) and len(_safe(search, scores, names, 10)) == 4),
    ]
    return _report('실습 8', results)


def field_answers():
    """현장 질문과 정답 문서. 실습 9의 판정을 확인하는 데 쓴다."""
    with open(DATA / '현장_질문_6.csv', encoding='utf-8-sig') as file:
        return {row['질문']: row for row in csv.DictReader(file)}


def check_judgement(questions, top_lists, judge, rank):
    """실습 9: 판정(O, X)이 정답 문서와 맞는지, X인 질문에 정답 문서의 순위를 맞게 적었는지 확인한다.

    top_lists는 질문마다 검색 상위 문서 번호의 목록이다. 1위 문서 번호(문자열)만 주면 순위가 2 이상의 정수인지만 본다.
    """
    answers = field_answers()
    results = [('질문을 모두 검색했다', len(top_lists) == len(questions) > 0)]
    for number, (question, found) in enumerate(zip(questions, top_lists), 1):
        found = [found] if isinstance(found, str) else list(found)
        gold = answers[question]['정답']
        truth = 'O' if found[0] == gold else 'X'
        results.append((f'질문 {number}: 1위 문서 {found[0]}의 판정', judge.get(number) == truth))
        if truth == 'X':
            written = rank.get(number)
            if gold in found:
                ok = written == found.index(gold) + 1
            else:                                   # 정답 문서가 받은 목록 밖에 있다
                ok = isinstance(written, int) and written >= 2
            results.append((f'질문 {number}: X이므로 2위와 3위 문서도 열어 정답 문서의 순위를 RANK에 적었다', ok))
    return _report('실습 9', results)
