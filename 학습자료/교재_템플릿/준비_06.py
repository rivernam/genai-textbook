# 설치: python -m pip install transformers torch
# 위 패키지는 예제 6-2만 씁니다
# 6장과 관통 프로젝트 2단계에서 씁니다
import csv
import random

with open(f'{DATA}/문의.csv', encoding='utf-8') as file:
    inquiries = list(csv.DictReader(file))        # 문의 60건. 열: 번호, 문의, 라벨, 긴급, 비고
LABELS = ['설비 이상', '품질', '안전', '문서와 데이터 요청']

# 100만 토큰당 단가(달러). 5장과 같습니다(Anthropic API의 기본 모델, 2026-11 확인)
PRICES = {'소형': {'input': 0.10, 'output': 0.50}, '기본': {'input': 2.00, 'output': 10.00},
          '대형': {'input': 4.00, 'output': 20.00}}


def cost(reply, tier):
    """응답 하나의 요금(달러). 입력 토큰과 출력 토큰(thinking 포함)에 각각의 단가를 곱해 더합니다"""
    price = PRICES[tier]
    return (reply.input_tokens * price['input'] + reply.output_tokens * price['output']) / 1_000_000


def parsed(text):
    """응답 텍스트를 JSON으로 파싱합니다. 실패하면 "파싱 오류"와 응답 앞부분을 돌려줍니다"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return f'파싱 오류: {text.strip()[:40]!r}'


def load_local_model():
    """예제 6-2용. 1장의 공개 LLM을 PC에서 불러옵니다. 처음 한 번 약 1GB를 내려받습니다"""
    import embed
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from transformers.utils import logging as transformers_logging
    name = 'Qwen/Qwen2.5-0.5B-Instruct'
    embed.ask_endpoint(name)                     # 모델이 PC에 없고 HF_ENDPOINT가 비어 있으면 주소를 묻습니다
    transformers_logging.disable_progress_bar()
    return AutoTokenizer.from_pretrained(name), AutoModelForCausalLM.from_pretrained(name).eval()


print(f'문의 {len(inquiries)}건, 라벨 {LABELS}')
