"""路由: /api/admin/logs

提供日志查询、过滤、搜索和导出功能。
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Generator, Optional

from flask import Blueprint, jsonify, request, send_file
from werkzeug.exceptions import BadRequest

from config import Config
from extensions import limiter
from utils.request_logger import LOGS_DIR, get_log_files

logger = logging.getLogger(__name__)

bp = Blueprint('logs', __name__)


@bp.route('/api/admin/logs', methods=['GET'])
@limiter.limit(Config.RATE_LIMIT_ADMIN)
def list_logs():
    """查询日志列表，支持分页和过滤。"""
    try:
        # 解析查询参数
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 50)), 200)
        model_filter = request.args.get('model', '').strip()
        status_filter = request.args.get('status', '').strip()
        start_time = request.args.get('start_time', '').strip()
        end_time = request.args.get('end_time', '').strip()
        search_query = request.args.get('search', '').strip()

        # 解析时间范围
        start_dt = _parse_datetime(start_time) if start_time else None
        end_dt = _parse_datetime(end_time) if end_time else None

        # 读取并过滤日志
        logs = []
        total = 0

        for log_entry in _iter_logs(start_dt, end_dt):
            # 应用过滤条件
            if not _matches_filters(log_entry, model_filter, status_filter, search_query):
                continue

            total += 1

            # 分页：跳过前面的页
            if total <= (page - 1) * limit:
                continue

            # 分页：收集当前页的数据
            if len(logs) < limit:
                logs.append(log_entry)

            # 如果已经收集够了，继续计数但不添加
            if len(logs) >= limit and total > page * limit:
                # 优化：如果已经超过当前页，可以提前终止（但需要完整计数）
                pass

        pages = (total + limit - 1) // limit if limit > 0 else 1

        return jsonify({
            'logs': logs,
            'total': total,
            'page': page,
            'pages': pages,
            'limit': limit,
        })

    except ValueError as e:
        return jsonify({'error': {'message': f'参数错误: {e}', 'type': 'invalid_request'}}), 400
    except Exception as e:
        logger.error(f'查询日志失败: {e}')
        return jsonify({'error': {'message': '查询日志失败', 'type': 'server_error'}}), 500


@bp.route('/api/admin/logs/<log_id>', methods=['GET'])
@limiter.limit(Config.RATE_LIMIT_ADMIN)
def get_log_detail(log_id: str):
    """获取单条日志详情。"""
    try:
        # 搜索所有日志文件
        for log_entry in _iter_logs():
            if log_entry.get('id') == log_id:
                return jsonify(log_entry)

        return jsonify({'error': {'message': '日志不存在', 'type': 'not_found'}}), 404

    except Exception as e:
        logger.error(f'获取日志详情失败: {e}')
        return jsonify({'error': {'message': '获取日志详情失败', 'type': 'server_error'}}), 500


@bp.route('/api/admin/logs/export', methods=['GET'])
@limiter.limit(Config.RATE_LIMIT_ADMIN)
def export_logs():
    """导出日志为 JSON 文件。"""
    try:
        # 解析过滤参数（与 list_logs 相同）
        model_filter = request.args.get('model', '').strip()
        status_filter = request.args.get('status', '').strip()
        start_time = request.args.get('start_time', '').strip()
        end_time = request.args.get('end_time', '').strip()
        search_query = request.args.get('search', '').strip()

        start_dt = _parse_datetime(start_time) if start_time else None
        end_dt = _parse_datetime(end_time) if end_time else None

        # 收集符合条件的日志
        logs = []
        total_size = 0
        max_size = 50 * 1024 * 1024  # 50MB 限制

        for log_entry in _iter_logs(start_dt, end_dt):
            if not _matches_filters(log_entry, model_filter, status_filter, search_query):
                continue

            # 估算大小（粗略）
            entry_size = len(json.dumps(log_entry, ensure_ascii=False))
            if total_size + entry_size > max_size:
                logger.warning('导出日志超过大小限制，已截断')
                break

            logs.append(log_entry)
            total_size += entry_size

        # 生成导出文件
        export_data = {
            'exported_at': datetime.utcnow().isoformat() + 'Z',
            'filters': {
                'model': model_filter or None,
                'status': status_filter or None,
                'start_time': start_time or None,
                'end_time': end_time or None,
                'search': search_query or None,
            },
            'total': len(logs),
            'logs': logs,
        }

        # 写入临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
            temp_path = f.name

        # 发送文件
        filename = f'logs-export-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}.json'
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json',
        )

    except Exception as e:
        logger.error(f'导出日志失败: {e}')
        return jsonify({'error': {'message': '导出日志失败', 'type': 'server_error'}}), 500


# ─── 内部辅助函数 ─────────────────────────────────────


def _iter_logs(
    start_dt: Optional[datetime] = None,
    end_dt: Optional[datetime] = None,
) -> Generator[dict[str, Any], None, None]:
    """逐行读取日志文件，返回日志条目生成器。"""
    log_files = get_log_files()

    for log_file in log_files:
        # 从文件名提取日期，判断是否在时间范围内
        try:
            filename = os.path.basename(log_file)
            date_str = filename[9:19]  # requests-YYYY-MM-DD.jsonl
            file_date = datetime.strptime(date_str, '%Y-%m-%d')
            # 添加 UTC 时区信息，使其成为 aware datetime
            file_date = file_date.replace(tzinfo=timezone.utc)

            # 如果文件日期不在范围内，跳过
            if start_dt and file_date < start_dt.replace(hour=0, minute=0, second=0, microsecond=0):
                continue
            if end_dt and file_date > end_dt.replace(hour=23, minute=59, second=59, microsecond=999999):
                continue

        except (ValueError, IndexError):
            # 文件名格式不对，跳过
            continue

        # 逐行读取日志文件
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        log_entry = json.loads(line)

                        # 进一步过滤时间范围（精确到秒）
                        if start_dt or end_dt:
                            timestamp_str = log_entry.get('timestamp', '')
                            try:
                                log_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                if start_dt and log_dt < start_dt:
                                    continue
                                if end_dt and log_dt > end_dt:
                                    continue
                            except (ValueError, AttributeError):
                                pass

                        yield log_entry

                    except json.JSONDecodeError:
                        # 跳过损坏的行
                        continue

        except (OSError, IOError) as e:
            logger.warning(f'读取日志文件失败 {log_file}: {e}')
            continue


def _matches_filters(
    log_entry: dict[str, Any],
    model_filter: str,
    status_filter: str,
    search_query: str,
) -> bool:
    """检查日志条目是否匹配过滤条件。"""
    # 模型过滤（模糊匹配）
    if model_filter:
        original_model = log_entry.get('request', {}).get('model', '')
        upstream_model = log_entry.get('mapping', {}).get('upstream_model', '')
        if model_filter.lower() not in original_model.lower() and \
           model_filter.lower() not in upstream_model.lower():
            return False

    # 状态过滤
    if status_filter:
        status_code = log_entry.get('upstream', {}).get('status_code', 0)
        error = log_entry.get('upstream', {}).get('error')

        if status_filter == 'success' and (status_code < 200 or status_code >= 300 or error):
            return False
        if status_filter == 'error' and (200 <= status_code < 300 and not error):
            return False

    # 增强的全文搜索（搜索更多字段）
    if search_query:
        search_lower = search_query.lower()
        
        # 构建可搜索字段列表
        searchable_fields = [
            log_entry.get('client_ip', ''),
            log_entry.get('request', {}).get('model', ''),
            log_entry.get('mapping', {}).get('upstream_model', ''),
            log_entry.get('mapping', {}).get('backend', ''),
            log_entry.get('upstream', {}).get('error', ''),
        ]
        
        # 搜索消息内容
        messages = log_entry.get('request', {}).get('messages', [])
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, str):
                searchable_fields.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        searchable_fields.append(item.get('text', ''))
        
        # 检查是否在任何字段中找到搜索词
        found = any(search_lower in str(field).lower() for field in searchable_fields)
        
        if not found:
            return False

    return True


def _parse_datetime(dt_str: str) -> datetime:
    """解析 ISO 8601 格式的时间字符串，返回 UTC aware datetime。"""
    try:
        # 支持多种格式
        if 'T' in dt_str:
            # ISO 8601: 2026-03-11T10:30:45Z
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        else:
            # 简单日期: 2026-03-11
            # 解析为 naive datetime，然后添加 UTC 时区
            dt = datetime.strptime(dt_str, '%Y-%m-%d')
            dt = dt.replace(tzinfo=timezone.utc)

        return dt
    except ValueError:
        raise ValueError(f'无效的时间格式: {dt_str}')


@bp.route('/api/admin/logs/stats', methods=['GET'])
@limiter.limit(Config.RATE_LIMIT_ADMIN)
def get_log_stats():
    """获取日志统计信息。"""
    try:
        # 解析时间范围参数
        start_time = request.args.get('start_time', '').strip()
        end_time = request.args.get('end_time', '').strip()
        
        start_dt = _parse_datetime(start_time) if start_time else None
        end_dt = _parse_datetime(end_time) if end_time else None
        
        # 统计数据
        total_requests = 0
        success_count = 0
        error_count = 0
        total_duration = 0
        duration_count = 0
        model_stats = {}
        backend_stats = {}
        
        for log_entry in _iter_logs(start_dt, end_dt):
            total_requests += 1
            
            # 统计成功/失败
            status_code = log_entry.get('upstream', {}).get('status_code', 0)
            error = log_entry.get('upstream', {}).get('error')
            
            if 200 <= status_code < 300 and not error:
                success_count += 1
            else:
                error_count += 1
            
            # 统计耗时
            duration = log_entry.get('upstream', {}).get('duration_ms', 0)
            if duration > 0:
                total_duration += duration
                duration_count += 1
            
            # 统计模型使用
            model = log_entry.get('request', {}).get('model', 'unknown')
            model_stats[model] = model_stats.get(model, 0) + 1
            
            # 统计后端类型
            backend = log_entry.get('mapping', {}).get('backend', 'unknown')
            backend_stats[backend] = backend_stats.get(backend, 0) + 1
        
        # 计算平均耗时
        avg_duration = int(total_duration / duration_count) if duration_count > 0 else 0
        
        # 计算成功率
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
        
        return jsonify({
            'total_requests': total_requests,
            'success_count': success_count,
            'error_count': error_count,
            'success_rate': round(success_rate, 2),
            'avg_duration_ms': avg_duration,
            'model_stats': model_stats,
            'backend_stats': backend_stats,
        })
    
    except Exception as e:
        logger.error(f'获取日志统计失败: {e}')
        return jsonify({'error': {'message': '获取统计失败', 'type': 'server_error'}}), 500
