#!/usr/bin/env python3
import argparse
import getpass
import hashlib
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = os.environ.get('DEEPSEARCH_BASE_URL', 'http://192.168.10.65:3200/api/v1')
CACHE_DIR = Path.home() / '.cache' / 'deepsearch-api-ops'


def cache_path(base_url: str) -> Path:
    digest = hashlib.sha256(base_url.encode('utf-8')).hexdigest()[:16]
    return CACHE_DIR / f'{digest}.json'


def save_tokens(base_url: str, payload: dict) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = cache_path(base_url)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def load_tokens(base_url: str) -> dict:
    path = cache_path(base_url)
    if not path.exists():
        raise SystemExit(f'No cached token for {base_url}. Run login first.')
    return json.loads(path.read_text(encoding='utf-8'))


def resolve_base_url(args) -> str:
    return getattr(args, 'base_url', None) or getattr(args, 'global_base_url', None) or DEFAULT_BASE_URL


def request_json(method: str, url: str, headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode('utf-8')
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        try:
            payload = json.loads(body) if body else None
        except json.JSONDecodeError:
            payload = {'raw': body}
        print(json.dumps({'status': exc.code, 'error': payload}, ensure_ascii=False, indent=2))
        raise SystemExit(exc.code)


def normalize_query_items(query_items: list[str]) -> list[tuple[str, str]]:
    normalized: list[tuple[str, str]] = []
    for item in query_items:
        if '=' not in item:
            raise SystemExit(f'Invalid query item: {item}. Use key=value format.')
        key, value = item.split('=', 1)
        normalized.append((key, value))
    return normalized


def build_url(base_url: str, path: str, query_items: list[str]) -> str:
    base = base_url.rstrip('/')
    suffix = path if path.startswith('/') else '/' + path
    if query_items:
        query = urllib.parse.urlencode(normalize_query_items(query_items))
        return f'{base}{suffix}?{query}'
    return f'{base}{suffix}'


def cmd_login(args):
    base_url = resolve_base_url(args)
    username = args.username or input('Username: ').strip()
    if not username:
        raise SystemExit('Username is required.')
    password = args.password or getpass.getpass('Password: ')
    if not password:
        raise SystemExit('Password is required.')
    url = build_url(base_url, '/auth/login', [])
    payload = json.dumps({'username': username, 'password': password}).encode('utf-8')
    status, data = request_json('POST', url, headers={'Content-Type': 'application/json'}, data=payload)
    path = save_tokens(base_url, data)
    print(json.dumps({'status': status, 'token_cache': str(path), 'user': username}, ensure_ascii=False, indent=2))


def auth_headers(base_url: str) -> dict:
    token = load_tokens(base_url).get('access_token')
    if not token:
        raise SystemExit(f'Cached token for {base_url} is missing access_token. Run login again.')
    return {'Authorization': f'Bearer {token}'}


def cmd_call(args):
    base_url = resolve_base_url(args)
    url = build_url(base_url, args.path, args.query or [])
    headers = auth_headers(base_url)
    data = None
    if args.json:
        headers['Content-Type'] = 'application/json'
        data = args.json.encode('utf-8')
    status, payload = request_json(args.method.upper(), url, headers=headers, data=data)
    print(json.dumps({'status': status, 'data': payload}, ensure_ascii=False, indent=2))


def encode_multipart(fields, files):
    boundary = '----DeepSearchBoundary7MA4YWxkTrZu0gW'
    body = bytearray()
    for name, value in fields:
        body.extend(f'--{boundary}\r\n'.encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(str(value).encode('utf-8'))
        body.extend(b'\r\n')
    for field_name, file_path in files:
        filename = os.path.basename(file_path)
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        with open(file_path, 'rb') as fh:
            content = fh.read()
        body.extend(f'--{boundary}\r\n'.encode())
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
        )
        body.extend(f'Content-Type: {content_type}\r\n\r\n'.encode())
        body.extend(content)
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode())
    return boundary, bytes(body)


def cmd_upload(args):
    base_url = resolve_base_url(args)
    file_path = os.path.abspath(args.file)
    if not os.path.exists(file_path):
        raise SystemExit(f'File not found: {file_path}')
    url = build_url(base_url, '/files/upload', [])
    headers = auth_headers(base_url)
    fields = []
    if args.folder_path:
        fields.append(('folder_path', args.folder_path))
    boundary, body = encode_multipart(fields, [('file', file_path)])
    headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
    status, payload = request_json('POST', url, headers=headers, data=body)
    print(json.dumps({'status': status, 'data': payload}, ensure_ascii=False, indent=2))


def parser():
    p = argparse.ArgumentParser(description='DeepSearch API helper')
    p.add_argument('--base-url', dest='global_base_url', help=f'API base URL, default: {DEFAULT_BASE_URL}')
    sub = p.add_subparsers(dest='command', required=True)

    login = sub.add_parser('login', help='Login and cache tokens')
    login.add_argument('--base-url')
    login.add_argument('--username')
    login.add_argument('--password')
    login.set_defaults(func=cmd_login)

    call = sub.add_parser('call', help='Call an authenticated JSON API')
    call.add_argument('--base-url')
    call.add_argument('--method', required=True, choices=['GET', 'POST', 'PUT', 'DELETE'])
    call.add_argument('--path', required=True, help='API path such as /files or /search')
    call.add_argument('--query', action='append', help='Query param in key=value form; repeatable')
    call.add_argument('--json', help='JSON string body')
    call.set_defaults(func=cmd_call)

    upload = sub.add_parser('upload', help='Upload one file')
    upload.add_argument('--base-url')
    upload.add_argument('--file', required=True)
    upload.add_argument('--folder-path')
    upload.set_defaults(func=cmd_upload)

    return p


if __name__ == '__main__':
    args = parser().parse_args()
    args.func(args)
