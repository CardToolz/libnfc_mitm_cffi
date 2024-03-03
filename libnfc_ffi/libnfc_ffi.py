#!/usr/bin/python3
from cffi import FFI

ffi = FFI()

def fetch_nfc_functions(hfile):
    lines = []
    with open(hfile) as f:
        for ln in f:
            if ln.startswith("NFC_EXPORT"):
                ln = ln.replace("NFC_EXPORT", "extern")
                ln = ln.replace("ATTRIBUTE_NONNULL(1)", "")
                # ln = ln.replace("typedef ", "")
                lines.append(ln)
    return "".join(lines)


def fetch_nfc_types(hfile):
    with open(hfile) as f:
        data = f.read() 
        data = data[data.index("#endif") + len("#endif"): data.index("#  pragma pack()")]
        data = data.replace("NFC_BUFSIZE_CONNSTRING", "1024")
        # data = data.replace("typedef ", "")
    return data

def fetch_nfc_constants(hfile):
    lines = []
    with open(hfile) as f:
        for ln in f:
            if ln.startswith("#define"):
                lines.append(ln)
    return "".join(lines)

def ffi_print_declarations(ffi):
    for key in ffi._parser._declarations:
        print(key, ffi._parser._declarations[key])

cdef_types = fetch_nfc_types("/usr/include/nfc/nfc-types.h")
# print (cdef_types)
cdef_funcs = fetch_nfc_functions("/usr/include/nfc/nfc.h")
cdef_defs = fetch_nfc_constants("/usr/include/nfc/nfc.h")

ffi.cdef(cdef_types, packed=True)
ffi.cdef(cdef_funcs, packed=True)
ffi.cdef(cdef_defs, packed=True)
      

libnfc = ffi.dlopen("libnfc.so")


if __name__ == "__main__":
    print("CFFI binding for libNFC")
    ver_str = ffi.string(libnfc.nfc_version()).decode("utf-8")
    print("libNFC version:", ver_str)
    print("imported types:")
    ffi_print_declarations(ffi)

    # some constants tst
    # print(sErrorMessages[libnfc.NFC_ECHIP])    
    # print(libnfc.NP_INFINITE_SELECT)