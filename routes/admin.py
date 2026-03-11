"""路由: 管理面板

提供 Web 管理界面和 API：
  - /admin         — 管理面板页面
  - /v1/models     — 模型列表（供 Cursor 查询）
  - /api/admin/*   — 登录验证、全局设置 CRUD、模型映射 CRUD
"""

import hmac
import ipaddress
import logging
import os
import socket
import subprocess
from urllib.parse import urlparse

from flask import Blueprint, request, jsonify, send_from_directory

import settings
from config import Config
from extensions import limiter

logger = logging.getLogger(__name__)

_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')

bp = Blueprint('admin', __name__)


# ─── 静态页面 ─────────────────────────────────────


@bp.route('/admin')
@bp.route('/admin/')
def admin_page():
    """返回管理面板首页 HTML 页面，供浏览器进入配置界面。"""
    # 获取 git commit hash 作为版本号
    try:
        git_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
    except Exception:
        # 如果获取失败，使用时间戳
        import time
        git_hash = str(int(time.time()))

    # 读取 HTML 文件
    html_path = os.path.join(_STATIC_DIR, 'admin.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # 动态注入版本号
    html = html.replace('/static/admin.js', f'/static/admin.js?v={git_hash}')

    return html, 200, {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }


@bp.route('/static/<path:filename>')
def static_files(filename):
    """提供管理面板所需的静态资源文件。"""
    return send_from_directory(_STATIC_DIR, filename)


# ─── 模型列表 ─────────────────────────────────────


@bp.route('/v1/models', methods=['GET'])
@limiter.limit(Config.RATE_LIMIT_API)
def list_models():
    """返回当前配置的模型列表，供 Cursor 拉取可用模型。"""
    mappings = settings.get().get('model_mappings', {})
    models = [{
        'id': name,
        'object': 'model',
        'owned_by': info.get('backend', 'custom'),
    } for name, info in mappings.items()]

    if not models:
        models.append({
            'id': 'claude-sonnet-4-5-20250929',
            'object': 'model',
            'owned_by': 'anthropic',
        })
    return jsonify({'object': 'list', 'data': models})


# ─── 登录验证 ─────────────────────────────────────


@bp.route('/api/admin/login', methods=['POST'])
@limiter.limit(Config.RATE_LIMIT_LOGIN)
def admin_login():
    """校验管理面板登录密钥，并返回是否允许进入后台。"""
    data = request.get_json(force=True)
    if not Config.ACCESS_API_KEY:
        logger.warning('管理面板在未配置 ACCESS_API_KEY 的情况下被访问。')
        return jsonify({'ok': True, 'message': '未配置鉴权，请勿暴露到公网'})
    if hmac.compare_digest(data.get('key', ''), Config.ACCESS_API_KEY):
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'message': '密钥错误'}), 401


# ─── 全局设置 ─────────────────────────────────────


@bp.route('/api/admin/settings', methods=['GET'])
@limiter.limit(Config.RATE_LIMIT_ADMIN)
def get_settings():
    """读取当前生效的全局代理配置。"""
    err = _check_auth()
    if err:
        return err
    s = settings.get()
    return jsonify({
        'proxy_target_url': s.get('proxy_target_url', ''),
        'proxy_api_key': s.get('proxy_api_key', ''),
        'env_target_url': Config.PROXY_TARGET_URL,
        'env_api_key': '***' if Config.PROXY_API_KEY else '',
        'logging': s.get('logging', {}),
    })


@bp.route('/api/admin/settings', methods=['PUT'])
@limiter.limit(Config.RATE_LIMIT_ADMIN)
def update_settings():
    """更新全局上游地址与密钥配置。"""
    err = _check_auth()
    if err:
        return err
    data = request.get_json(force=True)
    s = settings.get()
    if 'proxy_target_url' in data:
        try:
            s['proxy_target_url'] = _validate_target_url(data.get('proxy_target_url', ''), allow_empty=True)
        except ValueError as exc:
            return jsonify({'error': {'message': str(exc), 'type': 'validation_error'}}), 400
    if 'proxy_api_key' in data:
        s['proxy_api_key'] = data.get('proxy_api_key', '') or ''
    if 'logging' in data:
        logging_config = data.get('logging', {})
        s['logging'] = {
            'enabled': bool(logging_config.get('enabled', True)),
            'retention_days': int(logging_config.get('retention_days', 30)),
            'max_file_size_mb': int(logging_config.get('max_file_size_mb', 100)),
            'log_request_body': bool(logging_config.get('log_request_body', True)),
            'log_response_body': bool(logging_config.get('log_response_body', True)),
        }
    return _save_and_respond(s, '全局设置已更新')


# ─── 模型映射 CRUD ────────────────────────────────


@bp.route('/api/admin/mappings', methods=['GET'])
@limiter.limit(Config.RATE_LIMIT_ADMIN)
def list_mappings():
    """列出所有模型映射配置，供管理面板读取和展示。"""
    err = _check_auth()
    if err:
        return err
    return jsonify(settings.get().get('model_mappings', {}))


@bp.route('/api/admin/mappings', methods=['POST'])
@limiter.limit(Config.RATE_LIMIT_ADMIN)
def add_mapping():
    """新增一条模型映射，并写入持久化配置。"""
    err = _check_auth()
    if err:
        return err
    data = request.get_json(force=True)
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '名称不能为空'}), 400
    try:
        target_url = _validate_target_url(data.get('target_url', ''), allow_empty=True)
    except ValueError as exc:
        return jsonify({'error': {'message': str(exc), 'type': 'validation_error'}}), 400

    s = settings.get()
    mappings = s.setdefault('model_mappings', {})
    mappings[name] = {
        'upstream_model': data.get('upstream_model', name),
        'backend': data.get('backend', 'auto'),
        'target_url': target_url,
        'api_key': data.get('api_key', '') or '',
    }
    return _save_and_respond(s, f'映射已添加: {name}')


@bp.route('/api/admin/mappings/<path:name>', methods=['PUT'])
@limiter.limit(Config.RATE_LIMIT_ADMIN)
def update_mapping(name):
    """更新指定名称的模型映射，必要时支持重命名。"""
    err = _check_auth()
    if err:
        return err
    data = request.get_json(force=True)
    s = settings.get()
    mappings = s.get('model_mappings', {})
    if name not in mappings:
        return jsonify({'error': '映射不存在'}), 404

    new_name = data.get('name', name).strip()
    if not new_name:
        return jsonify({'error': '名称不能为空'}), 400
    try:
        target_url = _validate_target_url(data.get('target_url', ''), allow_empty=True)
    except ValueError as exc:
        return jsonify({'error': {'message': str(exc), 'type': 'validation_error'}}), 400
    entry = {
        'upstream_model': data.get('upstream_model', name),
        'backend': data.get('backend', 'auto'),
        'target_url': target_url,
        'api_key': data.get('api_key', '') or '',
    }
    if new_name != name:
        del mappings[name]
    mappings[new_name] = entry
    s['model_mappings'] = mappings
    return _save_and_respond(s, f'映射已更新: {name} → {new_name}')


@bp.route('/api/admin/mappings/<path:name>', methods=['DELETE'])
@limiter.limit(Config.RATE_LIMIT_ADMIN)
def delete_mapping(name):
    """删除指定名称的模型映射，并在存在时同步保存配置。"""
    err = _check_auth()
    if err:
        return err
    s = settings.get()
    mappings = s.get('model_mappings', {})
    if name in mappings:
        del mappings[name]
        s['model_mappings'] = mappings
        return _save_and_respond(s, f'映射已删除: {name}')
    return jsonify({'ok': True})


# ─── 内部辅助 ─────────────────────────────────────


def _check_auth():
    """Admin API 鉴权，返回 None 表示通过"""
    if not Config.ACCESS_API_KEY:
        return None
    auth = request.headers.get('Authorization', '')
    token = auth[7:] if auth.startswith('Bearer ') else request.headers.get('x-api-key', '')
    if not hmac.compare_digest(token or '', Config.ACCESS_API_KEY):
        return jsonify({'error': '未授权'}), 401
    return None


def _save_and_respond(data, log_msg):
    """保存配置并返回统一成功响应。

    当写盘失败时，这里也负责把异常转成结构化的 JSON 错误返回。
    """
    try:
        settings.save(data)
    except OSError as e:
        logger.error(f'保存失败: {e}')
        return jsonify({'error': {'message': '保存失败，请检查服务端日志', 'type': 'save_error'}}), 500
    logger.info(log_msg)
    return jsonify({'ok': True})


def _validate_target_url(value, *, allow_empty=False):
    """校验自定义上游地址，阻止落到内网或本地回环地址。"""
    url = (value or '').strip()
    if not url:
        if allow_empty:
            return ''
        raise ValueError('目标地址不能为空')

    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError('目标地址必须以 http:// 或 https:// 开头')
    if not parsed.hostname:
        raise ValueError('目标地址缺少主机名')
    if parsed.username or parsed.password:
        raise ValueError('目标地址不支持携带用户名或密码')

    _ensure_public_host(parsed.hostname)
    return url


def _ensure_public_host(hostname):
    """确保目标主机不指向回环、本地链路或私有地址。"""
    if hostname.lower() == 'localhost':
        raise ValueError('目标地址不能指向 localhost')

    try:
        _ensure_public_ip(ipaddress.ip_address(hostname))
        return
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError('目标地址主机名无法解析') from exc

    resolved_ips = {info[4][0] for info in infos if info[4]}
    if not resolved_ips:
        raise ValueError('目标地址主机名无法解析')

    for ip_text in resolved_ips:
        _ensure_public_ip(ipaddress.ip_address(ip_text))


def _ensure_public_ip(ip):
    """拒绝所有非公网地址，降低 SSRF 风险。"""
    if not ip.is_global:
        raise ValueError('目标地址不能指向本地、内网或保留地址')
