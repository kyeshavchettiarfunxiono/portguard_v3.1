async function loadTransnetStats() {
    const response = await APP.apiCall('/transnet/dashboard/stats');
    if (!response?.ok) {
        return;
    }
    const data = await response.json();

    const total = document.getElementById('transnetTotalVessels');
    const openStacks = document.getElementById('transnetOpenStacks');
    const closedStacks = document.getElementById('transnetClosedStacks');
    const updated = document.getElementById('transnetLastUpdated');
    const badge = document.getElementById('transnetIngestBadge');

    if (total) total.textContent = data.total_vessels ?? '-';
    if (openStacks) openStacks.textContent = data.stacks_open ?? '-';
    if (closedStacks) closedStacks.textContent = data.stacks_closed ?? '-';
    if (updated) {
        const ts = data.last_ingest_at || data.generated_at;
        updated.textContent = ts ? new Date(ts).toLocaleString() : '-';
    }
    if (badge) {
        const status = (data.last_ingest_status || 'unknown').toLowerCase();
        const map = {
            success: { bg: '#ecfdf3', color: '#027a48', label: 'Success' },
            warning: { bg: '#fffaeb', color: '#b54708', label: 'Warning' },
            failed: { bg: '#fef3f2', color: '#b42318', label: 'Failed' },
            running: { bg: '#eff8ff', color: '#175cd3', label: 'Running' },
            unknown: { bg: '#f2f4f7', color: '#344054', label: 'Unknown' }
        };
        const style = map[status] || map.unknown;
        badge.textContent = `Last ingest: ${style.label}`;
        badge.style.background = style.bg;
        badge.style.color = style.color;
    }
}

async function loadTransnetVessels() {
    const search = document.getElementById('transnetSearch');
    const query = search?.value ? `?q=${encodeURIComponent(search.value)}` : '';
    const response = await APP.apiCall(`/transnet/vessels${query}`);
    if (!response?.ok) {
        return;
    }

    const vessels = await response.json();
    const list = document.getElementById('transnetVesselList');
    if (!list) return;

    if (!vessels.length) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #888;">No vessels found</div>';
        return;
    }

    list.innerHTML = vessels.map(v => {
        const eta = v.eta ? new Date(v.eta).toLocaleString() : 'TBD';
        const etd = v.etd ? new Date(v.etd).toLocaleString() : 'TBD';
        const stackOpen = v.stack_open ? new Date(v.stack_open).toLocaleString() : 'TBD';
        const stackClose = v.stack_close ? new Date(v.stack_close).toLocaleString() : 'TBD';
        return `
            <div class="job-card">
                <div class="job-header">
                    <div class="job-id">${v.vessel_name || 'Unknown Vessel'}</div>
                    <span class="job-status status-ready">${v.status || 'Scheduled'}</span>
                </div>
                <div class="job-details">
                    <div class="job-detail"><span class="job-label">Voyage:</span> <span class="job-value">${v.voyage_number || '-'}</span></div>
                    <div class="job-detail"><span class="job-label">Terminal:</span> <span class="job-value">${v.terminal || '-'}</span></div>
                    <div class="job-detail"><span class="job-label">Berth:</span> <span class="job-value">${v.berth || '-'}</span></div>
                    <div class="job-detail"><span class="job-label">ETA:</span> <span class="job-value">${eta}</span></div>
                    <div class="job-detail"><span class="job-label">ETD:</span> <span class="job-value">${etd}</span></div>
                    <div class="job-detail"><span class="job-label">Stack Open:</span> <span class="job-value">${stackOpen}</span></div>
                    <div class="job-detail"><span class="job-label">Stack Close:</span> <span class="job-value">${stackClose}</span></div>
                </div>
                <div class="job-actions">
                    ${v.pdf_source_url ? `<a class="btn btn-secondary" href="${v.pdf_source_url}" target="_blank">View PDF</a>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

async function runTransnetScrape() {
    const button = document.getElementById('transnetScrapeBtn');
    if (button) {
        button.disabled = true;
        button.dataset.originalText = button.textContent || 'Run Live Scrape';
        button.textContent = 'Scraping...';
    }

    try {
        const response = await APP.apiCall('/transnet/live-scrape', { method: 'POST' });
        const payload = response ? await response.json() : null;

        if (response?.ok) {
            await loadTransnetStats();
            await loadTransnetVessels();

            const msg = payload?.message || 'Live scrape completed.';
            if (payload?.status === 'success') {
                alert(`✅ ${msg}`);
            } else if (payload?.status === 'warning') {
                alert(`⚠️ ${msg}`);
            } else {
                alert(msg);
            }
        } else {
            const detail = payload?.detail || payload?.message || 'Live scrape failed.';
            alert(`❌ ${detail}`);
        }
    } catch (error) {
        console.error('Transnet live scrape failed:', error);
        alert('❌ Live scrape failed. Check server logs.');
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = button.dataset.originalText || 'Run Live Scrape';
        }
    }
}

function attachTransnetHandlers() {
    const search = document.getElementById('transnetSearch');
    if (search && !search.dataset.bound) {
        search.addEventListener('input', () => {
            loadTransnetVessels();
        });
        search.dataset.bound = 'true';
    }
}

window.loadTransnetStats = loadTransnetStats;
window.loadTransnetVessels = loadTransnetVessels;
window.runTransnetScrape = runTransnetScrape;
window.attachTransnetHandlers = attachTransnetHandlers;
