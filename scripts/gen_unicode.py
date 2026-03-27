"""Generate Unicode mapping for Gardiner signs."""
import unicodedata
import re

# Build mapping from Unicode names (zero-padded like A001) to codepoints
uni_map = {}
for cp in range(0x13000, 0x13430):
    name = unicodedata.name(chr(cp), '')
    if name.startswith('EGYPTIAN HIEROGLYPH '):
        code = name.replace('EGYPTIAN HIEROGLYPH ', '')
        uni_map[code] = cp

def gardiner_to_unicode_name(gardiner_code):
    m = re.match(r'^([A-Za-z]+?)(\d+)([A-Z]?)$', gardiner_code)
    if not m:
        return gardiner_code
    prefix, num, suffix = m.groups()
    return f'{prefix.upper()}{int(num):03d}{suffix}'

from app.core.gardiner import GARDINER_TRANSLITERATION
missing = [s.code for s in GARDINER_TRANSLITERATION.values() if not s.unicode_char]

found = {}
not_found = []
for code in sorted(missing):
    uname = gardiner_to_unicode_name(code)
    if uname in uni_map:
        found[code] = uni_map[uname]
    else:
        not_found.append(f'{code} -> {uname}')

print(f'Found: {len(found)}, Not found: {len(not_found)}')
if not_found:
    print('Not found:', not_found)
print()
print('GARDINER_UNICODE = {')
for code, cp in sorted(found.items()):
    print(f'    "{code}": "\\U{cp:08X}",')
print('}')
