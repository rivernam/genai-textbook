"""2일차 재료 검사. tools/make_data_day2.py가 만든 파일을 확인한다."""
import re
from pathlib import Path

import pandas as pd
import pytest

DATA = Path(__file__).resolve().parents[1] / '노트북' / 'data' / '2일차'
LABELS = {'문서안내', '절차안내', '데이터요청', '긴급', '기타'}
LONG = 250  # 이 글자 수를 넘으면 "긴 문의"


def load(name):
    return pd.read_csv(DATA / name, dtype=str, keep_default_na=False)


def is_blank(text):
    return not text.strip()


def has_contact(text):
    return bool(re.search(r'[\w.]+@[\w.]+', text) or re.search(r'01\d-\d{3,4}-\d{4}', text))


@pytest.mark.parametrize('name', ['문의_예제.csv', '문의_예제_정답.csv',
                                  '문의_실습.csv', '문의_실습_정답.csv'])
def test_utf8_bom_for_excel(name):
    assert (DATA / name).read_bytes()[:3] == b'\xef\xbb\xbf'


@pytest.mark.parametrize('name, count, prefix', [('문의_예제.csv', 100, 'Q'),
                                                 ('문의_실습.csv', 60, 'P')])
def test_inquiry_files(name, count, prefix):
    frame = load(name)
    assert list(frame.columns) == ['id', '문의내용']
    assert len(frame) == count
    assert frame['id'].is_unique
    assert all(re.fullmatch(prefix + r'\d{3}', value) for value in frame['id'])


@pytest.mark.parametrize('inquiries, answers', [('문의_예제.csv', '문의_예제_정답.csv'),
                                                ('문의_실습.csv', '문의_실습_정답.csv')])
def test_answers_cover_every_nonblank_inquiry(inquiries, answers):
    frame, answer = load(inquiries), load(answers)
    assert list(answer.columns) == ['id', 'category', 'urgent', '난이도']
    nonblank = set(frame.loc[~frame['문의내용'].map(is_blank), 'id'])
    assert set(answer['id']) == nonblank
    assert set(answer['category']) <= LABELS
    assert set(answer['urgent']) <= {'true', 'false'}
    assert set(answer['난이도']) <= {'보통', '엣지'}
    # 긴급으로 분류한 문의는 모두 urgent가 true다
    assert set(answer.loc[answer['category'] == '긴급', 'urgent']) == {'true'}
    # 다섯 라벨이 모두 쓰인다
    assert set(answer['category']) == LABELS


def test_example_planted_cases():
    frame = load('문의_예제.csv')
    text = frame['문의내용']
    assert text.map(is_blank).sum() == 2
    assert (text.str.len() > LONG).sum() == 3
    assert text.map(has_contact).sum() == 0
    assert (load('문의_예제_정답.csv')['난이도'] == '엣지').sum() == 12


def test_practice_planted_cases():
    frame = load('문의_실습.csv')
    text = frame['문의내용']
    assert text.map(is_blank).sum() == 2
    assert (text.str.len() > LONG).sum() == 2
    assert text.map(has_contact).sum() == 2
    assert (load('문의_실습_정답.csv')['category'] == '기타').sum() == 3


def test_no_overlap_between_example_and_practice():
    example = {text for text in load('문의_예제.csv')['문의내용'] if not is_blank(text)}
    practice = {text for text in load('문의_실습.csv')['문의내용'] if not is_blank(text)}
    assert not example & practice


# ---- 파트 2 실습 재료: 접수 요청 ----

TEAMS = {'설비', '시설', 'IT', '안전', '기타'}


@pytest.mark.parametrize('name', ['접수_실습.csv', '접수_실습_정답.csv'])
def test_receipt_files_have_bom(name):
    assert (DATA / name).read_bytes()[:3] == b'\xef\xbb\xbf'


def test_receipts_and_answers():
    receipts, answers = load('접수_실습.csv'), load('접수_실습_정답.csv')
    assert list(receipts.columns) == ['id', '접수시각', '본문']
    assert list(answers.columns) == ['id', 'team', 'location', 'urgent', '난이도']
    assert len(receipts) == 80 and receipts['id'].is_unique
    assert list(receipts['id']) == list(answers['id'])
    assert receipts['본문'].is_unique and not receipts['본문'].map(is_blank).any()
    assert list(receipts['접수시각']) == sorted(receipts['접수시각'])
    assert set(answers['team']) == TEAMS
    assert set(answers['urgent']) <= {'true', 'false'}
    assert answers['team'].value_counts().to_dict() == {'설비': 22, '시설': 18, 'IT': 16, '안전': 14, '기타': 10}


def test_receipt_answers_follow_the_rules():
    receipts, answers = load('접수_실습.csv'), load('접수_실습_정답.csv')
    text = dict(zip(receipts['id'], receipts['본문']))
    for _, row in answers.iterrows():
        # 위치는 본문의 글자 그대로다. 그래야 "본문에 없는 위치를 지어냈는가"를 코드로 검사할 수 있다
        assert row['location'] in text[row['id']], row['id']
        if row['team'] == '기타':
            assert row['urgent'] == 'false' and row['location'] == '', row['id']
    assert (answers['location'] == '').sum() >= 25          # 위치가 없는 접수가 충분히 있다
    assert (answers['난이도'] == '엣지').sum() >= 12


def test_receipt_rule_text_names_every_team():
    rule = (DATA / '접수_규칙.txt').read_text(encoding='utf-8')
    assert all(f'- {team}:' in rule for team in TEAMS)
    assert 'null' in rule and 'urgent' in rule
