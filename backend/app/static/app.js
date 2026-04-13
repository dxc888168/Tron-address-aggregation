const apiBase = '/api/v1';
const logBox = document.getElementById('log-box');

let currentAddresses = [];
let selectedAddressIds = new Set();
let currentPage = 1;
let pageSize = 50;
let totalCount = 0;
const TERMINAL_JOB_STATUS = new Set(['SUCCESS', 'PARTIAL_FAILED', 'FAILED', 'CANCELED']);
const FAILED_JOB_STATUS = new Set(['PARTIAL_FAILED', 'FAILED', 'CANCELED']);
const JOB_STATUS_LABELS = {
  CREATED: '已创建',
  SCANNING: '扫描中',
  PLANNED: '已规划',
  FUNDING_TRX: '补TRX中',
  SWEEPING_USDT: '归集USDT中',
  SWEEPING_TRX: '归集TRX中',
  RECONCILING: '对账中',
  SUCCESS: '成功',
  PARTIAL_FAILED: '部分失败',
  FAILED: '失败',
  CANCELED: '已取消'
};
const ASSET_LABELS = {
  TRX: 'TRX',
  USDT_TRC20: 'USDT(TRC20)'
};
const REASON_LABELS = {
  NO_ELIGIBLE_ITEMS: '未发现可归集资产',
  USDT_AFTER_RESERVE_ZERO: 'USDT 余额扣除保留值后为 0',
  USDT_BELOW_MIN: 'USDT 余额未达到最小归集阈值',
  TRX_AFTER_RESERVE_ZERO: 'TRX 余额扣除保留值后为 0',
  TRX_BELOW_MIN: 'TRX 余额未达到最小归集阈值',
  NO_TOPUP_SOURCE_CONFIGURED: '未配置补充 TRX 地址',
  TOPUP_SOURCE_NOT_MANAGED: '补充 TRX 地址不在托管列表',
  ADDRESS_NOT_FOUND: '地址不存在',
  UNSUPPORTED_ASSET: '不支持的资产类型',
  SKIPPED: '已跳过'
};

const I18N = {
  totalAddresses: '\u5730\u5740\u603b\u6570',
  totalTrx: 'TRX \u603b\u91cf',
  totalUsdt: 'USDT \u603b\u91cf',
  trxNonZero: 'TRX \u975e\u96f6\u5730\u5740',
  usdtNonZero: 'USDT \u975e\u96f6\u5730\u5740',
  updatedAt: '\u66f4\u65b0\u65f6\u95f4',
  syncDone: '\u8d44\u4ea7\u540c\u6b65\u5b8c\u6210',
  generated: '\u6279\u91cf\u751f\u6210\u5730\u5740\u5b8c\u6210',
  sweepSubmitted: '\u4e00\u952e\u5f52\u96c6\u4efb\u52a1\u5df2\u53d1\u8d77',
  listRefreshed: '\u5df2\u5237\u65b0\u5730\u5740\u5217\u8868',
  jobsRefreshed: '\u5df2\u5237\u65b0\u4efb\u52a1\u5217\u8868',
  overviewRefreshed: '\u5df2\u5237\u65b0\u8d44\u4ea7\u603b\u89c8',
  exportAddressDone: '\u5730\u5740\u5bfc\u51fa\u6210\u529f',
  exportKeyDone: '\u79c1\u94a5\u5bfc\u51fa\u6210\u529f',
  noAddressData: '\u6ca1\u6709\u53ef\u5bfc\u51fa\u7684\u5730\u5740\u6570\u636e',
  noKeyData: '\u6ca1\u6709\u53ef\u5bfc\u51fa\u7684\u79c1\u94a5\u6570\u636e',
  ready: '\u672c\u5730\u514d\u767b\u5f55\u6a21\u5f0f\u5df2\u5c31\u7eea',
  initFailed: '\u521d\u59cb\u5316\u5931\u8d25',
  syncFailed: '\u540c\u6b65\u5931\u8d25',
  refreshFailed: '\u5237\u65b0\u5931\u8d25',
  generateFailed: '\u751f\u6210\u5931\u8d25',
  addressRefreshFailed: '\u5237\u65b0\u5730\u5740\u5931\u8d25',
  sweepFailed: '\u5f52\u96c6\u53d1\u8d77\u5931\u8d25',
  jobsFailed: '\u5237\u65b0\u4efb\u52a1\u5931\u8d25',
  exportFailed: '\u5bfc\u51fa\u5931\u8d25',
  tagSaved: '\u6807\u7b7e\u5df2\u4fdd\u5b58',
  tagSaveFailed: '\u6807\u7b7e\u4fdd\u5b58\u5931\u8d25',
  deleteDone: '\u6279\u91cf\u5220\u9664\u5b8c\u6210',
  deleteFailed: '\u6279\u91cf\u5220\u9664\u5931\u8d25',
  noSelection: '\u8bf7\u5148\u52fe\u9009\u8981\u5220\u9664\u7684\u5730\u5740',
  deleteConfirm: '\u786e\u8ba4\u5220\u9664\u5df2\u52fe\u9009\u5730\u5740\uff1f\uff08\u4e0d\u53ef\u6062\u590d\uff09',
  saveTagBtn: '\u4fdd\u5b58\u6807\u7b7e',
  pagePrefix: '\u7b2c',
  pageSuffix: '\u9875',
  totalPrefix: '\u5408\u8ba1',
  totalSuffix: '\u6761',
  sweepUsdtSubmitted: '\u4e00\u952e\u5f52\u96c6 USDT \u4efb\u52a1\u5df2\u53d1\u8d77',
  sweepTrxSubmitted: '\u4e00\u952e\u5f52\u96c6 TRX \u4efb\u52a1\u5df2\u53d1\u8d77',
  sweepTracking: '\u4efb\u52a1\u5df2\u53d1\u8d77\uff0c\u6b63\u5728\u67e5\u8be2\u6267\u884c\u7ed3\u679c',
  sweepFinished: '\u4efb\u52a1\u6267\u884c\u5b8c\u6210',
  sweepStillRunning: '\u4efb\u52a1\u4ecd\u5728\u6267\u884c\u4e2d\uff0c\u8bf7\u5728\u4efb\u52a1\u5217\u8868\u67e5\u770b\u8fdb\u5ea6',
  sweepFinalFailed: '\u4efb\u52a1\u6267\u884c\u5931\u8d25',
  sweepDetailFailed: '\u67e5\u8be2\u4efb\u52a1\u8be6\u60c5\u5931\u8d25',
  noCollectableAssets: '\u672a\u53d1\u73b0\u53ef\u5f52\u96c6\u8d44\u4ea7\uff08\u8ba1\u5212\u6570\u4e3a 0\uff09',
  jobsCleared: '\u5df2\u6e05\u7a7a\u5386\u53f2\u5f52\u96c6\u4efb\u52a1',
  jobsClearFailed: '\u6e05\u7a7a\u4efb\u52a1\u5931\u8d25',
  clearJobsConfirm: '\u786e\u8ba4\u6e05\u7a7a\u6240\u6709\u5386\u53f2\u5f52\u96c6\u4efb\u52a1\u8bb0\u5f55\uff1f',
  importNeedData: '\u8bf7\u5148\u8f93\u5165\u8981\u5bfc\u5165\u7684\u79c1\u94a5',
  importDone: '\u5bfc\u5165\u79c1\u94a5\u5b8c\u6210',
  importFailed: '\u5bfc\u5165\u79c1\u94a5\u5931\u8d25',
  importCountPrefix: '\u5df2\u8f93\u5165',
  importCountSuffix: '\u884c',
  importCleared: '\u5df2\u6e05\u7a7a\u5bfc\u5165\u5185\u5bb9',
  amountInvalid: '\u91d1\u989d\u683c\u5f0f\u4e0d\u6b63\u786e\uff0c\u8bf7\u8f93\u5165\u975e\u8d1f\u6570\uff0c\u6700\u591a 6 \u4f4d\u5c0f\u6570',
  targetRequired: '\u5f52\u96c6\u76ee\u6807\u5730\u5740\u4e0d\u80fd\u4e3a\u7a7a',
  targetInvalid: '\u5f52\u96c6\u76ee\u6807\u5730\u5740\u683c\u5f0f\u4e0d\u6b63\u786e',
  expandLog: '\u5c55\u5f00',
  collapseLog: '\u6536\u8d77',
  defaultLogTitle: '\u65e5\u5fd7'
};

function decimalToRaw6(input, fieldName) {
  const value = String(input ?? '').trim();
  if (!value) return 0;
  if (!/^\d+(\.\d{0,6})?$/.test(value)) {
    throw new Error(`${fieldName}: ${I18N.amountInvalid}`);
  }

  const [intPart, fracPart = ''] = value.split('.');
  const intRaw = Number(intPart) * 1_000_000;
  const fracRaw = Number((fracPart + '000000').slice(0, 6));
  const raw = intRaw + fracRaw;
  if (!Number.isFinite(raw) || raw < 0) {
    throw new Error(`${fieldName}: ${I18N.amountInvalid}`);
  }
  return Math.trunc(raw);
}

function countImportLines(raw) {
  return (raw || '')
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter((x) => x.length > 0).length;
}

function updateImportInputState() {
  const textarea = document.getElementById('import-pairs');
  const countEl = document.getElementById('import-line-count');
  const importBtn = document.getElementById('import-addresses-btn');
  if (!textarea || !countEl || !importBtn) return;

  const lineCount = countImportLines(textarea.value || '');
  countEl.textContent = `${I18N.importCountPrefix} ${lineCount} ${I18N.importCountSuffix}`;
  importBtn.disabled = lineCount <= 0;
}

function setupImportSection() {
  const textarea = document.getElementById('import-pairs');
  const clearBtn = document.getElementById('clear-import-btn');
  if (!textarea) return;

  textarea.addEventListener('input', updateImportInputState);
  updateImportInputState();

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      textarea.value = '';
      updateImportInputState();
      textarea.focus();
      log(I18N.importCleared);
    });
  }
}

function setupLogPanels() {
  const outputs = document.querySelectorAll('pre.log-output');
  outputs.forEach((pre) => {
    if (pre.dataset.panelReady === '1') return;
    pre.dataset.panelReady = '1';

    const panel = document.createElement('div');
    panel.className = 'log-panel';

    const header = document.createElement('div');
    header.className = 'log-panel-header';

    const title = document.createElement('span');
    title.className = 'log-panel-title';
    title.textContent = pre.dataset.logTitle || I18N.defaultLogTitle;

    const toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.className = 'log-panel-toggle';

    const syncToggleText = () => {
      toggleBtn.textContent = panel.classList.contains('collapsed') ? I18N.expandLog : I18N.collapseLog;
    };

    toggleBtn.addEventListener('click', () => {
      panel.classList.toggle('collapsed');
      syncToggleText();
    });

    header.appendChild(title);
    header.appendChild(toggleBtn);

    pre.parentNode.insertBefore(panel, pre);
    panel.appendChild(header);
    panel.appendChild(pre);

    if (!pre.textContent.trim()) {
      panel.classList.add('collapsed');
    }
    syncToggleText();

    const observer = new MutationObserver(() => {
      if (pre.textContent.trim()) {
        panel.classList.remove('collapsed');
      }
      syncToggleText();
    });
    observer.observe(pre, { childList: true, subtree: true, characterData: true });
  });
}

function log(msg, data = null) {
  const time = new Date().toLocaleString();
  const line = `[${time}] ${msg}`;
  logBox.textContent = data
    ? `${line}\n${JSON.stringify(data, null, 2)}\n\n${logBox.textContent}`
    : `${line}\n${logBox.textContent}`;
}

async function api(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  const res = await fetch(`${apiBase}${path}`, {
    ...options,
    headers
  });

  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (e) {
    data = { raw: text };
  }

  if (!res.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }

  return data;
}

function formatDateTime(value) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString('zh-CN', { hour12: false });
}

async function refreshOverview() {
  const data = await api('/assets/overview');
  document.getElementById('overview').innerHTML = `
    <div class="overview-metric">
      <span class="metric-label">${I18N.totalAddresses}</span>
      <span class="metric-value">${data.total_addresses}</span>
    </div>
    <div class="overview-metric">
      <span class="metric-label">${I18N.totalTrx}</span>
      <span class="metric-value">${data.trx_total_dec}</span>
    </div>
    <div class="overview-metric">
      <span class="metric-label">${I18N.totalUsdt}</span>
      <span class="metric-value">${data.usdt_total_dec}</span>
    </div>
    <div class="overview-metric">
      <span class="metric-label">${I18N.trxNonZero}</span>
      <span class="metric-value">${data.non_zero_trx_addresses}</span>
    </div>
    <div class="overview-metric">
      <span class="metric-label">${I18N.usdtNonZero}</span>
      <span class="metric-value">${data.non_zero_usdt_addresses}</span>
    </div>
    <div class="overview-updated">${I18N.updatedAt}：${formatDateTime(data.updated_at)}</div>
  `;
}

async function syncAssets() {
  const data = await api('/assets/sync', {
    method: 'POST',
    body: JSON.stringify({ mode: 'INCREMENTAL', address_ids: [], force: false })
  });
  log(I18N.syncDone, data);
  await refreshOverview();
  await refreshAddresses(currentPage);
}

async function generateAddresses(e) {
  e.preventDefault();
  const count = Number(document.getElementById('gen-count').value || 100);
  const startRaw = document.getElementById('gen-start').value;
  const tagPrefix = document.getElementById('gen-tag').value || null;

  const payload = {
    count,
    start_index: startRaw === '' ? null : Number(startRaw),
    tag_prefix: tagPrefix
  };

  const data = await api('/addresses/batch-generate', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  const sampleLines = (data.sample || [])
    .map((x) => `- #${x.addr_index}: ${x.address_base58}`)
    .join('\n');
  document.getElementById('gen-result').textContent = [
    `生成完成：${data.created_count} 个地址`,
    `索引范围：${data.range?.start_index ?? '-'} ~ ${data.range?.end_index ?? '-'}`,
    `示例（仅前 ${Math.min((data.sample || []).length, 5)} 条）：`,
    sampleLines || '-'
  ].join('\n');
  log(`${I18N.generated}: ${data.created_count} items`);
  await refreshOverview();
  await refreshAddresses(1);
}

function renderAddressRows() {
  const tbody = document.getElementById('addresses-body');
  tbody.innerHTML = '';

  currentAddresses.forEach((row) => {
    const checked = selectedAddressIds.has(row.id) ? 'checked' : '';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="checkbox-cell"><input class="row-check" type="checkbox" data-id="${row.id}" ${checked} /></td>
      <td class="index-col">${row.addr_index}</td>
      <td class="addr-col" title="${row.address_base58}">${row.address_base58}</td>
      <td class="num-col">${row.trx_balance_dec}</td>
      <td class="num-col">${row.usdt_balance_dec}</td>
      <td class="num-col">${row.energy_balance ?? 0}</td>
      <td class="num-col">${row.bandwidth_balance ?? 0}</td>
      <td><input class="tag-input" data-id="${row.id}" value="${row.tag || ''}" placeholder="tag" /></td>
      <td><button class="save-tag-btn" data-id="${row.id}" type="button">${I18N.saveTagBtn}</button></td>
    `;
    tbody.appendChild(tr);
  });

  updateSelectAllState();
}

function updatePaginationControls() {
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const info = document.getElementById('page-info');
  info.textContent = `${I18N.pagePrefix} ${currentPage} / ${totalPages} ${I18N.pageSuffix}, ${I18N.totalPrefix} ${totalCount} ${I18N.totalSuffix}`;

  document.getElementById('prev-page-btn').disabled = currentPage <= 1;
  document.getElementById('next-page-btn').disabled = currentPage >= totalPages;
}

function updateSelectAllState() {
  const selectAll = document.getElementById('select-all-current');
  if (!currentAddresses.length) {
    selectAll.checked = false;
    return;
  }
  const allChecked = currentAddresses.every((x) => selectedAddressIds.has(x.id));
  selectAll.checked = allChecked;
}

async function refreshAddresses(page = currentPage) {
  const requestedPage = Math.max(1, Number(page) || 1);
  const data = await api(`/addresses?page=${requestedPage}&page_size=${pageSize}`);
  totalCount = Number(data.total || 0);
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  if (requestedPage > totalPages) {
    return refreshAddresses(totalPages);
  }

  currentPage = requestedPage;
  currentAddresses = data.items || [];

  renderAddressRows();
  updatePaginationControls();
}

function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function extractFilenameFromDisposition(disposition, fallbackName) {
  if (!disposition) return fallbackName;
  const m = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (m && m[1]) {
    try {
      return decodeURIComponent(m[1]);
    } catch (e) {
      return m[1];
    }
  }
  return fallbackName;
}

async function downloadFile(path, fallbackName) {
  const res = await fetch(`${apiBase}${path}`);
  if (!res.ok) {
    const text = await res.text();
    let msg = `HTTP ${res.status}`;
    try {
      const data = text ? JSON.parse(text) : {};
      msg = data.detail || data.message || msg;
    } catch (e) {
      msg = text || msg;
    }
    throw new Error(msg);
  }

  const blob = await res.blob();
  const filename = extractFilenameFromDisposition(res.headers.get('content-disposition'), fallbackName);
  downloadBlob(filename, blob);
  return filename;
}

async function exportAllAddresses() {
  const fallback = `addresses_all_${Date.now()}.txt`;
  const name = await downloadFile('/addresses/export-all-addresses-txt', fallback);
  alert(`导出成功：${name}`);
  log(I18N.exportAddressDone, { file: name });
}

async function exportAllPrivateKeys() {
  const fallback = `private_keys_all_${Date.now()}.xlsx`;
  const name = await downloadFile('/addresses/export-all-private-keys-xlsx', fallback);
  alert(`导出成功：${name}`);
  log(I18N.exportKeyDone, { file: name });
}

async function importPrivateKeys() {
  const raw = document.getElementById('import-pairs').value || '';
  const lines = raw
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter((x) => x.length > 0);

  if (!lines.length) {
    throw new Error(I18N.importNeedData);
  }

  const tagPrefixRaw = document.getElementById('import-tag-prefix').value || '';
  const tagPrefix = tagPrefixRaw.trim() || null;

  const data = await api('/addresses/import', {
    method: 'POST',
    body: JSON.stringify({
      private_keys: lines,
      tag_prefix: tagPrefix
    })
  });

  alert(`导入完成：成功 ${data.imported_count}，跳过 ${data.skipped_count}，失败 ${data.error_count}`);
  log(`${I18N.importDone}: imported=${data.imported_count}, skipped=${data.skipped_count}, errors=${data.error_count}`);
  document.getElementById('import-pairs').value = '';
  updateImportInputState();
  await syncAssets();
  await refreshOverview();
  await refreshAddresses(1);
}

async function saveTag(addressId) {
  const input = document.querySelector(`.tag-input[data-id="${addressId}"]`);
  const tag = input ? input.value : '';
  await api(`/addresses/${addressId}/tag`, {
    method: 'PATCH',
    body: JSON.stringify({ tag })
  });
  log(I18N.tagSaved, { address_id: addressId, tag });
}

async function batchDeleteSelected() {
  const ids = Array.from(selectedAddressIds);
  if (!ids.length) {
    throw new Error(I18N.noSelection);
  }

  const ok = window.confirm(I18N.deleteConfirm);
  if (!ok) return;

  const data = await api('/addresses/batch-delete', {
    method: 'POST',
    body: JSON.stringify({ address_ids: ids })
  });

  ids.forEach((id) => selectedAddressIds.delete(id));
  log(I18N.deleteDone, data);

  const totalPages = Math.max(1, Math.ceil(Math.max(0, totalCount - data.changed) / pageSize));
  if (currentPage > totalPages) currentPage = totalPages;
  await refreshOverview();
  await refreshAddresses(currentPage);
}

function readSweepPayload(assets) {
  const target = (document.getElementById('target-address').value || '').trim();
  if (!target) {
    throw new Error(I18N.targetRequired);
  }
  if (!/^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(target)) {
    throw new Error(I18N.targetInvalid);
  }

  const reserveTrxRaw = decimalToRaw6(document.getElementById('reserve-trx').value, '保留 TRX');
  const reserveUsdtRaw = decimalToRaw6(document.getElementById('reserve-usdt').value, '保留 USDT');
  return {
    target_address_base58: target,
    assets,
    min_trx_raw: 1,
    min_usdt_raw: 1,
    reserve_trx_raw: reserveTrxRaw,
    reserve_usdt_raw: reserveUsdtRaw,
    address_filter: { status: 'ACTIVE' }
  };
}

function jobStatusText(status) {
  return JOB_STATUS_LABELS[status] || status || '';
}

function assetListText(raw) {
  if (!raw) return '';
  return String(raw)
    .split(',')
    .map((x) => ASSET_LABELS[x] || x)
    .join(', ');
}

function reasonText(reason) {
  if (!reason) return '';
  return REASON_LABELS[reason] || reason;
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function fetchJobDetail(jobId) {
  return api(`/sweep/jobs/${jobId}`);
}

function extractSweepError(detail) {
  const job = detail?.job || {};
  if (job.error_message) {
    return reasonText(String(job.error_message));
  }

  const failedItems = detail?.failed_items || [];
  if (failedItems.length > 0) {
    const first = failedItems[0];
    const addr = first.address_base58 || '-';
    const asset = ASSET_LABELS[first.asset] || first.asset || '-';
    const reason = reasonText(first.fail_reason) || '未知原因';
    return `${addr} ${asset}: ${reason}`;
  }

  return '未知原因';
}

function formatJobDetailChinese(detail) {
  const job = detail?.job || {};
  const summary = detail?.summary || {};
  const failedItems = detail?.failed_items || [];
  const lines = [];
  lines.push(`任务号: ${job.job_no ?? '-'}`);
  lines.push(`状态: ${jobStatusText(job.status)}`);
  lines.push(`归集资产: ${assetListText(job.asset_list) || '-'}`);
  lines.push(`目标地址: ${job.target_address_base58 || '-'}`);
  lines.push(`检查地址数: ${summary.checked_addresses ?? '-'}`);
  lines.push(`可归集地址数: ${summary.planned_addresses ?? '-'}`);
  lines.push(`计划归集条目: ${summary.planned_items ?? job.planned_count ?? 0}`);
  lines.push(`跳过条目: ${summary.skipped_items ?? '-'}`);
  lines.push(`成功: ${job.success_count ?? 0}`);
  lines.push(`失败: ${job.failed_count ?? 0}`);
  lines.push(`开始时间: ${job.started_at || '-'}`);
  lines.push(`结束时间: ${job.ended_at || '-'}`);
  if (job.error_message) {
    lines.push(`任务错误: ${reasonText(job.error_message)}`);
  }

  const skipReasons = summary.skip_reasons || {};
  const skipReasonEntries = Object.entries(skipReasons);
  if (skipReasonEntries.length > 0) {
    lines.push('');
    lines.push('跳过原因统计:');
    skipReasonEntries.forEach(([reason, count], idx) => {
      lines.push(`${idx + 1}. ${reasonText(reason)}: ${count}`);
    });
  }

  if ((job.planned_count || 0) === 0 && job.status === 'SUCCESS') {
    lines.push(I18N.noCollectableAssets);
  }

  if (failedItems.length > 0) {
    lines.push('');
    lines.push('失败明细:');
    failedItems.slice(0, 10).forEach((x, idx) => {
      lines.push(
        `${idx + 1}. 地址: ${x.address_base58 || '-'} | 资产: ${ASSET_LABELS[x.asset] || x.asset || '-'} | 原因: ${
          reasonText(x.fail_reason) || '未知原因'
        }`
      );
    });
    if (failedItems.length > 10) {
      lines.push(`... 其余 ${failedItems.length - 10} 条请到任务详情查看`);
    }
  }

  return lines.join('\n');
}

async function waitForJobTerminal(jobId, maxAttempts = 20, intervalMs = 1500) {
  let lastDetail = null;
  for (let i = 0; i < maxAttempts; i += 1) {
    try {
      lastDetail = await fetchJobDetail(jobId);
    } catch (err) {
      log(`${I18N.sweepDetailFailed}: ${err.message}`);
    }

    const status = lastDetail?.job?.status;
    if (status && TERMINAL_JOB_STATUS.has(status)) {
      return { reachedTerminal: true, detail: lastDetail };
    }

    await sleep(intervalMs);
  }

  return { reachedTerminal: false, detail: lastDetail };
}

async function runSweepByAsset(asset) {
  const payload = { ...readSweepPayload([asset]), idem_key: `sweep_${asset}_${Date.now()}` };
  const data = await api('/sweep/run', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  document.getElementById('sweep-run-result').textContent = [
    I18N.sweepTracking,
    `任务号: ${data.job_no}`,
    `任务ID: ${data.job_id}`,
    `当前状态: ${jobStatusText(data.status)}`
  ].join('\n');
  const submittedMsg = asset === 'USDT_TRC20' ? I18N.sweepUsdtSubmitted : I18N.sweepTrxSubmitted;
  log(`${submittedMsg}，任务号: ${data.job_no}`);

  await refreshJobs();
  const tracked = await waitForJobTerminal(data.job_id);
  await refreshJobs();

  if (tracked.detail) {
    document.getElementById('sweep-run-result').textContent = formatJobDetailChinese(tracked.detail);
  }

  if (!tracked.reachedTerminal) {
    log(I18N.sweepStillRunning, { job_id: data.job_id });
    return;
  }

  const finalStatus = tracked.detail?.job?.status || data.status;
  if (FAILED_JOB_STATUS.has(finalStatus)) {
    const reason = extractSweepError(tracked.detail);
    const msg = `${I18N.sweepFinalFailed}: ${jobStatusText(finalStatus)} | ${reason}`;
    log(msg);
    alert(msg);
    return;
  }

  if (tracked.detail?.job?.planned_count === 0) {
    log(`${I18N.sweepFinished}: ${jobStatusText(finalStatus)} | ${I18N.noCollectableAssets}`);
  } else {
    const job = tracked.detail?.job || {};
    log(
      `${I18N.sweepFinished}: ${jobStatusText(finalStatus)} | 计划:${job.planned_count ?? 0} 成功:${job.success_count ?? 0} 失败:${
        job.failed_count ?? 0
      }`
    );
  }
}

async function refreshJobs() {
  const data = await api('/sweep/jobs?page=1&page_size=30');
  const tbody = document.getElementById('jobs-body');
  tbody.innerHTML = '';

  data.items.forEach((row) => {
    const tr = document.createElement('tr');
    const statusText = jobStatusText(row.status);
    const errText = reasonText(row.error_message || '');
    tr.innerHTML = `
      <td>${row.job_no}</td>
      <td title="${row.status}">${statusText}</td>
      <td>${row.planned_count}</td>
      <td>${row.success_count}</td>
      <td>${row.failed_count}</td>
      <td>${errText}</td>
      <td>${row.created_at || ''}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function clearJobsHistory() {
  const ok = window.confirm(I18N.clearJobsConfirm);
  if (!ok) return;

  const data = await api('/sweep/jobs/clear', {
    method: 'POST',
    body: JSON.stringify({})
  });

  log(`${I18N.jobsCleared}，任务:${data.jobs} 条，明细:${data.items} 条`);
  document.getElementById('sweep-run-result').textContent = '';
  await refreshJobs();
}

async function initialRefresh() {
  await Promise.all([refreshOverview(), refreshAddresses(1), refreshJobs()]);
}

window.addEventListener('DOMContentLoaded', async () => {
  setupLogPanels();
  setupImportSection();

  document.getElementById('sync-assets-btn').addEventListener('click', async () => {
    try {
      await syncAssets();
    } catch (err) {
      log(`${I18N.syncFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('refresh-overview-btn').addEventListener('click', async () => {
    try {
      await refreshOverview();
      log(I18N.overviewRefreshed);
    } catch (err) {
      log(`${I18N.refreshFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('gen-form').addEventListener('submit', async (e) => {
    try {
      await generateAddresses(e);
    } catch (err) {
      log(`${I18N.generateFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('refresh-addresses-btn').addEventListener('click', async () => {
    try {
      await refreshAddresses(currentPage);
      log(I18N.listRefreshed);
    } catch (err) {
      log(`${I18N.addressRefreshFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('export-all-addresses-btn').addEventListener('click', async () => {
    try {
      await exportAllAddresses();
    } catch (err) {
      log(`${I18N.exportFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('export-all-keys-btn').addEventListener('click', async () => {
    try {
      await exportAllPrivateKeys();
    } catch (err) {
      log(`${I18N.exportFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('import-addresses-btn').addEventListener('click', async () => {
    try {
      await importPrivateKeys();
    } catch (err) {
      log(`${I18N.importFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('delete-selected-btn').addEventListener('click', async () => {
    try {
      await batchDeleteSelected();
    } catch (err) {
      log(`${I18N.deleteFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('sweep-usdt-btn').addEventListener('click', async () => {
    try {
      await runSweepByAsset('USDT_TRC20');
    } catch (err) {
      log(`${I18N.sweepFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('sweep-trx-btn').addEventListener('click', async () => {
    try {
      await runSweepByAsset('TRX');
    } catch (err) {
      log(`${I18N.sweepFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('refresh-jobs-btn').addEventListener('click', async () => {
    try {
      await refreshJobs();
      log(I18N.jobsRefreshed);
    } catch (err) {
      log(`${I18N.jobsFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('clear-jobs-btn').addEventListener('click', async () => {
    try {
      await clearJobsHistory();
    } catch (err) {
      log(`${I18N.jobsClearFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('page-size-select').addEventListener('change', async (e) => {
    try {
      pageSize = Number(e.target.value || 50);
      currentPage = 1;
      await refreshAddresses(1);
      log(`${I18N.listRefreshed}: page_size=${pageSize}`);
    } catch (err) {
      log(`${I18N.addressRefreshFailed}: ${err.message}`);
      alert(err.message);
    }
  });

  document.getElementById('prev-page-btn').addEventListener('click', async () => {
    if (currentPage > 1) {
      await refreshAddresses(currentPage - 1);
    }
  });

  document.getElementById('next-page-btn').addEventListener('click', async () => {
    const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
    if (currentPage < totalPages) {
      await refreshAddresses(currentPage + 1);
    }
  });

  document.getElementById('select-all-current').addEventListener('change', (e) => {
    const checked = e.target.checked;
    currentAddresses.forEach((row) => {
      if (checked) {
        selectedAddressIds.add(row.id);
      } else {
        selectedAddressIds.delete(row.id);
      }
    });
    renderAddressRows();
  });

  document.getElementById('addresses-body').addEventListener('change', (e) => {
    const target = e.target;
    if (target.classList.contains('row-check')) {
      const id = target.dataset.id;
      if (target.checked) {
        selectedAddressIds.add(id);
      } else {
        selectedAddressIds.delete(id);
      }
      updateSelectAllState();
    }
  });

  document.getElementById('addresses-body').addEventListener('click', async (e) => {
    const target = e.target;
    if (target.classList.contains('save-tag-btn')) {
      const id = target.dataset.id;
      try {
        await saveTag(id);
      } catch (err) {
        log(`${I18N.tagSaveFailed}: ${err.message}`);
        alert(err.message);
      }
    }
  });

  try {
    pageSize = Number(document.getElementById('page-size-select').value || 50);
    await initialRefresh();
    log(I18N.ready);
  } catch (err) {
    log(`${I18N.initFailed}: ${err.message}`);
    alert(err.message);
  }
});
