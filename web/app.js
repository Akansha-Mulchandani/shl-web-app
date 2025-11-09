const apiBaseInput = document.getElementById('apiBase');
const saveBaseBtn = document.getElementById('saveBase');
const healthBtn = document.getElementById('healthBtn');
const healthStatus = document.getElementById('healthStatus');
const queryEl = document.getElementById('query');
const kEl = document.getElementById('k');
const recommendBtn = document.getElementById('recommendBtn');
const errorEl = document.getElementById('error');
const tableBody = document.querySelector('#results tbody');
const downloadBtn = document.getElementById('downloadCsv');

// Load base URL from localStorage
apiBaseInput.value = localStorage.getItem('API_BASE_URL') || '';

saveBaseBtn.addEventListener('click', () => {
  localStorage.setItem('API_BASE_URL', apiBaseInput.value.trim());
  healthStatus.textContent = 'Saved.';
});

healthBtn.addEventListener('click', async () => {
  const base = (apiBaseInput.value || '').trim();
  if (!base) return (healthStatus.textContent = 'Enter API base URL first.');
  healthStatus.textContent = 'Checking...';
  try {
    const res = await fetch(`${base.replace(/\/$/, '')}/health`);
    const json = await res.json();
    healthStatus.textContent = `Health: ${JSON.stringify(json)}`;
  } catch (e) {
    healthStatus.textContent = `Health check failed: ${e}`;
  }
});

recommendBtn.addEventListener('click', async () => {
  errorEl.textContent = '';
  tableBody.innerHTML = '';
  const base = (apiBaseInput.value || '').trim();
  if (!base) return (errorEl.textContent = 'Enter API base URL first.');
  const q = (queryEl.value || '').trim();
  if (!q) return (errorEl.textContent = 'Enter a query or JD.');
  const k = parseInt(kEl.value || '10', 10);
  try {
    const res = await fetch(`${base.replace(/\/$/, '')}/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q, k })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const arr = data.recommended_assessments || [];
    arr.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><a href="${r.url}" target="_blank" rel="noopener">${r.url}</a></td>
        <td>${Array.isArray(r.test_type) ? r.test_type.join(', ') : ''}</td>
        <td>${r.duration ?? ''}</td>
        <td>${r.adaptive_support ? 'Yes' : 'No'}</td>
        <td>${r.remote_support ? 'Yes' : 'No'}</td>
        <td>${r.description ?? ''}</td>
      `;
      tableBody.appendChild(tr);
    });
    downloadBtn.onclick = () => downloadCsv(q, arr);
  } catch (e) {
    errorEl.textContent = `Error: ${e.message || e}`;
  }
});

function downloadCsv(query, assessments) {
  // Two columns: Query, Assessment_url
  const rows = [['Query', 'Assessment_url']];
  assessments.forEach(r => rows.push([normalize(query), r.url || '']));
  const csv = rows.map(cols => cols.map(escapeCsv).join(',')).join('\r\n');
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'predictions.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}

function escapeCsv(v) {
  const s = String(v ?? '');
  if (s.includes('"') || s.includes(',') || s.includes('\n')) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

function normalize(text) {
  return (text || '').replace(/[\r\n]+/g, ' ').trim();
}
