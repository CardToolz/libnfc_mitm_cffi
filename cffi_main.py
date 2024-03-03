#!/usr/bin/python3

from libnfc_ffi.libnfc_ffi import ffi, libnfc as nfc

ctx = ffi.new("nfc_context**")

print("nfc_init"), nfc.nfc_init(ctx)
c = ctx[0]
conn_strings = ffi.new("nfc_connstring[10]")
d = nfc.nfc_list_devices(c, conn_strings, 10)
print("nfc_list_devices", d)

device = nfc.nfc_open(c, conn_strings[0])
print("nfc_open", device) 

nfc.nfc_close(device)
print("nfc_close")
