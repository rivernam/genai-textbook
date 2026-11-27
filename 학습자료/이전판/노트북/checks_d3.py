"""3일차 파트 1 실습(실습 1)의 테스트. 임베딩 모델도 API도 부르지 않는다."""
import copy
import hashlib
import tempfile
from pathlib import Path

import numpy as np


def _report(name, results):
    for number, (label, ok) in enumerate(results, 1):
        print(f'{number}.', '통과' if ok else '실패', label)
    passed = all(ok for _, ok in results)
    print(f'{name} 통과' if passed else f'{name}: 실패한 항목을 고쳐 다시 실행해 주세요')
    return passed


def _safe(function, *args):
    try:
        return function(*args)
    except Exception as error:                      # 학습자의 함수에서 난 오류는 실패로 센다
        return error


def fake_embed(text):
    """모델 대신 쓰는 임베딩. 같은 글은 늘 같은 벡터, 다른 글은 다른 벡터가 나온다."""
    seed = int(hashlib.md5(text.encode('utf-8')).hexdigest()[:8], 16)
    vector = np.random.default_rng(seed).standard_normal(8)
    return vector / np.linalg.norm(vector)


def _snapshot(index):
    return (list(index.names), list(index.docs), index.vectors.copy())


def _unchanged(index, snapshot):
    names, docs, vectors = snapshot
    return (list(index.names) == names and list(index.docs) == docs
            and index.vectors.shape == vectors.shape and bool(np.array_equal(index.vectors, vectors)))


def check_apply_changes(apply_changes, VectorIndex):
    """실습 1: 작은 인덱스에 변경 목록을 반영해 보고, 잘못된 목록은 아무것도 고치지 않는지 확인한다."""
    names = ['A', 'B', 'C', 'D', 'E']
    docs = [f'문서 {name}의 본문' for name in names]
    base = VectorIndex(names, docs, np.array([fake_embed(doc) for doc in docs]), 'fake')
    with tempfile.TemporaryDirectory() as folder:
        for name, text in [('B', '개정된 문서 B'), ('F', '새 문서 F'), ('G', '새 문서 G')]:
            (Path(folder) / f'{name}.md').write_text(text, encoding='utf-8')

        index = copy.deepcopy(base)
        result = _safe(apply_changes, index, ['B'], ['F'], ['D', 'E'], folder, fake_embed)
        applied = not isinstance(result, Exception)
        if not applied:                                # 정상 목록에서 난 예외는 1~6번이 모두 실패하는 이유이므로 먼저 보여 준다
            print('정상 목록을 반영하다 오류가 났습니다:', f'{type(result).__name__}: {result}')
        by_name = dict(zip(index.names, index.docs))
        rows_match = applied and all(
            bool(np.allclose(index.vectors[row], fake_embed(index.docs[row]))) for row in range(len(index.names)))

        broken = copy.deepcopy(base)
        before = _snapshot(broken)
        unknown_retired = _safe(apply_changes, broken, ['B'], ['F'], ['D', '없는문서'], folder, fake_embed)
        unknown_ok = isinstance(unknown_retired, ValueError) and _unchanged(broken, before)
        unknown_revised = _safe(apply_changes, broken, ['B', '없는문서'], [], [], folder, fake_embed)
        unknown_revised_ok = isinstance(unknown_revised, ValueError) and _unchanged(broken, before)
        # 개정 B를 앞에 두어, 미리 검사하지 않고 add()의 오류에 기대는 구현은 B가 이미 고쳐져 실패한다
        duplicated = _safe(apply_changes, broken, ['B'], ['A'], [], folder, fake_embed)
        duplicated_ok = isinstance(duplicated, ValueError) and _unchanged(broken, before)
        no_file = _safe(apply_changes, broken, ['C'], ['F'], [], folder, fake_embed)
        no_file_ok = isinstance(no_file, ValueError) and _unchanged(broken, before)
        no_added_file = _safe(apply_changes, broken, ['B'], ['H'], [], folder, fake_embed)
        no_added_file_ok = isinstance(no_added_file, ValueError) and _unchanged(broken, before)

        def failing_embed(text):                       # 신규 문서 F를 임베딩할 때 오류가 나는 모델
            if text == '새 문서 F':
                raise RuntimeError('임베딩 실패')
            return fake_embed(text)

        embed_failed = _safe(apply_changes, broken, ['B'], ['F'], ['D'], folder, failing_embed)
        # 과제는 오류의 종류를 정하지 않으므로 어떤 예외든 받는다. 정상 목록을 반영하지 못하는 구현이 통과하지 않게 applied도 본다
        embed_failed_ok = applied and isinstance(embed_failed, Exception) and _unchanged(broken, before)

    results = [
        ('개정: 해당 문서의 본문을 새 파일의 글로 바꾼다', applied and by_name.get('B') == '개정된 문서 B'),
        ('신규: 맨 아래에 새 문서가 추가된다', applied and index.names[-1:] == ['F'] and by_name.get('F') == '새 문서 F'),
        ('폐기: 폐기한 문서가 인덱스에서 없어진다', applied and 'D' not in index.names and 'E' not in index.names),
        ('벡터, 문서 번호, 본문의 개수가 같다', applied and len(index.names) == len(index.docs) == len(index.vectors) == 4),
        ('모든 행의 벡터가 그 행의 본문을 임베딩한 값이다(순서가 어긋나지 않았다)', rows_match),
        ('반환값이 {"교체": 1, "추가": 1, "삭제": 2, "행 수": 4}이다',
         result == {'교체': 1, '추가': 1, '삭제': 2, '행 수': 4}),
        ('폐기 목록에 인덱스에 없는 문서가 있으면 ValueError를 내고 아무것도 고치지 않는다', unknown_ok),
        ('개정 목록에 인덱스에 없는 문서가 있으면 ValueError를 내고 아무것도 고치지 않는다', unknown_revised_ok),
        ('신규 목록에 이미 있는 문서가 있으면 ValueError를 내고 아무것도 고치지 않는다', duplicated_ok),
        ('개정 목록의 문서 파일이 없으면 ValueError를 내고 아무것도 고치지 않는다', no_file_ok),
        ('신규 목록의 문서 파일이 없으면 ValueError를 내고 아무것도 고치지 않는다', no_added_file_ok),
        ('임베딩 중에 오류가 나도 인덱스가 그대로다(벡터를 먼저 모두 계산한 뒤 반영한다)', embed_failed_ok),
    ]
    return _report('실습 1', results)
