# 설치: python -m pip install transformers torch
# 2장의 예제는 PC에서 공개 소형 LLM 두 개(베이스 모델과 instruct 모델)를 실행합니다. 처음 한 번 각각 약 1GB를 내려받습니다
# API 키가 없어도 예제 2-1, 2-2와 실습은 실행할 수 있습니다. 아래 연결 확인에서 오류가 나도
# "PC에서 실행하는 모델" 줄이 출력됐으면 계속 진행합니다. 키가 없으면 "준비 (1)"의 입력 칸에서 Enter만 누릅니다
import embed
import torch
BASE_MODEL = 'Qwen/Qwen2.5-0.5B'                  # 사전 학습만 마친 베이스 모델
INSTRUCT_MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'     # 같은 베이스 모델에 SFT와 강화 학습을 더한 모델
for name in [BASE_MODEL, INSTRUCT_MODEL]:
    embed.ask_endpoint(name)                      # 모델이 PC에 없고 HF_ENDPOINT가 비어 있으면 주소를 묻습니다
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.utils import logging as transformers_logging
transformers_logging.disable_progress_bar()
tokenizer = AutoTokenizer.from_pretrained(INSTRUCT_MODEL)   # 두 모델은 어휘가 같아 토크나이저 하나로 씁니다
base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL).eval()
instruct_model = AutoModelForCausalLM.from_pretrained(INSTRUCT_MODEL).eval()
for local_model in [base_model, instruct_model]:  # 두 모델 모두 반복 억제 없이 언제나 1위 토큰을 고르게(greedy decoding) 설정합니다
    local_model.generation_config.update(do_sample=False, temperature=None, top_p=None, top_k=None,
                                         repetition_penalty=None)


def generate(model, characters, start, length=30):
    """예제 2-1용. 앞 8글자를 보고 다음 글자를 샘플링해 붙이는 일을 되풀이합니다(1장의 네 단계)"""
    ids = [characters.index(ch) for ch in start]
    for _ in range(length):
        with torch.no_grad():
            logits = model(torch.tensor([ids[-8:]]))[0]
        ids.append(torch.multinomial(torch.softmax(logits, dim=-1), 1).item())
    return ''.join(characters[i] for i in ids).replace('\n', ' / ')


print('PC에서 실행하는 모델:', BASE_MODEL, INSTRUCT_MODEL)
