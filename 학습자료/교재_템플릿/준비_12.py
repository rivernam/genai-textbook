# 설치: python -m pip install transformers torch
# 12장의 예제는 1장의 공개 모델 Qwen2.5-0.5B-Instruct를 PC의 CPU에서 실행합니다. 처음 한 번 약 1GB를 내려받습니다
# 예제 12-1~12-3과 실습 12-1은 API 키 없이 실행할 수 있습니다. 실습 12-2만 API를 호출합니다
import csv

import embed
import torch

MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
embed.ask_endpoint(MODEL)                         # 모델이 PC에 없고 HF_ENDPOINT가 비어 있으면 주소를 묻습니다
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.utils import logging as transformers_logging
transformers_logging.disable_progress_bar()
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32)   # 파라미터마다 4바이트(fp32)로 올립니다
model.generation_config.update(do_sample=False, temperature=None, top_p=None, top_k=None)  # 언제나 1위 토큰을 고릅니다

with open(f'{DATA}/후공정_문장.txt', encoding='utf-8') as file:
    sentences = [line.strip() for line in file if line.strip()][:10]   # 손실을 계산할 후공정 문장 10개
with open(f'{DATA}/알람.csv', encoding='utf-8') as file:
    alarms = list(csv.DictReader(file))           # 11장의 설비 알람 96건. 열: 번호, 알람, 표준, 용도


def answer(model, question, max_new_tokens=30):
    """질문 하나에 대한 모델의 답"""
    messages = [{'role': 'system', 'content': '질문에 한 문장으로 답한다.'}, {'role': 'user', 'content': question}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors='pt')
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=max_new_tokens)
    return tokenizer.decode(output[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()


def mean_loss(model):
    """후공정 문장 10개의 평균 손실(2장). 낮을수록 모델이 그 문장을 그럴듯하게 봅니다"""
    total = 0.0
    for sentence in sentences:
        ids = tokenizer(sentence, return_tensors='pt')['input_ids']
        with torch.no_grad():
            total += model(ids, labels=ids).loss.item()
    return total / len(sentences)


# 소형 모델의 100만 토큰당 단가(달러). 5장 "LLM API"의 표, `llm.py`가 쓰는 Anthropic 모델 기준(2026-11 확인)
# 사내 API를 쓰면 사내 안내의 단가로 바꿉니다
PRICES = {'input': 0.10, 'output': 0.50}


print(f'PC에서 실행하는 모델: {MODEL}, 알람 {len(alarms)}건')
