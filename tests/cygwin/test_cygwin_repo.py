import pathlib
import tempfile

import pytest

from cimple import pkg


def test_download_cygwin_file(cygwin_release_content_side_effect, mocker):
    mocker.patch("cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect)

    url_path = "x86_64/setup.xz"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN: Downloading the Cygwin file
        downloaded_file = pkg.cygwin.download_cygwin_file(url_path, pathlib.Path(tmpdir))

        # THEN: The file should be downloaded and exist at the target path
        assert downloaded_file.exists(), f"Downloaded file does not exist at {downloaded_file}"
        assert downloaded_file.name == "setup.xz", "Downloaded file has unexpected name"


@pytest.mark.parametrize(
    "release_content,expected_package,expected_version,expected_install,expected_depends",
    [
        (
            """
@ 2048-cli
sdesc: "2048 game for terminal"
ldesc: "A CLI version/engine of the game 2048 for your *NIX terminal."
category: Games Unmaintained
version: 0.9.1-1
install: x86_64/release/2048-cli/2048-cli-0.9.1-1.tar.xz 9548 b33704135031a4728b9ecf7fc72d53e661974f147420c4473eafe135d72eb102528bcb4889c645453b216355db4a9e17b6b63eb7578b7e9c9341c5f27a53f4e0
source: x86_64/release/2048-cli/2048-cli-0.9.1-1-src.tar.xz 118896 363ab00a3db123bb4db69e313b63cbc5e70166afd4849e7ba5654b4ffc8d315b3c26233dca195f1f909d57a38dce0cc5b6e8523d72312072c1697bc3135812b7
depends2: cygwin, libncursesw10
""",  # noqa: E501
            "2048-cli",
            "0.9.1-1",
            "x86_64/release/2048-cli/2048-cli-0.9.1-1.tar.xz",
            ["cygwin", "libncursesw10"],
        ),  # Simple
        (
            """
# This file was automatically generated at 2025-08-10 15:12:36 GMT.
#
# If you edit it, your edits will be discarded next time the file is
# generated.
#
# See https://sourceware.org/cygwin-apps/setup.ini.html for a description
# of the format.
release: cygwin
arch: x86_64
setup-timestamp: 1754838756
include-setup: setup <2.878 not supported
setup-minimum-version: 2.903
setup-version: 2.934

@ 2048-cli
sdesc: "2048 game for terminal"
ldesc: "A CLI version/engine of the game 2048 for your *NIX terminal."
category: Games Unmaintained
version: 0.9.1-1
install: x86_64/release/2048-cli/2048-cli-0.9.1-1.tar.xz 9548 b33704135031a4728b9ecf7fc72d53e661974f147420c4473eafe135d72eb102528bcb4889c645453b216355db4a9e17b6b63eb7578b7e9c9341c5f27a53f4e0
source: x86_64/release/2048-cli/2048-cli-0.9.1-1-src.tar.xz 118896 363ab00a3db123bb4db69e313b63cbc5e70166afd4849e7ba5654b4ffc8d315b3c26233dca195f1f909d57a38dce0cc5b6e8523d72312072c1697bc3135812b7
depends2: cygwin, libncursesw10
""",  # noqa: E501
            "2048-cli",
            "0.9.1-1",
            "x86_64/release/2048-cli/2048-cli-0.9.1-1.tar.xz",
            ["cygwin", "libncursesw10"],
        ),  # With preamble
        (
            """@ a2ps
sdesc: "Anything to PostScript converter"
ldesc: "a2ps is an Any to PostScript filter. It started as a Text to
PostScript converter, with pretty printing features and all the expected
features from this kind of programs. But today, it is also able to deal with
other file types (PostScript, Texinfo, compressed, whatever...) provided you
have the necessary tools."
category: Text Unmaintained
version: 4.15.7-0
install: x86_64/release/a2ps/a2ps-4.15.7-0-x86_64.tar.xz 674140 c5794ffa80b567c0feeb4792e55544ca825878d343a6fc517d7e9bf21483f96ede6234732f273e2ec4faa87d871b3cf3fb4cfad809e992b2321770679fb128e4
source: x86_64/release/a2ps/a2ps-4.15.7-0-src.tar.xz 3550496 b597fd07263a34eeca7269ee079d93f659b5a0b326f1fa0f86bee2a240cc20344f62c818eb7668785c6012e9dfe61ca9fa80f5272e0853a64e20423a7443f654
depends2: bash, cygutils-extra, cygwin, ghostscript, html2ps, libgc1, libintl8, libpaper1, perl_base, texlive-collection-fontutils, texlive-collection-latex, wdiff
build-depends: autoconf, automake, bison, bzip2, cloc, cygport, cygutils-extra, emacs, file, gettext-devel, ghostscript, gperf, groff, groff-perl, help2man, html2ps, html2ps, libgc-devel, libpaper-devel, libtool, pkg-config, texinfo, texlive-collection-fontutils, texlive-collection-latex, wdiff, xhtml2ps, xorg-x11-fonts-Type1
[prev]
version: 4.14-2
install: x86_64/release/a2ps/a2ps-4.14-2.tar.bz2 1109452 a69931bb9f2b3aa5a2b04a539c5cab6cfe120e05fe5eb827ef0aa6f9e4b91bdb39c9051d78ef82eb380c5f2d82ac64f26fb1c643305c67911f584977d191d754
source: x86_64/release/a2ps/a2ps-4.14-2-src.tar.bz2 2952031 596fd48b3e2e181984678c4846d7ca51f8876b724d475ca5f448a62e24c78076074b2df89d664a835562cddd27da39992987cd63f750b7dfad56c0b6563453a3
depends2: ImageMagick, bash, bzip2, cygutils-extra, cygwin, file, font-ibm-type1, ghostscript, ghostscript-fonts-std, groff, gv, gzip, html2ps, libiconv2, libintl8, libpaper1, perl, texinfo-tex, texlive, texlive-collection-fontutils, texlive-collection-latex
[prev]
version: 4.14-3
install: x86_64/release/a2ps/a2ps-4.14-3.tar.xz 950292 cde9c3be2cb21e0c7f88bc047869b96891bfef25497d85ae111cf40eb7dea84a832cd5826c9edd29224b90975864b253951b32178b8c0c67a71e8576c0a796fd
source: x86_64/release/a2ps/a2ps-4.14-3-src.tar.xz 2913740 8125933ad2463940f6fcc92c4839767b82e77eac01b4b95ab60fe6f7b03480c2deb2043fedc4e7e7aeacc829503d579ef8a34a1a67c940c8d457e1d1d72a40fe
depends2: ImageMagick, bash, bzip2, cygutils-extra, cygwin, file, font-ibm-type1, ghostscript, ghostscript-fonts-std, groff, gv, gzip, html2ps, libiconv2, libintl8, libpaper1, perl, texinfo-tex, texlive, texlive-collection-fontutils, texlive-collection-latex
""",  # noqa: E501
            "a2ps",
            "4.14-3",
            "x86_64/release/a2ps/a2ps-4.14-3.tar.xz",
            [
                "ImageMagick",
                "bash",
                "bzip2",
                "cygutils-extra",
                "cygwin",
                "file",
                "font-ibm-type1",
                "ghostscript",
                "ghostscript-fonts-std",
                "groff",
                "gv",
                "gzip",
                "html2ps",
                "libiconv2",
                "libintl8",
                "libpaper1",
                "perl",
                "texinfo-tex",
                "texlive",
                "texlive-collection-fontutils",
                "texlive-collection-latex",
            ],
        ),  # With multiple versions
        (
            """@ a2ps
sdesc: "Anything to PostScript converter"
ldesc: "a2ps is an Any to PostScript filter. It started as a Text to
PostScript converter, with pretty printing features and all the expected
features from this kind of programs. But today, it is also able to deal with
other file types (PostScript, Texinfo, compressed, whatever...) provided you
have the necessary tools."
category: Text Unmaintained
version: 4.15.7-0
install: x86_64/release/a2ps/a2ps-4.15.7-0-x86_64.tar.xz 674140 c5794ffa80b567c0feeb4792e55544ca825878d343a6fc517d7e9bf21483f96ede6234732f273e2ec4faa87d871b3cf3fb4cfad809e992b2321770679fb128e4
source: x86_64/release/a2ps/a2ps-4.15.7-0-src.tar.xz 3550496 b597fd07263a34eeca7269ee079d93f659b5a0b326f1fa0f86bee2a240cc20344f62c818eb7668785c6012e9dfe61ca9fa80f5272e0853a64e20423a7443f654
depends2: bash, cygutils-extra, cygwin, ghostscript, html2ps, libgc1, libintl8, libpaper1, perl_base, texlive-collection-fontutils, texlive-collection-latex, wdiff
build-depends: autoconf, automake, bison, bzip2, cloc, cygport, cygutils-extra, emacs, file, gettext-devel, ghostscript, gperf, groff, groff-perl, help2man, html2ps, html2ps, libgc-devel, libpaper-devel, libtool, pkg-config, texinfo, texlive-collection-fontutils, texlive-collection-latex, wdiff, xhtml2ps, xorg-x11-fonts-Type1
[prev]
version: 4.14-2
install: x86_64/release/a2ps/a2ps-4.14-2.tar.bz2 1109452 a69931bb9f2b3aa5a2b04a539c5cab6cfe120e05fe5eb827ef0aa6f9e4b91bdb39c9051d78ef82eb380c5f2d82ac64f26fb1c643305c67911f584977d191d754
source: x86_64/release/a2ps/a2ps-4.14-2-src.tar.bz2 2952031 596fd48b3e2e181984678c4846d7ca51f8876b724d475ca5f448a62e24c78076074b2df89d664a835562cddd27da39992987cd63f750b7dfad56c0b6563453a3
depends2: ImageMagick, bash, bzip2, cygutils-extra, cygwin, file, font-ibm-type1, ghostscript, ghostscript-fonts-std, groff, gv, gzip, html2ps, libiconv2, libintl8, libpaper1, perl, texinfo-tex, texlive, texlive-collection-fontutils, texlive-collection-latex
[prev]
version: 4.14-3
install: x86_64/release/a2ps/a2ps-4.14-3.tar.xz 950292 cde9c3be2cb21e0c7f88bc047869b96891bfef25497d85ae111cf40eb7dea84a832cd5826c9edd29224b90975864b253951b32178b8c0c67a71e8576c0a796fd
source: x86_64/release/a2ps/a2ps-4.14-3-src.tar.xz 2913740 8125933ad2463940f6fcc92c4839767b82e77eac01b4b95ab60fe6f7b03480c2deb2043fedc4e7e7aeacc829503d579ef8a34a1a67c940c8d457e1d1d72a40fe
depends2: ImageMagick, bash, bzip2, cygutils-extra, cygwin, file, font-ibm-type1, ghostscript, ghostscript-fonts-std, groff, gv, gzip, html2ps, libiconv2, libintl8, libpaper1, perl, texinfo-tex, texlive, texlive-collection-fontutils, texlive-collection-latex
""",  # noqa: E501
            "a2ps",
            "4.15.7-0",
            "x86_64/release/a2ps/a2ps-4.15.7-0-x86_64.tar.xz",
            [
                "bash",
                "cygutils-extra",
                "cygwin",
                "ghostscript",
                "html2ps",
                "libgc1",
                "libintl8",
                "libpaper1",
                "perl_base",
                "texlive-collection-fontutils",
                "texlive-collection-latex",
                "wdiff",
            ],
        ),  # All versions are available
        (
            """@ avahi
sdesc: "Avahi service discovery suite (daemon)"
ldesc: "
Avahi is a free, LGPL implementation of DNS Service Discovery (DNS-SD RFC 6763)
over Multicast DNS (mDNS RFC 6762), commonly known as 'Zerconf' and compatible
with Apple Bonjour.

This enables you to plug your laptop or computer into a network and instantly be
able to view other people who you can chat with, find printers to print to, or
find files being shared."
category: Net Unmaintained
version: 0.8-1
install: x86_64/release/avahi/avahi-0.8-1.tar.xz 150680 82ff9ebfca3e4927d821fe4198f533e95e48d506a16dc57598559002a8ec304de7eac900f0bb113d6a5f72fccbba2887357cdae273e869476aeb72cd70fcdaa9
source: x86_64/release/avahi/avahi-0.8-1-src.tar.xz 1604244 59c9d247e11cf1636543fcf59204c63b0310d250829aab02b13da309312165d78a67bd9d47e6c6d32a0388090ca271ae35e6a887d82ec58e9386192001c5e520
depends2: bash, csih, cygwin, dbus, libavahi-common3, libavahi-core7, libdaemon0, libdbus1_3, libexpat1, mDNSResponder
build-depends: cygport, gettext-devel, gobject-introspection, libQt5Core-devel, libdaemon-devel, libdbus1-devel, libdns_sd-devel, libevent-devel, libexpat-devel, libgdbm-devel, libglib2.0-devel, libgtk2.0-devel, libgtk3-devel, libiconv-devel, libintl-devel, python-gi-devel, python39-dbus, xmltoman
[prev]
version: 0.6.32-1
install: x86_64/release/avahi/avahi-0.6.32-1.tar.xz 143300 6f068906ec5dec6e7969d1a115386a69e820dadb3ad3e275bac8198019cf45cf80fbf5fb11ab9ead0e00183ed97a916e3224ea857b9486193627d9870110b900
source: x86_64/release/avahi/avahi-0.6.32-1-src.tar.xz 1309620 921162d70a89fd35250236d12d11ed3f73369464672c4f307f715b4d63888ccb4f4dcf9a98c678bd8e2ae4554f2f1ae604ceeb008c13b1e444b3eaf51dde3e1d
depends2: bash, csih, cygwin, dbus, libavahi-common3, libavahi-core7, libdaemon0, libdbus1_3, libexpat1, libssp0, mDNSResponder
[prev]
version: 0.7-1
install: x86_64/release/avahi/avahi-0.7-1.tar.xz 147020 81443372b48a442f7e367254afb6cc2a699e412d3f6c0b8a409d0391c63d7e9703ee300c946533595d118b11a0527315037de312d0a7c1baafb5ea5a85ae6c67
source: x86_64/release/avahi/avahi-0.7-1-src.tar.xz 1348848 4bad13e99ee3d14dea67fa3e180cdead32b418644af37d39c1a4108b5adcef1b3701d412fd950ae7e09ee38ce5029626c7f3f6df5618c5471cf79845ba6488da
depends2: bash, csih, cygwin, dbus, libavahi-common3, libavahi-core7, libdaemon0, libdbus1_3, libexpat1, mDNSResponder
""",  # noqa: E501
            "avahi",
            "0.7-1",
            "x86_64/release/avahi/avahi-0.7-1.tar.xz",
            [
                "bash",
                "csih",
                "cygwin",
                "dbus",
                "libavahi-common3",
                "libavahi-core7",
                "libdaemon0",
                "libdbus1_3",
                "libexpat1",
                "mDNSResponder",
            ],
        ),  # With quoted empty lines
    ],
    ids=[
        "test_parse_release_simple",
        "test_parse_cygwin_release_with_preamble",
        "test_parse_cygwin_release_with_multiple_versions",
        "test_parse_cygwin_release_all_versions_are_available",
        "test_parse_cygwin_release_with_empty_lines",
    ],
)
def test_parse_release_simple(
    release_content, expected_package, expected_version, expected_install, expected_depends
):
    # GIVEN: A Cygwin release content
    cygwin_release = pkg.cygwin.CygwinRelease()
    assert not cygwin_release.initialized, "CygwinRelease should not be initialized yet"

    # WHEN: Parsing the release content
    cygwin_release.parse_release_file(release_content)

    # THEN: The package should be parsed correctly
    package_key = f"{expected_package}-{expected_version}"
    assert package_key in cygwin_release.packages
    package = cygwin_release.packages[package_key]
    assert package.name == expected_package
    assert package.version == expected_version
    assert package.install_path == expected_install
    assert package.depends == expected_depends


def test_parse_cygwin_release_full(
    cygwin_release_content_side_effect,
    mocker,
):
    mocker.patch("cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect)

    # WHEN: Parsing the Cygwin release for the package
    cygwin_release = pkg.cygwin.CygwinRelease()
    assert cygwin_release.initialized is False, "CygwinRelease should not be initialized yet"
    cygwin_release.parse_release_from_repo()

    # THEN: The function should return the correct package install_path
    expected_packages = [
        # Multiple versions
        (
            "make",
            "4.4.1-2",
            "x86_64/release/make/make-4.4.1-2.tar.xz",
            ["cygwin", "libguile3.0_1", "libintl8"],
        ),
        (
            "make",
            "4.4-1",
            "x86_64/release/make/make-4.4-1.tar.xz",
            ["cygwin", "libguile3.0_1", "libintl8"],
        ),
        # Other packages
        (
            "liblcms2_2",
            "2.14-1",
            "x86_64/release/lcms2/liblcms2_2/liblcms2_2-2.14-1.tar.xz",
            ["cygwin"],
        ),
        # coreutils, this is special because it uses [test] sections
        (
            "coreutils",
            "9.0-1",
            "x86_64/release/coreutils/coreutils-9.0-1.tar.xz",
            ["cygwin", "libattr1", "libgcc1", "libgmp10", "libiconv2", "libintl8", "tzcode"],
        ),
        # cygwin itself
        # This package uses [test] section, dependency version requirements, and _windows
        (
            "cygwin",
            "3.6.4-1",
            "x86_64/release/cygwin/cygwin-3.6.4-1-x86_64.tar.xz",
            ["bash", "libgcc1", "libintl8", "libzstd1", "zlib0"],
        ),
    ]
    for (
        expected_package_name,
        expected_version,
        expected_install_path,
        expected_dependencies,
    ) in expected_packages:
        package_key = f"{expected_package_name}-{expected_version}"
        assert package_key in cygwin_release.packages
        assert cygwin_release.packages[package_key].name == expected_package_name
        assert cygwin_release.packages[package_key].version == expected_version
        assert cygwin_release.packages[package_key].install_path == expected_install_path
        assert cygwin_release.packages[package_key].depends == expected_dependencies


def test_parse_cygwin_release_test_versions_are_skipped(cygwin_release_content_side_effect, mocker):
    mocker.patch("cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect)

    # WHEN: Parsing the Cygwin release for the package
    cygwin_release = pkg.cygwin.CygwinRelease()
    assert cygwin_release.initialized is False, "CygwinRelease should not be initialized yet"
    cygwin_release.parse_release_from_repo()

    # THEN: Test versions should be skipped
    # coreutils-9.5-1 is a test version and should be skipped
    assert "coreutils-9.5-1" not in cygwin_release.packages
