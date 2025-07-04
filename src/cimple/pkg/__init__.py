import cimple.common.image as image


def build_pkg():
    # with open("./pkg.toml", "rb") as f:
    #     config_dict = tomllib.load(f)
    #     config = pkg_config.PkgConfig.model_validate(config_dict)

    image.prepare_image("windows", "x86_64", "bootstrap-msys")
