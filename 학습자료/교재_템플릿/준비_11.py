# 설치: python -m pip install transformers torch peft
# 11장의 예제는 1장의 공개 모델 Qwen2.5-0.5B-Instruct를 PC의 CPU에서 학습합니다. 처음 한 번 약 1GB를 내려받습니다
# API 키가 없어도 예제와 실습은 실행할 수 있습니다. 아래 연결 확인에서 오류가 나도
# "학습 데이터" 줄이 출력됐으면 계속 진행합니다. 키가 없으면 "준비 (1)"의 입력 칸에서 Enter만 누릅니다
import csv

import embed
import torch

MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
embed.ask_endpoint(MODEL)                         # 모델이 PC에 없고 HF_ENDPOINT가 비어 있으면 주소를 묻습니다
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.utils import logging as transformers_logging
transformers_logging.disable_progress_bar()
torch.manual_seed(0)                              # LoRA 행렬의 초깃값을 실행할 때마다 같게 합니다
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32)   # CPU는 bf16 계산이 느려 fp32로 올립니다
model.generation_config.update(do_sample=False, temperature=None, top_p=None, top_k=None)  # 언제나 1위 토큰을 고릅니다

with open(f'{DATA}/알람.csv', encoding='utf-8') as file:
    alarms = list(csv.DictReader(file))           # 설비 알람 96건. 열: 번호, 알람, 표준, 용도
train_rows = [row for row in alarms if row['용도'] == '학습']
eval_rows = [row for row in alarms if row['용도'] == '평가']
SYSTEM = '설비 알람을 사내 표준 형식으로 바꿔 답한다.'


def chat_prompt(alarm, system=SYSTEM):
    """시스템 프롬프트와 알람을 채팅 템플릿에 넣고, 모델의 답 차례를 여는 표시까지 붙인 글"""
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': alarm}]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def make_batch(rows, max_length=128):
    """학습 데이터 여러 건을 패딩한 배치로 만듭니다. 손실은 답(표준 형식) 부분에서만 계산합니다"""
    texts = [chat_prompt(row['알람']) + row['표준'] + '<|im_end|>' for row in rows]
    batch = tokenizer(texts, padding=True, truncation=True, max_length=max_length, return_tensors='pt')
    labels = batch['input_ids'].clone()
    for index, row in enumerate(rows):
        prompt_length = len(tokenizer(chat_prompt(row['알람']))['input_ids'])
        labels[index, :prompt_length] = -100      # -100인 위치는 손실 계산에서 뺍니다
    labels[batch['attention_mask'] == 0] = -100   # 패딩 위치도 뺍니다
    batch['labels'] = labels
    return batch


def answer(model, alarm, system=SYSTEM):
    """알람 하나에 대한 모델의 답(최대 20토큰)"""
    model.eval()
    inputs = tokenizer(chat_prompt(alarm, system), return_tensors='pt')
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=20)
    return tokenizer.decode(output[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()


print(f'PC에서 학습하는 모델: {MODEL}')
print(f'학습 데이터 {len(train_rows)}건, 평가셋 {len(eval_rows)}건. 예: {train_rows[0]["알람"]} → {train_rows[0]["표준"]}')
