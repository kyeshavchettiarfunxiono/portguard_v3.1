/**
 * Tab Loader - Dynamically loads and manages tab content
 * Handles loading HTML templates and managing tab state
 */

const TabLoader = {
    loadedTabs: new Set(),
    activeTab: 'overview',

    /**
     * Load a tab template from /templates/tabs/
     */
    async loadTab(tabName) {
        // Skip if already loaded
        if (this.loadedTabs.has(tabName)) {
            console.log(`📄 Tab ${tabName} already loaded`);
            return true;
        }

        try {
            console.log(`📥 Loading tab template: ${tabName}`);
            const response = await fetch(`/templates/tabs/${tabName}.html`);

            if (!response.ok) {
                console.error(`Failed to load tab ${tabName}: ${response.status}`);
                return false;
            }

            const html = await response.text();
            
            // Create a temporary container
            const temp = document.createElement('div');
            temp.innerHTML = html;

            // Find the tab element - try multiple ID patterns
            let tabElement = temp.querySelector(`#${tabName}`);
            if (!tabElement) {
                // Try hyphenated version
                const hyphenated = tabName.replace(/_/g, '-');
                tabElement = temp.querySelector(`#${hyphenated}`);
            }
            if (!tabElement) {
                // Try with -tab suffix
                tabElement = temp.querySelector(`[id$="-tab"][id*="${tabName}"]`);
            }
            if (!tabElement) {
                // Last resort - any div with class tab-panel or tab-content
                tabElement = temp.querySelector('.tab-panel, .tab-content');
            }
            
            if (!tabElement) {
                console.error(`No tab element found in ${tabName}.html`);
                return false;
            }

            // Set proper ID if it doesn't match tabName
            if (tabElement.id !== tabName) {
                tabElement.id = tabName;
            }

            // Insert into main content area
            const container = document.getElementById('tab-container');
            if (container) {
                container.appendChild(tabElement);
            } else {
                document.body.appendChild(tabElement);
            }

            this.loadedTabs.add(tabName);
            console.log(`✅ Tab ${tabName} loaded successfully`);
            return true;

        } catch (error) {
            console.error(`Error loading tab ${tabName}:`, error);
            return false;
        }
    },

    /**
     * Switch to a tab and load if necessary
     */
    async switchTab(tabName) {
        // Load if not already loaded
        if (!this.loadedTabs.has(tabName)) {
            const loaded = await this.loadTab(tabName);
            if (!loaded) {
                console.error(`Failed to switch to tab ${tabName}`);
                return false;
            }
        }

        // Hide all tabs
        document.querySelectorAll('.tab-panel, .tab-content').forEach(el => {
            el.style.display = 'none';
            el.classList.remove('active');
        });

        // Show selected tab - try multiple ID patterns
        let tab = document.getElementById(tabName);
        if (!tab) {
            const hyphenated = tabName.replace(/_/g, '-');
            tab = document.getElementById(hyphenated);
        }
        
        if (tab) {
            tab.style.display = 'block';
            tab.classList.add('active');
            window.scrollTo(0, 0);
            this.activeTab = tabName;
            console.log(`📊 Switched to tab: ${tabName}`);
            
            // Trigger tab-specific loaders
            this.triggerTabLoader(tabName);
            
            return true;
        } else {
            console.error(`Tab element not found for ${tabName}`);
            return false;
        }
    },

    /**
     * Trigger tab-specific data loaders after switching
     */
    triggerTabLoader(tabName) {
        switch(tabName) {
            case 'export_packing':
                if (window.Containers && typeof window.Containers.loadContainers === 'function') {
                    console.log('📦 Loading export containers...');
                    window.Containers.loadContainers().then(containers => {
                        if (typeof window.displayExportContainers === 'function') {
                            window.displayExportContainers(containers);
                        }
                        if (typeof window.updateExportPackingStats === 'function') {
                            window.updateExportPackingStats(containers);
                        }
                    }).catch(err => console.error('Error loading containers:', err));
                }
                break;
            case 'import_unpacking':
                if (typeof loadAvailableFCLContainers === 'function') {
                    console.log('📥 Loading FCL containers...');
                    loadAvailableFCLContainers();
                }
                break;
            case 'export_truck':
                if (typeof loadBackloadTruckData === 'function') {
                    console.log('🚚 Loading backload trucks...');
                    loadBackloadTruckData();
                }
                break;
            case 'damage':
                if (typeof window.loadDamageReports === 'function') {
                    window.loadDamageReports();
                }
                break;
            case 'supervisor_overview':
                if (typeof window.loadSupervisorAlerts === 'function') {
                    window.loadSupervisorAlerts();
                }
                if (typeof window.checkVesselRelease === 'function') {
                    window.checkVesselRelease();
                }
                break;
            case 'truck_unpacking':
                if (typeof loadTruckOffloadingData === 'function') {
                    console.log('🚛 Loading truck offloading data...');
                    loadTruckOffloadingData();
                }
                break;
            case 'admin_overview':
                if (typeof window.loadAdminOverview === 'function') {
                    window.loadAdminOverview();
                }
                if (typeof window.attachAdminRevenueFilter === 'function') {
                    window.attachAdminRevenueFilter();
                }
                if (typeof window.loadDowntimeRate === 'function') {
                    window.loadDowntimeRate();
                }
                break;
            case 'user_management':
                if (typeof window.loadAdminUsers === 'function') {
                    window.loadAdminUsers();
                }
                break;
            case 'transnet_dashboard':
                if (typeof window.loadTransnetStats === 'function') {
                    window.loadTransnetStats();
                }
                if (typeof window.attachTransnetHandlers === 'function') {
                    window.attachTransnetHandlers();
                }
                if (typeof window.loadTransnetVessels === 'function') {
                    window.loadTransnetVessels();
                }
                break;
            case 'vessel_bookings':
                if (typeof window.loadVesselBookings === 'function') {
                    window.loadVesselBookings();
                }
                if (typeof window.attachBookingHandlers === 'function') {
                    window.attachBookingHandlers();
                }
                break;
            case 'operational_incidents':
                const tryInit = () => {
                    if (typeof window.initOperationalIncidents === 'function') {
                        window.initOperationalIncidents();
                        return true;
                    }
                    if (typeof window.loadIncidentReports === 'function') {
                        window.loadIncidentReports();
                        return true;
                    }
                    return false;
                };

                if (!tryInit()) {
                    const script = document.createElement('script');
                    script.src = '/static/js/operational_incidents.js?v=20260216.1';
                    script.onload = () => {
                        tryInit();
                    };
                    document.body.appendChild(script);
                }
                setTimeout(() => {
                    tryInit();
                }, 0);
                break;
        }
    },

    /**
     * Preload multiple tabs for faster switching
     */
    async preloadTabs(tabs) {
        console.log(`📂 Preloading ${tabs.length} tabs...`);
        for (const tab of tabs) {
            if (!this.loadedTabs.has(tab)) {
                await this.loadTab(tab);
            }
        }
        console.log(`✅ All tabs preloaded`);
    }
};

// Make globally available
window.TabLoader = TabLoader;
