"""1일차 파트 3 실습 폴더(코딩도구_실습_1일차)의 검사 스크립트와 재료를 확인한다."""
import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / '노트북' / '코딩도구_실습_1일차'


def load_check():
    spec = importlib.util.spec_from_file_location('check_day1', FOLDER / 'check.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_example(tmp_path, change=None):
    text = (FOLDER / '풀이' / '회의요약표_예시.md').read_text(encoding='utf-8')
    (tmp_path / '회의요약표.md').write_text(change(text) if change else text, encoding='utf-8')
    return tmp_path


def passed(results):
    return [name[0] for name, ok, _ in results if ok]


def test_materials_are_the_original_files():
    source = ROOT / '작업' / '1일차' / '원본재료' / 'day01-cc'
    names = sorted(path.name for path in (FOLDER / '작업폴더' / '회의록').glob('*.txt'))
    assert len(names) == 10
    if source.exists():                                   # 작업 폴더는 공유 대상이 아니라 없을 수 있다
        for name in names:
            assert (FOLDER / '작업폴더' / '회의록' / name).read_bytes() == (source / '회의록' / name).read_bytes()


def test_check_and_answers_are_outside_the_working_folder():
    inside = [path.name for path in (FOLDER / '작업폴더').rglob('*') if path.is_file()]
    assert 'check.py' not in inside and not any('예시' in name or '풀이' in name for name in inside)


def test_example_table_passes_all_checks(tmp_path):
    results = load_check().run(copy_example(tmp_path))
    assert passed(results) == list('12345678'), [detail for _, ok, detail in results if not ok]


def test_missing_file_fails_all(tmp_path):
    assert passed(load_check().run(tmp_path)) == []


def test_each_check_catches_its_error(tmp_path):
    check = load_check()
    cases = {
        '1': lambda text: text.replace('| 날짜 | 주제 | 결정 | 액션 | 담당 | 기한 |', '| 날짜 | 회의 | 결정 | 액션 | 담당 | 기한 |'),
        '2': lambda text: '\n'.join(line for line in text.splitlines() if '협력사' not in line),
        '3': lambda text: text.replace('| 2026-08-20 | 신입', '| 8/20 | 신입'),
        '4': lambda text: text.replace('1) 2026-08-28 2) 2026-08-19', '1) 8/28 2) 8/19'),
        '5': lambda text: text.replace('2026-08-25 (다음 주 화요일)', '다음 주 화요일'),
        '6': lambda text: text.replace('캘리 끝날 때까지', '2026-08-21'),
        '7': lambda text: text.replace('회신 | 미기재 | 2026-08-26', '회신 | 이OO | 2026-08-26'),
        '8': lambda text: text.replace('"미기재" 칸 수: 4칸', '"미기재" 칸 수: 5칸'),
    }
    for number, change in cases.items():
        folder = tmp_path / number
        folder.mkdir()
        failed = [name[0] for name, ok, _ in check.run(copy_example(folder, change)) if not ok]
        assert number in failed, (number, failed)
        shutil.rmtree(folder)


def test_weekly_report_counts(tmp_path):
    report = ('[주간 보고]\n\n1. 이번 주 요약\n   - 요약\n\n2. 주요 결정 사항\n   - 결정\n\n3. 다음 주까지 할 일\n'
              '   | 할 일 | 담당 | 기한 | 출처 회의 |\n   | --- | --- | --- | --- |\n   | 일 A | 김OO | 2026-08-24 | 회의 |\n'
              '   | 일 B | 이OO | 2026-08-28 | 회의 |\n\n4. 확인이 필요한 것\n   - 담당 미정 1\n   - 기한 미정 2\n   - 확인 3\n\n'
              '5. 참고한 회의록\n   - 파일.txt\n')
    (tmp_path / '주간보고_초안.md').write_text(report, encoding='utf-8')
    assert load_check().weekly_report_counts(tmp_path) == (2, 3, ['1', '2', '3', '4', '5'])
