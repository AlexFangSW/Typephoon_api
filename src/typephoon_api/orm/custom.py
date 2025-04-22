from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles


class BigSerial(BigInteger):
    pass


@compiles(BigSerial, "postgresql")
def compile_bigserial(element, compiler, **kw):
    return "BIGSERIAL"
