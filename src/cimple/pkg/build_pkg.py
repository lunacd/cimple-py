import cimple.pkg.pkg_config as pkg_config

def build_pkg():
    with open("./pkg.json", encoding="utf-8") as f:
        config = pkg_config.PkgConfig.model_validate_json(f.read())

    