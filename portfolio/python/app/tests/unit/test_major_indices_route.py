from types import SimpleNamespace

from api.v1.market.stock import get_major_indices


def test_major_indices_returns_the_index_list():
    indices = get_major_indices(request=None, current_user=SimpleNamespace(id=1))

    assert any(index["symbol"] == "^GSPC" for index in indices)
