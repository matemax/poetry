import os

from cleo.testers import CommandTester

from poetry.__version__ import __version__
from poetry.packages.package import Package
from poetry.semver.version import Version
from poetry.utils._compat import WINDOWS
from poetry.utils._compat import Path


FIXTURES = Path(__file__).parent.joinpath("fixtures")


def test_self_update_should_install_all_necessary_elements(
    app, http, mocker, environ, tmp_dir
):
    os.environ["POETRY_HOME"] = tmp_dir

    command = app.find("self update")

    version = Version.parse(__version__).next_minor.text
    mocker.patch(
        "poetry.repositories.pypi_repository.PyPiRepository.find_packages",
        return_value=[Package("poetry", version)],
    )
    mocker.patch.object(command, "_check_recommended_installation", return_value=None)
    mocker.patch.object(
        command, "_get_release_name", return_value="poetry-{}-darwin".format(version)
    )

    http.register_uri(
        "GET",
        command.BASE_URL + "/{}/poetry-{}-darwin.sha256sum".format(version, version),
        body=FIXTURES.joinpath("poetry-1.0.5-darwin.sha256sum").read_bytes(),
    )
    http.register_uri(
        "GET",
        command.BASE_URL + "/{}/poetry-{}-darwin.tar.gz".format(version, version),
        body=FIXTURES.joinpath("poetry-1.0.5-darwin.tar.gz").read_bytes(),
    )

    tester = CommandTester(command)
    tester.execute()

    bin_ = Path(tmp_dir).joinpath("bin")
    lib = Path(tmp_dir).joinpath("lib")
    assert bin_.exists()

    script = bin_.joinpath("poetry")
    assert script.exists()

    expected_script = """\
# -*- coding: utf-8 -*-
import glob
import sys
import os

lib = os.path.normpath(os.path.join(os.path.realpath(__file__), "../..", "lib"))
vendors = os.path.join(lib, "poetry", "_vendor")
current_vendors = os.path.join(
    vendors, "py{}".format(".".join(str(v) for v in sys.version_info[:2]))
)
sys.path.insert(0, lib)
sys.path.insert(0, current_vendors)

if __name__ == "__main__":
    from poetry.console import main
    main()
"""
    if not WINDOWS:
        expected_script = "#!/usr/bin/env python\n" + expected_script

    assert expected_script == script.read_text()

    bat = bin_.joinpath("poetry.bat")
    expected_bat = """\
'@echo off\r\npython "poetry" %*\r\n'
"""
    if WINDOWS:
        assert bat.exists()
        assert expected_bat == bat.read_text()

    assert lib.exists()
    assert lib.joinpath("poetry").exists()
