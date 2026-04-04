# FIXED VERSION (RPM parsing improved)

import re

def parse_blynk_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, list):
            value = value[0] if value else default
        m = re.search(r'-?\d+', str(value))
        return int(m.group(0)) if m else default
    except:
        return default
