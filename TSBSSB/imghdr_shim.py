import sys
import types

# Shim for removed imghdr in Python 3.13+
imghdr = types.ModuleType("imghdr")
def what(file, h=None):
    return None # Minimal shim
imghdr.what = what
sys.modules["imghdr"] = imghdr
