DATA = 'data/1일차'


def read_material(name):
    """재료 폴더(data/1일차)의 파일을 읽어 문자열로 돌려줍니다."""
    return open(f'{DATA}/{name}', encoding='utf-8').read().strip()
