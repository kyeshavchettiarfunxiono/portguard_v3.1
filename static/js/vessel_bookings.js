let vesselBookingItems = [];

function formatClientLabel(value) {
    return String(value || '')
        .trim()
        .replace(/_/g, ' ')
        .toLowerCase()
        .replace(/\b\w/g, letter => letter.toUpperCase());
}

async function loadBookingClients(bookingType) {
    const clientSelect = document.getElementById('bookingClient');
    if (!clientSelect) return;

    clientSelect.innerHTML = '<option value="">Loading clients...</option>';
    const response = await APP.apiCall(`/bookings/client-options?booking_type=${encodeURIComponent(bookingType)}`);
    if (!response?.ok) {
        clientSelect.innerHTML = '<option value="">Select client</option>';
        return;
    }

    const payload = await response.json();
    const clients = Array.isArray(payload.clients) ? payload.clients : [];

    clientSelect.innerHTML = '<option value="">Select client</option>';
    clients.forEach((client) => {
        const option = document.createElement('option');
        option.value = client;
        option.textContent = formatClientLabel(client);
        clientSelect.appendChild(option);
    });
}

async function syncBookingTypeFormState() {
    const bookingTypeSelect = document.getElementById('bookingType');
    const bookingType = (bookingTypeSelect?.value || 'EXPORT').toUpperCase();
    const isImport = bookingType === 'IMPORT';

    document.querySelectorAll('.import-only-field').forEach((node) => {
        node.style.display = isImport ? 'block' : 'none';
    });

    await loadBookingClients(bookingType);
}

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

function normalizeBookingReference(value) {
    return String(value || '').trim().toUpperCase();
}

async function findExistingBookingByReference(bookingReference, bookingType, client) {
    const normalizedReference = normalizeBookingReference(bookingReference);
    const normalizedType = String(bookingType || 'EXPORT').trim().toUpperCase();
    const normalizedClient = String(client || '').trim().replace(/\s+/g, '_').toUpperCase();

    if (!normalizedReference || !normalizedClient) {
        return null;
    }

    const response = await APP.apiCall(`/bookings/?client=${encodeURIComponent(normalizedClient)}&booking_type=${encodeURIComponent(normalizedType)}`);
    if (!response?.ok) {
        return null;
    }

    const bookings = await response.json();
    if (!Array.isArray(bookings)) {
        return null;
    }

    return bookings.find((booking) => normalizeBookingReference(booking?.booking_reference) === normalizedReference) || null;
}

async function approveQueueItemWithBooking(queueId, bookingId, errorElement) {
    if (!queueId) return true;

    const approveResponse = await APP.apiCall(`/transnet/booking-queue/${queueId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ booking_id: bookingId })
    });

    if (!approveResponse?.ok) {
        if (errorElement) {
            errorElement.textContent = 'Booking found/created but approval failed. Please retry approval.';
            errorElement.classList.remove('is-hidden');
        }
        return false;
    }

    return true;
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
    const bookingType = document.getElementById('bookingType');
    const vesselName = document.getElementById('bookingVesselName');
    const voyage = document.getElementById('bookingVoyage');
    const reference = document.getElementById('bookingReference');
    const containerType = document.getElementById('bookingContainerType');
    const arrivalVoyage = document.getElementById('bookingArrivalVoyage');
    const dateInDepot = document.getElementById('bookingDateInDepot');
    const category = document.getElementById('bookingCategory');
    const notes = document.getElementById('bookingNotes');

    if (!modal) return;

    if (error) {
        error.textContent = '';
        error.classList.add('is-hidden');
    }

    queueInput.value = queueId || '';
    if (bookingType) {
        bookingType.value = 'EXPORT';
    }
    if (card) {
        vesselName.value = card.dataset.vesselName || '';
        voyage.value = card.dataset.voyageNumber || '';
    } else {
        vesselName.value = '';
        voyage.value = '';
    }

    reference.value = '';
    containerType.value = '';
    if (arrivalVoyage) arrivalVoyage.value = '';
    if (dateInDepot) dateInDepot.value = '';
    if (category) category.value = '';
    if (notes) notes.value = '';
    title.textContent = queueId ? 'Approve Booking' : 'Create Booking';

    syncBookingTypeFormState();
    modal.style.display = 'flex';
}

function closeBookingModal() {
    const modal = document.getElementById('bookingModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function openImportBookingModal() {
    openBookingModal(null, null);
    const bookingType = document.getElementById('bookingType');
    if (bookingType) {
        bookingType.value = 'IMPORT';
        syncBookingTypeFormState();
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
            const bookingType = (document.getElementById('bookingType')?.value || 'EXPORT').toUpperCase();
            const vesselName = document.getElementById('bookingVesselName')?.value.trim();
            const voyageNumber = document.getElementById('bookingVoyage')?.value.trim();
            const arrivalVoyage = document.getElementById('bookingArrivalVoyage')?.value.trim();
            const dateInDepot = document.getElementById('bookingDateInDepot')?.value;
            const bookingReference = document.getElementById('bookingReference')?.value.trim();
            const rawClient = document.getElementById('bookingClient')?.value.trim();
            const client = rawClient ? rawClient.replace(/\s+/g, '_').toUpperCase() : '';
            const containerType = document.getElementById('bookingContainerType')?.value.trim();
            const category = (document.getElementById('bookingCategory')?.value || '').trim().toUpperCase();
            const notes = document.getElementById('bookingNotes')?.value.trim();
            const error = document.getElementById('bookingModalError');

            if (!vesselName || !bookingReference || !client || !containerType) {
                if (error) {
                    error.textContent = 'Please fill in all required fields.';
                    error.classList.remove('is-hidden');
                }
                return;
            }

            if (bookingType === 'IMPORT' && !category) {
                if (error) {
                    error.textContent = 'Please choose import category (FCL or GRP).';
                    error.classList.remove('is-hidden');
                }
                return;
            }

            const createResponse = await APP.apiCall('/bookings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    booking_reference: normalizeBookingReference(bookingReference),
                    booking_type: bookingType,
                    client,
                    vessel_name: vesselName,
                    voyage_number: voyageNumber || null,
                    arrival_voyage: bookingType === 'IMPORT' ? (arrivalVoyage || null) : null,
                    date_in_depot: bookingType === 'IMPORT' && dateInDepot ? new Date(dateInDepot).toISOString() : null,
                    container_type: containerType,
                    category: bookingType === 'IMPORT' ? category : null,
                    notes: bookingType === 'IMPORT' ? (notes || null) : null,
                })
            });

            if (!createResponse?.ok) {
                let detail = 'Failed to create booking.';
                let statusCode = 0;
                if (typeof createResponse.status === 'number') {
                    statusCode = createResponse.status;
                }
                try {
                    const payload = await createResponse.json();
                    if (payload?.detail) {
                        detail = payload.detail;
                    }
                } catch (_err) {
                    detail = 'Failed to create booking. Please try again.';
                }

                const duplicateReference = statusCode === 409 && /reference already exists/i.test(detail);
                if (duplicateReference) {
                    const existingBooking = await findExistingBookingByReference(bookingReference, bookingType, client);
                    if (existingBooking?.id) {
                        const approved = await approveQueueItemWithBooking(queueId, existingBooking.id, error);
                        if (!approved) {
                            return;
                        }

                        closeBookingModal();
                        loadVesselBookings();
                        refreshBookingDropdowns();
                        if (typeof APP.showSuccess === 'function') {
                            APP.showSuccess('Existing booking was reused successfully.');
                        }
                        return;
                    }
                }

                if (error) {
                    error.textContent = detail;
                    error.classList.remove('is-hidden');
                }
                return;
            }

            const created = await createResponse.json();

            const approved = await approveQueueItemWithBooking(queueId, created.id, error);
            if (!approved) {
                return;
            }

            closeBookingModal();
            loadVesselBookings();
            refreshBookingDropdowns();
        });
        form.dataset.bound = 'true';
    }

    const bookingType = document.getElementById('bookingType');
    if (bookingType && !bookingType.dataset.bound) {
        bookingType.addEventListener('change', () => {
            syncBookingTypeFormState();
        });
        bookingType.dataset.bound = 'true';
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
window.openBookingModal = openBookingModal;
window.openImportBookingModal = openImportBookingModal;
