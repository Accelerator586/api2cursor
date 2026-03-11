"""Flask 应用工厂

创建并配置 Flask 应用：
  - 注册所有路由蓝图
  - 设置 JSON 错误处理器（避免返回 HTML）
  - 配置全局鉴权中间件
  - 启动日志清理定时任务
"""

import hmac
import logging
import threading

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

import settings
from config import Config
from extensions import limiter
from routes import register_routes
from utils.request_logger import cleanup_old_logs, is_enabled, LOGS_DIR, get_config

logger = logging.getLogger(__name__)


def create_app():
    """创建并配置 Flask 应用实例。

    这里统一完成跨路由共享的初始化逻辑，包括配置加载、跨域、错误处理、
    访问鉴权、健康检查以及蓝图注册。
    """
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
    if Config.CORS_ALLOWED_ORIGINS:
        CORS(app, origins=Config.CORS_ALLOWED_ORIGINS)
    limiter.init_app(app)
    settings.load()
    Config.log_security_warnings()

    # 日志功能状态检查
    logger.info(f'日志功能状态: {"启用" if is_enabled() else "禁用"}')
    logger.info(f'日志目录: {LOGS_DIR}')
    logger.info(f'日志配置: {get_config()}')

    # 启动日志清理定时任务
    _start_log_cleanup_scheduler()

    # ─── JSON 错误处理器 ──────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        """将未匹配到的路径统一转换为 JSON 404 响应。"""
        return jsonify({'error': {'message': '未找到', 'type': 'not_found'}}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        """将不支持的请求方法统一转换为 JSON 405 响应。"""
        return jsonify({'error': {'message': '方法不允许', 'type': 'method_not_allowed'}}), 405

    @app.errorhandler(413)
    def request_too_large(e):
        """将超过限制的请求体统一转换为 JSON 413 响应。"""
        return jsonify({'error': {'message': '请求体过大', 'type': 'request_too_large'}}), 413

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        """将速率限制错误统一转换为 JSON 429 响应。"""
        return jsonify({'error': {'message': '请求过于频繁，请稍后再试', 'type': 'rate_limit_exceeded'}}), 429

    @app.errorhandler(500)
    def internal_error(e):
        """将未捕获的服务端异常统一包装为 JSON 500 响应。"""
        return jsonify({'error': {'message': '服务器内部错误', 'type': 'server_error'}}), 500

    # ─── 全局鉴权中间件 ──────────────────────────

    @app.before_request
    def check_access():
        """在进入业务路由前校验访问密钥。

        当配置了 `ACCESS_API_KEY` 时，除健康检查和管理面板相关路径外，
        所有请求都必须携带正确的 Bearer Token 或 `x-api-key`。
        """
        if not Config.ACCESS_API_KEY:
            return

        # 无需鉴权的路径
        skip = ('/health', '/admin', '/static/', '/api/admin')
        if any(request.path == p or request.path.startswith(p) for p in skip):
            return

        auth = request.headers.get('Authorization', '')
        token = auth[7:] if auth.startswith('Bearer ') else request.headers.get('x-api-key', '')
        if not hmac.compare_digest(token or '', Config.ACCESS_API_KEY):
            logger.warning(f'鉴权拒绝: {request.path}')
            return jsonify({
                'error': {'message': 'API 密钥无效', 'type': 'authentication_error'}
            }), 401

    # ─── 健康检查 ────────────────────────────────

    @app.route('/health', methods=['GET'])
    @limiter.limit(Config.RATE_LIMIT_HEALTH)
    def health():
        """返回服务健康状态。"""
        return jsonify({'status': 'ok'})

    # ─── 注册路由蓝图 ────────────────────────────

    register_routes(app)

    return app


def _start_log_cleanup_scheduler():
    """启动后台线程定期清理过期日志。"""
    def cleanup_task():
        import time
        while True:
            try:
                cleanup_old_logs()
            except Exception as e:
                logger.error(f'日志清理任务失败: {e}')
            # 每天清理一次
            time.sleep(24 * 60 * 60)

    thread = threading.Thread(target=cleanup_task, daemon=True, name='LogCleanup')
    thread.start()
    logger.info('日志清理定时任务已启动')
