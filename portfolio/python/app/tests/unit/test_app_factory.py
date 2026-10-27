"""The app factory keeps the public routes and gives each one id and tag."""

from pathlib import Path

from main import app

_METHODS = {"get", "post", "put", "patch", "delete"}


def _operations():
    schema = app.openapi()
    found = []
    ids = []
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            if method not in _METHODS:
                continue
            found.append(f"{method.upper()} {path}")
            ids.append(operation["operationId"])
            assert len(operation["tags"]) == 1, (
                f"{method.upper()} {path} tags={operation['tags']}"
            )
    return found, ids


def test_routes_match_the_recorded_api():
    found, _ids = _operations()
    expected = Path(__file__).with_name("api_routes.txt").read_text().splitlines()
    assert sorted(found) == expected


def test_operation_ids_are_unique():
    _found, ids = _operations()
    assert len(ids) == len(set(ids))


def test_openapi_operations_match_the_snapshot():
    schema = app.openapi()
    found = []
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            if method not in _METHODS:
                continue
            found.append(f"{method.upper()} {path} {operation['operationId']}")
    expected = (
        Path(__file__).with_name("openapi_operations.txt").read_text().splitlines()
    )
    assert sorted(found) == expected
