(function () {
    function toIsoOrNull(localDateValue) {
        if (!localDateValue) return null;
        const date = new Date(localDateValue);
        if (Number.isNaN(date.getTime())) return null;
        return date.toISOString();
    }

    function getFilterValue(id) {
        const element = document.getElementById(id);
        return element ? String(element.value || '').trim() : '';
    }

    function buildQuery() {
        const params = new URLSearchParams();
        params.set('limit', '100');

        const level = getFilterValue('auditLevelFilter');
        const endpoint = getFilterValue('auditEndpointFilter');
        const actor = getFilterValue('auditActorFilter');
        const statusCode = getFilterValue('auditStatusFilter');
        const fromValue = toIsoOrNull(getFilterValue('auditFromFilter'));
        const toValue = toIsoOrNull(getFilterValue('auditToFilter'));

        if (level) params.set('level', level);
        if (endpoint) params.set('endpoint_contains', endpoint);
        if (actor) params.set('actor_email', actor);
        if (statusCode) params.set('status_code', statusCode);
        if (fromValue) params.set('from_time', fromValue);
        if (toValue) params.set('to_time', toValue);

        return params.toString();
    }

    function getStatusClass(code) {
        if (!code) return 'status-ready';
        if (code >= 500) return 'status-rejected';
        if (code >= 400) return 'status-alert';
        return 'status-completed';
    }

    function escapeHtml(input) {
        return String(input || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    async function loadAuditLogs() {
        const list = document.getElementById('auditLogList');
        const meta = document.getElementById('auditMeta');
        if (!list) return;

        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #888;">Loading audit logs...</div>';

        try {
            const query = buildQuery();
            const response = await APP.apiCall(`/admin/audit/logs?${query}`);
            if (!response) {
                list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #b93c3c;">Network error while loading logs.</div>';
                return;
            }

            if (!response.ok) {
                let detail = 'Failed to load audit logs.';
                try {
                    const payload = await response.json();
                    if (payload?.detail) detail = payload.detail;
                } catch (_error) {}
                list.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #b93c3c;">${escapeHtml(detail)}</div>`;
                return;
            }

            const data = await response.json();
            const logs = Array.isArray(data.logs) ? data.logs : [];

            if (meta) {
                meta.textContent = `Showing ${logs.length} of ${Number(data.total || 0)} event(s)`;
            }

            if (!logs.length) {
                list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #888;">No audit logs matched the selected filters.</div>';
                return;
            }

            list.innerHTML = logs.map((row) => {
                const eventTime = row.event_time ? new Date(row.event_time).toLocaleString() : '-';
                const status = row.status_code || '-';
                const level = row.level || 'INFO';
                const actor = row.actor_email || 'System';
                const endpoint = row.endpoint || '-';
                const method = row.http_method || '-';
                const requestId = row.request_id || '-';
                const ipAddress = row.ip_address || '-';
                const action = row.action || '-';
                const reference = row.reference || '-';

                return `
                    <div class="job-card" style="border-left: 4px solid #0f1d3d;">
                        <div class="job-header" style="display: flex; justify-content: space-between; gap: 0.5rem; align-items: center;">
                            <div class="job-id">${escapeHtml(reference)}</div>
                            <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                                <span class="job-status status-ready">${escapeHtml(level)}</span>
                                <span class="job-status ${getStatusClass(Number(status))}">${escapeHtml(String(status))}</span>
                            </div>
                        </div>
                        <div class="job-details" style="grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));">
                            <div class="job-detail"><span class="job-label">Time:</span> <span class="job-value">${escapeHtml(eventTime)}</span></div>
                            <div class="job-detail"><span class="job-label">Actor:</span> <span class="job-value">${escapeHtml(actor)}</span></div>
                            <div class="job-detail"><span class="job-label">Action:</span> <span class="job-value">${escapeHtml(action)}</span></div>
                            <div class="job-detail"><span class="job-label">Endpoint:</span> <span class="job-value">${escapeHtml(method)} ${escapeHtml(endpoint)}</span></div>
                            <div class="job-detail"><span class="job-label">Request ID:</span> <span class="job-value">${escapeHtml(requestId)}</span></div>
                            <div class="job-detail"><span class="job-label">IP Address:</span> <span class="job-value">${escapeHtml(ipAddress)}</span></div>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (error) {
            console.error('Failed to load audit logs:', error);
            list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #b93c3c;">Unexpected error while loading audit logs.</div>';
        }
    }

    function attachAuditLogHandlers() {
        const filterIds = [
            'auditLevelFilter',
            'auditEndpointFilter',
            'auditActorFilter',
            'auditStatusFilter',
            'auditFromFilter',
            'auditToFilter'
        ];

        filterIds.forEach((id) => {
            const input = document.getElementById(id);
            if (!input || input.dataset.bound === 'true') return;
            const eventName = input.tagName === 'SELECT' ? 'change' : 'input';
            input.addEventListener(eventName, () => {
                loadAuditLogs();
            });
            input.dataset.bound = 'true';
        });
    }

    function clearAuditFilters() {
        const ids = [
            'auditLevelFilter',
            'auditEndpointFilter',
            'auditActorFilter',
            'auditStatusFilter',
            'auditFromFilter',
            'auditToFilter'
        ];

        ids.forEach((id) => {
            const element = document.getElementById(id);
            if (element) {
                element.value = '';
            }
        });

        loadAuditLogs();
    }

    async function pruneAuditLogs() {
        const approved = confirm('Prune logs older than retention policy?');
        if (!approved) return;

        const response = await APP.apiCall('/admin/audit/prune', {
            method: 'POST'
        });

        if (!response) {
            alert('Failed to prune logs. Network error.');
            return;
        }
        if (!response.ok) {
            alert('Failed to prune logs.');
            return;
        }

        const payload = await response.json();
        alert(`Pruned ${Number(payload.deleted || 0)} old audit log(s).`);
        await loadAuditLogs();
    }

    window.loadAuditLogs = loadAuditLogs;
    window.attachAuditLogHandlers = attachAuditLogHandlers;
    window.clearAuditFilters = clearAuditFilters;
    window.pruneAuditLogs = pruneAuditLogs;
})();
