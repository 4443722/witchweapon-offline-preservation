"""Change selected binary AXML attributes; preserve compiled resources/classes."""
import struct

U32 = lambda b, p: struct.unpack_from('<I', b, p)[0]
NONE = 0xffffffff

def patch_manifest(data, package='com.codex.witchweapon.local', label='魔女兵器·单人测试'):
    assert struct.unpack_from('<HH', data) == (3, 8)
    chunks = []
    pos = 8
    while pos < len(data):
        kind, header, size = struct.unpack_from('<HHI', data, pos)
        assert size >= header and pos + size <= len(data)
        chunks.append(bytearray(data[pos:pos + size])); pos += size
    pool = chunks[0]
    assert struct.unpack_from('<H', pool)[0] == 1
    count, style_count, flags, strings_start, styles_start = struct.unpack_from('<5I', pool, 8)
    strings = []
    def length8(buf, at):
        n = buf[at]; return (((n & 127) << 8) | buf[at + 1], at + 2) if n & 128 else (n, at + 1)
    def length16(buf, at):
        n = struct.unpack_from('<H', buf, at)[0]
        return (((n & 32767) << 16) | struct.unpack_from('<H', buf, at + 2)[0], at + 4) if n & 32768 else (n, at + 2)
    for i in range(count):
        at = strings_start + U32(pool, 28 + i * 4)
        if flags & 256:
            _, at = length8(pool, at); n, at = length8(pool, at)
            strings.append(bytes(pool[at:at + n]).decode('utf-8'))
        else:
            n, at = length16(pool, at); strings.append(bytes(pool[at:at + n * 2]).decode('utf-16le'))
    def intern(text):
        if text not in strings: strings.append(text)
        return strings.index(text)
    def string_attr(chunk, at, text):
        index = intern(text)
        struct.pack_into('<I', chunk, at + 8, index)
        struct.pack_into('<HBBI', chunk, at + 12, 8, 0, 3, index)
    def value(chunk, at):
        raw = U32(chunk, at + 8)
        if raw != NONE: return strings[raw]
        return strings[U32(chunk, at + 16)] if chunk[at + 15] == 3 else None
    permissions = {'android.permission.INTERNET', 'android.permission.WAKE_LOCK', 'android.permission.VIBRATE',
                   'android.permission.ACCESS_NETWORK_STATE', 'android.permission.ACCESS_WIFI_STATE'}
    output, skipping, removed = [], 0, []
    for chunk in chunks[1:]:
        kind = struct.unpack_from('<H', chunk)[0]
        if skipping:
            if kind == 0x102: skipping += 1
            elif kind == 0x103: skipping -= 1
            continue
        if kind == 0x102:
            tag = strings[U32(chunk, 20)]
            attr_start, attr_size, attr_count = struct.unpack_from('<HHH', chunk, 24)
            assert attr_size == 20
            attrs = {strings[U32(chunk, 16 + attr_start + i * 20 + 4)]: 16 + attr_start + i * 20 for i in range(attr_count)}
            if tag == 'uses-permission':
                name = value(chunk, attrs['name'])
                if name not in permissions:
                    removed.append(name); skipping = 1; continue
            if tag == 'permission':
                removed.append(value(chunk, attrs['name'])); skipping = 1; continue
            if tag in {'service', 'receiver', 'provider'}:
                removed.append(tag + ':' + str(value(chunk, attrs['name']))); skipping = 1; continue
            if tag == 'activity' and value(chunk, attrs['name']) != 'com.shuiqinling.ww.android.LingGameActivity':
                removed.append('activity:' + str(value(chunk, attrs['name']))); skipping = 1; continue
            if tag == 'application' and 'name' in attrs:
                string_attr(chunk, attrs['name'], 'com.codex.witchweapon.OfflineApplication')
            if tag == 'manifest':
                string_attr(chunk, attrs['package'], package)
                if 'versionName' in attrs: string_attr(chunk, attrs['versionName'], '2.0.1-local-stage1')
                if 'versionCode' in attrs:
                    at = attrs['versionCode']; struct.pack_into('<I', chunk, at + 8, NONE)
                    struct.pack_into('<HBBI', chunk, at + 12, 8, 0, 16, 20043077)
            if tag in {'application', 'activity'} and 'label' in attrs: string_attr(chunk, attrs['label'], label)
            if tag == 'provider' and 'authorities' in attrs:
                at = attrs['authorities']; string_attr(chunk, at, value(chunk, at).replace('com.shuiqinling.ww.android.cn00', package))
            if tag == 'data' and 'scheme' in attrs:
                string_attr(chunk, attrs['scheme'], 'codex-witchweapon-local')
        output.append(bytes(chunk))
    offsets, encoded = [], bytearray()
    def enc8(n): return bytes([(n >> 8) | 128, n & 255]) if n >= 128 else bytes([n])
    def enc16(n): return struct.pack('<HH', (n >> 16) | 32768, n & 65535) if n >= 32768 else struct.pack('<H', n)
    for text in strings:
        offsets.append(len(encoded)); units = len(text.encode('utf-16le')) // 2
        if flags & 256:
            raw = text.encode('utf-8'); encoded += enc8(units) + enc8(len(raw)) + raw + b'\0'
        else: encoded += enc16(units) + text.encode('utf-16le') + b'\0\0'
    encoded += b'\0' * (-len(encoded) % 4)
    styles = bytes(pool[styles_start:]) if styles_start else b''
    style_offsets = bytes(pool[28 + count * 4:28 + (count + style_count) * 4])
    start = 28 + (len(strings) + style_count) * 4
    new_styles = start + len(encoded) if styles else 0
    size = start + len(encoded) + len(styles)
    new_pool = struct.pack('<HHI5I', 1, 28, size, len(strings), style_count, flags & ~1, start, new_styles)
    new_pool += struct.pack('<' + 'I' * len(offsets), *offsets) + style_offsets + encoded + styles
    body = new_pool + b''.join(output)
    return struct.pack('<HHI', 3, 8, len(body) + 8) + body, removed
