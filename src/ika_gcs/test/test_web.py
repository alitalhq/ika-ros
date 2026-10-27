import os
import re

WEB = os.path.join(os.path.dirname(__file__), '..', 'web')


def _read(name):
    with open(os.path.join(WEB, name), encoding='utf-8') as f:
        return f.read()


def test_scripts_and_styles_exist():
    html = _read('index.html')
    for ref in re.findall(r'(?:src|href)="([^"]+)"', html):
        assert os.path.isfile(os.path.join(WEB, ref)), ref


def test_app_element_ids_exist_in_html():
    ids = set(re.findall(r'\bid="([^"]+)"', _read('index.html')))
    js = _read('app.js')
    used = set(re.findall(r"\$\('([^']+)'\)", js))
    assert used, 'app.js içinde $(...) kullanımı bulunamadı'
    assert used <= ids, sorted(used - ids)
