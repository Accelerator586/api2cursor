const API = '';
let authKey = '';
let editingName = null;

function togglePwd(id) {
  const el = document.getElementById(id);
  el.type = el.type === 'password' ? 'text' : 'password';
}

function toast(msg, ok = true) {
  const area = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = 'toast ' + (ok ? 'toast-ok' : 'toast-err');
  el.textContent = msg;
  area.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (authKey) headers['Authorization'] = 'Bearer ' + authKey;
  const res = await fetch(API + path, { ...opts, headers });
  const ct = res.headers.get('content-type') || '';
  if (!ct.includes('application/json')) {
    const text = await res.text();
    if (!res.ok) throw new Error('HTTP ' + res.status + ': ' + text.substring(0, 100));
    throw new Error('服务器返回了非 JSON 响应');
  }
  const data = await res.json();
  if (!res.ok) {
    const e = data.error;
    const msg = (typeof e === 'object' && e !== null) ? (e.message || JSON.stringify(e)) : (e || data.message || 'HTTP ' + res.status);
    throw new Error(msg);
  }
  return data;
}

// ─── 登录 ───────────────────────────────────────────
async function doLogin() {
  const key = document.getElementById('loginKey').value.trim();
  if (!key) { toast('请输入密钥', false); return; }
  try {
    const r = await api('/api/admin/login', { method: 'POST', body: JSON.stringify({ key }) });
    if (r.ok) {
      authKey = key;
      sessionStorage.setItem('_ak', key);
      document.getElementById('login').style.display = 'none';
      document.getElementById('dashboard').style.display = 'block';
      loadDashboard();
    }
  } catch (e) {
    toast('密钥无效', false);
  }
}

function doLogout() {
  authKey = '';
  sessionStorage.removeItem('_ak');
  document.getElementById('dashboard').style.display = 'none';
  document.getElementById('login').style.display = 'flex';
}

// ─── 仪表盘 ─────────────────────────────────────────
async function loadDashboard() {
  try {
    const s = await api('/api/admin/settings');
    document.getElementById('targetUrl').value = s.proxy_target_url || '';
    document.getElementById('proxyKey').value = s.proxy_api_key || '';
    document.getElementById('envUrl').textContent = s.env_target_url ? '环境变量: ' + s.env_target_url : '';
    document.getElementById('envKey').textContent = s.env_api_key ? '环境变量: (已配置)' : '环境变量: (未设置)';
    
    // 加载日志配置
    const logging = s.logging || {};
    document.getElementById('logEnabled').checked = logging.enabled !== false;
    document.getElementById('logRetentionDays').value = logging.retention_days || 30;
    document.getElementById('logRequestBody').checked = logging.log_request_body !== false;
    document.getElementById('logResponseBody').checked = logging.log_response_body !== false;
    
    await loadMappings();
    checkHealth();
  } catch (e) {
    toast('加载设置失败: ' + e.message, false);
  }
}

async function checkHealth() {
  try {
    const r = await fetch(API + '/health');
    const d = await r.json();
    const b = document.getElementById('statusBadge');
    if (d.status === 'ok') {
      b.textContent = '已连接';
      b.style.background = 'rgba(34,197,94,.15)';
      b.style.color = 'var(--green)';
    } else {
      b.textContent = '异常';
    }
  } catch {
    const b = document.getElementById('statusBadge');
    b.textContent = '离线';
    b.style.background = 'rgba(239,68,68,.15)';
    b.style.color = 'var(--red)';
  }
}

async function saveSettings() {
  try {
    await api('/api/admin/settings', {
      method: 'PUT',
      body: JSON.stringify({
        proxy_target_url: document.getElementById('targetUrl').value.trim(),
        proxy_api_key: document.getElementById('proxyKey').value.trim(),
        logging: {
          enabled: document.getElementById('logEnabled').checked,
          retention_days: parseInt(document.getElementById('logRetentionDays').value) || 30,
          log_request_body: document.getElementById('logRequestBody').checked,
          log_response_body: document.getElementById('logResponseBody').checked,
        },
      }),
    });
    toast('设置已保存');
  } catch (e) {
    toast('保存失败: ' + e.message, false);
  }
}

// ─── 模型映射 ───────────────────────────────────────
async function loadMappings() {
  const mappings = await api('/api/admin/mappings');
  const el = document.getElementById('mappingList');
  const keys = Object.keys(mappings);

  if (!keys.length) {
    el.innerHTML = '<div class="empty">暂无模型映射<br><span style="font-size:13px">点击「+ 添加映射」开始配置</span></div>';
    return;
  }

  el.innerHTML = '<div class="mapping-list">' + keys.map(name => {
    const m = mappings[name];
    const backend = m.backend || 'auto';
    const tagClass = backend === 'anthropic'
      ? 'tag-anthropic'
      : backend === 'responses'
        ? 'tag-responses'
        : backend === 'openai'
          ? 'tag-openai'
          : 'tag-auto';
    const tagLabel = backend === 'auto'
      ? '自动'
      : backend === 'responses'
        ? 'responses'
        : backend;
    const hasOverride = m.target_url || m.api_key;
    return `<div class="mapping-item">
      <div class="mapping-top">
        <span class="mapping-name">${esc(name)}</span>
        <span class="mapping-arrow">&rarr;</span>
        <span class="mapping-upstream">${esc(m.upstream_model || name)}</span>
        <div class="mapping-meta">
          <span class="tag ${tagClass}">${tagLabel}</span>
          ${hasOverride ? '<span class="tag tag-override">自定义地址</span>' : ''}
        </div>
        <div class="mapping-actions">
          <button class="btn btn-ghost btn-sm" onclick="openEditModal('${esc(name)}')">编辑</button>
          <button class="btn btn-red btn-sm" onclick="deleteMapping('${esc(name)}')">删除</button>
        </div>
      </div>
    </div>`;
  }).join('') + '</div>';
}

function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

// ─── 弹窗 ──────────────────────────────────────────
function openAddModal() {
  editingName = null;
  document.getElementById('modalTitle').textContent = '添加模型映射';
  document.getElementById('mName').value = '';
  document.getElementById('mName').disabled = false;
  document.getElementById('mUpstream').value = '';
  document.getElementById('mBackend').value = 'auto';
  document.getElementById('mUrl').value = '';
  document.getElementById('mKey').value = '';
  document.getElementById('modal').classList.add('active');
}

async function openEditModal(name) {
  editingName = name;
  document.getElementById('modalTitle').textContent = '编辑模型映射';
  try {
    const mappings = await api('/api/admin/mappings');
    const m = mappings[name];
    if (!m) { toast('映射未找到', false); return; }
    document.getElementById('mName').value = name;
    document.getElementById('mName').disabled = false;
    document.getElementById('mUpstream').value = m.upstream_model || '';
    document.getElementById('mBackend').value = m.backend || 'auto';
    document.getElementById('mUrl').value = m.target_url || '';
    document.getElementById('mKey').value = m.api_key || '';
    document.getElementById('modal').classList.add('active');
  } catch (e) {
    toast('错误: ' + e.message, false);
  }
}

function closeModal() {
  document.getElementById('modal').classList.remove('active');
  editingName = null;
}

async function saveMapping() {
  const name = document.getElementById('mName').value.trim();
  const upstream = document.getElementById('mUpstream').value.trim();
  if (!name) { toast('请填写 Cursor 模型名', false); return; }
  if (!upstream) { toast('请填写上游模型名', false); return; }

  const payload = {
    name,
    upstream_model: upstream,
    backend: document.getElementById('mBackend').value,
    target_url: document.getElementById('mUrl').value.trim(),
    api_key: document.getElementById('mKey').value.trim(),
  };

  try {
    if (editingName) {
      await api('/api/admin/mappings/' + encodeURIComponent(editingName), {
        method: 'PUT', body: JSON.stringify(payload),
      });
      toast('映射已更新');
    } else {
      await api('/api/admin/mappings', {
        method: 'POST', body: JSON.stringify(payload),
      });
      toast('映射已添加');
    }
    closeModal();
    await loadMappings();
  } catch (e) {
    toast('操作失败: ' + e.message, false);
  }
}

async function deleteMapping(name) {
  if (!confirm('确定要删除映射「' + name + '」吗？')) return;
  try {
    await api('/api/admin/mappings/' + encodeURIComponent(name), { method: 'DELETE' });
    toast('映射已删除');
    await loadMappings();
  } catch (e) {
    toast('删除失败: ' + e.message, false);
  }
}

// ─── 标签页切换 ─────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  if (tab === 'settings') {
    document.querySelectorAll('.tab')[0].classList.add('active');
    document.getElementById('tabSettings').classList.add('active');
  } else if (tab === 'logs') {
    document.querySelectorAll('.tab')[1].classList.add('active');
    document.getElementById('tabLogs').classList.add('active');
    loadLogs();
    loadLogStats();
  }
}

// ─── 日志管理 ───────────────────────────────────────
let currentPage = 1;
let currentLimit = 50;

function updateTimeRange() {
  const range = document.getElementById('filterTimeRange').value;
  const customRow = document.getElementById('customTimeRow');
  
  if (range === 'custom') {
    customRow.style.display = 'flex';
  } else {
    customRow.style.display = 'none';
    
    const now = new Date();
    const endTime = document.getElementById('filterEndTime');
    endTime.value = now.toISOString().slice(0, 16);
    
    const startTime = document.getElementById('filterStartTime');
    if (range === 'today') {
      // FIX: Use UTC methods to avoid timezone conversion
      const today = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
      startTime.value = today.toISOString().slice(0, 16);
    } else if (range === '7days') {
      const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      startTime.value = sevenDaysAgo.toISOString().slice(0, 16);
    } else if (range === '30days') {
      const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      startTime.value = thirtyDaysAgo.toISOString().slice(0, 16);
    }
  }
}

async function loadLogs(page = 1) {
  currentPage = page;

  // 显示加载指示器
  const loadingEl = document.getElementById('logLoading');
  const listEl = document.getElementById('logList');
  if (loadingEl) loadingEl.style.display = 'flex';
  if (listEl) listEl.style.display = 'none';

  try {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: currentLimit.toString(),
    });

    const model = document.getElementById('filterModel').value.trim();
    if (model) params.append('model', model);

    const status = document.getElementById('filterStatus').value;
    if (status) params.append('status', status);

    const range = document.getElementById('filterTimeRange').value;
    if (range !== 'custom') {
      updateTimeRange();
    }

    const startTime = document.getElementById('filterStartTime').value;
    if (startTime) params.append('start_time', new Date(startTime).toISOString());

    const endTime = document.getElementById('filterEndTime').value;
    if (endTime) params.append('end_time', new Date(endTime).toISOString());

    const search = document.getElementById('filterSearch').value.trim();
    if (search) params.append('search', search);

    console.log('Loading logs with params:', params.toString());

    const data = await api('/api/admin/logs?' + params.toString());

    console.log('Logs response:', data);

    renderLogs(data);

    // 同时更新统计数据
    loadLogStats();
  } catch (e) {
    console.error('Failed to load logs:', e);
    toast('加载日志失败: ' + e.message, false);
    if (listEl) {
      listEl.innerHTML = '<div class="empty">加载失败: ' + e.message + '</div>';
      listEl.style.display = 'block';
    }
  } finally {
    // 隐藏加载指示器
    if (loadingEl) loadingEl.style.display = 'none';
    if (listEl) listEl.style.display = 'block';
  }
}

function renderLogs(data) {
  const el = document.getElementById('logList');

  if (!data.logs || data.logs.length === 0) {
    if (data.total === 0) {
      // No logs at all
      el.innerHTML = `
        <div class="empty">
          <p>暂无日志数据</p>
          <p style="font-size: 0.9em; color: var(--text-secondary); margin-top: 8px;">
            请先向 API 端点发起请求以生成日志：<br>
            • /v1/chat/completions<br>
            • /v1/responses<br>
            • /v1/messages
          </p>
        </div>
      `;
    } else {
      // Filtered out
      el.innerHTML = '<div class="empty">没有符合条件的日志</div>';
    }
    document.getElementById('logPagination').innerHTML = '';
    return;
  }

  el.innerHTML = '<div class="log-table">' +
    '<div class="log-header">' +
      '<div class="log-col-time">时间</div>' +
      '<div class="log-col-ip">客户端IP</div>' +
      '<div class="log-col-model">模型映射</div>' +
      '<div class="log-col-status">状态</div>' +
      '<div class="log-col-duration">耗时</div>' +
      '<div class="log-col-error">错误信息</div>' +
      '<div class="log-col-actions">操作</div>' +
    '</div>' +
    data.logs.map(log => {
      const time = new Date(log.timestamp).toLocaleString('zh-CN');
      const ip = log.client_ip || 'unknown';
      const originalModel = log.request?.model || 'unknown';
      const upstreamModel = log.mapping?.upstream_model || originalModel;
      const backend = log.mapping?.backend || 'auto';
      const statusCode = log.upstream?.status_code || 0;
      const error = log.upstream?.error;
      const duration = log.upstream?.duration_ms || 0;

      const isSuccess = statusCode >= 200 && statusCode < 300 && !error;
      const statusClass = isSuccess ? 'status-success' : 'status-error';
      const statusText = isSuccess ? '成功' : '失败';

      const durationClass = duration < 500 ? 'duration-fast' : duration < 2000 ? 'duration-medium' : 'duration-slow';

      return `<div class="log-row">
        <div class="log-col-time">${esc(time)}</div>
        <div class="log-col-ip">${esc(ip)}</div>
        <div class="log-col-model">
          <div class="model-mapping">
            <span class="model-original">${esc(originalModel)}</span>
            <span class="model-arrow">→</span>
            <span class="model-upstream">${esc(upstreamModel)}</span>
            <span class="tag tag-${backend}">${backend}</span>
          </div>
        </div>
        <div class="log-col-status">
          <span class="status-badge ${statusClass}">${statusText}</span>
          ${statusCode ? `<span class="status-code">${statusCode}</span>` : ''}
        </div>
        <div class="log-col-duration">
          <span class="${durationClass}">${duration}ms</span>
        </div>
        <div class="log-col-error">
          ${error ? `<span class="error-summary" title="${esc(error)}">${esc(error.substring(0, 50))}${error.length > 50 ? '...' : ''}</span>` : '<span style="color:var(--muted)">-</span>'}
        </div>
        <div class="log-col-actions">
          <button class="btn btn-ghost btn-sm" onclick='viewLogDetail(${JSON.stringify(log.id)})'>详情</button>
        </div>
      </div>`;
    }).join('') +
    '</div>';

  renderPagination(data);
}

function renderPagination(data) {
  const el = document.getElementById('logPagination');
  
  if (data.pages <= 1) {
    el.innerHTML = '';
    return;
  }
  
  let html = '<div class="pagination-info">共 ' + data.total + ' 条，第 ' + data.page + '/' + data.pages + ' 页</div>';
  html += '<div class="pagination-buttons">';
  
  if (data.page > 1) {
    html += '<button class="btn btn-ghost btn-sm" onclick="loadLogs(' + (data.page - 1) + ')">上一页</button>';
  }
  
  if (data.page < data.pages) {
    html += '<button class="btn btn-ghost btn-sm" onclick="loadLogs(' + (data.page + 1) + ')">下一页</button>';
  }
  
  html += '</div>';
  el.innerHTML = html;
}

async function viewLogDetail(logId) {
  try {
    const log = await api('/api/admin/logs/' + encodeURIComponent(logId));
    
    const time = new Date(log.timestamp).toLocaleString('zh-CN');
    const statusCode = log.upstream?.status_code || 0;
    const error = log.upstream?.error;
    const isSuccess = statusCode >= 200 && statusCode < 300 && !error;
    
    let html = '<div class="log-detail">';
    
    // 基本信息
    html += '<div class="detail-section">';
    html += '<h4>基本信息</h4>';
    html += '<div class="detail-grid">';
    html += '<div class="detail-item"><label>日志ID:</label><span>' + esc(log.id) + '</span></div>';
    html += '<div class="detail-item"><label>时间:</label><span>' + esc(time) + '</span></div>';
    html += '<div class="detail-item"><label>客户端IP:</label><span>' + esc(log.client_ip) + '</span></div>';
    html += '</div></div>';
    
    // 请求信息
    html += '<div class="detail-section">';
    html += '<h4>请求信息</h4>';
    html += '<div class="detail-grid">';
    html += '<div class="detail-item"><label>模型:</label><span>' + esc(log.request?.model || 'unknown') + '</span></div>';
    html += '<div class="detail-item"><label>流式:</label><span>' + (log.request?.stream ? '是' : '否') + '</span></div>';
    if (log.request?.messages) {
      html += '<div class="detail-item full-width"><label>消息数:</label><span>' + log.request.messages.length + '</span></div>';
      html += '<div class="detail-item full-width"><label>消息内容:</label><pre>' + esc(JSON.stringify(log.request.messages, null, 2)) + '</pre></div>';
    }
    html += '</div></div>';
    
    // 模型映射
    html += '<div class="detail-section">';
    html += '<h4>模型映射</h4>';
    html += '<div class="detail-grid">';
    html += '<div class="detail-item"><label>原始模型:</label><span>' + esc(log.mapping?.original_model || '') + '</span></div>';
    html += '<div class="detail-item"><label>上游模型:</label><span>' + esc(log.mapping?.upstream_model || '') + '</span></div>';
    html += '<div class="detail-item"><label>后端类型:</label><span>' + esc(log.mapping?.backend || '') + '</span></div>';
    html += '<div class="detail-item"><label>目标地址:</label><span>' + esc(log.mapping?.target_url || '') + '</span></div>';
    html += '</div></div>';
    
    // 上游响应
    html += '<div class="detail-section">';
    html += '<h4>上游响应</h4>';
    html += '<div class="detail-grid">';
    html += '<div class="detail-item"><label>状态码:</label><span class="' + (isSuccess ? 'status-success' : 'status-error') + '">' + statusCode + '</span></div>';
    html += '<div class="detail-item"><label>耗时:</label><span>' + (log.upstream?.duration_ms || 0) + 'ms</span></div>';
    if (error) {
      html += '<div class="detail-item full-width"><label>错误:</label><pre class="error-text">' + esc(error) + '</pre></div>';
    }
    if (log.upstream?.response && !error) {
      html += '<div class="detail-item full-width"><label>响应内容:</label><pre>' + esc(JSON.stringify(log.upstream.response, null, 2)) + '</pre></div>';
    }
    html += '</div></div>';
    
    // Token 使用
    if (log.tokens && (log.tokens.prompt || log.tokens.completion)) {
      html += '<div class="detail-section">';
      html += '<h4>Token 使用</h4>';
      html += '<div class="detail-grid">';
      html += '<div class="detail-item"><label>输入:</label><span>' + (log.tokens.prompt || 0) + '</span></div>';
      html += '<div class="detail-item"><label>输出:</label><span>' + (log.tokens.completion || 0) + '</span></div>';
      html += '<div class="detail-item"><label>总计:</label><span>' + (log.tokens.total || 0) + '</span></div>';
      html += '</div></div>';
    }
    
    html += '</div>';
    
    document.getElementById('logDetailContent').innerHTML = html;
    document.getElementById('logDetailModal').classList.add('active');
  } catch (e) {
    toast('加载日志详情失败: ' + e.message, false);
  }
}

function closeLogDetail() {
  document.getElementById('logDetailModal').classList.remove('active');
}

async function exportLogs() {
  try {
    const params = new URLSearchParams();

    const model = document.getElementById('filterModel').value.trim();
    if (model) params.append('model', model);

    const status = document.getElementById('filterStatus').value;
    if (status) params.append('status', status);

    const startTime = document.getElementById('filterStartTime').value;
    if (startTime) params.append('start_time', new Date(startTime).toISOString());

    const endTime = document.getElementById('filterEndTime').value;
    if (endTime) params.append('end_time', new Date(endTime).toISOString());

    const search = document.getElementById('filterSearch').value.trim();
    if (search) params.append('search', search);

    const url = API + '/api/admin/logs/export?' + params.toString();
    const headers = {};
    if (authKey) headers['Authorization'] = 'Bearer ' + authKey;

    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error('导出失败: HTTP ' + res.status);

    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = 'logs-export-' + new Date().toISOString().slice(0, 10) + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);

    toast('日志已导出');
  } catch (e) {
    toast('导出失败: ' + e.message, false);
  }
}

// ─── 日志统计 ───────────────────────────────────────
async function loadLogStats() {
  try {
    // 获取当前过滤条件
    const params = new URLSearchParams();
    const startTime = document.getElementById('filterStartTime').value;
    if (startTime) params.append('start_time', new Date(startTime).toISOString());
    const endTime = document.getElementById('filterEndTime').value;
    if (endTime) params.append('end_time', new Date(endTime).toISOString());

    console.log('Loading stats with params:', params.toString());

    // 调用统计 API
    const stats = await api('/api/admin/logs/stats?' + params.toString());

    console.log('Stats response:', stats);

    // 更新核心指标
    document.getElementById('statTotalRequests').textContent = formatNumber(stats.total_requests);
    document.getElementById('statSuccessRate').textContent = stats.success_rate.toFixed(2) + '%';
    document.getElementById('statErrorRate').textContent = (100 - stats.success_rate).toFixed(2) + '%';
    document.getElementById('statAvgDuration').textContent = stats.avg_duration_ms + 'ms';

    // 更新模型分布（显示前3个）
    const modelStats = stats.model_stats || {};

    if (Object.keys(modelStats).length === 0) {
      document.getElementById('statsModelsList').textContent = '暂无数据';
      return;
    }

    const topModels = Object.entries(modelStats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([model, count]) => {
        const percentage = stats.total_requests > 0
          ? ((count / stats.total_requests) * 100).toFixed(1)
          : '0.0';
        return `${model} (${percentage}%)`;
      })
      .join(' · ');

    document.getElementById('statsModelsList').textContent = topModels || '暂无数据';

  } catch (e) {
    console.error('Failed to load stats:', e);
    toast('加载统计失败: ' + e.message, false);
    // 显示错误状态
    document.getElementById('statsModelsList').textContent = '加载失败';
  }
}

function formatNumber(num) {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
}

// ─── 初始化 ─────────────────────────────────────────
(function init() {
  const saved = sessionStorage.getItem('_ak');
  if (saved) {
    authKey = saved;
    document.getElementById('login').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';
    loadDashboard();
  }
  
  // 初始化时间范围
  updateTimeRange();
})();

document.getElementById('modal').addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});
document.getElementById('logDetailModal').addEventListener('click', function(e) {
  if (e.target === this) closeLogDetail();
});
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closeModal();
    closeLogDetail();
  }
});
