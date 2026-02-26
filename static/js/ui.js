/**
 * PortGuard CCMS - Operator Dashboard - UI Module
 * Handles tab switching, page navigation, and UI state management
 */

// ============= TAB MANAGEMENT =============
function switchTab(tabName) {
    console.log(`📑 Switching to tab: ${tabName}`);

    // Hide all tab content
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
        tab.style.display = 'none';
    });

    // Show selected tab
    const selectedTab = document.getElementById(tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
        selectedTab.style.display = 'block';
        window.scrollTo(0, 0);

        // Refresh data if needed
        if (tabName === 'active-jobs') {
            loadActiveContainers();
        } else if (tabName === 'new-jobs') {
            loadNewContainers();
        } else if (tabName === 'ready') {
            loadReadyContainers();
        } else if (tabName === 'completed') {
            loadCompletedContainers();
        }
    }

    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.toLowerCase().includes(tabName.split('-')[0])) {
            btn.classList.add('active');
        }
    });
}

// ============= PAGE SWITCHING =============
function switchSidebar(page) {
    console.log(`🔀 Switching page: ${page}`);

    // Hide all main pages
    document.querySelectorAll('[id$="Page"]').forEach(page => {
        page.style.display = 'none';
    });

    // Update sidebar active state
    document.querySelectorAll('.sidebar-link').forEach(link => {
        link.classList.remove('active');
    });

    // Show selected page and mark sidebar item
    switch (page) {
        case 'export-packing':
            toggleExportPackingPage(true);
            document.querySelectorAll('.sidebar-link')[0].classList.add('active');
            break;
        case 'export-truck':
            if (window.TabLoader && typeof TabLoader.switchTab === 'function') {
                TabLoader.switchTab('export_truck');
            } else {
                switchTab('export_truck');
            }
            document.querySelectorAll('.sidebar-link')[1].classList.add('active');
            break;
        case 'import-unpacking':
            toggleImportUnpackingPage(true);
            document.querySelectorAll('.sidebar-link')[2].classList.add('active');
            break;
        case 'truck-unpacking':
            if (window.TabLoader && typeof TabLoader.switchTab === 'function') {
                TabLoader.switchTab('truck_unpacking');
            } else {
                switchTab('truck_unpacking');
            }
            document.querySelectorAll('.sidebar-link')[3].classList.add('active');
            break;
        case 'damage-reports':
            switchTab('damage');
            document.querySelectorAll('.sidebar-link')[4].classList.add('active');
            break;
        default:
            // Return to overview
            switchTab('overview');
            document.querySelectorAll('.sidebar-link')[0].classList.add('active');
    }
}

// ============= EXPORT PACKING PAGE =============
function toggleExportPackingPage(show) {
    console.log(`📦 ${show ? 'Opening' : 'Closing'} Export Packing page`);
    
    const page = document.getElementById('exportPackingPage');
    const header = document.querySelector('header');
    const tabs = document.getElementById('overview')?.parentElement || null;

    if (show) {
        if (page) page.style.display = 'block';
        if (header) header.style.display = 'block';
        window.scrollTo(0, 0);
        loadExportPackingData();
    } else {
        if (page) page.style.display = 'none';
        if (header) header.style.display = 'block';
        switchTab('overview');
    }
}

async function loadExportPackingData() {
    try {
        const response = await APP.apiCall('/containers');
        if (response?.ok) {
            const containers = await response.json();
            displayExportPackingContainers(containers);
            updateExportPackingStats(containers);
        }
    } catch (error) {
        console.error('Error loading export packing data:', error);
        APP.showError('Failed to load export containers');
    }
}

function displayExportPackingContainers(containers) {
    // Filter export containers
    const exportContainers = containers.filter(c => 
        normalizeType(c.type) && !normalizeType(c.type).includes('FCL')
    );

    // Display ready for work
    const readyList = document.getElementById('exportReadyForWorkList');
    if (readyList) {
        const readyContainers = exportContainers.filter(c => 
            ['REGISTERED', 'PACKING'].includes(normalizeStatus(c.status))
        );

        if (readyContainers.length === 0) {
            readyList.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: #888;"><p>No containers ready for work</p></div>';
        } else {
            readyList.innerHTML = readyContainers.map(c => `
                <div class="container-card" onclick="openContainer('${c.id}', 'packing')">
                    <div class="container-card-header">
                        <span class="container-number">${c.container_no}</span>
                        <span class="container-client">${c.client || 'N/A'}</span>
                    </div>
                    <div class="container-card-details">
                        <div>
                            <span>Status:</span>
                            <span>${normalizeStatus(c.status).replace('_', ' ')}</span>
                        </div>
                        <div>
                            <span>Type:</span>
                            <span>${normalizeType(c.type) || 'Standard'}</span>
                        </div>
                    </div>
                    <div class="container-card-footer">
                        <span class="progress-bar">${APP.getProgressForStatus(normalizeStatus(c.status))}</span>
                        <span>→</span>
                    </div>
                </div>
            `).join('');
        }
    }
}

function updateExportPackingStats(containers) {
    const stats = {
        new: containers.filter(c => normalizeStatus(c.status) === 'PENDING_REVIEW').length,
        ready: containers.filter(c => ['REGISTERED', 'PACKING'].includes(normalizeStatus(c.status))).length,
        inUse: containers.filter(c => c.assigned_to && c.assigned_to !== 'current_user').length,
        needsRepair: containers.filter(c => c.needs_repair).length
    };

    document.getElementById('exportNewCount').textContent = stats.new;
    document.getElementById('exportReadyCount').textContent = stats.ready;
    document.getElementById('exportInUseCount').textContent = stats.inUse;
    document.getElementById('exportNeedsRepairCount').textContent = stats.needsRepair;
    document.getElementById('exportReadyWorkCount').textContent = stats.ready;
}

// ============= IMPORT UNPACKING PAGE =============
function toggleImportUnpackingPage(show) {
    console.log(`📥 ${show ? 'Opening' : 'Closing'} Import Unpacking page`);
    
    const header = document.querySelector('header');
    const tab = document.getElementById('import-unpacking-tab');

    if (show) {
        // Hide all main content
        document.querySelectorAll('.tab-content').forEach(t => {
            t.style.display = 'none';
            t.classList.remove('active');
        });
        
        if (header) header.style.display = 'block';
        if (tab) {
            tab.style.display = 'block';
            tab.classList.add('active');
        }
        window.scrollTo(0, 0);
        // Load FCL containers for unpacking
        if (window.Containers && window.Containers.loadAvailableFCLContainers) {
            window.Containers.loadAvailableFCLContainers();
        }
    } else {
        if (header) header.style.display = 'block';
        if (tab) {
            tab.style.display = 'none';
            tab.classList.remove('active');
        }
        document.getElementById('overview').style.display = 'block';
        document.getElementById('overview').classList.add('active');
    }
}

// ============= MODAL MANAGEMENT =============
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        console.log(`📋 Opened modal: ${modalId}`);
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        const form = modal.querySelector('form');
        if (form) form.reset();
        console.log(`📋 Closed modal: ${modalId}`);
    }
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    if (e.target.id && e.target.style.position === 'fixed' && e.target.style.display === 'flex') {
        const form = e.target.querySelector('form');
        if (form && confirm('Close this dialog without saving?')) {
            closeModal(e.target.id);
        }
    }
});

// ============= DASHBOARD DATA LOADING =============
async function loadDashboardData() {
    try {
        const response = await APP.apiCall('/containers');
        if (response?.ok) {
            const containers = await response.json();
            updateDashboardStats(containers);
            displayActiveJob(containers);
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

function updateDashboardStats(containers) {
    const stats = {
        total: containers.length,
        pending: containers.filter(c => c.status === 'PENDING_REVIEW').length,
        repairs: containers.filter(c => c.needs_repair).length,
        active: containers.filter(c => c.status === 'PACKING' || c.status === 'UNPACKING').length,
        new: containers.filter(c => c.status === 'PENDING_REVIEW').length,
        ready: containers.filter(c => ['REGISTERED', 'PACKING'].includes(c.status)).length,
        completed: containers.filter(c => c.status === 'COMPLETED').length
    };

    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = String(value);
    };

    setText('statTotal', stats.total);
    setText('statPending', stats.pending);
    setText('statRepairs', stats.repairs);
    setText('statActive', stats.active || '-');
    setText('countNew', stats.new);
    setText('countReady', stats.ready);
    setText('countCompleted', stats.completed);
}

function displayActiveJob(containers) {
    const activeContainer = containers.find(c => 
        c.status === 'PACKING' || c.status === 'UNPACKING'
    );

    const card = document.getElementById('activeJobCard');
    if (!card) return;

    if (activeContainer) {
        const activeJobId = document.getElementById('activeJobId');
        const activeJobType = document.getElementById('activeJobType');
        const activeJobStatus = document.getElementById('activeJobStatus');
        const activeJobStarted = document.getElementById('activeJobStarted');

        if (activeJobId) activeJobId.textContent = activeContainer.container_no;
        if (activeJobType) activeJobType.textContent = activeContainer.type || 'Unknown';
        if (activeJobStatus) activeJobStatus.textContent = activeContainer.status.replace('_', ' ');
        if (activeJobStarted) activeJobStarted.textContent = APP.formatDate(activeContainer.created_at);
    }
}

// ============= UNPACKING WORKFLOW MANAGEMENT =============
let currentUnpackingSession = { containerId: null, progress: null };
let currentUnpackingStep = 'EXTERIOR_INSPECTION';
let currentPhotoStep = null;
let damageContainerMode = 'existing';
let editingDamageReportId = null;
let cachedDamageReports = [];

async function startUnpackingWorkflow(containerId) {
    console.log(`📥 Starting unpacking workflow for: ${containerId}`);
    try {
        const containerResponse = await APP.apiCall(`/containers/${containerId}`);
        if (containerResponse?.ok) {
            const container = await containerResponse.json();
            if (container.needs_repair) {
                APP.showError('Container is blocked by damage and needs repair before unpacking.');
                return;
            }
        }

        const response = await APP.apiCall(`/unpacking/${containerId}/start`, { method: 'POST' });
        if (response?.ok) {
            await loadUnpackingProgress(containerId);
            openModal('unpackingWorkflowModal');
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to start unpacking workflow');
        }
    } catch (error) {
        console.error('Error starting unpacking workflow:', error);
        APP.showError('Error starting unpacking workflow');
    }
}

async function loadUnpackingProgress(containerId) {
    try {
        const response = await APP.apiCall(`/unpacking/${containerId}/progress`);
        if (response?.ok) {
            const progress = await response.json();
            currentUnpackingSession = { containerId, progress };
            currentUnpackingStep = progress.current_step || 'EXTERIOR_INSPECTION';
            const display = document.getElementById('unpackingContainerDisplay');
            if (display) {
                display.textContent = `Container: ${progress.container_no}`;
            }
            renderUnpackingSteps(progress);
            switchUnpackingStep(currentUnpackingStep);
            updateActiveUnpackingCard(progress);
        } else {
            APP.showError('Failed to load unpacking progress');
        }
    } catch (error) {
        console.error('Error loading unpacking progress:', error);
        APP.showError('Error loading unpacking progress');
    }
}

function switchUnpackingStep(step) {
    currentUnpackingStep = step;
    console.log(`📋 Switching to unpacking step: ${step}`);
    
    // Update active step styling
    document.querySelectorAll('.workflow-step').forEach(el => {
        el.classList.remove('is-active');
    });
    
    const activeStep = document.querySelector(`[data-step="${step}"]`);
    if (activeStep) {
        activeStep.classList.add('is-active');
    }
    
    // Load step content
    loadUnpackingStepForm(step);
    if (currentUnpackingSession.progress) {
        updateUnpackingPhotoCounts(currentUnpackingSession.progress);
        updateUnloadingDurationDisplay(currentUnpackingSession.progress);
    }
}

function updateUnloadingDurationDisplay(progress) {
    const durationField = document.getElementById('unloadingDurationMinutes');
    const badge = document.getElementById('unloadingTimerBadge');

    if (!durationField) return;

    const minutes = progress?.cargo_unloading_duration_minutes;
    if (minutes === null || minutes === undefined) {
        durationField.value = 'In progress / not completed yet';
        if (badge) {
            const startedAt = progress?.cargo_unloading_started_at;
            badge.textContent = startedAt
                ? `Unloading started: ${new Date(startedAt).toLocaleString()}`
                : 'Unloading timer starts automatically when you enter this step';
        }
        return;
    }

    durationField.value = String(minutes);
    if (badge) {
        const completedAt = progress?.cargo_unloading_completed_at;
        badge.textContent = completedAt
            ? `Unloading completed: ${new Date(completedAt).toLocaleString()} (${minutes} min)`
            : `Unloading completed (${minutes} min)`;
    }
}

function loadUnpackingStepForm(step) {
    const contentArea = document.getElementById('unpackingStepContent');
    
    const stepForms = {
        'EXTERIOR_INSPECTION': `
    <div class="unpacking-form">
        <h3 class="unpacking-header">📷 Exterior Inspection Photos</h3>
        <div class="form-group">
            <label style="color: #666; margin-bottom: 0.5rem; display: block;">
                Document the exterior condition of the container
            </label>
            <div class="unpacking-card">
                <input type="checkbox" id="exteriorLock" checked> <label for="exteriorLock">Lock/Seal intact</label><br>
                <input type="checkbox" id="exteriorDamage"> <label for="exteriorDamage">Visible damage</label><br>
                <input type="checkbox" id="exteriorStains"> <label for="exteriorStains">Stains/leakage marks</label><br>
                <input type="checkbox" id="exteriorOther"> <label for="exteriorOther">Other observations</label>
            </div>
            <button class="btn btn-secondary" onclick="openPhotoModalForStep('EXTERIOR_INSPECTION')" style="width: 100%;">
                📸 Upload Exterior Photos
            </button>
        </div>
        <div id="exteriorPhotoCount" style="color: #666;">Photos: 0</div>
    </div>
        `,
        'DOOR_OPENING': `
    <div class="unpacking-form">
        <h3 class="unpacking-header">🚪 Door Opening & Seal Documentation</h3>
        <div class="unpacking-note">
            <strong>Safety Check:</strong> Ensure proper safety measures before opening container doors.
        </div>
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Seal Number</label>
            <input type="text" id="sealNumber" placeholder="Seal #..." style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; margin-bottom: 1rem;">
        </div>
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Door Condition</label>
            <select id="doorCondition" style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; margin-bottom: 1rem;">
                <option value="">Select...</option>
                <option value="GOOD">Good - Operates smoothly</option>
                <option value="STIFF">Stiff - Needs lubrication</option>
                <option value="DAMAGED">Damaged - Unable to open</option>
                <option value="OTHER">Other</option>
            </select>
        </div>
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Observations</label>
            <textarea id="doorObservations" placeholder="Any observations during door opening..." style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; min-height: 100px; margin-bottom: 1rem;"></textarea>
        </div>
        <button class="btn btn-secondary" onclick="openPhotoModalForStep('DOOR_OPENING')" style="width: 100%;">
            📸 Upload Seal + Door Photos
        </button>
        <div id="doorPhotoCount" style="color: #666;">Photos: 0</div>
        <small style="color: #666; display: block; margin-top: 0.45rem;">At least one clear seal photo is required before continuing.</small>
    </div>
        `,
        'INTERIOR_INSPECTION': `
    <div class="unpacking-form">
        <h3 class="unpacking-header">🔍 Interior Inspection</h3>
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Interior Condition</label>
            <select id="interiorCondition" style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; margin-bottom: 1rem;">
                <option value="">Select...</option>
                <option value="CLEAN">Clean</option>
                <option value="DUSTY">Dusty/Soiled</option>
                <option value="WET">Wet/Damp</option>
                <option value="DAMAGED">Damaged interior</option>
                <option value="CONTAMINATED">Contaminated</option>
            </select>
        </div>
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Cargo Condition Overview</label>
            <textarea id="cargoCondition" placeholder="Overall visual assessment of cargo..." style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; min-height: 100px; margin-bottom: 1rem;"></textarea>
        </div>
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">
                <input type="checkbox" id="reportDamage"> Report Damage/Issues
            </label>
        </div>
        <button class="btn btn-secondary" onclick="openPhotoModalForStep('INTERIOR_INSPECTION')" style="width: 100%;">
            📸 Upload Interior Photos
        </button>
        <button class="btn btn-secondary" onclick="openDamageModal()" style="width: 100%;">
            🔴 Report Damage
        </button>
        <div id="interiorPhotoCount" style="color: #666;">Photos: 0</div>
    </div>
        `,
        'CARGO_UNLOADING': `
    <div class="unpacking-form">
        <h3 class="unpacking-header">📦 Cargo Unloading Progress</h3>
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Unloading Status *</label>
            <select id="unloadingStatus" required style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; margin-bottom: 1rem;">
                <option value="">Select...</option>
                <option value="NOT_STARTED">Not Started</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="COMPLETED">Completed</option>
            </select>
        </div>
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Pallets/Units Unloaded</label>
            <input type="number" id="unitsUnloaded" min="0" placeholder="Number of units..." style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; margin-bottom: 1rem;">
        </div>
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Auto Calculated Unloading Duration (minutes)</label>
            <input type="text" id="unloadingDurationMinutes" readonly placeholder="Calculated automatically from start to completion" style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; margin-bottom: 1rem; background: #f7f7f7;">
            <div id="unloadingTimerBadge" class="blocked-badge" style="display: inline-flex; margin-bottom: 0.8rem;">Unloading timer starts automatically when you enter this step</div>
        </div>
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Unloading Notes</label>
            <textarea id="unloadingNotes" placeholder="Any issues or observations during unloading..." style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; min-height: 100px; margin-bottom: 1rem;"></textarea>
        </div>
        <button class="btn btn-secondary" onclick="openPhotoModalForStep('CARGO_UNLOADING')" style="width: 100%;">
            📸 Upload Unloading Photos
        </button>
        <div id="unloadingPhotoCount" style="color: #666;">Photos: 0</div>
        <small style="color: #666; display: block; margin-top: 0.45rem;">Minimum 2 photos required (you can upload more) to capture cargo during unpacking.</small>
    </div>
        `,
        'CARGO_MANIFEST': `
    <div class="unpacking-form">
        <h3 class="unpacking-header">📋 Cargo Manifest & Inventory</h3>
        <div class="unpacking-card" style="background: #e7f3ff; border-color: #cfe3ff;">
            <strong>Add cargo items below as they are verified during unloading</strong>
        </div>

        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Manifest / Depot List Reference</label>
            <input type="text" id="manifestDocumentReference" placeholder="e.g., MB-2025-001" style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; margin-bottom: 1rem;">
        </div>

        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Manifest Notes</label>
            <textarea id="manifestDocumentNotes" placeholder="Summary of import manifest/depot list notes..." style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; min-height: 80px; margin-bottom: 1rem;"></textarea>
        </div>
        
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Item Description</label>
            <input type="text" id="cargoDescription" placeholder="e.g., Steel coils, Packaging materials..." style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; margin-bottom: 1rem;">
        </div>
        
        <div class="unpacking-grid">
            <div class="form-group">
                <label style="color: #0f1d3d; font-weight: 600;">Quantity</label>
                <input type="number" id="cargoQuantity" min="1" placeholder="Qty..." style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px;">
            </div>
            <div class="form-group">
                <label style="color: #0f1d3d; font-weight: 600;">Unit</label>
                <select id="cargoUnit" style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px;">
                    <option value="pieces">Pieces</option>
                    <option value="boxes">Boxes</option>
                    <option value="pallets">Pallets</option>
                    <option value="tons">Tons</option>
                    <option value="kg">Kg</option>
                </select>
            </div>
        </div>
        
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Condition</label>
            <select id="cargoItemCondition" style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; margin-bottom: 1rem;">
                <option value="GOOD">Good</option>
                <option value="ACCEPTABLE">Acceptable</option>
                <option value="DAMAGED">Damaged</option>
                <option value="MISSING">Missing</option>
            </select>
        </div>

        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Notes</label>
            <textarea id="cargoNotes" placeholder="Item-specific notes..." style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; min-height: 80px; margin-bottom: 1rem;"></textarea>
        </div>

        <div id="manifestPhotoCount" style="color: #666;">Manifest items: 0</div>

        <button class="btn btn-primary" onclick="addCargoItem()" style="width: 100%;">➕ Add Item to Manifest</button>
        <button class="btn btn-secondary" onclick="documentManifestDetails()" style="width: 100%; margin-top: 0.75rem;">📝 Save Manifest Documentation</button>
        <small id="manifestCompletionStatus" style="color: #666; display: block; margin-top: 0.45rem;">Manifest documentation pending</small>

        <h4 style="color: #0f1d3d; margin-top: 1rem;">Added Items:</h4>
        <div id="manifestItemsList" class="unpacking-list">
            <p style="color: #999; text-align: center;">No items added yet</p>
        </div>
    </div>
        `,
        'FINAL_INSPECTION': `
    <div class="unpacking-form">
        <h3 class="unpacking-header">✅ Final Inspection & Completion</h3>
        <div class="unpacking-card" style="background: #d4edda; border-color: #b4dfc1; color: #155724;">
            <strong>Review Summary:</strong> Verify all previous steps are complete and documented.
        </div>
        
        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Completion Checklist</label>
            <div class="unpacking-card" style="display: flex; flex-direction: column; gap: 0.75rem;">
                <label><input type="checkbox" id="checkExterior" checked disabled> Exterior inspection completed</label>
                <label><input type="checkbox" id="checkDoors" checked disabled> Door opening documented</label>
                <label><input type="checkbox" id="checkInterior" checked disabled> Interior inspection done</label>
                <label><input type="checkbox" id="checkUnloading" checked disabled> Cargo unloading completed</label>
                <label><input type="checkbox" id="checkManifest" checked disabled> Manifest documented</label>
                <label><input type="checkbox" id="checkDamageResolved"> Any reported damages resolved/documented</label>
            </div>
        </div>

        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Final Inspection Notes *</label>
            <textarea id="finalInspectionNotes" placeholder="Final remarks and inspection conclusions..." required style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; min-height: 120px; margin-bottom: 1rem;"></textarea>
        </div>

        <div class="form-group">
            <label style="color: #0f1d3d; font-weight: 600;">Inspection Status *</label>
            <select id="finalStatus" required style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 4px; margin-bottom: 1rem;">
                <option value="">Select...</option>
                <option value="PASS">✅ PASS - No Issues</option>
                <option value="PASS_WITH_NOTES">⚠️ PASS - With Notes</option>
                <option value="NEEDS_REVIEW">🔍 Needs Further Review</option>
                <option value="HOLD">❌ HOLD - Issue Found</option>
            </select>
        </div>

        <div class="unpacking-note">
            <strong>Note:</strong> Unpacking will be marked as complete once you click "Complete Unpacking" in the action buttons.
        </div>
    </div>
        `
    };

    contentArea.innerHTML = stepForms[step] || '<p>Step not found</p>';

    if (step !== 'FINAL_INSPECTION') {
        const actions = document.createElement('div');
        actions.className = 'unpacking-actions';
        const canRevert = step !== 'EXTERIOR_INSPECTION';
        actions.innerHTML = `
            <button class="btn btn-primary" onclick="advanceUnpackingStep()">✓ Advance to Next Step</button>
            ${canRevert ? '<button class="btn btn-secondary" onclick="revertUnpackingStep()" style="background: #f0f0f0; color: #333; border: 1px solid #ddd;">↶ Revert Step</button>' : ''}
        `;
        contentArea.appendChild(actions);
    }
}

function openPhotoModalForStep(step) {
    const stepNames = {
        'EXTERIOR_INSPECTION': 'Exterior Inspection',
        'DOOR_OPENING': 'Door Opening',
        'INTERIOR_INSPECTION': 'Interior Inspection',
        'CARGO_UNLOADING': 'Cargo Unloading',
        'CARGO_MANIFEST': 'Cargo Manifest'
    };
    
    const stepLabel = document.getElementById('photoModalStep');
    if (stepLabel) {
        stepLabel.textContent = 'Step: ' + (stepNames[step] || step);
    }
    currentPhotoStep = step;
    openModal('photoUploadModal');
}

function closePhotoModal() {
    closeModal('photoUploadModal');
}

function openDamageModal() {
    initializeDamageModal();
    openModal('damageReportModal');
}

function closeDamageModal() {
    closeModal('damageReportModal');
    editingDamageReportId = null;
    const photoCount = document.getElementById('damagePhotoCount');
    if (photoCount) photoCount.textContent = 'No photos selected';
    const title = document.getElementById('damageModalTitle');
    if (title) title.textContent = '🔴 Report Damage';
    const submitBtn = document.getElementById('damageSubmitBtn');
    if (submitBtn) submitBtn.textContent = 'Report Damage';
    const containerSelect = document.getElementById('damageContainerSelect');
    if (containerSelect) containerSelect.disabled = false;
    const containerNumber = document.getElementById('damageContainerNumber');
    if (containerNumber) containerNumber.disabled = false;
    const bookingSelect = document.getElementById('damageBookingSelect');
    if (bookingSelect) bookingSelect.disabled = false;
}

function closeUnpackingWorkflow() {
    if (confirm('Close unpacking workflow? Any unsaved progress will be lost.')) {
        closeModal('unpackingWorkflowModal');
        currentUnpackingSession = null;
    }
}

async function saveUnpackingProgress() {
    if (!currentUnpackingSession.containerId) return;
    await loadUnpackingProgress(currentUnpackingSession.containerId);
    APP.showSuccess('Progress refreshed');
}

async function completeUnpacking() {
    if (!currentUnpackingSession.containerId) return;
    if (!confirm('Mark this unpacking as complete? This cannot be undone.')) return;

    const notes = document.getElementById('finalInspectionNotes')?.value || '';
    const query = notes ? `?final_notes=${encodeURIComponent(notes)}` : '';

    try {
        const response = await APP.apiCall(`/unpacking/${currentUnpackingSession.containerId}/complete${query}`, { method: 'POST' });
        if (response?.ok) {
            APP.showSuccess('Unpacking marked as complete');
            closeUnpackingWorkflow();
            currentUnpackingSession = { containerId: null, progress: null };
            resetActiveUnpackingCard();
            showUnpackingBanner();
            if (window.Containers && window.Containers.loadAvailableFCLContainers) {
                window.Containers.loadAvailableFCLContainers();
            }
            loadDashboardData();
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to complete unpacking');
        }
    } catch (error) {
        console.error('Error completing unpacking:', error);
        APP.showError('Error completing unpacking');
    }
}

function resetActiveUnpackingCard() {
    const idEl = document.getElementById('activeUnpackingId');
    const details = document.getElementById('activeUnpackingDetails');
    const actions = document.getElementById('activeUnpackingActions');
    const noEl = document.getElementById('activeUnpackingNo');
    const stepEl = document.getElementById('activeUnpackingStep');
    const progEl = document.getElementById('activeUnpackingProgress');

    if (idEl) idEl.textContent = 'No active container';
    if (noEl) noEl.textContent = '-';
    if (stepEl) stepEl.textContent = '-';
    if (progEl) progEl.textContent = '-';
    if (details) details.style.display = 'none';
    if (actions) actions.style.display = 'none';
}

function showUnpackingBanner() {
    const banner = document.getElementById('unpackingSuccessBanner');
    if (!banner) return;
    banner.style.display = 'block';
    clearTimeout(banner._hideTimer);
    banner._hideTimer = setTimeout(() => {
        banner.style.display = 'none';
    }, 6000);
}

function addCargoItem() {
    if (!currentUnpackingSession.containerId) return;
    const description = document.getElementById('cargoDescription')?.value || '';
    const quantity = Number(document.getElementById('cargoQuantity')?.value || 0);
    const unit = document.getElementById('cargoUnit')?.value || 'pieces';
    const condition = document.getElementById('cargoItemCondition')?.value || 'GOOD';
    const notes = document.getElementById('cargoNotes')?.value || '';

    if (!description || quantity <= 0) {
        APP.showError('Please enter item description and quantity');
        return;
    }

    APP.apiCall(`/unpacking/${currentUnpackingSession.containerId}/cargo-item`, {
        method: 'POST',
        body: JSON.stringify({ description, quantity, unit, condition, notes })
    }).then(async response => {
        if (response?.ok) {
            APP.showSuccess('Item added to manifest');
            const list = document.getElementById('manifestItemsList');
            if (list) {
                const item = document.createElement('div');
                item.style.cssText = 'padding: 0.5rem 0; border-bottom: 1px solid #e0e0e0;';
                item.textContent = `${description} (${quantity} ${unit}) - ${condition}`;
                if (list.textContent.includes('No items added yet')) list.innerHTML = '';
                list.appendChild(item);
            }
            await loadUnpackingProgress(currentUnpackingSession.containerId);
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to add cargo item');
        }
    }).catch(error => {
        console.error('Error adding cargo item:', error);
        APP.showError('Error adding cargo item');
    });
}

function documentManifestDetails() {
    if (!currentUnpackingSession.containerId) return;
    const document_reference = document.getElementById('manifestDocumentReference')?.value?.trim() || null;
    const manifest_notes = document.getElementById('manifestDocumentNotes')?.value?.trim() || null;

    APP.apiCall(`/unpacking/${currentUnpackingSession.containerId}/manifest-details`, {
        method: 'POST',
        body: JSON.stringify({ document_reference, manifest_notes })
    }).then(async response => {
        if (response?.ok) {
            APP.showSuccess('Manifest documentation saved');
            await loadUnpackingProgress(currentUnpackingSession.containerId);
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to save manifest documentation');
        }
    }).catch(error => {
        console.error('Error saving manifest documentation:', error);
        APP.showError('Error saving manifest documentation');
    });
}

async function uploadPhotos() {
    if (!currentUnpackingSession.containerId || !currentPhotoStep) return;
    const files = document.getElementById('photoFileInput').files;
    if (files.length === 0) {
        APP.showError('Please select at least one photo');
        return;
    }

    const token = localStorage.getItem('access_token');
    try {
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);
            const response = await fetch(`/api/unpacking/${currentUnpackingSession.containerId}/photo-upload?step=${currentPhotoStep}`, {
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

        APP.showSuccess(`Uploaded ${files.length} photo(s)`);
        closePhotoModal();
        document.getElementById('photoFileInput').value = '';
        currentPhotoStep = null;
        await loadUnpackingProgress(currentUnpackingSession.containerId);
    } catch (error) {
        console.error('Error uploading photos:', error);
        APP.showError('Error uploading photos');
    }
}

async function submitDamageReport(e) {
    e.preventDefault();
    const damageType = document.getElementById('damageType')?.value?.trim();
    const severity = document.getElementById('damageSeverity')?.value?.trim();
    const location = document.getElementById('damageLocation')?.value?.trim();
    const description = document.getElementById('damageDescription')?.value?.trim() || '';
    const photos = document.getElementById('damagePhotoInput')?.files;

    if (!damageType || !severity || !location || !description) {
        APP.showError('Please complete all required damage fields');
        return;
    }

    try {
        if (editingDamageReportId) {
            const updateResponse = await APP.apiCall(`/damage-reports/${editingDamageReportId}`, {
                method: 'PUT',
                body: JSON.stringify({
                    damage_type: damageType,
                    severity,
                    location,
                    description
                })
            });

            if (!updateResponse?.ok) {
                const error = await updateResponse.json();
                APP.showError(error.detail || 'Failed to update damage report');
                return;
            }

            if (photos && photos.length > 0) {
                const photoFormData = new FormData();
                for (const photo of photos) {
                    photoFormData.append('photos', photo);
                }
                const photoResponse = await fetch(`/api/damage-reports/${editingDamageReportId}/photos`, {
                    method: 'POST',
                    headers: {
                        Authorization: `Bearer ${localStorage.getItem('access_token')}`
                    },
                    body: photoFormData
                });
                if (!photoResponse.ok) {
                    const error = await photoResponse.json();
                    APP.showError(error.detail || 'Failed to add damage photos');
                    return;
                }
            }

            APP.showSuccess('Damage report updated');
        } else {
            if (!photos || photos.length < 1) {
                APP.showError('At least one damage photo is required');
                return;
            }

            const formData = new FormData();
            formData.append('damage_type', damageType);
            formData.append('severity', severity);
            formData.append('location', location);
            formData.append('description', description);

            if (currentUnpackingSession?.containerId) {
                formData.append('container_id', currentUnpackingSession.containerId);
            } else if (damageContainerMode === 'existing') {
                const containerId = document.getElementById('damageContainerSelect')?.value;
                if (!containerId) {
                    APP.showError('Select a container');
                    return;
                }
                formData.append('container_id', containerId);
            } else {
                const containerNo = document.getElementById('damageContainerNumber')?.value?.trim()?.toUpperCase();
                const bookingId = document.getElementById('damageBookingSelect')?.value;
                if (!containerNo) {
                    APP.showError('Enter container number');
                    return;
                }
                formData.append('container_no', containerNo);
                if (bookingId) {
                    formData.append('booking_id', bookingId);
                }
            }

            for (const photo of photos) {
                formData.append('photos', photo);
            }

            const response = await fetch('/api/damage-reports/', {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${localStorage.getItem('access_token')}`
                },
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                APP.showError(error.detail || 'Failed to submit damage report');
                return;
            }

            APP.showSuccess('Damage report submitted');
        }

        closeDamageModal();
        await loadDamageReports();
        if (window.Containers && typeof window.Containers.loadContainers === 'function') {
            await window.Containers.loadContainers();
        }
        if (currentUnpackingSession?.containerId) {
            await loadUnpackingProgress(currentUnpackingSession.containerId);
        }
    } catch (error) {
        console.error('Error submitting damage report:', error);
        APP.showError('Error submitting damage report');
    }
}

function setDamageContainerMode(mode, force = false) {
    if (editingDamageReportId && !force) return;
    damageContainerMode = mode;
    const existingSection = document.getElementById('damageExistingSection');
    const newSection = document.getElementById('damageNewSection');
    const existingBtn = document.getElementById('damageSelectExistingBtn');
    const newBtn = document.getElementById('damageEnterNumberBtn');
    const existingSelect = document.getElementById('damageContainerSelect');
    const containerNumber = document.getElementById('damageContainerNumber');
    const bookingSelect = document.getElementById('damageBookingSelect');

    if (existingSection) existingSection.style.display = mode === 'existing' ? 'block' : 'none';
    if (newSection) newSection.style.display = mode === 'new' ? 'block' : 'none';
    if (existingBtn) existingBtn.classList.toggle('active', mode === 'existing');
    if (newBtn) newBtn.classList.toggle('active', mode === 'new');

    if (existingSelect) existingSelect.required = mode === 'existing';
    if (containerNumber) containerNumber.required = mode === 'new';
    if (bookingSelect) bookingSelect.required = false;
}

async function initializeDamageModal() {
    setDamageContainerMode('existing', true);

    const photoInput = document.getElementById('damagePhotoInput');
    const photoCount = document.getElementById('damagePhotoCount');
    if (photoInput && !photoInput.dataset.bound) {
        photoInput.addEventListener('change', () => {
            const count = photoInput.files?.length || 0;
            if (photoCount) {
                photoCount.textContent = count ? `${count} photo(s) selected` : 'No photos selected';
            }
        });
        photoInput.dataset.bound = '1';
    }

    if (!currentUnpackingSession?.containerId) {
        await Promise.all([
            loadDamageContainerOptions(),
            loadDamageBookingOptions()
        ]);
    }
}

async function loadDamageContainerOptions() {
    const select = document.getElementById('damageContainerSelect');
    if (!select) return;

    const response = await APP.apiCall('/containers');
    if (!response?.ok) return;
    const containers = await response.json();
    select.innerHTML = '<option value="">Select container</option>' + containers
        .map(c => `<option value="${c.id}">${c.container_no} (${c.status})</option>`)
        .join('');
}

async function loadDamageBookingOptions() {
    const select = document.getElementById('damageBookingSelect');
    if (!select) return;

    const response = await APP.apiCall('/bookings');
    if (!response?.ok) return;
    const bookings = await response.json();
    select.innerHTML = '<option value="">Select booking</option>' + bookings
        .map(b => `<option value="${b.id}">${b.booking_reference} - ${b.client}</option>`)
        .join('');
}

async function loadDamageReports() {
    const list = document.getElementById('damageReportsList');
    if (!list) return;

    try {
        const response = await APP.apiCall('/damage-reports/');
        if (!response?.ok) {
            list.innerHTML = '<p style="color:#c0392b; grid-column:1/-1;">Failed to load damage reports</p>';
            return;
        }

        const reports = await response.json();
        cachedDamageReports = Array.isArray(reports) ? reports : [];
        if (!cachedDamageReports.length) {
            list.innerHTML = '<p style="color:#888; grid-column:1/-1;">No damage reports yet</p>';
            return;
        }

        list.innerHTML = cachedDamageReports.map(report => {
            const severity = String(report.severity || '').toUpperCase();
            const isBlocking = severity === 'MAJOR' || severity === 'CRITICAL';
            const photos = Array.isArray(report.photos) ? report.photos : [];
            const photoHtml = photos.length
                ? `<div class="damage-photo-gallery">${photos.map(photo => `
                    <div class="damage-photo-item">
                        <img src="${photo.url}" alt="Damage photo" />
                        <button class="btn btn-sm btn-secondary" onclick="deleteDamagePhoto('${report.id}','${photo.id}')" ${photos.length <= 1 ? 'disabled' : ''}>Delete</button>
                    </div>
                `).join('')}</div>`
                : '<div class="damage-help">No photos</div>';

            return `
                <div class="job-card">
                    <div class="job-header">
                        <div class="job-id">${report.container_no}</div>
                        <span class="job-status ${severity === 'CRITICAL' ? 'status-pending' : severity === 'MAJOR' ? 'status-in-progress' : 'status-ready'}">${severity}${report.is_resolved ? ' (RESOLVED)' : ''}</span>
                    </div>
                    <div class="job-details">
                        <div class="job-detail"><span class="job-label">Type:</span> <span class="job-value">${report.damage_type}</span></div>
                        <div class="job-detail"><span class="job-label">Location:</span> <span class="job-value">${report.location || '-'}</span></div>
                        <div class="job-detail"><span class="job-label">Photos:</span> <span class="job-value">${report.photo_count}</span></div>
                        <div class="job-detail"><span class="job-label">Reported:</span> <span class="job-value">${APP.formatDate(report.reported_at)}</span></div>
                    </div>
                    <div style="margin-top:0.75rem; color:#334;">${report.description}</div>
                    ${photoHtml}
                    <div class="damage-actions-inline">
                        <button class="btn btn-sm btn-secondary" onclick="openEditDamageReport('${report.id}')">Edit</button>
                        ${report.is_resolved
                            ? '<button class="btn btn-sm btn-secondary" onclick="reopenDamageReport(\'' + report.id + '\')">Reopen</button>'
                            : '<button class="btn btn-sm btn-primary" onclick="resolveDamageReport(\'' + report.id + '\')">Mark Repaired</button>'}
                    </div>
                    ${isBlocking && !report.is_resolved ? '<div class="damage-blocked-note">Container blocked due to Major/Critical damage. Repair required before packing/unpacking start/continue.</div>' : ''}
                    ${report.is_resolved && report.resolved_notes ? `<div class="damage-help" style="margin-top:0.5rem;">Resolved notes: ${report.resolved_notes}</div>` : ''}
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading damage reports:', error);
        list.innerHTML = '<p style="color:#c0392b; grid-column:1/-1;">Error loading damage reports</p>';
    }
}

async function openEditDamageReport(reportId) {
    const report = cachedDamageReports.find(item => String(item.id) === String(reportId));
    if (!report) {
        APP.showError('Damage report not found');
        return;
    }

    editingDamageReportId = String(reportId);
    await initializeDamageModal();
    const title = document.getElementById('damageModalTitle');
    const submitBtn = document.getElementById('damageSubmitBtn');
    if (title) title.textContent = '✏️ Update Damage Report';
    if (submitBtn) submitBtn.textContent = 'Update Damage Report';

    setDamageContainerMode('existing', true);
    const containerSelect = document.getElementById('damageContainerSelect');
    if (containerSelect) {
        containerSelect.value = report.container_id;
        containerSelect.disabled = true;
    }
    const newContainerInput = document.getElementById('damageContainerNumber');
    if (newContainerInput) newContainerInput.disabled = true;
    const bookingSelect = document.getElementById('damageBookingSelect');
    if (bookingSelect) bookingSelect.disabled = true;

    const damageType = document.getElementById('damageType');
    const damageSeverity = document.getElementById('damageSeverity');
    const damageLocation = document.getElementById('damageLocation');
    const damageDescription = document.getElementById('damageDescription');
    if (damageType) damageType.value = report.damage_type || '';
    if (damageSeverity) damageSeverity.value = report.severity || '';
    if (damageLocation) damageLocation.value = report.location || '';
    if (damageDescription) damageDescription.value = report.description || '';

    const photoCount = document.getElementById('damagePhotoCount');
    if (photoCount) photoCount.textContent = 'Select extra photos only if needed';

    openModal('damageReportModal');
}

async function resolveDamageReport(reportId) {
    const notes = prompt('Add repair completion notes (optional):') || '';
    const response = await APP.apiCall(`/damage-reports/${reportId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ notes })
    });
    if (response?.ok) {
        APP.showSuccess('Damage report marked as repaired');
        await loadDamageReports();
        if (window.Containers && typeof window.Containers.loadContainers === 'function') {
            await window.Containers.loadContainers();
        }
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to mark repaired');
    }
}

async function reopenDamageReport(reportId) {
    const response = await APP.apiCall(`/damage-reports/${reportId}/reopen`, { method: 'POST' });
    if (response?.ok) {
        APP.showSuccess('Damage report reopened');
        await loadDamageReports();
        if (window.Containers && typeof window.Containers.loadContainers === 'function') {
            await window.Containers.loadContainers();
        }
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to reopen report');
    }
}

async function deleteDamagePhoto(reportId, photoId) {
    if (!confirm('Delete this photo?')) return;
    const response = await APP.apiCall(`/damage-reports/${reportId}/photos/${photoId}`, {
        method: 'DELETE'
    });
    if (response?.ok) {
        APP.showSuccess('Photo deleted');
        await loadDamageReports();
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to delete photo');
    }
}

async function advanceUnpackingStep() {
    if (!currentUnpackingSession.containerId) return;
    if (currentUnpackingStep === 'CARGO_MANIFEST') {
        const progress = currentUnpackingSession.progress || {};
        if (!progress.manifest_complete || !progress.manifest_documented_at) {
            APP.showError('Save manifest documentation before advancing.');
            return;
        }
    }
    try {
        const response = await APP.apiCall(`/unpacking/${currentUnpackingSession.containerId}/advance-step`, { method: 'POST' });
        if (response?.ok) {
            await loadUnpackingProgress(currentUnpackingSession.containerId);
            APP.showSuccess('Advanced to next step');
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Cannot advance step');
        }
    } catch (error) {
        console.error('Error advancing step:', error);
        APP.showError('Error advancing step');
    }
}

async function revertUnpackingStep() {
    if (!currentUnpackingSession.containerId) return;
    if (!confirm('Revert to previous step? This will clear photos from current step.')) return;
    try {
        const response = await APP.apiCall(`/unpacking/${currentUnpackingSession.containerId}/revert-step`, { method: 'POST' });
        if (response?.ok) {
            await loadUnpackingProgress(currentUnpackingSession.containerId);
            APP.showSuccess('Reverted to previous step');
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Cannot revert step');
        }
    } catch (error) {
        console.error('Error reverting step:', error);
        APP.showError('Error reverting step');
    }
}

function updateUnpackingPhotoCounts(progress) {
    const exterior = document.getElementById('exteriorPhotoCount');
    const door = document.getElementById('doorPhotoCount');
    const interior = document.getElementById('interiorPhotoCount');
    const unloading = document.getElementById('unloadingPhotoCount');
    const manifest = document.getElementById('manifestPhotoCount');
    if (exterior) exterior.textContent = `Photos: ${progress.exterior_inspection_photos}/${progress.exterior_required}`;
    if (door) door.textContent = `Photos: ${progress.door_opening_photos}/${progress.door_required}`;
    if (interior) interior.textContent = `Photos: ${progress.interior_inspection_photos}/${progress.interior_required}`;
    if (unloading) unloading.textContent = `Photos: ${progress.cargo_unloading_photos}/${progress.cargo_required}`;
    if (manifest) manifest.textContent = `Manifest items: ${progress.cargo_items_count || 0}`;
    const manifestStatus = document.getElementById('manifestCompletionStatus');
    if (manifestStatus) {
        manifestStatus.textContent = progress.manifest_complete
            ? `Manifest documented${progress.manifest_documented_at ? ` at ${new Date(progress.manifest_documented_at).toLocaleString()}` : ''}`
            : 'Manifest documentation pending';
    }

    const manifestRef = document.getElementById('manifestDocumentReference');
    if (manifestRef && progress.manifest_document_reference && !manifestRef.value) {
        manifestRef.value = progress.manifest_document_reference;
    }

    const manifestNotes = document.getElementById('manifestDocumentNotes');
    if (manifestNotes && progress.manifest_notes && !manifestNotes.value) {
        manifestNotes.value = progress.manifest_notes;
    }
}

function renderUnpackingSteps(progress) {
    const steps = [
        'EXTERIOR_INSPECTION',
        'DOOR_OPENING',
        'INTERIOR_INSPECTION',
        'CARGO_UNLOADING',
        'CARGO_MANIFEST',
        'FINAL_INSPECTION'
    ];
    const stepContainer = document.getElementById('workflowSteps');
    if (!stepContainer) return;

    const requiredMap = {
        EXTERIOR_INSPECTION: progress.exterior_required,
        DOOR_OPENING: progress.door_required,
        INTERIOR_INSPECTION: progress.interior_required,
        CARGO_UNLOADING: progress.cargo_required,
        CARGO_MANIFEST: 1,
        FINAL_INSPECTION: 1
    };
    const countMap = {
        EXTERIOR_INSPECTION: progress.exterior_inspection_photos,
        DOOR_OPENING: progress.door_opening_photos,
        INTERIOR_INSPECTION: progress.interior_inspection_photos,
        CARGO_UNLOADING: progress.cargo_unloading_photos,
        CARGO_MANIFEST: progress.manifest_complete ? 1 : 0,
        FINAL_INSPECTION: 0
    };

    stepContainer.innerHTML = steps.map(step => {
        const isActive = step === progress.current_step;
        const isComplete = (countMap[step] || 0) >= (requiredMap[step] || 1);
        const stepClass = isActive ? 'is-active' : (isComplete ? 'is-complete' : 'is-ready');
        return `
            <div class="workflow-step ${stepClass}" data-step="${step}" onclick="switchUnpackingStep('${step}')">
                <div class="workflow-step-icon">${isComplete ? '✓' : (isActive ? '●' : '○')}</div>
                <div class="workflow-step-title">${step.replace(/_/g, ' ')}</div>
                <div class="workflow-step-count">${countMap[step] || 0}/${requiredMap[step] || 1}</div>
            </div>
        `;
    }).join('');
}

function updateActiveUnpackingCard(progress) {
    const idEl = document.getElementById('activeUnpackingId');
    const details = document.getElementById('activeUnpackingDetails');
    const actions = document.getElementById('activeUnpackingActions');
    const noEl = document.getElementById('activeUnpackingNo');
    const stepEl = document.getElementById('activeUnpackingStep');
    const progEl = document.getElementById('activeUnpackingProgress');

    if (idEl) idEl.textContent = progress.container_no || 'Active container';
    if (noEl) noEl.textContent = progress.container_no || '-';
    if (stepEl) stepEl.textContent = progress.current_step.replace(/_/g, ' ');
    if (progEl) progEl.textContent = progress.is_complete ? 'Complete' : 'In Progress';
    if (details) details.style.display = 'grid';
    if (actions) actions.style.display = 'flex';
}

// Export for use in other modules
window.UI = {
    switchTab,
    switchSidebar,
    toggleExportPackingPage,
    toggleImportUnpackingPage,
    openModal,
    closeModal,
    startUnpackingWorkflow,
    loadUnpackingProgress,
    switchUnpackingStep,
    openPhotoModalForStep,
    closePhotoModal,
    openDamageModal,
    closeDamageModal,
    setDamageContainerMode,
    loadDamageReports,
    openEditDamageReport,
    resolveDamageReport,
    reopenDamageReport,
    deleteDamagePhoto,
    closeUnpackingWorkflow,
    saveUnpackingProgress,
    completeUnpacking,
    addCargoItem,
    documentManifestDetails,
    advanceUnpackingStep,
    revertUnpackingStep,
    uploadPhotos,
    submitDamageReport
};

window.openDamageModal = openDamageModal;
window.closeDamageModal = closeDamageModal;
window.submitDamageReport = submitDamageReport;
window.setDamageContainerMode = setDamageContainerMode;
window.loadDamageReports = loadDamageReports;
window.openEditDamageReport = openEditDamageReport;
window.resolveDamageReport = resolveDamageReport;
window.reopenDamageReport = reopenDamageReport;
window.deleteDamagePhoto = deleteDamagePhoto;
window.documentManifestDetails = documentManifestDetails;
