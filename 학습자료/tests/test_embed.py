"""노트북/embed.py: 모델을 불러오는 순서와 접두어를 가짜 모델로 확인한다. 실제 모델은 부르지 않는다."""
import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '노트북'))


class FakeModel:
    def __init__(self):
        self.seen = []

    def encode(self, texts, normalize_embeddings=False, batch_size=32):
        self.seen.append(list(texts))
        assert normalize_embeddings
        return np.ones((len(texts), 4)) / 2


@pytest.fixture
def embed(monkeypatch):
    module = importlib.import_module('embed')
    monkeypatch.setattr(module, '_model', None)
    monkeypatch.delenv('EMBED_MODEL', raising=False)
    monkeypatch.delenv('HF_ENDPOINT', raising=False)
    return module


def test_default_model_and_override(embed, monkeypatch):
    assert embed.model_name() == 'intfloat/multilingual-e5-small'
    monkeypatch.setenv('EMBED_MODEL', 'C:/models/my-model')
    assert embed.model_name() == 'C:/models/my-model'


def test_saved_model_is_used_without_asking(embed, capsys):
    calls = []

    def loader(name, local_only):
        calls.append(local_only)
        return FakeModel()

    def never(prompt):
        raise AssertionError('저장된 모델이 있으면 주소를 묻지 않아야 한다')

    embed.load(loader=loader, prompt=never, saved=lambda name: True)
    assert calls == [True]
    assert 'PC에 저장된' in capsys.readouterr().out


def test_asks_address_only_when_missing_and_never_prints_it(embed, monkeypatch, capsys):
    monkeypatch.delitem(sys.modules, 'huggingface_hub', raising=False)

    def loader(name, local_only):
        if local_only:
            raise OSError('저장된 파일 없음')
        return FakeModel()

    embed.load(loader=loader, prompt=lambda text: ' https://proxy.example/hf ', saved=lambda name: False)
    import os
    assert os.environ['HF_ENDPOINT'] == 'https://proxy.example/hf'
    assert 'proxy.example' not in capsys.readouterr().out


def test_existing_address_is_not_asked_again(embed, monkeypatch):
    monkeypatch.setenv('HF_ENDPOINT', 'https://proxy.example/hf')

    def loader(name, local_only):
        if local_only:
            raise OSError
        return FakeModel()

    def never(prompt):
        raise AssertionError('HF_ENDPOINT가 있으면 묻지 않아야 한다')

    assert isinstance(embed.load(loader=loader, prompt=never), FakeModel)


def test_download_failure_explains_what_to_set(embed, monkeypatch):
    monkeypatch.setenv('HF_ENDPOINT', 'https://proxy.example/hf')

    def loader(name, local_only):
        raise OSError('연결 실패')

    with pytest.raises(RuntimeError) as error:
        embed.load(loader=loader)
    assert 'HF_ENDPOINT' in str(error.value) and 'EMBED_MODEL' in str(error.value)
    assert 'proxy.example' not in str(error.value)


def test_e5_prefixes(embed, monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(embed, '_model', fake)
    assert embed.passages(['가', '나']).shape == (2, 4)
    assert embed.query('질문').shape == (4,)
    assert fake.seen == [['passage: 가', 'passage: 나'], ['query: 질문']]


def test_no_prefix_for_other_models(embed, monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(embed, '_model', fake)
    monkeypatch.setenv('EMBED_MODEL', 'some/other-model')
    embed.passages(['가'])
    embed.query('질문')
    assert fake.seen == [['가'], ['질문']]


def test_address_is_asked_before_the_library_is_imported(embed, monkeypatch):
    """주소를 물을 때는 아직 아무 모델도 불러오지 않아야 한다(huggingface_hub가 주소를 처음에만 읽으므로)."""
    monkeypatch.delitem(sys.modules, 'huggingface_hub', raising=False)
    order = []

    def loader(name, local_only):
        order.append(('load', local_only))
        if local_only:
            raise OSError('저장된 파일 없음')
        return FakeModel()

    def prompt(text):
        order.append('ask')
        return 'https://proxy.example/hf'

    embed.load(loader=loader, prompt=prompt, saved=lambda name: False)
    assert order == ['ask', ('load', True), ('load', False)]


def test_saved_model_is_not_asked_even_without_address(embed):
    def never(prompt):
        raise AssertionError('모델이 PC에 있으면 주소를 묻지 않아야 한다')

    assert isinstance(embed.load(loader=lambda name, local_only: FakeModel(), prompt=never, saved=lambda name: True), FakeModel)


def test_saved_locally_reads_the_cache_folder(embed, monkeypatch, tmp_path):
    monkeypatch.setenv('HF_HUB_CACHE', str(tmp_path))
    assert not embed._saved_locally('org/model')
    (tmp_path / 'models--org--model' / 'snapshots' / 'abc').mkdir(parents=True)
    assert embed._saved_locally('org/model')
    assert embed._saved_locally(str(tmp_path))


def test_missing_package_is_reported_as_install_problem(embed, monkeypatch):
    monkeypatch.setattr(embed.importlib.util, 'find_spec', lambda name: None)
    with pytest.raises(RuntimeError) as error:
        embed.load()
    assert 'pip install sentence-transformers' in str(error.value)
