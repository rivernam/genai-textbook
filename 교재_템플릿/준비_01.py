# 설치: python -m pip install transformers torch
# 1장의 예제는 PC에서 공개 소형 LLM을 실행해 토큰과 확률을 직접 봅니다. 처음 한 번 약 1GB를 내려받습니다
# API 키가 없어도 예제 1-1~1-3과 실습은 실행할 수 있습니다. 아래 연결 확인에서 오류가 나도
# "PC에서 실행하는 모델" 줄이 출력됐으면 계속 진행합니다
import embed
import torch
LOCAL_MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
embed.ask_endpoint(LOCAL_MODEL)          # 모델이 PC에 없고 HF_ENDPOINT가 비어 있으면 주소를 묻습니다
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.utils import logging as transformers_logging
transformers_logging.disable_progress_bar()
tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL)
model = AutoModelForCausalLM.from_pretrained(LOCAL_MODEL)
model.eval()                              # 학습하지 않고 계산만 합니다
print('PC에서 실행하는 모델:', LOCAL_MODEL)
