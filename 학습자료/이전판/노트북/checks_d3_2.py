"""3일차 파트 2 실습(실습 2)의 테스트. 임베딩 모델도 API도 부르지 않는다.

작은 견본 문서 파일을 임시 폴더에 만들어 학습자의 함수를 검사한다.
"""
import tempfile
from pathlib import Path


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


def _show_errors(outcomes):
    """학습자의 함수가 예외를 냈으면 무엇을 고칠지 알 수 있게 예외의 이름과 내용을 출력한다."""
    for name, outcome in outcomes.items():
        if isinstance(outcome, Exception):
            print(f'{name} 실행 중 오류: {type(outcome).__name__}: {outcome}')


def make_sample_folder(folder):
    """md, docx, xlsx 각 1건과 열리지 않는 파일 2건(0바이트 pdf, 텍스트 파일인 docx)을 만든다."""
    from docx import Document
    from openpyxl import Workbook

    folder = Path(folder)
    (folder / 'a.md').write_text('# A 문서\n본문 줄 하나\n기 밀 · 초안\n본문 줄 둘\n', encoding='utf-8')
    document = Document()
    document.add_heading('B 문서', level=1)
    document.add_paragraph('본문 줄 셋')
    document.add_paragraph('— 계속 —')
    document.save(folder / 'b.docx')
    book = Workbook()
    sheet = book.active
    for row in [('알람 코드표', None, None), (None, None, None), ('코드', '설비군', '알람명'),
                ('E-1', 'ETCH', '압력 상한'), ('E-2', 'CVD', None), ('E-3', 'CVD', '기밀 누설')]:
        sheet.append(row)
    book.save(folder / 'c.xlsx')
    (folder / 'd.pdf').write_bytes(b'')
    (folder / 'e.docx').write_text('이 파일은 docx가 아닙니다', encoding='utf-8')
    return folder


def check_pipeline(find_header_row, read_xlsx, drop_noise, process):
    """실습 2: 함수 네 개의 동작을 확인한다."""
    with tempfile.TemporaryDirectory() as temp:
        folder = make_sample_folder(temp)
        header = _safe(find_header_row, [('제목', None, None), (None, None, None), ('a', 'b', 'c'), (1, 2, 3)])
        header_first = _safe(find_header_row, [('a', 'b'), (1, 2)])
        no_header = _safe(find_header_row, [('제목', None), (None, None)])
        text_raw = _safe(read_xlsx, folder / 'c.xlsx')
        text = text_raw if isinstance(text_raw, str) else ''
        kept = _safe(drop_noise, ['본문 A', '기 밀 · 초안', '- 1 -', '본문 B', '문서관리시스템 안내'], ['기밀', '문서관리시스템'])
        chunks, report = [], {}
        outcome = _safe(process, folder, ['기밀', '— 계속 —'], 30)
        _show_errors({'find_header_row': header, 'read_xlsx': text_raw, 'drop_noise': kept, 'process': outcome})
        if isinstance(outcome, tuple) and len(outcome) == 2 and isinstance(outcome[1], dict):
            chunks, report = outcome
        failed = report.get('실패', [])
        results = [
            ('find_header_row: 모든 칸이 채워진 첫 줄의 위치를 돌려준다(첫 줄이면 0)', header == 2 and header_first == 0),
            ('find_header_row: 그런 줄이 없으면 None을 돌려준다', no_header is None),
            ('read_xlsx: 장식 줄이 아니라 열 이름 줄부터 읽고, 열 이름이 값 앞에 붙는다', '코드' in text and 'E-1' in text and '알람 코드표' not in text),
            ('read_xlsx: 데이터 한 행이 한 줄이 되고, 빈 칸은 쓰지 않는다', len(text.strip().split('\n')) == 3 and 'None' not in text and 'nan' not in text),
            ('drop_noise: 글자 사이가 벌어진 줄과 쪽번호 줄을 지우고 (남긴 줄, 지운 줄 수)를 돌려준다',
             kept == (['본문 A', '본문 B'], 3)),
            ('process: 열린 파일 3건', report.get('열린 파일') == 3),
            ('process: 열리지 않은 파일 2건을 (파일 이름, 오류 이름)으로 남긴다',
             sorted(name for name, _ in failed) == ['d.pdf', 'e.docx'] and all(isinstance(kind, str) for _, kind in failed)),
            ('process: 지운 줄 수를 센다(md 1줄, docx 1줄)', report.get('지운 줄') == 2),
            ('process: 엑셀의 행 문장에는 노이즈 규칙을 적용하지 않는다(알람명 "기밀 누설"이 남는다)',
             '기밀 누설' in ''.join(chunk['text'] for chunk in chunks if chunk.get('doc_id') == 'c')),
            ('process: 청크는 doc_id와 text를 갖고 길이가 size 이하다',
             bool(chunks) and all(set(chunk) >= {'doc_id', 'text'} and len(chunk['text']) <= 30 for chunk in chunks)),
            ('process: 청크에 지운 줄의 글이 남아 있지 않다',
             not any('기 밀' in chunk['text'] or '계속' in chunk['text'] for chunk in chunks)),
            ('process: 세 파일의 청크가 모두 있다', {chunk['doc_id'] for chunk in chunks} == {'a', 'b', 'c'}),
        ]
    return _report('실습 2', results)
