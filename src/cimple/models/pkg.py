import pydantic


class PkgId(pydantic.BaseModel):
    name: str
    version: str
