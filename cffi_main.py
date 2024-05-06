#!/usr/bin/python3
from libnfc_ffi import ffi, nfc

ctx = ffi.new("nfc_context**")

print("nfc_init")
nfc.nfc_init(ctx)

c = ctx[0]
conn_strings = ffi.new("nfc_connstring[10]")

devices = nfc.nfc_list_devices(c, conn_strings, 10)
print(f"nfc_list_devices {devices}")

device = nfc.nfc_open(c, conn_strings[0])
print(f"nfc_open {device}")

nfc.nfc_close(device)
print("nfc_close")
