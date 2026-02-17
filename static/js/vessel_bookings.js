let vesselBookingItems = [];

async function loadVesselBookings() {
    const list = document.getElementById('vesselBookingList');
    if (!list) return;

    const response = await APP.apiCall('/transnet/booking-queue');
    if (!response?.ok) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #b42318;">Failed to load approvals</div>';
        return;
    }

    vesselBookingItems = await response.json();
    applyBookingFilters();
}

function applyBookingFilters() {
    const search = document.getElementById('vesselBookingSearch');
    const statusFilter = document.getElementById('vesselBookingStatusFilter');
    const term = (search?.value || '').toLowerCase();
    const status = statusFilter?.value || '';

    let filtered = vesselBookingItems;
    if (term) {
        filtered = filtered.filter(item => {
            const hay = [item.vessel_name, item.voyage_number, item.terminal, item.berth]
                .filter(Boolean)
                .join(' ')
                .toLowerCase();
            return hay.includes(term);
        });
    }

    if (status) {
        filtered = filtered.filter(item => item.status === status);
    }

    renderBookingSections(filtered);
}

function renderBookingSections(items) {
    const list = document.getElementById('vesselBookingList');
    const approvedList = document.getElementById('vesselBookingApprovedList');
    const declinedList = document.getElementById('vesselBookingDeclinedList');
    const badge = document.getElementById('vesselBookingPendingCount');
    const pendingStat = document.getElementById('vesselBookingPendingStat');
    const approvedStat = document.getElementById('vesselBookingApprovedStat');
    const declinedStat = document.getElementById('vesselBookingDeclinedStat');
    if (!list || !approvedList || !declinedList) return;

    const pending = items.filter(item => item.status === 'pending');
    const approved = items.filter(item => item.status === 'approved');
    const declined = items.filter(item => item.status === 'declined');

    list.innerHTML = pending.length
        ? pending.map(renderBookingCard).join('')
        : '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #888;">No pending approvals</div>';

    approvedList.innerHTML = approved.length
        ? approved.map(renderBookingCard).join('')
        : '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #888;">No approved vessels</div>';

    declinedList.innerHTML = declined.length
        ? declined.map(renderBookingCard).join('')
        : '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #888;">No declined vessels</div>';

    if (badge) {
        badge.textContent = `Pending: ${pending.length}`;
    }
    if (pendingStat) pendingStat.textContent = pending.length;
    if (approvedStat) approvedStat.textContent = approved.length;
    if (declinedStat) declinedStat.textContent = declined.length;

    bindBookingActions();
}

function renderBookingCard(item) {
    const eta = item.eta ? new Date(item.eta).toLocaleString() : 'TBD';
    const statusMap = {
        pending: { label: 'Pending', className: 'status-ready' },
        approved: { label: 'Approved', className: 'status-completed' },
        declined: { label: 'Declined', className: 'status-blocked' }
    };
    const statusInfo = statusMap[item.status] || statusMap.pending;

    return `
        <div class="job-card" data-queue-id="${item.id}" data-vessel-name="${item.vessel_name || ''}" data-voyage-number="${item.voyage_number || ''}">
            <div class="job-header">
                <div class="job-id">${item.vessel_name || 'Unknown Vessel'}</div>
                <span class="job-status ${statusInfo.className}">${statusInfo.label}</span>
            </div>
            <div class="job-details">
                <div class="job-detail"><span class="job-label">Voyage:</span> <span class="job-value">${item.voyage_number || '-'}</span></div>
                <div class="job-detail"><span class="job-label">Terminal:</span> <span class="job-value">${item.terminal || '-'}</span></div>
                <div class="job-detail"><span class="job-label">Berth:</span> <span class="job-value">${item.berth || '-'}</span></div>
                <div class="job-detail"><span class="job-label">ETA:</span> <span class="job-value">${eta}</span></div>
            </div>
            <div class="job-actions">
                ${item.status === 'pending' ? '<button class="btn btn-primary" data-action="approve">Approve</button>' : ''}
                ${item.status === 'pending' ? '<button class="btn btn-secondary" data-action="decline">Decline</button>' : ''}
                ${item.status === 'declined' ? '<button class="btn btn-secondary" data-action="requeue">Re-Queue</button>' : ''}
                ${item.status !== 'approved' ? '<button class="btn btn-secondary" data-action="create">Create Booking</button>' : ''}
                ${item.pdf_source_url ? `<a class="btn btn-secondary" href="${item.pdf_source_url}" target="_blank">View PDF</a>` : ''}
            </div>
        </div>
    `;
}

function bindBookingActions() {
    document.querySelectorAll('#vesselBookingList .job-card, #vesselBookingDeclinedList .job-card, #vesselBookingApprovedList .job-card').forEach(card => {
        const queueId = card.dataset.queueId;
        card.querySelectorAll('button[data-action]').forEach(button => {
            button.addEventListener('click', () => {
                const action = button.dataset.action;
                if (action === 'approve') {
                    openBookingModal(queueId, card);
                } else if (action === 'decline') {
                    declineQueueItem(queueId);
                } else if (action === 'requeue') {
                    requeueQueueItem(queueId);
                } else if (action === 'create') {
                    openBookingModal(null, card);
                }
            });
        });
    });
}

async function declineQueueItem(queueId) {
    const response = await APP.apiCall(`/transnet/booking-queue/${queueId}/decline`, { method: 'POST' });
    if (response?.ok) {
        loadVesselBookings();
    }
}

function refreshBookingDropdowns() {
    if (typeof window.loadFCLBookings === 'function') {
        window.loadFCLBookings();
    }
    if (typeof window.loadBookingsForClient === 'function') {
        window.loadBookingsForClient();
    }
}

async function requeueQueueItem(queueId) {
    const response = await APP.apiCall(`/transnet/booking-queue/${queueId}/requeue`, { method: 'POST' });
    if (response?.ok) {
        loadVesselBookings();
    }
}

function openBookingModal(queueId, card) {
    const modal = document.getElementById('bookingModal');
    const title = document.getElementById('bookingModalTitle');
    const error = document.getElementById('bookingModalError');
    const queueInput = document.getElementById('bookingQueueId');
    const vesselName = document.getElementById('bookingVesselName');
    const voyage = document.getElementById('bookingVoyage');
    const reference = document.getElementById('bookingReference');
    const client = document.getElementById('bookingClient');
    const containerType = document.getElementById('bookingContainerType');

    if (!modal) return;

    if (error) {
        error.textContent = '';
        error.classList.add('is-hidden');
    }

    queueInput.value = queueId || '';
    if (card) {
        vesselName.value = card.dataset.vesselName || '';
        voyage.value = card.dataset.voyageNumber || '';
    } else {
        vesselName.value = '';
        voyage.value = '';
    }

    reference.value = '';
    client.value = '';
    containerType.value = '';
    title.textContent = queueId ? 'Approve Booking' : 'Create Booking';

    modal.style.display = 'flex';
}

function closeBookingModal() {
    const modal = document.getElementById('bookingModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function attachBookingHandlers() {
    const newBookingBtn = document.getElementById('newBookingBtn');
    const modal = document.getElementById('bookingModal');
    const form = document.getElementById('bookingForm');
    const search = document.getElementById('vesselBookingSearch');
    const statusFilter = document.getElementById('vesselBookingStatusFilter');

    if (newBookingBtn && !newBookingBtn.dataset.bound) {
        newBookingBtn.addEventListener('click', () => openBookingModal(null, null));
        newBookingBtn.dataset.bound = 'true';
    }

    if (search && !search.dataset.bound) {
        search.addEventListener('input', applyBookingFilters);
        search.dataset.bound = 'true';
    }

    if (statusFilter && !statusFilter.dataset.bound) {
        statusFilter.addEventListener('change', applyBookingFilters);
        statusFilter.dataset.bound = 'true';
    }

    if (form && !form.dataset.bound) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            const queueId = document.getElementById('bookingQueueId')?.value || null;
            const vesselName = document.getElementById('bookingVesselName')?.value.trim();
            const bookingReference = document.getElementById('bookingReference')?.value.trim();
            const rawClient = document.getElementById('bookingClient')?.value.trim();
            const client = rawClient ? rawClient.replace(/\s+/g, '_').toUpperCase() : '';
            const containerType = document.getElementById('bookingContainerType')?.value.trim();
            const error = document.getElementById('bookingModalError');

            if (!vesselName || !bookingReference || !client || !containerType) {
                if (error) {
                    error.textContent = 'Please fill in all required fields.';
                    error.classList.remove('is-hidden');
                }
                return;
            }

            const createResponse = await APP.apiCall('/bookings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    booking_reference: bookingReference,
                    client,
                    vessel_name: vesselName,
                    container_type: containerType,
                })
            });

            if (!createResponse?.ok) {
                if (error) {
                    error.textContent = 'Failed to create booking. Check the reference.';
                    error.classList.remove('is-hidden');
                }
                return;
            }

            const created = await createResponse.json();

            if (queueId) {
                const approveResponse = await APP.apiCall(`/transnet/booking-queue/${queueId}/approve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ booking_id: created.id })
                });

                if (!approveResponse?.ok) {
                    if (error) {
                        error.textContent = 'Booking created but approval failed.';
                        error.classList.remove('is-hidden');
                    }
                    return;
                }
            }

            closeBookingModal();
            loadVesselBookings();
            refreshBookingDropdowns();
        });
        form.dataset.bound = 'true';
    }

    if (modal && !modal.dataset.bound) {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeBookingModal();
            }
        });
        modal.dataset.bound = 'true';
    }
}

window.loadVesselBookings = loadVesselBookings;
window.attachBookingHandlers = attachBookingHandlers;
window.closeBookingModal = closeBookingModal;
