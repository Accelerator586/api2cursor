"""请求日志收集器

记录每个 API 请求的完整生命周期，包括：
- 请求信息（模型、参数、消息内容）
- 模型映射结果
- 上游 API 调用状态
- 响应数据和 token 使用情况

日志以 JSONL 格式存储，每行一个 JSON 对象，便于追加写入和逐行读取。
"""

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from flask import g, request

logger = logging.getLogger(__name__)

# 日志目录
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(_ROOT_DIR, 'data', 'logs')

# 线程锁，保证并发写入安全
_lock = threading.Lock()

# 日志配置默认值
_DEFAULT_CONFIG = {
    'enabled': True,
    'retention_days': 30,
    'max_file_size_mb': 100,
    'log_request_body': True,
    'log_response_body': True,
}

# 全局配置缓存
_config = dict(_DEFAULT_CONFIG)


def set_config(config: dict[str, Any]) -> None:
    """更新日志配置。"""
    global _config
    _config = {**_DEFAULT_CONFIG, **config}


def get_config() -> dict[str, Any]:
    """获取当前日志配置。"""
    return dict(_config)


def is_enabled() -> bool:
    """检查日志功能是否启用。"""
    return _config.get('enabled', True)


class RequestLogger:
    """请求日志记录器，跟踪单个请求的生命周期。"""

    def __init__(self):
        """初始化日志记录器。"""
        self.log_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.data = {
            'id': self.log_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'client_ip': self._get_client_ip(),
            'request': {},
            'mapping': {},
            'upstream': {},
            'tokens': {},
        }

    def _get_client_ip(self) -> str:
        """获取客户端 IP 地址。"""
        if request.environ.get('HTTP_X_FORWARDED_FOR'):
            return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
        return request.environ.get('REMOTE_ADDR', 'unknown')

    def log_request(self, model: str, payload: dict[str, Any]) -> None:
        """记录请求信息。"""
        if not _config.get('log_request_body', True):
            # 仅记录元数据
            self.data['request'] = {
                'model': model,
                'stream': payload.get('stream', False),
                'message_count': len(payload.get('messages', [])),
            }
        else:
            # 记录完整请求
            self.data['request'] = {
                'model': model,
                'stream': payload.get('stream', False),
                'messages': payload.get('messages', []),
                'temperature': payload.get('temperature'),
                'max_tokens': payload.get('max_tokens'),
                'tools': payload.get('tools', []),
                'tool_choice': payload.get('tool_choice'),
            }

    def log_mapping(
        self,
        original_model: str,
        upstream_model: str,
        backend: str,
        target_url: str,
    ) -> None:
        """记录模型映射信息。"""
        self.data['mapping'] = {
            'original_model': original_model,
            'upstream_model': upstream_model,
            'backend': backend,
            'target_url': target_url,
        }

    def log_upstream_success(
        self,
        status_code: int,
        response_data: Optional[dict[str, Any]] = None,
    ) -> None:
        """记录上游 API 成功响应。"""
        duration_ms = int((time.time() - self.start_time) * 1000)
        self.data['upstream'] = {
            'status_code': status_code,
            'duration_ms': duration_ms,
            'error': None,
        }

        if _config.get('log_response_body', True) and response_data:
            self.data['upstream']['response'] = response_data

        # 提取 token 使用情况
        if response_data and 'usage' in response_data:
            usage = response_data['usage']
            self.data['tokens'] = {
                'prompt': usage.get('prompt_tokens', 0),
                'completion': usage.get('completion_tokens', 0),
                'total': usage.get('total_tokens', 0),
            }

    def log_upstream_error(self, status_code: int, error_message: str) -> None:
        """记录上游 API 错误。"""
        duration_ms = int((time.time() - self.start_time) * 1000)
        self.data['upstream'] = {
            'status_code': status_code,
            'duration_ms': duration_ms,
            'error': error_message,
        }

    def log_stream_complete(self, token_usage: Optional[dict[str, int]] = None) -> None:
        """记录流式响应完成。"""
        duration_ms = int((time.time() - self.start_time) * 1000)
        self.data['upstream'] = {
            'status_code': 200,
            'duration_ms': duration_ms,
            'error': None,
            'stream': True,
        }

        if token_usage:
            self.data['tokens'] = token_usage

    def save(self) -> None:
        """将日志写入文件。"""
        if not is_enabled():
            return

        try:
            # 确保日志目录存在
            os.makedirs(LOGS_DIR, exist_ok=True)

            # 按日期生成日志文件名
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
            log_file = os.path.join(LOGS_DIR, f'requests-{date_str}.jsonl')

            # 线程安全地追加写入
            with _lock:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(self.data, ensure_ascii=False) + '\n')

            logger.debug(f'日志已保存: {self.log_id}')
        except Exception as e:
            logger.error(f'保存日志失败: {e}')


def start_request_logging(model: str, payload: dict[str, Any]) -> Optional[RequestLogger]:
    """开始记录请求，返回日志记录器实例。"""
    if not is_enabled():
        return None

    try:
        req_logger = RequestLogger()
        req_logger.log_request(model, payload)
        # 将日志记录器存储在 Flask 的 g 对象中，供后续使用
        g.request_logger = req_logger
        return req_logger
    except Exception as e:
        logger.error(f'启动请求日志失败: {e}')
        return None


def get_request_logger() -> Optional[RequestLogger]:
    """获取当前请求的日志记录器。"""
    return getattr(g, 'request_logger', None)


def cleanup_old_logs() -> None:
    """清理过期的日志文件。"""
    if not is_enabled():
        return

    try:
        retention_days = _config.get('retention_days', 30)
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        if not os.path.exists(LOGS_DIR):
            return

        for filename in os.listdir(LOGS_DIR):
            if not filename.startswith('requests-') or not filename.endswith('.jsonl'):
                continue

            # 从文件名提取日期
            try:
                date_str = filename[9:19]  # requests-YYYY-MM-DD.jsonl
                file_date = datetime.strptime(date_str, '%Y-%m-%d')

                if file_date < cutoff_date:
                    file_path = os.path.join(LOGS_DIR, filename)
                    os.remove(file_path)
                    logger.info(f'已删除过期日志: {filename}')
            except (ValueError, IndexError):
                continue

    except Exception as e:
        logger.error(f'清理日志失败: {e}')


def get_log_files() -> list[str]:
    """获取所有日志文件列表，按日期倒序排列。"""
    if not os.path.exists(LOGS_DIR):
        return []

    files = []
    for filename in os.listdir(LOGS_DIR):
        if filename.startswith('requests-') and filename.endswith('.jsonl'):
            files.append(os.path.join(LOGS_DIR, filename))

    return sorted(files, reverse=True)
