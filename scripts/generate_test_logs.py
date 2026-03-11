#!/usr/bin/env python3
"""生成测试日志数据"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import uuid
from datetime import datetime
from utils.request_logger import LOGS_DIR

def generate_test_logs(count=10):
    """生成测试日志"""
    print(f'生成 {count} 条测试日志...')

    # 确保日志目录存在
    os.makedirs(LOGS_DIR, exist_ok=True)

    # 生成日志文件路径
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    log_file = os.path.join(LOGS_DIR, f'requests-{date_str}.jsonl')

    with open(log_file, 'a', encoding='utf-8') as f:
        for i in range(count):
            # 构造日志数据
            log_data = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'client_ip': '127.0.0.1',
                'request': {
                    'model': 'claude-sonnet-4',
                    'stream': False,
                    'messages': [{'role': 'user', 'content': f'Test message {i+1}'}],
                    'temperature': 0.7,
                    'max_tokens': 1000,
                },
                'mapping': {
                    'original_model': 'claude-sonnet-4',
                    'upstream_model': 'claude-sonnet-4-20250514',
                    'backend': 'anthropic',
                    'target_url': 'https://api.anthropic.com/v1/messages',
                },
                'upstream': {},
                'tokens': {},
            }

            # 模拟成功/失败响应
            if i % 5 == 0:
                # 20% 错误率
                log_data['upstream'] = {
                    'status_code': 500,
                    'duration_ms': 1000 + i * 100,
                    'error': 'Test error message',
                }
            else:
                log_data['upstream'] = {
                    'status_code': 200,
                    'duration_ms': 500 + i * 50,
                    'error': None,
                }
                log_data['tokens'] = {
                    'prompt': 10,
                    'completion': 20,
                    'total': 30,
                }

            # 写入日志
            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
            time.sleep(0.05)

    print(f'✓ 已生成 {count} 条测试日志')
    print(f'日志文件: {log_file}')

if __name__ == '__main__':
    generate_test_logs(20)
