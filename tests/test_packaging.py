from importlib.resources import files

import pytest

import chromaqr.server


@pytest.fixture
def client():
    chromaqr.server.app.config["TESTING"] = True
    with chromaqr.server.app.test_client() as test_client:
        yield test_client


def test_ui_resources_are_package_data():
    package = files("chromaqr")
    for name in ("base.html", "home.html", "demo.html", "realtime.html"):
        assert package.joinpath("templates", name).is_file()
    assert package.joinpath("static", "logo.png").is_file()


@pytest.mark.parametrize("path", ["/", "/demo", "/realtime", "/logo.png"])
def test_packaged_ui_routes(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.data
