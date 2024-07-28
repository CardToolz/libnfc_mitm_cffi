#!/usr/bin/python3
from pathlib import Path

from cffi import FFI

NFC_HEADERS = Path("/usr/include/nfc/nfc.h")
NFC_TYPES_HEADERS = Path("/usr/include/nfc/nfc-types.h")


def _fetch_nfc_functions(hfile: Path) -> str:
    lines = []
    with open(hfile) as f:
        for ln in f:
            if ln.startswith("NFC_EXPORT"):
                ln = ln.replace("NFC_EXPORT", "extern")
                ln = ln.replace("ATTRIBUTE_NONNULL(1)", "")
                # ln = ln.replace("typedef ", "")
                lines.append(ln)
    return "".join(lines)


def _fetch_nfc_types(hfile: Path) -> str:
    with open(hfile) as f:
        data = f.read()
        data = data[
            data.index("#endif") + len("#endif") : data.index("#  pragma pack()")
        ]
        data = data.replace("NFC_BUFSIZE_CONNSTRING", "1024")
        # data = data.replace("typedef ", "")
    return data


def _fetch_nfc_constants(hfile: Path) -> str:
    lines = []
    with open(hfile) as f:
        for ln in f:
            if ln.startswith("#define"):
                lines.append(ln)
    return "".join(lines)


def _ffi_print_declarations(ffi: FFI) -> None:
    for key, value in ffi._parser._declarations.items():
        print(key, value)


cdef_types = _fetch_nfc_types(NFC_TYPES_HEADERS)
cdef_funcs = _fetch_nfc_functions(NFC_HEADERS)
cdef_defs = _fetch_nfc_constants(NFC_HEADERS)

ffi = FFI()
ffi.cdef(cdef_types, packed=True)
ffi.cdef(cdef_funcs, packed=True)
ffi.cdef(cdef_defs, packed=True)
libnfc = ffi.dlopen("libnfc.so")


if __name__ == "__main__":
    print("CFFI binding for libNFC")
    ver_str = ffi.string(libnfc.nfc_version()).decode("utf-8")
    print("libNFC version:", ver_str)
    print("imported types:")
    _ffi_print_declarations(ffi)

    # some constants tst
    # print(sErrorMessages[libnfc.NFC_ECHIP])
    # print(libnfc.NP_INFINITE_SELECT)
