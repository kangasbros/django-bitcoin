#
# Django field type for a Bitcoin Address
#
import re
from django import forms
from django.forms.util import ValidationError
import hashlib


class BCAddressField(forms.CharField):
    default_error_messages = {
        'invalid': 'Invalid Bitcoin address.',
        }

    def __init__(self, *args, **kwargs):
        super(BCAddressField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value and not self.required:
            return None
        value = value.strip()
        if re.match(r"[a-zA-Z1-9]{27,35}$", value) is None:
            raise ValidationError(self.error_messages['invalid'])
        version = get_bcaddress_version(value)
        if version is None:
            raise ValidationError(self.error_messages['invalid'])
        return value


def is_valid_btc_address(value):
    value = value.strip()
    if re.match(r"[a-zA-Z1-9]{27,35}$", value) is None:
        return False
    version = get_bcaddress_version(value)
    if version is None:
        return False
    return True


__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)


def b58encode(v):
    """ encode v, which is a string of bytes, to base58.                                                                                                                                                                                                                             
    """

    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += (256**i) * ord(c)

    result = ''
    while long_value >= __b58base:
        div, mod = divmod(long_value, __b58base)
        result = __b58chars[mod] + result
        long_value = div
    result = __b58chars[long_value] + result

    # Bitcoin does a little leading-zero-compression:                                                                                                                                                                                                                                    
    # leading 0-bytes in the input become leading-1s                                                                                                                                                                                                                                     
    nPad = 0
    for c in v:
        if c == '\0': nPad += 1
        else: break

    return (__b58chars[0]*nPad) + result

def b58decode(v, length):
    """ decode v into a string of len bytes                                                                                                                                                                                                                                                        
    """
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base**i)

    result = ''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result

    nPad = 0
    for c in v:
        if c == __b58chars[0]: nPad += 1
        else: break

    result = chr(0)*nPad + result
    if length is not None and len(result) != length:
        return None

    return result


def b36encode(number, alphabet='0123456789abcdefghijklmnopqrstuvwxyz'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, (int, long)):
        long_value = 0L
        for (i, c) in enumerate(number[::-1]):
            long_value += (256**i) * ord(c)
        number = long_value

    base36 = '' if number != 0 else '0'
    sign = ''
    if number < 0:
        sign = '-'
        number = -number

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


def b36decode(number):
    return int(number, 36)


def get_bcaddress_version(strAddress):
    """ Returns None if strAddress is invalid.    Otherwise returns integer version of address. """
    addr = b58decode(strAddress, 25)
    if addr is None: return None
    version = addr[0]
    checksum = addr[-4:]
    vh160 = addr[:-4] # Version plus hash160 is what is checksummed                                                                                                                                                                                                        
    h3=hashlib.sha256(hashlib.sha256(vh160).digest()).digest()
    if h3[0:4] == checksum:
        return ord(version)
    return None
