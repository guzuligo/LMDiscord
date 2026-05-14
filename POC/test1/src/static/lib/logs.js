// ==================== Log Panel Functions ====================
// Shared between main page (script.js) and debug page (debug_script.js)

function toggleLogPanel() {
    const panel = document.getElementById('logPanel');
    if (panel) panel.classList.toggle('collapsed');
}

function onLogLevelFilterChange(filterValue) {
    const currentFilter = filterValue || (typeof state !== 'undefined' ? state.currentLogLevelFilter : (typeof debugState !== 'undefined' ? debugState.currentLogLevelFilter : 'ALL'));
    const levelParam = currentFilter !== 'ALL' ? `&level=${currentFilter}` : '';
    
    if (typeof fetchLogs === 'function') {
        fetchLogs(levelParam);
    }
}

async function refreshLogs(levelParam) {
    levelParam = levelParam || '';
    if (typeof state !== 'undefined') state.lastLogCount = 0;
    if (typeof debugState !== 'undefined') debugState.lastLogCount = 0;
    await fetchLogs(levelParam);
}

async function clearLogs() {
    try {
        await fetch('/api/logs/clear', { method: 'POST' });
        if (typeof state !== 'undefined') {
            state.lastLogCount = 0;
            state.newLogCount = 0;
        }
        if (typeof debugState !== 'undefined') {
            debugState.lastLogCount = 0;
        }
        
        // Clear both possible log containers
        const panelContainer = document.getElementById('logPanelContainer');
        if (panelContainer) panelContainer.innerHTML = '';
        
        const logsTabContainer = document.getElementById('logContainer');
        if (logsTabContainer) logsTabContainer.innerHTML = '';
        
        const debugLogContainer = document.getElementById('debugLogContainer');
        if (debugLogContainer) debugLogContainer.innerHTML = '';
        
        updateLogStats({ DEBUG: 0, INFO: 0, WARNING: 0, ERROR: 0, CRITICAL: 0, total: 0 });
    } catch (e) {
        console.error('Failed to clear logs:', e);
    }
}

async function fetchLogs(levelParam) {
    levelParam = levelParam || '';
    const limit = 200;
    try {
        const response = await fetch(`/api/logs?limit=${limit}${levelParam}`);
        const data = await response.json();
        
        if (data.success) {
            // Try main page first, then debug page
            if (typeof updateLogDisplay === 'function') {
                updateLogDisplay(data.logs, data.stats);
            }
            if (typeof updateDebugLogDisplay === 'function') {
                updateDebugLogDisplay(data.logs);
            }
        }
    } catch (e) {
        console.error('Failed to fetch logs:', e);
    }
}

function updateLogDisplay(logs, stats) {
    if (!logs) return;
    
    const panelContainer = document.getElementById('logPanelContainer');
    if (!panelContainer) return;
    
    const newLogs = logs.length - (state?.lastLogCount || 0);
    if (newLogs > 0) {
        if (document.getElementById('logs-tab')?.classList.contains('active')) {
            state.newLogCount = 0;
        } else {
            state.newLogCount += newLogs;
        }
    }
    
    // Update badge
    const badge = document.getElementById('logBadge');
    if (badge) {
        if (state?.newLogCount > 0) {
            badge.style.display = 'inline';
            badge.textContent = state.newLogCount > 99 ? '99+' : state.newLogCount;
        } else {
            badge.style.display = 'none';
        }
    }
    
    // Update stats
    if (stats) updateLogStats(stats);
    
    // Update panel container with new logs
    if (logs.length > (state?.lastLogCount || 0)) {
        const newLogCount = logs.length - (state?.lastLogCount || 0);
        const newLogEntries = logs.slice(-newLogCount);
        for (const log of newLogEntries) {
            const logEl = createLogElement(log);
            panelContainer.appendChild(logEl);
        }
        panelContainer.scrollTop = panelContainer.scrollHeight;
    }
    
    // Update tab container with all logs if active
    if (document.getElementById('logs-tab')?.classList.contains('active')) {
        const logsTabContainer = document.getElementById('logContainer');
        if (logsTabContainer) {
            logsTabContainer.innerHTML = '';
            for (const log of logs) {
                logsTabContainer.appendChild(createLogElement(log));
            }
            logsTabContainer.scrollTop = logsTabContainer.scrollHeight;
        }
    }
    
    if (typeof state !== 'undefined') state.lastLogCount = logs.length;
}

function updateDebugLogDisplay(logs) {
    // Only run on debug page where debugState is defined
    if (typeof debugState === 'undefined') {
        console.warn('[logs.js] updateDebugLogDisplay called but debugState is undefined - not on debug page');
        return;
    }
    if (!logs) {
        console.warn('[logs.js] updateDebugLogDisplay called with no logs data');
        return;
    }
    
    const debugLogContainerEl = document.getElementById('debugLogContainer');
    if (!debugLogContainerEl) {
        console.warn('[logs.js] updateDebugLogDisplay: debugLogContainer element not found');
        return;
    }
    
    // Handle empty logs
    if (!logs || logs.length === 0) {
        if (debugState.lastLogCount === 0) {
            debugLogContainerEl.innerHTML = '<div style="color: #6c7086; text-align: center; padding: 20px; font-style: italic;">No logs available. The application logger has not recorded any entries yet.</div>';
        }
        return;
    }
    
    // On first load (lastLogCount === 0), render all logs
    if (debugState.lastLogCount === 0) {
        debugLogContainerEl.innerHTML = '';
        for (const log of logs) {
            const entry = document.createElement('div');
            entry.className = 'debug-log-entry';
            
            const levelColor = getLogLevelColor(log.level);
            entry.innerHTML = `
                <span style="color: #6c7086;">${log.timestamp_formatted}</span>
                <span style="color: ${levelColor}; font-weight: bold;">[${log.level}]</span>
                <span style="color: #89b4fa;">${log.module || 'App'}</span>
                <span style="color: #cdd6f4;">${escapeHtml(log.message)}</span>
            `;
            debugLogContainerEl.appendChild(entry);
        }
        console.log(`[logs.js] render all ${logs.length} logs on initial load`);
    } else {
        // Only append new logs
        const newLogCount = logs.length - debugState.lastLogCount;
        if (newLogCount > 0) {
            const newLogs = logs.slice(debugState.lastLogCount);
            for (const log of newLogs) {
                const entry = document.createElement('div');
                entry.className = 'debug-log-entry';
                
                const levelColor = getLogLevelColor(log.level);
                entry.innerHTML = `
                    <span style="color: #6c7086;">${log.timestamp_formatted}</span>
                    <span style="color: ${levelColor}; font-weight: bold;">[${log.level}]</span>
                    <span style="color: #89b4fa;">${log.module || 'App'}</span>
                    <span style="color: #cdd6f4;">${escapeHtml(log.message)}</span>
                `;
                debugLogContainerEl.appendChild(entry);
            }
            console.log(`[logs.js] appended ${newLogCount} new logs (total: ${logs.length})`);
        }
    }
    
    // Auto-scroll to bottom
    debugLogContainerEl.scrollTop = debugLogContainerEl.scrollHeight;
    
    // Always update lastLogCount to match current total
    debugState.lastLogCount = logs.length;
}
