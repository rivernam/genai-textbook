"""임베딩 모델을 불러오고 글을 벡터로 바꾸는 공통 함수.

교재의 예제와 실습은 이 파일로 임베딩 모델을 쓴다. 모델은 PC에서 실행하고 요금이 들지 않는다.

환경 변수
  EMBED_MODEL   임베딩 모델의 이름이나, 모델 파일이 든 폴더의 경로. 비워 두면 intfloat/multilingual-e5-small
  HF_ENDPOINT   모델을 내려받을 주소. 사내에서는 사내 Hugging Face 프록시 주소를 넣는다.
                비워 두면 huggingface.co에서 받는다. Jupyter를 시작하기 전에 설정한다.

모델은 처음 한 번만 내려받고(약 470MB), 그 뒤에는 PC에 저장된 파일을 쓴다.
주소는 이 파일에도 노트북에도 적지 않는다. 환경 변수로만 넣는다.
"""
import importlib.util
import os
import sys
from getpass import getpass

DEFAULT_MODEL = 'intfloat/multilingual-e5-small'
_model = None


def model_name():
    """쓸 임베딩 모델의 이름(또는 폴더 경로)."""
    return os.environ.get('EMBED_MODEL', '').strip() or DEFAULT_MODEL


def _uses_prefix(name):
    """e5 계열 모델은 문서에 'passage: ', 질문에 'query: ' 를 앞에 붙여야 한다(모델 카드의 규칙)."""
    return 'e5' in os.path.basename(str(name).rstrip('/\\')).lower()


def _load(name, local_only):
    from sentence_transformers import SentenceTransformer
    try:                                             # 모델을 읽을 때 나오는 진행 표시줄을 끕니다
        from transformers.utils import logging as transformers_logging
        transformers_logging.disable_progress_bar()
    except Exception:
        pass
    return SentenceTransformer(name, local_files_only=local_only)


def _saved_locally(name):
    """모델 파일이 PC에 있는지 확인합니다. huggingface_hub를 불러오지 않고 캐시 폴더만 봅니다.

    huggingface_hub는 처음 불러올 때 HF_ENDPOINT를 한 번만 읽으므로, 주소를 묻기 전에 불러오면 안 됩니다.
    """
    if os.path.isdir(name):
        return True
    cache = (os.environ.get('HF_HUB_CACHE')
             or (os.environ.get('HF_HOME') and os.path.join(os.environ['HF_HOME'], 'hub'))
             or os.path.join(os.environ.get('XDG_CACHE_HOME') or os.path.join(os.path.expanduser('~'), '.cache'),
                             'huggingface', 'hub'))
    snapshots = os.path.join(cache, 'models--' + name.replace('/', '--'), 'snapshots')
    return os.path.isdir(snapshots) and any(os.scandir(snapshots))


def ask_endpoint(name, ask=True, prompt=getpass, saved=_saved_locally):
    """모델이 PC에 없고 HF_ENDPOINT가 비어 있으면 주소를 물어 환경 변수에 넣습니다.

    huggingface_hub(transformers, sentence_transformers가 불러옴)를 불러오기 전에 불러야 합니다.
    임베딩 모델이 아닌 모델(1장의 공개 소형 LLM)을 내려받을 때도 씁니다.
    """
    if not saved(name) and not os.environ.get('HF_ENDPOINT') and ask:
        address = prompt('HF_ENDPOINT (사내 Hugging Face 프록시 주소. huggingface.co에서 직접 받으려면 Enter): ').strip()
        if address:
            if 'huggingface_hub' in sys.modules:
                # 주소는 라이브러리를 처음 불러올 때 한 번만 읽습니다. 이미 불러왔다면 새 주소가 적용되지 않습니다
                raise RuntimeError('HF_ENDPOINT는 Jupyter를 시작하기 전에 설정해야 합니다. '
                                   '환경 변수 HF_ENDPOINT를 설정하고 Jupyter를 다시 시작해 주세요.')
            os.environ['HF_ENDPOINT'] = address


def load(ask=True, loader=_load, prompt=getpass, saved=_saved_locally):
    """임베딩 모델을 불러와 돌려줍니다. 두 번째부터는 불러 둔 모델을 그대로 돌려줍니다.

    PC에 저장된 모델이 있으면 그것을 씁니다. 없으면 HF_ENDPOINT의 주소에서 내려받습니다.
    모델이 PC에 없고 HF_ENDPOINT가 비어 있고 ask가 참이면 주소를 물어봅니다. 입력한 값은
    화면에 보이지 않고 노트북 파일에도 저장되지 않습니다.
    """
    global _model
    if _model is not None:
        return _model
    if loader is _load and importlib.util.find_spec('sentence_transformers') is None:
        raise RuntimeError('sentence-transformers 패키지가 없습니다. '
                           '터미널에서 python -m pip install sentence-transformers 명령을 실행한 뒤 커널을 다시 시작해 주세요.')
    name = model_name()
    ask_endpoint(name, ask, prompt, saved)
    try:
        _model = loader(name, True)                  # PC에 저장된 파일만 씁니다
        print(f'임베딩 모델: {name} (PC에 저장된 파일을 씁니다)')
        return _model
    except Exception:                                # 저장된 파일이 없으면 내려받습니다
        pass
    try:
        _model = loader(name, False)
    except Exception as error:
        raise RuntimeError(
            f'임베딩 모델 {name}을 내려받지 못했습니다. 다음 가운데 하나를 확인해 주세요.\n'
            '  1. 환경 변수 HF_ENDPOINT에 사내 Hugging Face 프록시 주소를 넣고 Jupyter를 다시 시작합니다.\n'
            '  2. 모델 파일이 든 폴더를 따로 받았다면 환경 변수 EMBED_MODEL에 그 폴더의 경로를 넣습니다.\n'
            f'원래 오류: {type(error).__name__}') from error
    print(f'임베딩 모델: {name} (내려받았습니다)')
    return _model


def passages(texts, batch_size=32):
    """문서 글의 목록을 벡터의 배열(문서 수 × 차원)로 바꿉니다. 벡터의 길이는 1로 맞춥니다."""
    name = model_name()
    prefix = 'passage: ' if _uses_prefix(name) else ''
    return load().encode([prefix + text for text in texts], normalize_embeddings=True, batch_size=batch_size)


def query(text):
    """질문 하나를 벡터로 바꿉니다. 벡터의 길이는 1로 맞춥니다."""
    name = model_name()
    prefix = 'query: ' if _uses_prefix(name) else ''
    return load().encode([prefix + text], normalize_embeddings=True)[0]
