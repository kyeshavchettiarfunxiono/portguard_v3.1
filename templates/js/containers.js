/**
 * PortGuard CCMS - Operator Dashboard - Containers Module
 * Handles container loading, filtering, and display
 */

// ============= MAIN CONTAINER LOADING =============
async function loadContainers() {
    try {
        const response = await APP.apiCall('/containers');
        if (response?.ok) {
            const containers = await response.json();
            displayReadyForWorkContainers(containers);
            displayCompletedContainers(containers);
            loadActiveContainersForTab(containers);
        }
    } catch (error) {
        console.error('Error loading containers:', error);
    }
}

// ============= CONTAINER FILTERING & DISPLAY =============
function loadActiveContainers() {
    APP.apiCall('/containers').then(async (response) => {
        if (response?.ok) {
            const containers = await response.json();
            loadActiveContainersForTab(containers);
        }
    });
}

function loadActiveContainersForTab(containers) {
    const activeContainers = containers.filter(c => 
        ['PACKING', 'UNPACKING'].includes(c.status)
    );

    const list = document.getElementById('activeJobsList');
    if (!list) return;

    if (activeContainers.length === 0) {
        list.innerHTML = '<p style="color: #888; grid-column: 1/-1;">No active containers</p>';
    } else {
        list.innerHTML = activeContainers.map(c => createJobCardHTML(c)).join('');
    }
}

function loadNewContainers() {
    APP.apiCall('/containers').then(async (response) => {
        if (response?.ok) {
            const containers = await response.json();
            const newContainers = containers.filter(c => 
                c.status === 'PENDING_REVIEW'
            );

            const list = document.getElementById('newJobsList');
            if (list) {
                if (newContainers.length === 0) {
                    list.innerHTML = '<p style="color: #888; grid-column: 1/-1;">No new containers</p>';
                } else {
                    list.innerHTML = newContainers.map(c => createJobCardHTML(c)).join('');
                }
            }
        }
    });
}

function loadReadyContainers() {
    APP.apiCall('/containers').then(async (response) => {
        if (response?.ok) {
            const containers = await response.json();
            const readyContainers = containers.filter(c => 
                ['REGISTERED', 'PACKING', 'UNPACKING'].includes(c.status)
            );

            const list = document.getElementById('readyJobsList');
            if (list) {
                if (readyContainers.length === 0) {
                    list.innerHTML = '<p style="color: #888; grid-column: 1/-1;">No containers ready for work</p>';
                } else {
                    list.innerHTML = readyContainers.map(c => createJobCardHTML(c)).join('');
                }
            }
        }
    });
}

function loadCompletedContainers() {
    APP.apiCall('/containers').then(async (response) => {
        if (response?.ok) {
            const containers = await response.json();
            const completedContainers = containers.filter(c => 
                c.status === 'COMPLETED'
            );

            const list = document.getElementById('completedJobsList');
            if (list) {
                if (completedContainers.length === 0) {
                    list.innerHTML = '<p style="color: #888; grid-column: 1/-1;">No completed containers</p>';
                } else {
                    list.innerHTML = completedContainers.map(c => createJobCardHTML(c)).join('');
                }
            }
        }
    });
}

function displayReadyForWorkContainers(containers) {
    const readyContainers = containers.filter(c => 
        ['REGISTERED', 'PACKING', 'UNPACKING'].includes(c.status)
    );

    const list = document.getElementById('readyForWorkList');
    if (!list) return;

    if (readyContainers.length === 0) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: #888;"><p>No containers ready for work</p></div>';
    } else {
        list.innerHTML = readyContainers.map(c => `
            <div class="container-card" onclick="openContainer('${c.id}')">
                <div class="container-card-header">
                    <span class="container-number">${c.container_no}</span>
                    <span class="container-client">${c.client || 'N/A'}</span>
                </div>
                <div class="container-card-details">
                    <div>
                        <span>Status:</span>
                        <span>${c.status.replace('_', ' ')}</span>
                    </div>
                    <div>
                        <span>Type:</span>
                        <span>${c.type || 'Standard'}</span>
                    </div>
                </div>
                <div class="container-card-footer">
                    <span class="progress-bar">${APP.getProgressForStatus(c.status)}</span>
                    <span>→</span>
                </div>
            </div>
        `).join('');
    }
}

function displayCompletedContainers(containers) {
    const completedContainers = containers.filter(c => 
        c.status === 'COMPLETED'
    );

    const list = document.getElementById('completedJobsList');
    if (!list) return;

    if (completedContainers.length === 0) {
        list.innerHTML = '<p style="color: #888; grid-column: 1/-1;">No completed containers</p>';
    } else {
        list.innerHTML = completedContainers.map(c => createJobCardHTML(c)).join('');
    }
}

// ============= CONTAINER CARD HTML GENERATION =============
function createJobCardHTML(container) {
    const statusClass = APP.getStatusClass(container.status);
    const progress = APP.getProgressForStatus(container.status);

    return `
        <div class="job-card">
            <div class="job-header">
                <div class="job-id">${container.container_no}</div>
                <span class="job-status ${statusClass}">${container.status.replace('_', ' ')}</span>
            </div>
            <div class="job-details">
                <div class="job-detail">
                    <span class="job-label">Client:</span>
                    <span class="job-value">${container.client || 'N/A'}</span>
                </div>
                <div class="job-detail">
                    <span class="job-label">Type:</span>
                    <span class="job-value">${container.type || 'Standard'}</span>
                </div>
                <div class="job-detail">
                    <span class="job-label">Progress:</span>
                    <span class="job-value">${progress}</span>
                </div>
                ${container.started_at ? `
                <div class="job-detail">
                    <span class="job-label">Started:</span>
                    <span class="job-value">${APP.formatTime(container.started_at)}</span>
                </div>
                ` : ''}
            </div>
            <div class="job-actions">
                <button onclick="viewContainerDetails('${container.id}')">View Details</button>
                ${['PACKING', 'UNPACKING'].includes(container.status) ? `
                <button onclick="openContainer('${container.id}')">Continue</button>
                ` : ''}
            </div>
        </div>
    `;
}

// ============= CONTAINER ACTIONS =============
function openContainer(containerId, workType = 'packing') {
    console.log(`📦 Opening container ${containerId} for ${workType}`);
    // This will be called from the main HTML with actual workflow
    APP.showAlert(`Opening container ${containerId} for ${workType} workflow`);
    // In actual implementation, this would load the workflow modal
}

function viewContainerDetails(containerId) {
    console.log(`👁️ Viewing details for container ${containerId}`);
    APP.apiCall(`/containers/${containerId}`).then(async (response) => {
        if (response?.ok) {
            const container = await response.json();
            displayContainerDetailsModal(container);
        }
    });
}

function displayContainerDetailsModal(container) {
    const details = `
Container: ${container.container_no}
Status: ${container.status}
Client: ${container.client || 'N/A'}
Type: ${container.type || 'Standard'}
Created: ${APP.formatDate(container.created_at)}
${container.started_at ? `Started: ${APP.formatDate(container.started_at)}` : ''}
${container.completed_at ? `Completed: ${APP.formatDate(container.completed_at)}` : ''}
    `;
    APP.showAlert(details, 'info');
}

// ============= FCL CONTAINERS =============
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

            const list = document.getElementById('availableFCLList');
            if (list) {
                if (fclContainers.length === 0) {
                    list.innerHTML = '<p style="color: #888; grid-column: 1/-1;">No available FCL containers. Register a new one to get started.</p>';
                } else {
                    list.innerHTML = fclContainers.map(c => `
                        <div class="job-card">
                            <div class="job-header">
                                <div class="job-id">${c.container_no}</div>
                                <span class="job-status status-ready">Ready</span>
                            </div>
                            <div class="job-details">
                                <div class="job-detail">
                                    <span class="job-label">Vessel:</span>
                                    <span class="job-value">${c.vessel_name || 'N/A'}</span>
                                </div>
                                <div class="job-detail">
                                    <span class="job-label">Arrival:</span>
                                    <span class="job-value">${APP.formatDate(c.arrival_date)}</span>
                                </div>
                            </div>
                            <div class="job-actions">
                                <button onclick="startUnpacking('${c.id}')">Start Unpacking</button>
                                <button onclick="viewContainerDetails('${c.id}')">Details</button>
                            </div>
                        </div>
                    `).join('');
                }
            }
        }
    } catch (error) {
        console.error('Error loading FCL containers:', error);
    }
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

function startUnpacking(containerId) {
    console.log(`🔓 Starting unpacking for container ${containerId}`);
    APP.showAlert(`Starting unpacking workflow for ${containerId}`);
}

// Export for use in other modules
window.Containers = {
    loadContainers,
    loadActiveContainers,
    loadNewContainers,
    loadReadyContainers,
    loadCompletedContainers,
    openContainer,
    viewContainerDetails,
    loadAvailableFCLContainers,
    startUnpacking
};

window.showRegisterFCLForm = showRegisterFCLForm;
window.closeFCLModal = closeFCLModal;
window.submitFCLRegistration = submitFCLRegistration;
window.updateFCLBookingDetails = updateFCLBookingDetails;
