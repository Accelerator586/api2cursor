"""环境变量配置"""

import logging
import os

logger = logging.getLogger(__name__)


class Config:
    """集中声明服务运行依赖的环境变量配置。

    这个类不承担运行时逻辑，只作为模块级配置容器，统一暴露上游地址、
    鉴权密钥、端口、超时和调试开关，供应用启动、路由鉴权和请求转发层共享。
    """

    # 上游 API 地址
    PROXY_TARGET_URL = os.getenv('PROXY_TARGET_URL', 'https://api.anthropic.com')
    # 上游 API 密钥
    PROXY_API_KEY = os.getenv('PROXY_API_KEY', '')
    # 服务监听端口
    PROXY_PORT = int(os.getenv('PROXY_PORT', '3029'))
    # 请求超时时间（秒）
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', '300'))
    # 访问鉴权密钥，留空则不启用鉴权
    ACCESS_API_KEY = os.getenv('ACCESS_API_KEY', '')
    # 调试模式：开启后输出详细的请求/响应日志
    DEBUG = os.getenv('DEBUG', '').lower() in ('1', 'true', 'yes', 'on')
    # 浏览器跨域白名单；未配置时默认不启用 CORS
    CORS_ALLOWED_ORIGINS = tuple(
        origin.strip()
        for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
        if origin.strip()
    )
    # 最大请求体大小（字节）
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(10 * 1024 * 1024)))
    # 速率限制
    RATE_LIMIT_LOGIN = os.getenv('RATE_LIMIT_LOGIN', '5 per minute')
    RATE_LIMIT_ADMIN = os.getenv('RATE_LIMIT_ADMIN', '30 per minute')
    RATE_LIMIT_API = os.getenv('RATE_LIMIT_API', '120 per minute')
    RATE_LIMIT_HEALTH = os.getenv('RATE_LIMIT_HEALTH', '60 per minute')

    @classmethod
    def log_security_warnings(cls):
        """输出生产部署前需要关注的安全告警。"""
        if not cls.ACCESS_API_KEY:
            logger.warning('未配置 ACCESS_API_KEY；请勿将该服务直接暴露到公网。')
