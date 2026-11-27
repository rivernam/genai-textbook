"""3일차 파트 3 실습(실습 3)의 테스트. 임베딩 모델도 API도 부르지 않는다."""
from collections import namedtuple

Hit = namedtuple('Hit', 'score doc_id version type date section text')
Chunk = namedtuple('Chunk', 'doc_id version type date section text')


def _report(name, results):
    for number, (label, ok) in enumerate(results, 1):
        print(f'{number}.', '통과' if ok else '실패', label)
    passed = all(ok for _, ok in results)
    print(f'{name} 통과' if passed else f'{name}: 실패한 항목을 고쳐 다시 실행해 주세요')
    return passed


def _safe(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception as error:                      # 학습자의 함수에서 난 오류는 실패로 센다
        return error


def check_practice_3(build_prompt, latest_version_rows, rule):
    """실습 3: 프롬프트를 만드는 함수와 구판을 제외하는 함수를 작은 입력으로 확인한다."""
    hits = [Hit(0.9, 'SOP-A', 'v1.0', 'SOP', '2026-01-01', '관리 기준', '## 관리 기준\n본문 가'),
            Hit(0.8, 'QIR-B', 'v2.0', '품질이슈', '2026-02-01', '현상', '## 현상\n본문 나')]
    question = '질문입니다'
    with_rule = _safe(build_prompt, hits, question)
    without_rule = _safe(build_prompt, hits, question, use_rule=False)
    ok_text = isinstance(with_rule, str) and isinstance(without_rule, str)

    chunks = [Chunk('A', 'v1.0', 'SOP', '2025-01-01', '절1', '가'), Chunk('A', 'v2.0', 'SOP', '2026-01-01', '절1', '나'),
              Chunk('A', 'v2.0', 'SOP', '2026-01-01', '절2', '다'), Chunk('B', 'v1.0', 'SOP', '2026-01-01', '절1', '라'),
              Chunk('C', 'v1.9', 'SOP', '2025-01-01', '절1', '마'), Chunk('C', 'v1.10', 'SOP', '2026-01-01', '절1', '바')]
    rows = _safe(latest_version_rows, chunks)
    single = _safe(latest_version_rows, chunks[3:4])

    results = [
        ('build_prompt: 검색 결과의 청크마다 [문서번호_버전]이 앞에 붙는다',
         ok_text and '[SOP-A_v1.0]' in with_rule and '[QIR-B_v2.0]' in with_rule),
        ('build_prompt: 청크의 본문이 순서대로 들어간다',
         ok_text and '본문 가' in with_rule and '본문 나' in with_rule and with_rule.index('본문 가') < with_rule.index('본문 나')),
        ('build_prompt: 질문이 프롬프트의 맨 끝에 있다', ok_text and with_rule.rstrip().endswith(question)),
        ('build_prompt: use_rule=True이면 근거 없음 규칙이 들어간다', ok_text and rule in with_rule),
        ('build_prompt: use_rule=False이면 근거 없음 규칙이 들어가지 않는다', ok_text and rule not in without_rule
         and '근거를 찾지 못했습니다' not in without_rule),
        ('build_prompt: 검색 결과 앞에 지시 글(역할 지정 등)이 있다',
         ok_text and '[SOP-A_v1.0]' in with_rule and with_rule[:with_rule.index('[SOP-A_v1.0]')].strip() != ''),
        ('build_prompt: 출력 규칙(문장마다 근거 [문서번호]를 붙인다)이 들어간다',
         ok_text and '[문서번호]' in with_rule and '[문서번호]' in without_rule),
        ('build_prompt: 근거 없음 규칙이 검색 결과 뒤, 질문 앞에 있다',
         ok_text and with_rule.index('본문 나') < with_rule.index(rule) < with_rule.rindex(question)),
        ('latest_version_rows: 버전이 가장 높은 문서의 청크 행만 남긴다(같은 버전의 청크는 모두 남긴다)', rows == [1, 2, 3, 5]),
        ('latest_version_rows: 버전을 숫자로 비교한다(v1.10이 v1.9보다 높다)', isinstance(rows, list) and 5 in rows and 4 not in rows),
        ('latest_version_rows: 판이 하나뿐인 문서는 그대로 남긴다', single == [0]),
    ]
    return _report('실습 3', results)
