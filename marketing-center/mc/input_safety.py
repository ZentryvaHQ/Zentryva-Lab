"""Reject explicit credential fields before writing local input snapshots.

Not a general secret detector: operators must still use synthetic, non-secret data.
"""
from urllib.parse import urlsplit, parse_qsl

SENSITIVE={'apikey','accesstoken','refreshtoken','password','secret','clientsecret','authorization','privatekey','token'}

def sensitive_key(value):
    return ''.join(c for c in str(value).casefold() if c.isalnum()) in SENSITIVE

def check_input(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if sensitive_key(key):raise ValueError('Credential fields are forbidden in shadow inputs')
            check_input(item)
    elif isinstance(value,list):
        for item in value:check_input(item)
    elif isinstance(value,str):
        uri=urlsplit(value)
        if uri.scheme.casefold() not in ('http','https'):return
        parameters=parse_qsl(uri.query)+parse_qsl(uri.fragment)
        if uri.username or uri.password or any(sensitive_key(k) for k,_ in parameters):
            raise ValueError('Credential-bearing URLs are forbidden')
