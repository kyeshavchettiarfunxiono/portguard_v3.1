/**
 * PortGuard CCMS - Operator Dashboard - Containers Module
 * Handles all container-related operations: CRUD, filtering, and display
 */

// ============= CONTAINER LOADING =============
function normalizeEnum(value) {
    if (value && typeof value === 'object' && 'value' in value) {
        return value.value;
    }
    return value ?? '';
}

function normalizeStatus(value) {
    return String(normalizeEnum(value));
}

function normalizeType(value) {
    return String(normalizeEnum(value));
}

async function loadContainers() {
    try {
        const response = await APP.apiCall('/containers');
        if (response?.ok) {
            const containers = await response.json();
            displayContainers(containers);
            return containers;
        }
    } catch (error) {
        console.error('Error loading containers:', error);
        APP.showError('Failed to load containers');
    }
}

async function loadActiveContainers() {
    try {
        const response = await APP.apiCall('/containers?status=PACKING,UNPACKING');
        if (response?.ok) {
            const containers = await response.json();
            displayActiveContainers(containers);
        }
    } catch (error) {
        console.error('Error loading active containers:', error);
    }
}

async function loadNewContainers() {
    try {
        const response = await APP.apiCall('/containers?status=PENDING_REVIEW');
        if (response?.ok) {
            const containers = await response.json();
            displayNewContainers(containers);
        }
    } catch (error) {
        console.error('Error loading new containers:', error);
    }
}

async function loadReadyContainers() {
    try {
        const response = await APP.apiCall('/containers?status=REGISTERED,PACKING');
        if (response?.ok) {
            const containers = await response.json();
            displayReadyContainers(containers);
        }
    } catch (error) {
        console.error('Error loading ready containers:', error);
    }
}

async function loadCompletedContainers() {
    try {
        const response = await APP.apiCall('/containers?status=FINALIZED');
        if (response?.ok) {
            const containers = await response.json();
            displayCompletedContainers(containers);
        }
    } catch (error) {
        console.error('Error loading completed containers:', error);
    }
}

function getActivePackingContainerId() {
    return localStorage.getItem('active_packing_container_id');
}

// ============= DOWNTIME REPORTING =============
async function submitDowntimeReport(event) {
    event.preventDefault();

    const containerId = document.getElementById('downtimeContainerId').value.trim();
    const downtimeType = document.getElementById('downtimeType').value;
    const startValue = document.getElementById('downtimeStart').value;
    const endValue = document.getElementById('downtimeEnd').value;
    const reason = document.getElementById('downtimeReason').value.trim();

    if (!containerId || !downtimeType || !startValue || !reason) {
        APP.showError('Please fill in all required fields');
        return;
    }

    const payload = {
        downtime_type: downtimeType,
        reason,
        start_time: new Date(startValue).toISOString(),
        end_time: endValue ? new Date(endValue).toISOString() : null
    };

    try {
        const response = await APP.apiCall(`/containers/${containerId}/downtime/log`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (response?.ok) {
            const result = await response.json();
            let statusText = 'Downtime logged (ongoing)';
            if (result.status === 'COMPLETED') {
                const cost = Number(result.cost_impact || 0);
                const duration = Number(result.duration_hours || 0);
                const costText = cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                const durationText = duration > 0 ? ` (${duration.toFixed(2)} hrs)` : '';
                statusText = `Cost: R${costText}${durationText}`;
            }
            APP.showSuccess(`Downtime logged. ${statusText}`);
            event.target.reset();
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to log downtime');
        }
    } catch (error) {
        console.error('Error logging downtime:', error);
        APP.showError('Error logging downtime');
    }
}

window.submitDowntimeReport = submitDowntimeReport;

// ============= CONTAINER DISPLAY =============
function displayContainers(containers) {
    const list = document.getElementById('containersList');
    if (!list) return;

    list.innerHTML = containers.map(c => createJobCardHTML(c)).join('');
}

function displayActiveContainers(containers) {
    const list = document.getElementById('activeJobsList');
    if (!list) return;
    const activePackingId = getActivePackingContainerId();
    const activeContainers = containers.filter(c => {
        const status = normalizeStatus(c.status);
        if (status === 'UNPACKING') return true;
        if (status === 'PACKING') {
            return !activePackingId || String(c.id) === String(activePackingId);
        }
        return false;
    });

    if (activeContainers.length === 0) {
        list.innerHTML = '<div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: #999;">No active jobs</div>';
    } else {
        list.innerHTML = activeContainers.map(c => createJobCardHTML(c)).join('');
    }
}

function displayNewContainers(containers) {
    const list = document.getElementById('newJobsList');
    if (!list) return;

    if (containers.length === 0) {
        list.innerHTML = '<div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: #999;">No new jobs</div>';
    } else {
        list.innerHTML = containers.map(c => createJobCardHTML(c)).join('');
    }
}

function displayReadyContainers(containers) {
    const list = document.getElementById('readyJobsList');
    if (!list) return;
    const activePackingId = getActivePackingContainerId();
    const readyContainers = containers.filter(c => {
        const status = normalizeStatus(c.status);
        if (status === 'REGISTERED') return true;
        if (status === 'PACKING') {
            return !activePackingId || String(c.id) !== String(activePackingId);
        }
        return false;
    });

    if (readyContainers.length === 0) {
        list.innerHTML = '<div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: #999;">No containers ready for work</div>';
    } else {
        list.innerHTML = readyContainers.map(c => createReadyJobCardHTML(c, activePackingId)).join('');
    }
}

function displayCompletedContainers(containers) {
    const list = document.getElementById('completedJobsList');
    if (!list) return;

    if (containers.length === 0) {
        list.innerHTML = '<div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: #999;">No completed jobs yet</div>';
    } else {
        list.innerHTML = containers.map(c => createJobCardHTML(c)).join('');
    }
}

function displayExportContainers(containers) {
    const list = document.getElementById('exportContainersList');
    if (!list) return;

    const activePackingId = getActivePackingContainerId();

    const registeredContainers = containers.filter(c => {
        const status = normalizeStatus(c.status);
        return status === 'REGISTERED' || status === 'PACKING';
    });

    if (registeredContainers.length === 0) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #999;">No containers available for packing. Create a new container to get started.</div>';
        return;
    }

    list.innerHTML = registeredContainers.map(c => {
        const status = normalizeStatus(c.status);
        const blockedByDamage = Boolean(c.needs_repair);
        const isPaused = status === 'PACKING' && (!activePackingId || String(c.id) !== String(activePackingId));
        const statusText = isPaused ? 'PAUSED' : status.replace('_', ' ');
        const statusStyle = isPaused
            ? 'background: #ffe8cc; color: #8a4b08;'
            : 'background: #fff3cd; color: #856404;';
        const progress = APP.getProgressForStatus(status);
        return `
            <div class="container-card" style="cursor: pointer;" onclick="viewExportContainerDetails('${c.id}')">
                <div class="container-card-header">
                    <span class="container-number">${c.container_no}</span>
                    <span class="container-type">${normalizeType(c.type)}</span>
                </div>
                <div class="container-card-details">
                    <div><span>Client:</span> <span>${c.client || 'N/A'}</span></div>
                    <div><span>Status:</span> <span class="status-badge" style="${statusStyle}">${statusText}</span></div>
                </div>
                <div class="container-card-footer">
                    <div class="progress-bar-container"><div class="progress-bar" style="width: ${progress}"></div></div>
                </div>
                <button class="btn btn-primary" ${blockedByDamage ? 'disabled' : ''} onclick="event.stopPropagation(); continuePacking('${c.id}')" style="width: 100%; margin-top: 1rem;">▶️ ${status === 'PACKING' ? 'Continue Packing' : 'Start Packing'}</button>
                ${blockedByDamage ? '<div class="damage-blocked-note">Blocked: damage marked as Major/Critical. Complete repair first.</div>' : ''}
            </div>
        `;
    }).join('');
}

function updateExportPackingStats(containers) {
    const available = containers.filter(c => normalizeStatus(c.status) === 'REGISTERED').length;
    const inProgress = containers.filter(c => normalizeStatus(c.status) === 'PACKING').length;
    const packed = containers.filter(c => normalizeStatus(c.status) === 'PENDING_REVIEW').length;
    const vesselCount = new Set(containers.map(c => c.booking_id).filter(Boolean)).size;

    const availableEl = document.getElementById('exportAvailableCount');
    const inProgressEl = document.getElementById('exportInProgressCount');
    const packedEl = document.getElementById('exportPackedCount');
    const vesselsEl = document.getElementById('exportVesselsCount');

    if (availableEl) availableEl.textContent = String(available);
    if (inProgressEl) inProgressEl.textContent = String(inProgress);
    if (packedEl) packedEl.textContent = String(packed);
    if (vesselsEl) vesselsEl.textContent = String(vesselCount);
}

// ============= JOB CARD CREATION =============
function createJobCardHTML(container) {
    const statusValue = normalizeStatus(container.status);
    const typeValue = normalizeType(container.type) || 'Standard';
    const statusClass = APP.getStatusClass(statusValue);
    const progressPercent = APP.getProgressForStatus(statusValue);
    const client = container.client || 'N/A';
    const activePackingId = getActivePackingContainerId();
    const isActivePacking = statusValue === 'PACKING' && activePackingId && String(container.id) === String(activePackingId);
    const statusLabel = isActivePacking ? 'PACKING (ACTIVE)' : statusValue.replace('_', ' ');
    
    return `
        <div class="container-card" onclick="openContainer('${container.id}', 'view')">
            <div class="container-card-header">
                <span class="container-number">${container.container_no}</span>
                <span class="container-type">${typeValue}</span>
            </div>
            
            <div class="container-card-details">
                <div>
                    <span>Client:</span>
                    <span>${client}</span>
                </div>
                <div>
                    <span>Status:</span>
                    <span class="status-badge ${statusClass}">${statusLabel}</span>
                </div>
                <div>
                    <span>Created:</span>
                    <span>${APP.formatDate(container.created_at)}</span>
                </div>
            </div>
            
            <div class="container-card-footer">
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${progressPercent}"></div>
                </div>
                <span class="progress-text">${progressPercent}</span>
            </div>
            
            <div class="container-card-actions">
                <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); openContainer('${container.id}', 'edit')">
                    Edit
                </button>
                <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); viewContainerDetails('${container.id}')">
                    Details
                </button>
            </div>
        </div>
    `;
}

function createReadyJobCardHTML(container, activePackingId) {
    const status = normalizeStatus(container.status);
    const typeValue = normalizeType(container.type) || 'Standard';
    const client = container.client || 'N/A';
    const isPaused = status === 'PACKING' && (!activePackingId || String(container.id) !== String(activePackingId));
    const statusText = isPaused ? 'PAUSED' : status.replace('_', ' ');
    const statusStyle = isPaused
        ? 'background: #ffe8cc; color: #8a4b08;'
        : 'background: #e7f5ff; color: #1c7ed6;';
    const progressPercent = APP.getProgressForStatus(status);
    const actionLabel = status === 'PACKING' ? 'Continue Packing' : 'Start Packing';
    const blockedByDamage = Boolean(container.needs_repair);

    return `
        <div class="container-card" onclick="openContainer('${container.id}', 'view')">
            <div class="container-card-header">
                <span class="container-number">${container.container_no}</span>
                <span class="container-type">${typeValue}</span>
            </div>

            <div class="container-card-details">
                <div>
                    <span>Client:</span>
                    <span>${client}</span>
                </div>
                <div>
                    <span>Status:</span>
                    <span class="status-badge" style="${statusStyle}">${statusText}</span>
                </div>
                <div>
                    <span>Created:</span>
                    <span>${APP.formatDate(container.created_at)}</span>
                </div>
            </div>

            <div class="container-card-footer">
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${progressPercent}"></div>
                </div>
                <span class="progress-text">${progressPercent}</span>
            </div>

            <div class="container-card-actions">
                <button class="btn btn-sm btn-primary" ${blockedByDamage ? 'disabled' : ''} onclick="event.stopPropagation(); continuePacking('${container.id}')">
                    ▶️ ${actionLabel}
                </button>
                <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); viewContainerDetails('${container.id}')">
                    Details
                </button>
            </div>
            ${blockedByDamage ? '<div class="damage-blocked-note">Blocked: damage marked as Major/Critical. Complete repair first.</div>' : ''}
        </div>
    `;
}

// ============= CONTAINER OPERATIONS =============
async function openContainer(containerId, action) {
    try {
        const response = await APP.apiCall(`/containers/${containerId}`);
        if (response?.ok) {
            const container = await response.json();
            
            if (action === 'edit') {
                populateContainerForm(container);
                openModal('containerModal');
            } else if (action === 'view' || action === 'packing') {
                updateContainerPanel(container);
                openModal('containerDetailsModal');
            }
        }
    } catch (error) {
        console.error('Error opening container:', error);
        APP.showError('Failed to load container details');
    }
}

async function viewContainerDetails(containerId) {
    try {
        const response = await APP.apiCall(`/containers/${containerId}`);
        if (response?.ok) {
            const container = await response.json();
            displayDetailedView(container);
        }
    } catch (error) {
        console.error('Error viewing container details:', error);
        APP.showError('Failed to load container details');
    }
}

function populateContainerForm(container) {
    document.getElementById('containerID').value = container.id || '';
    document.getElementById('containerNo').value = container.container_no || '';
    document.getElementById('containerType').value = container.type || '';
    document.getElementById('clientName').value = container.client || '';
    document.getElementById('containerStatus').value = container.status || '';
    document.getElementById('notes').value = container.notes || '';
}

function updateContainerPanel(container) {
    document.getElementById('panelContainerNo').textContent = container.container_no || 'N/A';
    document.getElementById('panelType').textContent = container.type || 'Standard';
    document.getElementById('panelClient').textContent = container.client || 'N/A';
    document.getElementById('panelStatus').textContent = container.status.replace('_', ' ');
    document.getElementById('panelCreated').textContent = APP.formatDate(container.created_at);
    document.getElementById('panelNotes').textContent = container.notes || 'No notes';
}

function displayDetailedView(container) {
    const details = `
        <div style="padding: 2rem;">
            <h3>${container.container_no}</h3>
            <table style="width: 100%; margin-top: 1rem;">
                <tr>
                    <td><strong>Type:</strong></td>
                    <td>${container.type || 'Standard'}</td>
                </tr>
                <tr>
                    <td><strong>Client:</strong></td>
                    <td>${container.client || 'N/A'}</td>
                </tr>
                <tr>
                    <td><strong>Status:</strong></td>
                    <td><span class="status-badge ${APP.getStatusClass(container.status)}">${container.status.replace('_', ' ')}</span></td>
                </tr>
                <tr>
                    <td><strong>Created:</strong></td>
                    <td>${APP.formatDate(container.created_at)}</td>
                </tr>
                <tr>
                    <td><strong>Notes:</strong></td>
                    <td>${container.notes || 'No notes'}</td>
                </tr>
            </table>
        </div>
    `;
    
    const modal = document.getElementById('containerDetailsModal');
    if (modal) {
        modal.querySelector('.-modal-body').innerHTML = details;
        openModal('containerDetailsModal');
    }
}

// ============= IMPORT/FCL OPERATIONS =============
async function loadAvailableFCLContainers() {
    try {
        const response = await APP.apiCall('/containers');
        if (response?.ok) {
            const containers = await response.json();
            const fclContainers = containers.filter(c => {
                const hasImportMarkers = Boolean(c.arrival_date || c.unpacking_location || c.cargo_type);
                const isUnpacking = ['REGISTERED', 'UNPACKING'].includes(c.status);
                return isUnpacking && (hasImportMarkers || c.status === 'UNPACKING');
            });
            displayFCLContainers(fclContainers);
            return fclContainers;
        }
    } catch (error) {
        console.error('Error loading FCL containers:', error);
    }
}

function displayFCLContainers(containers) {
    const list = document.getElementById('availableFCLList');
    if (!list) return;

    if (containers.length === 0) {
        list.innerHTML = '<div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: #999;">No FCL containers available</div>';
    } else {
        list.innerHTML = containers.map(c => createFCLJobCardHTML(c)).join('');
    }
}

// Special card for FCL containers with unpacking button
function createFCLJobCardHTML(container) {
    const statusClass = APP.getStatusClass(container.status);
    const progressPercent = APP.getProgressForStatus(container.status);
    const type = container.type || 'FCL';
    const client = container.client || 'N/A';
    
    return `
        <div class="container-card">
            <div class="container-card-header">
                <span class="container-number">${container.container_no}</span>
                <span class="container-type">${type}</span>
            </div>
            
            <div class="container-card-details">
                <div>
                    <span>Client:</span>
                    <span>${client}</span>
                </div>
                <div>
                    <span>Status:</span>
                    <span class="status-badge ${statusClass}">${container.status.replace('_', ' ')}</span>
                </div>
                <div>
                    <span>Created:</span>
                    <span>${APP.formatDate(container.created_at)}</span>
                </div>
            </div>
            
            <div class="container-card-footer">
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${progressPercent}%;"></div>
                </div>
                <span class="progress-text">${progressPercent}%</span>
            </div>
            
            <div class="container-card-actions">
                <button class="btn btn-primary" onclick="startUnpackingForContainer('${container.id}'); return false;" style="width: 100%;">
                    📥 Start Unpacking
                </button>
            </div>
        </div>
    `;
}

let fclBookingsData = {};

async function loadFCLBookings() {
    try {
        const response = await APP.apiCall('/bookings');
        if (!response?.ok) {
            APP.showError('Failed to load bookings');
            return;
        }
        const bookings = await response.json();
        fclBookingsData = {};
        bookings.forEach(booking => {
            fclBookingsData[booking.id] = booking;
        });

        const select = document.getElementById('fclBooking');
        if (!select) return;
        select.innerHTML = '<option value="">Select booking...</option>' +
            bookings.map(b => `<option value="${b.id}">${b.booking_reference} - ${b.vessel_name} (${b.client})</option>`).join('');
    } catch (error) {
        console.error('Error loading FCL bookings:', error);
        APP.showError('Error loading bookings');
    }
}

function updateFCLBookingDetails() {
    const bookingId = document.getElementById('fclBooking')?.value;
    const booking = fclBookingsData[bookingId];
    if (!booking) return;

    const clientInput = document.getElementById('fclClient');
    const vesselInput = document.getElementById('fclVesselName');
    if (clientInput) clientInput.value = booking.client || '';
    if (vesselInput) vesselInput.value = booking.vessel_name || '';

    const typeMap = {
        '20FT': '20ft',
        '40FT': '40ft',
        'HC': '40ft_HC'
    };
    const typeSelect = document.getElementById('fclContainerType');
    if (typeSelect && booking.container_type) {
        typeSelect.value = typeMap[booking.container_type] || '';
    }
}

function showRegisterFCLForm() {
    const modal = document.getElementById('fclContainerModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        loadFCLBookings();
    }
}

function closeFCLModal() {
    const modal = document.getElementById('fclContainerModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        const form = document.getElementById('fclRegistrationForm');
        if (form) form.reset();
    }
}

// ============= TRUCK OPERATIONS =============
async function loadBackloadTrucks() {
    try {
        const response = await APP.apiCall('/backload-trucks');
        if (response?.ok) {
            const trucks = await response.json();
            const list = document.getElementById('exportTruckList');
            if (list) {
                if (trucks.length === 0) {
                    list.innerHTML = '<div style="text-align: center; padding: 2rem; color: #999;">No backload trucks registered</div>';
                } else {
                    list.innerHTML = trucks.map(t => `
                        <div class="container-card">
                            <div class="container-card-header">
                                <span class="container-number">${t.truck_registration}</span>
                                <span class="container-type">${t.client}</span>
                            </div>
                            <div class="container-card-details">
                                <div><span>Driver:</span> <span>${t.driver_name}</span></div>
                                <div><span>Status:</span> <span class="status-badge ${APP.getStatusClass(t.status)}">${t.status}</span></div>
                            </div>
                        </div>
                    `).join('');
                }
            }
        }
    } catch (error) {
        console.error('Error loading backload trucks:', error);
    }
}

async function loadTruckOffloading() {
    try {
        const response = await APP.apiCall('/truck-offloading');
        if (response?.ok) {
            const trucks = await response.json();
            const list = document.getElementById('truckOffloadingList');
            if (list) {
                if (trucks.length === 0) {
                    list.innerHTML = '<div style="text-align: center; padding: 2rem; color: #999;">No trucks for offloading</div>';
                } else {
                    list.innerHTML = trucks.map(t => `
                        <div class="container-card">
                            <div class="container-card-header">
                                <span class="container-number">${t.truck_registration}</span>
                                <span class="container-type">${t.commodity_type}</span>
                            </div>
                            <div class="container-card-details">
                                <div><span>Client:</span> <span>${t.client}</span></div>
                                <div><span>Status:</span> <span class="status-badge ${APP.getStatusClass(t.status)}">${t.status}</span></div>
                            </div>
                        </div>
                    `).join('');
                }
            }
        }
    } catch (error) {
        console.error('Error loading truck offloading:', error);
    }
}

// ============= CONTAINER REGISTRATION & UPDATES =============
async function registerContainer(formData) {
    try {
        const response = await APP.apiCall('/containers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (response?.ok) {
            const result = await response.json();
            APP.showSuccess('Container registered successfully');
            loadContainers();
            return result;
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to register container');
            return null;
        }
    } catch (error) {
        console.error('Error registering container:', error);
        APP.showError('Error registering container');
        return null;
    }
}

// ============= PACKING WORKFLOW =============
let currentPackingContainerId = null;
let currentPackingStep = null;

const PACKING_STEP_INFO = {
    BEFORE_PACKING: {
        title: 'Step 1: Before Packing Photos',
        instructions: 'Document the empty container condition. Capture interior, exterior, doors, floor, roof, and corners. 20ft: minimum 4 photos. 40ft/HC: minimum 5 photos.'
    },
    CARGO_PHOTOS: {
        title: 'Step 2: Cargo Photos',
        instructions: 'Document cargo loading, labels, securing, and packing process.'
    },
    AFTER_PACKING: {
        title: 'Step 3: After Packing Photos',
        instructions: 'Document the fully packed container before doors are closed.'
    },
    SEALING: {
        title: 'Step 4: Sealing',
        instructions: 'Apply the seal, capture the seal photo, and enter seal details.'
    }
};

async function startPacking(containerId) {
    try {
        const containerRes = await APP.apiCall(`/containers/${containerId}`);
        if (containerRes?.ok) {
            const container = await containerRes.json();
            if (container.needs_repair) {
                APP.showError('Container is blocked by damage and needs repair before packing.');
                return;
            }
        }

        const response = await APP.apiCall(`/packing/start/${containerId}`, { method: 'POST' });
        if (!response?.ok) {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to start packing');
            return;
        }

        currentPackingContainerId = containerId;
        localStorage.setItem('active_packing_container_id', containerId);
        openPackingWorkflow();
        await loadPackingProgress();
        await loadContainers();
    } catch (error) {
        console.error('Error starting packing:', error);
        APP.showError('Error starting packing');
    }
}

function continuePacking(containerId) {
    startPacking(containerId);
}

function openPackingWorkflow() {
    const modal = document.getElementById('packingWorkflowModal');
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

function closePackingWorkflow() {
    const modal = document.getElementById('packingWorkflowModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

async function loadPackingProgress() {
    if (!currentPackingContainerId) return;

    const response = await APP.apiCall(`/packing/${currentPackingContainerId}/progress`);
    if (!response?.ok) return;
    const progress = await response.json();

    currentPackingStep = progress.current_step;
    updatePackingStepUI(progress);
    await updatePackingAdvanceState();
    await loadPackingPhotos();
}

function updatePackingStepUI(progress) {
    const info = PACKING_STEP_INFO[progress.current_step] || {};
    const containerDisplay = document.getElementById('packingContainerDisplay');
    const stepTitle = document.getElementById('packingStepTitle');
    const stepInstructions = document.getElementById('packingStepInstructions');
    const requiredEl = document.getElementById('packingRequiredPhotos');
    const uploadedEl = document.getElementById('packingUploadedPhotos');
    const typeEl = document.getElementById('packingContainerType');
    const stepEl = document.getElementById('packingCurrentStep');
    const sealSection = document.getElementById('packingSealSection');
    const nextBtn = document.getElementById('packingNextBtn');
    const completeBtn = document.getElementById('packingCompleteBtn');

    if (containerDisplay) containerDisplay.textContent = `Container: ${currentPackingContainerId}`;
    if (stepTitle) stepTitle.textContent = info.title || 'Packing Step';
    if (stepInstructions) stepInstructions.textContent = info.instructions || '';
    if (requiredEl) requiredEl.textContent = String(progress.required_photos || 0);
    if (uploadedEl) uploadedEl.textContent = String(progress.current_photos || 0);
    if (typeEl) typeEl.textContent = progress.container_type || '-';
    if (stepEl) stepEl.textContent = progress.current_step || '-';

    const stepOrder = ['BEFORE_PACKING', 'CARGO_PHOTOS', 'AFTER_PACKING', 'SEALING'];
    const currentIndex = stepOrder.indexOf(progress.current_step);
    const chipMap = {
        BEFORE_PACKING: document.getElementById('packingStepBefore'),
        CARGO_PHOTOS: document.getElementById('packingStepCargo'),
        AFTER_PACKING: document.getElementById('packingStepAfter'),
        SEALING: document.getElementById('packingStepSeal')
    };

    stepOrder.forEach((step, index) => {
        const el = chipMap[step];
        if (!el) return;
        if (index < currentIndex) {
            el.className = 'job-status status-completed';
        } else if (index === currentIndex) {
            el.className = 'job-status status-in-progress';
        } else {
            el.className = 'job-status status-ready';
        }
    });

    if (sealSection) sealSection.style.display = progress.current_step === 'SEALING' ? 'block' : 'none';
    if (nextBtn) nextBtn.style.display = progress.current_step === 'SEALING' ? 'none' : 'inline-flex';
    if (completeBtn) completeBtn.style.display = progress.current_step === 'SEALING' ? 'inline-flex' : 'none';

    if (nextBtn) {
        const nextLabels = {
            BEFORE_PACKING: 'Next: Cargo Photos',
            CARGO_PHOTOS: 'Next: After Packing',
            AFTER_PACKING: 'Next: Sealing'
        };
        nextBtn.textContent = nextLabels[progress.current_step] || 'Next Step';
    }
}

async function updatePackingAdvanceState() {
    if (!currentPackingContainerId) return;
    const response = await APP.apiCall(`/packing/${currentPackingContainerId}/can-advance`);
    if (!response?.ok) return;
    const data = await response.json();
    const nextBtn = document.getElementById('packingNextBtn');
    if (nextBtn) nextBtn.disabled = !data.can_advance;
}

function openPackingPhotoPicker() {
    const input = document.getElementById('packingPhotoInput');
    if (input) {
        input.value = '';
        input.click();
    }
}

const packingPhotoInput = document.getElementById('packingPhotoInput');
if (packingPhotoInput) {
    packingPhotoInput.addEventListener('change', async (event) => {
        const files = event.target.files || [];
        await uploadPackingPhotos(files);
    });
}

async function uploadPackingPhotos(files) {
    if (!currentPackingContainerId || !currentPackingStep || !files.length) return;
    const token = localStorage.getItem('access_token');
    if (!token) {
        APP.showError('Authentication token not found. Please log in again.');
        return;
    }

    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`/api/packing/photo-upload/${currentPackingContainerId}?step=${encodeURIComponent(currentPackingStep)}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to upload photo');
            return;
        }
    }

    await loadPackingProgress();
}

async function loadPackingPhotos() {
    if (!currentPackingContainerId || !currentPackingStep) return;

    const response = await APP.apiCall(`/packing/${currentPackingContainerId}/photos?step=${encodeURIComponent(currentPackingStep)}`);
    if (!response?.ok) return;
    const data = await response.json();
    renderPackingPhotoGallery(data.photos || []);
}

function renderPackingPhotoGallery(photos) {
    const grid = document.getElementById('packingPhotoGrid');
    const empty = document.getElementById('packingPhotoEmpty');
    const countEl = document.getElementById('packingPhotoCountText');
    if (!grid) return;

    if (countEl) {
        const countLabel = photos.length === 1 ? '1 photo' : `${photos.length} photos`;
        countEl.textContent = countLabel;
    }

    if (photos.length === 0) {
        grid.innerHTML = '';
        if (empty) {
            grid.appendChild(empty);
        }
        return;
    }

    grid.innerHTML = photos.map(photo => {
        const safeId = photo.id || '';
        const url = photo.url || '';
        return `
            <div style="position: relative; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; background: #f8f9ff;">
                <img src="${url}" alt="Packing photo" style="width: 100%; height: 120px; object-fit: cover; display: block;">
                <button type="button" onclick="deletePackingPhoto('${safeId}')" style="position: absolute; top: 6px; right: 6px; background: rgba(15, 29, 61, 0.85); color: white; border: none; border-radius: 999px; width: 26px; height: 26px; cursor: pointer;">×</button>
            </div>
        `;
    }).join('');
}

async function deletePackingPhoto(photoId) {
    if (!currentPackingContainerId || !photoId) return;
    if (!confirm('Remove this photo?')) return;

    const response = await APP.apiCall(`/packing/${currentPackingContainerId}/photos/${photoId}`, {
        method: 'DELETE'
    });

    if (!response?.ok) {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to remove photo');
        return;
    }

    await loadPackingProgress();
}

async function advancePackingStep() {
    if (!currentPackingContainerId) return;
    const response = await APP.apiCall(`/packing/advance-step/${currentPackingContainerId}`, { method: 'POST' });
    if (response?.ok) {
        await loadPackingProgress();
        return;
    }
    const error = await response.json();
    APP.showError(error.detail || 'Cannot advance step');
}

async function completePackingSeal() {
    if (!currentPackingContainerId) return;
    const sealNumber = document.getElementById('packingSealNumber')?.value.trim();
    if (!sealNumber) {
        APP.showError('Seal number is required');
        return;
    }

    const payload = {
        container_id: currentPackingContainerId,
        seal_number: sealNumber,
        gross_mass: document.getElementById('packingGrossMass')?.value.trim() || null,
        tare_weight: document.getElementById('packingTareWeight')?.value.trim() || null
    };

    const response = await APP.apiCall(`/packing/seal/${currentPackingContainerId}`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });

    if (response?.ok) {
        APP.showSuccess('✅ Packing complete. Container moved to review.');
        closePackingWorkflow();
        await loadContainers();
        return;
    }

    const error = await response.json();
    APP.showError(error.detail || 'Failed to complete packing');
}

async function pausePackingAndRelease() {
    if (!currentPackingContainerId) return;
    const confirmPause = confirm('Pause & Release container?\n\nYour progress will be saved and the container will be available for handover.');
    if (!confirmPause) return;

    try {
        const response = await APP.apiCall(`/packing/${currentPackingContainerId}/pause`, { method: 'POST' });
        if (response?.ok) {
            const result = await response.json();
            APP.showSuccess(result.message || 'Container paused and released for handover.');
            localStorage.removeItem('active_packing_container_id');
            closePackingWorkflow();
            await loadContainers();
            return;
        }
        const error = await response.json();
        APP.showError(error.detail || 'Failed to pause and release container');
    } catch (error) {
        console.error('Error pausing packing:', error);
        APP.showError('Error pausing container');
    }
}

// ============= PACKING COMPLETION HELPERS =============
async function completePackingAndReview(containerId) {
    try {
        const response = await APP.apiCall(`/containers/${containerId}/complete-packing`, { method: 'POST' });
        if (response?.ok) {
            APP.showSuccess('✅ Evidence verified. Container moved to Review.');
            loadContainers();
            return true;
        }
        const error = await response.json();
        APP.showError(error.detail || 'Failed to complete packing');
        return false;
    } catch (error) {
        console.error('Error completing packing:', error);
        APP.showError('Error completing packing');
        return false;
    }
}

// ============= NEW CONTAINER MODAL HELPERS =============
function openNewContainerModal() {
    const modal = document.getElementById('newContainerModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        
        // Load bookings for initial display
        loadBookingsForClient();
    }
}

function closeNewContainerModal() {
    const modal = document.getElementById('newContainerModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
    
    // Reset form
    document.getElementById('newContainerForm').reset();
}

// Handle client change - load vessel bookings and display client-specific refs section
async function onClientChange(event) {
    const client = event.target.value;
    const refSection = document.getElementById('packing-ref-section');
    const vesselSelect = document.getElementById('vesselBooking');
    
    // Clear previous content
    if (refSection) {
        refSection.innerHTML = '';
    }
    
    if (!client) {
        vesselSelect.innerHTML = '<option value="">Select client first</option>';
        vesselSelect.disabled = true;
        return;
    }
    
    // Load bookings for this client
    await loadBookingsForClient(client);
    vesselSelect.disabled = false;
    
    // Show client-specific reference fields
    if (client === 'HULAMIN') {
        refSection.innerHTML = `
            <div class="form-group" style="margin-top: 1rem;">
                <label style="color: #0f1d3d; font-weight: 600; display: flex; gap: 0.5rem; align-items: center;">
                    RE Numbers (Hulamin) <span style="color: #dc143c;">*</span>
                </label>
                <div style="display: flex; gap: 0.5rem; margin-bottom: 0.75rem;">
                    <input type="text" id="reNumberInput" placeholder="Add RE number (e.g., RE123)" maxlength="20" 
                           style="flex: 1; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px;">
                    <button type="button" onclick="addRENumber()" style="padding: 0.75rem 1.5rem; background: #0f1d3d; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">Add</button>
                </div>
                <div id="hulaminRefs" style="display: flex; flex-wrap: wrap; gap: 0.5rem;"></div>
                <small style="color: #888; display: block; margin-top: 0.5rem;">Add all RE numbers associated with this container</small>
            </div>
        `;
    } else if (client === 'PG_BISON') {
        refSection.innerHTML = `
            <div class="form-group" style="margin-top: 1rem;">
                <label style="color: #0f1d3d; font-weight: 600; display: flex; gap: 0.5rem; align-items: center;">
                    HEXP Number <span style="color: #dc143c;">*</span>
                </label>
                <input type="text" id="hexpNumber" placeholder="e.g., HEXP456789" maxlength="50"
                       style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px;">
                <small style="color: #888; display: block; margin-top: 0.5rem;">Enter the HEXP reference number</small>
            </div>
        `;
    }
}

// Add RE number for Hulamin
function addRENumber() {
    const input = document.getElementById('reNumberInput');
    const value = input.value.trim().toUpperCase();
    
    if (!value) {
        APP.showError('Please enter an RE number');
        return;
    }
    
    // Check if already added
    const existing = Array.from(document.querySelectorAll('#hulaminRefs .ref-tag'))
        .map(tag => tag.textContent.replace('×', '').trim());
    
    if (existing.includes(value)) {
        APP.showError('This RE number is already added');
        return;
    }

    const container = document.getElementById('hulaminRefs');
    const tag = document.createElement('div');
    tag.className = 'ref-tag';
    tag.style.cssText = `
        background: rgba(220, 20, 60, 0.2);
        border: 1px solid #dc143c;
        border-radius: 20px;
        padding: 0.5rem 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.9rem;
        color: #dc143c;
        font-weight: 600;
    `;
    tag.innerHTML = `
        <span>${value}</span>
        <button type="button" onclick="this.parentElement.remove()" style="background: none; border: none; color: #dc143c; cursor: pointer; font-size: 1.2rem;">×</button>
    `;
    container.appendChild(tag);
    input.value = '';
    input.focus();
}

// Load bookings for selected client
async function loadBookingsForClient(client = null) {
    try {
        const selectedClient = client || document.getElementById('client').value;
        if (!selectedClient) {
            document.getElementById('vesselBooking').innerHTML = '<option value="">Select client first</option>';
            return;
        }

        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/bookings?client=${selectedClient}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const bookings = await response.json();
            const select = document.getElementById('vesselBooking');
            select.innerHTML = '<option value="">Select vessel booking</option>' +
                bookings.map(b => `<option value="${b.id}">${b.booking_reference} - ${b.vessel_name}</option>`).join('');
            
            // Update booking count display if exists
            const countElement = document.getElementById('bookingAvailableCount');
            if (countElement) {
                countElement.textContent = bookings.length;
            }
        } else {
            APP.showError('Failed to load bookings');
        }
    } catch (error) {
        console.error('Error loading bookings:', error);
        APP.showError('Error loading bookings');
    }
}

// Handle vessel booking selection
function onVesselBookingChange(event) {
    // Could add additional logic here if needed
    console.log('Vessel booking selected:', event.target.value);
}

async function updateContainer(containerId, formData) {
    try {
        const response = await APP.apiCall(`/containers/${containerId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (response?.ok) {
            const result = await response.json();
            APP.showSuccess('Container updated successfully');
            loadContainers();
            return result;
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to update container');
            return null;
        }
    } catch (error) {
        console.error('Error updating container:', error);
        APP.showError('Error updating container');
        return null;
    }
}

async function deleteContainer(containerId) {
    if (!confirm('Are you sure you want to delete this container?')) return;

    try {
        const response = await APP.apiCall(`/containers/${containerId}`, { method: 'DELETE' });

        if (response?.ok) {
            APP.showSuccess('Container deleted successfully');
            loadContainers();
        } else {
            APP.showError('Failed to delete container');
        }
    } catch (error) {
        console.error('Error deleting container:', error);
        APP.showError('Error deleting container');
    }
}

// ============= FORM HANDLING =============
function handleContainerFormSubmit(e) {
    e.preventDefault();
    
    const containerId = document.getElementById('containerID').value;
    const formData = {
        container_no: document.getElementById('containerNo').value,
        type: document.getElementById('containerType').value,
        client: document.getElementById('clientName').value,
        status: document.getElementById('containerStatus').value,
        notes: document.getElementById('notes').value
    };

    if (containerId) {
        updateContainer(containerId, formData);
    } else {
        registerContainer(formData);
    }

    closeModal('containerModal');
}

// ============= NEW CONTAINER REGISTRATION (Export Packing) =============
async function submitNewContainer(event) {
    event.preventDefault();

    const containerNum = document.getElementById('containerNumber').value.trim().toUpperCase();
    const client = document.getElementById('client').value;
    const vesselBookingId = document.getElementById('vesselBooking').value;
    const additionalNotes = document.getElementById('additionalNotes').value.trim();

    // Validate container number format
    if (!containerNum || containerNum.length !== 11) {
        APP.showError('Container number must be exactly 11 characters (4 letters + 7 digits)');
        return;
    }
    const containerRegex = /^[A-Z]{4}[0-9]{7}$/;
    if (!containerRegex.test(containerNum)) {
        APP.showError('Invalid format. Expected: 4 uppercase letters + 7 digits (e.g., MSMU4557285)');
        return;
    }

    if (!client) {
        APP.showError('Please select a client');
        return;
    }

    if (!vesselBookingId) {
        APP.showError('Please select a vessel booking');
        return;
    }

    // Build client_reference based on client type
    let clientRef = null;
    if (client === 'HULAMIN') {
        const hulaminjRefs = Array.from(document.querySelectorAll('#hulaminRefs .ref-tag'))
            .map(tag => tag.textContent.replace('×', '').trim());
        if (hulaminjRefs.length === 0) {
            APP.showError('Please add at least one RE number for Hulamin');
            return;
        }
        clientRef = { re_numbers: hulaminjRefs };
    } else if (client === 'PG_BISON') {
        const hexpNum = document.getElementById('hexpNumber') ? document.getElementById('hexpNumber').value.trim() : '';
        if (!hexpNum) {
            APP.showError('Please enter HEXP number for PG Bison');
            return;
        }
        clientRef = { hexp_number: hexpNum };
    }

    // Get container type from form; default to 40FT
    const containerTypeSelect = document.getElementById('containerType');
    let containerType = containerTypeSelect ? containerTypeSelect.value : '40FT';
    
    // Map form values to schema enum values
    const typeMap = {
        '': '40FT',
        '20ft': '20FT',
        '40ft': '40FT',
        '40ft_HC': 'HC'
    };
    containerType = typeMap[containerType] || '40FT';

    // Construct payload matching ContainerCreate schema
    const payload = {
        container_no: containerNum,
        booking_id: vesselBookingId,
        type: containerType,
        client: client,
        client_reference: clientRef,
        notes: additionalNotes || null
    };

    try {
        const token = localStorage.getItem('access_token');
        if (!token) {
            APP.showError('Authentication token not found. Please log in again.');
            return;
        }

        const response = await fetch('/api/containers/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const result = await response.json();
            APP.showSuccess(`✅ Container ${containerNum} registered successfully!`);
            
            // Close modal and refresh the containers list
            closeNewContainerModal();
            
            // Reload containers to show in appropriate lists
            if (window.Containers && window.Containers.loadContainers) {
                const containers = await window.Containers.loadContainers();
                // If we're currently on export_packing tab, display them
                if (TabLoader.activeTab === 'export_packing') {
                    if (typeof window.displayExportContainers === 'function') {
                        window.displayExportContainers(containers);
                    } else if (typeof window.loadExportPackingData === 'function') {
                        window.loadExportPackingData();
                    }
                }
            }
            
            // Reset form
            document.getElementById('newContainerForm').reset();
        } else {
            const error = await response.json();
            APP.showError(`❌ ${error.detail || 'Failed to register container'}`);
        }
    } catch (error) {
        console.error('Error registering container:', error);
        APP.showError(`❌ Error: ${error.message}`);
    }
}

// ============= FCL REGISTRATION =============
async function submitFCLRegistration(e) {
    e.preventDefault();
    try {
        const form = document.getElementById('fclRegistrationForm');
        const formData = new FormData(form);

        const typeMap = {
            '20ft': '20FT',
            '40ft': '40FT',
            '40ft_HC': 'HC'
        };

        const payload = {
            container_no: (formData.get('container_no') || '').toString().trim().toUpperCase(),
            type: typeMap[(formData.get('type') || '').toString()] || '40FT',
            booking_id: (formData.get('booking_id') || '').toString(),
            arrival_date: formData.get('arrival_date') ? new Date(formData.get('arrival_date')).toISOString() : null,
            client: (formData.get('client') || '').toString(),
            cargo_type: (formData.get('cargo_type') || '').toString() || null,
            seal_no: (formData.get('seal_no') || '').toString() || null,
            unpacking_location: (formData.get('unpacking_location') || '').toString() || null,
            notes: (formData.get('notes') || '').toString() || null
        };

        if (!payload.container_no || !payload.booking_id || !payload.arrival_date) {
            APP.showError('Please fill in all required fields (marked with *)');
            return;
        }

        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/containers/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const container = await response.json();
            APP.showSuccess(`✅ Container ${container.container_no} registered successfully!`);
            closeFCLModal();
            loadAvailableFCLContainers();
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to register container');
        }
    } catch (error) {
        console.error('Error registering FCL container:', error);
        APP.showError('Error registering FCL container');
    }
}

// Expose handlers for inline onclick bindings
window.openNewContainerModal = openNewContainerModal;
window.closeNewContainerModal = closeNewContainerModal;
window.submitNewContainer = submitNewContainer;
window.onClientChange = onClientChange;
window.onVesselBookingChange = onVesselBookingChange;
window.addRENumber = addRENumber;
window.showRegisterFCLForm = showRegisterFCLForm;
window.closeFCLModal = closeFCLModal;
window.submitFCLRegistration = submitFCLRegistration;
window.updateFCLBookingDetails = updateFCLBookingDetails;
window.loadFCLBookings = loadFCLBookings;
window.loadBookingsForClient = loadBookingsForClient;
window.displayExportContainers = displayExportContainers;
window.updateExportPackingStats = updateExportPackingStats;

// Export for use in other modules
window.Containers = {
    loadContainers,
    loadActiveContainers,
    loadNewContainers,
    loadReadyContainers,
    loadCompletedContainers,
    openContainer,
    viewContainerDetails,
    registerContainer,
    updateContainer,
    deleteContainer,
    loadAvailableFCLContainers,
    startUnpackingForContainer,
    completePackingAndReview,
    loadBackloadTrucks,
    loadTruckOffloading
};

// ============= UNPACKING WORKFLOW SUPPORT =============
async function startUnpackingForContainer(containerId) {
    console.log(`Starting unpacking for container: ${containerId}`);
    
    // Get container details first
    try {
        const response = await APP.apiCall(`/containers/${containerId}`);
        if (response?.ok) {
            const container = await response.json();
            console.log('Container loaded:', container);
            
            // Pass to UI module to start workflow
            if (window.UI && window.UI.startUnpackingWorkflow) {
                window.UI.startUnpackingWorkflow(containerId);
            }
        }
    } catch (error) {
        console.error('Error loading container for unpacking:', error);
        APP.showError('Failed to load container');
    }
}

function continueUnpacking(containerId) {
    if (window.UI && window.UI.startUnpackingWorkflow) {
        window.UI.startUnpackingWorkflow(containerId);
    }
}

function viewUnpackingDetails(containerId) {
    viewContainerDetails(containerId);
}
