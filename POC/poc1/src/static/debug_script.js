// ==================== Debug Panel State ====================
const debugState = {
    statusPollInterval: null,
    logPollInterval: null,
    lastLogCount: 0,
    currentLogLevelFilter: 'ALL',
    discordBotInfo: null,
    sessionInfo: null,
    lastApiResponse: null,
    lastLogApiResponse: null
};

// ==================== Initialization ====================

window.addEventListener('load', async () => {
    console.log('[DebugPanel] Page loaded, initializing...');
    
    // Initialize log count to 0 so all logs appear on first fetch
    debugState.lastLogCount = 0;
    
    // Load log level setting
    await loadLogLevel();
    
    // Load module filter setting
    await loadModuleFilter();
    
    // Add a test log entry to verify log display is working
    await testLogDisplay();
    
    await checkStatus();
    await fetchDebugLogs();
    
    console.log('[DebugPanel] Starting polling: status=2s, logs=3s');
    
    // Start polling
    debugState.statusPollInterval = setInterval(checkStatus, 2000);
    debugState.logPollInterval = setInterval(fetchDebugLogs, 3000);
});

// ==================== Discord Connection from Debug Page ====================

async function connectDiscordFromDebug() {
    const token = document.getElementById('discordTokenInput')?.value?.trim();
    
    if (!token) {
        addDiagnosticOutput('❌ Please enter a Discord bot token', 'error');
        return;
    }
    
    if (!debugState.lastApiResponse || !debugState.lastApiResponse.lm_connected) {
        addDiagnosticOutput('⚠️ Please connect to LM Studio first', 'error');
        return;
    }
    
    addDiagnosticOutput('🔌 Connecting Discord bot...');
    
    try {
        const response = await fetch('/api/discord/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addDiagnosticOutput('✅ Discord connection initiated. Waiting for status update...', 'success');
            // Force immediate status refresh
            await checkStatus();
        } else {
            addDiagnosticOutput(`❌ Discord connection failed: ${data.message}`, 'error');
        }
    } catch (e) {
        addDiagnosticOutput(`❌ Error: ${e.message}`, 'error');
    }
}

// ==================== Status Checking ====================

async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        debugState.lastApiResponse = await response.json();
        
        console.log('[DebugPanel] Status API response:', debugState.lastApiResponse);
        
        if (!response.ok) {
            console.error('[DebugPanel] Status API HTTP error:', response.status);
            return;
        }
        
        const data = debugState.lastApiResponse;

        // LM Studio status
        updateConnectionStatus('lm', data.lm_connected, data.lm_model || 'Not connected');

        // Discord status
        updateConnectionStatus('discord', data.discord_connected, data.discord_status || 'Not connected');

        // Get bot info if connected
        if (data.discord_connected) {
            await fetchBotInfo();
        }
    } catch (e) {
        console.error('[DebugPanel] Failed to check status:', e);
        updateConnectionStatus('lm', false, 'API Error');
        updateConnectionStatus('discord', false, 'API Error');
    }
}

function updateConnectionStatus(type, isConnected, statusText) {
    const dot = document.getElementById(`${type}StatusDot`);
    const text = document.getElementById(`${type}StatusText`);
    
    if (!dot || !text) return;
    
    dot.className = 'status-dot';
    if (isConnected) {
        dot.classList.add('connected');
        text.textContent = statusText;
    } else {
        dot.classList.add('disconnected');
        text.textContent = statusText;
    }
}

// ==================== Bot Info & Sessions ====================

async function fetchBotInfo() {
    try {
        const response = await fetch('/api/discord/info');
        const data = await response.json();
        
        if (data.success) {
            debugState.discordBotInfo = data;
            await fetchSessionInfo();
        }
    } catch (e) {
        console.error('Failed to fetch bot info:', e);
    }
}

async function fetchSessionInfo() {
    try {
        const response = await fetch('/api/discord/sessions');
        const data = await response.json();
        
        if (data.success) {
            debugState.sessionInfo = data;
            renderSessionList(data.sessions || []);
        }
    } catch (e) {
        console.error('Failed to fetch session info:', e);
    }
}

function renderSessionList(sessions) {
    const sessionListEl = document.getElementById('sessionList');
    if (!sessionListEl) return;
    
    if (!sessions || sessions.length === 0) {
        sessionListEl.innerHTML = '<div class="no-sessions">No active sessions</div>';
        return;
    }
    
    sessionListEl.innerHTML = sessions.map(session => `
        <div class="session-item">
            <div>
                <span class="session-item-channel">Channel: ${session.channel_id}</span>
                <span class="session-item-user">User: ${session.user}</span>
                <span class="session-item-time">Last: ${session.last_activity}</span>
            </div>
            <button class="session-clear-btn" onclick="clearSession('${session.channel_id}')">Clear</button>
        </div>
    `).join('');
}

async function clearSession(channelId) {
    try {
        const response = await fetch('/api/discord/clear_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel_id: channelId })
        });
        const data = await response.json();
        
        if (data.success) {
            addDiagnosticOutput(`Session cleared for channel ${channelId}`);
            await fetchSessionInfo();
        } else {
            addDiagnosticOutput(`Error clearing session: ${data.message}`, 'error');
        }
    } catch (e) {
        addDiagnosticOutput(`Error: ${e.message}`, 'error');
    }
}

// ==================== Diagnostics ====================

const diagnosticOutputEl = document.getElementById('diagnosticOutput');

function addDiagnosticOutput(message, type = 'info') {
    if (!diagnosticOutputEl) return;
    
    const timestamp = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.style.color = type === 'error' ? '#f38ba8' : type === 'success' ? '#a6e3a1' : '#cdd6f4';
    entry.textContent = `[${timestamp}] ${message}`;
    diagnosticOutputEl.appendChild(entry);
    diagnosticOutputEl.scrollTop = diagnosticOutputEl.scrollHeight;
}

async function testLmConnection() {
    addDiagnosticOutput('Testing LM Studio connection...');
    try {
        const hostname = document.getElementById('debugLmHost')?.value || 'localhost';
        const port = parseInt(document.getElementById('debugLmPort')?.value) || 1234;
        
        const response = await fetch('/api/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hostname, port })
        });
        const data = await response.json();
        
        if (data.success) {
            addDiagnosticOutput(`✅ Connected: ${data.model}`, 'success');
        } else {
            addDiagnosticOutput(`❌ Failed: ${data.message}`, 'error');
        }
    } catch (e) {
        addDiagnosticOutput(`❌ Error: ${e.message}`, 'error');
    }
}

async function testDiscordConnection() {
    addDiagnosticOutput('Testing Discord connection...');
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.discord_connected) {
            addDiagnosticOutput(`✅ Discord bot is connected as ${data.discord_bot_user || 'unknown'}`, 'success');
        } else {
            addDiagnosticOutput('❌ Discord bot is not connected (please connect via main page first)', 'error');
        }
    } catch (e) {
        addDiagnosticOutput(`❌ Error: ${e.message}`, 'error');
    }
}

async function forceDisconnectDiscord() {
    if (!confirm('Are you sure you want to disconnect the Discord bot?')) return;
    
    addDiagnosticOutput('Forcing Discord disconnect...');
    try {
        const response = await fetch('/api/discord/disconnect', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            addDiagnosticOutput('✅ Discord bot disconnected', 'success');
            await checkStatus();
        } else {
            addDiagnosticOutput(`❌ Failed: ${data.message}`, 'error');
        }
    } catch (e) {
        addDiagnosticOutput(`❌ Error: ${e.message}`, 'error');
    }
}

async function forceResetDiscord() {
    if (!confirm('⚠️ Force reset all Discord state? This will disconnect the bot and clear all tracking state. Use this if the bot is stuck.')) return;
    
    addDiagnosticOutput('🔥 Force resetting Discord state...', 'warning');
    try {
        const response = await fetch('/api/discord/force_reset', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            addDiagnosticOutput('✅ Discord state force reset successful!', 'success');
            // Force immediate status refresh to reflect reset state
            await checkStatus();
        } else {
            addDiagnosticOutput(`❌ Failed: ${data.message}`, 'error');
        }
    } catch (e) {
        addDiagnosticOutput(`❌ Error: ${e.message}`, 'error');
    }
}

async function clearAllSessions() {
    if (!confirm('Are you sure you want to clear ALL sessions?')) return;
    
    addDiagnosticOutput('Clearing all sessions...');
    try {
        const response = await fetch('/api/discord/clear_all_sessions', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            addDiagnosticOutput(`✅ All sessions cleared: ${data.cleared_count} sessions removed`, 'success');
            await fetchSessionInfo();
        } else {
            addDiagnosticOutput(`❌ Failed: ${data.message}`, 'error');
        }
    } catch (e) {
        addDiagnosticOutput(`❌ Error: ${e.message}`, 'error');
    }
}

// ==================== Debug Logs ====================

async function fetchDebugLogs() {
    try {
        const levelParam = debugState.currentLogLevelFilter !== 'ALL' ? `&level=${debugState.currentLogLevelFilter}` : '';
        const url = `/api/logs?limit=200${levelParam}`;
        
        console.log('[DebugPanel] Fetching logs from:', url);
        
        const response = await fetch(url);
        debugState.lastLogApiResponse = await response.json();
        
        console.log('[DebugPanel] Logs API response:', debugState.lastLogApiResponse);
        
        if (!response.ok) {
            console.error('[DebugPanel] Logs API HTTP error:', response.status);
            return;
        }
        
        if (debugState.lastLogApiResponse.success) {
            console.log(`[DebugPanel] Received ${debugState.lastLogApiResponse.total} logs, lastLogCount was ${debugState.lastLogCount}`);
            
            // Manually update the debug log display to ensure it works on this page
            if (typeof updateDebugLogDisplay === 'function') {
                updateDebugLogDisplay(debugState.lastLogApiResponse.logs);
                console.log('[DebugPanel] updateDebugLogDisplay called successfully');
            } else {
                console.error('[DebugPanel] updateDebugLogDisplay function not found!');
            }
            
            // Also update stats if the function exists
            if (typeof updateLogStats === 'function' && debugState.lastLogApiResponse.stats) {
                updateLogStats(debugState.lastLogApiResponse.stats);
            }
        } else {
            console.error('[DebugPanel] Logs API returned success=false:', debugState.lastLogApiResponse.error);
        }
    } catch (e) {
        console.error('[DebugPanel] Failed to fetch debug logs:', e);
    }
}

async function clearDebugLogs() {
    try {
        await fetch('/api/logs/clear', { method: 'POST' });
        debugState.lastLogCount = 0;
        const debugLogContainer = document.getElementById('debugLogContainer');
        if (debugLogContainer) debugLogContainer.innerHTML = '';
        addDiagnosticOutput('Debug logs cleared', 'success');
    } catch (e) {
        addDiagnosticOutput(`Error clearing logs: ${e.message}`, 'error');
    }
}

function onDebugLogLevelFilterChange() {
    const filterEl = document.getElementById('logLevelFilter');
    debugState.currentLogLevelFilter = filterEl?.value || 'ALL';
    debugState.lastLogCount = 0;
    fetchDebugLogs();
}

// ==================== Log Level Settings ====================

async function loadLogLevel() {
    try {
        const response = await fetch('/api/settings/log_level');
        const data = await response.json();
        if (data.success) {
            const select = document.getElementById('debugLogLevel');
            if (select) {
                select.value = data.log_level;
            }
        }
    } catch (e) {
        console.error('Failed to load log level:', e);
    }
}

async function updateLogLevel(level) {
    try {
        const response = await fetch('/api/settings/log_level', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ log_level: level })
        });
        const data = await response.json();
        
        if (data.success) {
            addDiagnosticOutput(`Log level set to: ${level}`, 'success');
            // Refresh logs to apply new filter
            debugState.lastLogCount = 0;
            fetchDebugLogs();
        } else {
            addDiagnosticOutput(`Error setting log level: ${data.error}`, 'error');
        }
    } catch (e) {
        addDiagnosticOutput(`Error: ${e.message}`, 'error');
    }
}


// ==================== Settings Override ====================

async function saveSettingOverride(settingName, value) {
    const endpoint = `/api/settings/${settingName}`;
    
    let body = {};
    if (settingName === 'temperature') {
        body = { temperature: parseFloat(value) };
    } else if (settingName === 'max_tokens') {
        body = { max_tokens: parseInt(value) };
    } else if (settingName === 'max_response_length') {
        body = { max_response_length: parseInt(value) };
    } else if (settingName === 'message_delay') {
        body = { message_delay: parseInt(value) };
    } else if (settingName === 'system_prompt') {
        body = { system_prompt: value };
    }
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await response.json();
        
        if (data.success) {
            addDiagnosticOutput(`Setting "${settingName}" updated to: ${value}`, 'success');
        } else {
            addDiagnosticOutput(`Error updating "${settingName}": ${data.error}`, 'error');
        }
    } catch (e) {
        addDiagnosticOutput(`Error: ${e.message}`, 'error');
    }
}

// ==================== Token Refresh ====================

async function refreshDebugTokens() {
    try {
        const response = await fetch('/api/tokens/debug/refresh');
        const data = await response.json();
        
        if (data.success && data.usage) {
            const promptEl = document.getElementById('debugPromptTokens');
            const completionEl = document.getElementById('debugCompletionTokens');
            const totalEl = document.getElementById('debugTotalTokens');
            
            if (promptEl) promptEl.textContent = data.usage.prompt_tokens?.toLocaleString() || '-';
            if (completionEl) completionEl.textContent = data.usage.completion_tokens?.toLocaleString() || '-';
            if (totalEl) totalEl.textContent = data.usage.total_tokens?.toLocaleString() || '-';
            
            addDiagnosticOutput(`Tokens refreshed: ${data.usage.total_tokens} total`, 'success');
        } else {
            addDiagnosticOutput('No token data available', 'info');
        }
    } catch (e) {
        addDiagnosticOutput(`Error: ${e.message}`, 'error');
    }
}

// ==================== Test Log Display ====================

async function testLogDisplay() {
    console.log('[DebugPanel] Testing log display...');
    
    // Push a test log entry server-side to verify the pipeline works
    try {
        const response = await fetch('/api/logs', { method: 'GET' });
        const data = await response.json();
        
        if (data.success) {
            console.log(`[DebugPanel] Current log count: ${data.total}`);
            
            if (data.total === 0) {
                // No logs exist - push a test entry
                console.log('[DebugPanel] No logs found, pushing test entry...');
                // We'll use the diagnostics output to show status
                addDiagnosticOutput('🔧 Debug panel initialized. Logs will appear here when the application generates them.', 'info');
                addDiagnosticOutput(`📊 Log API returned ${data.total} entries. If logs don't appear, check the server-side logger.`, 'info');
            } else {
                addDiagnosticOutput(`🔧 Debug panel initialized. Found ${data.total} existing log entries.`, 'success');
            }
        }
    } catch (e) {
        console.error('[DebugPanel] Test log display failed:', e);
        addDiagnosticOutput(`❌ Failed to connect to log API: ${e.message}`, 'error');
    }
}

// ==================== Close Button ====================

// ==================== Module Filter ====================

async function loadModuleFilter() {
    try {
        const response = await fetch('/api/settings/module_filter');
        const data = await response.json();
        if (data.success) {
            const textarea = document.getElementById('moduleFilterInput');
            if (textarea) {
                textarea.value = data.modules.join(', ');
            }
        }
    } catch (e) {
        console.error('Failed to load module filter:', e);
    }
}

async function saveModuleFilter() {
    const textarea = document.getElementById('moduleFilterInput');
    const raw = textarea?.value?.trim() || '';
    
    let modules = [];
    if (raw) {
        modules = raw.split(',').map(m => m.trim()).filter(m => m.length > 0);
    }
    
    try {
        const response = await fetch('/api/settings/module_filter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ modules })
        });
        const data = await response.json();
        
        const statusEl = document.getElementById('moduleFilterStatus');
        if (statusEl) {
            if (data.success) {
                statusEl.style.color = '#a6e3a1';
                statusEl.textContent = `✅ Module filter saved: ${modules.length} module(s) filtered`;
                setTimeout(() => { statusEl.style.color = '#a6adc8'; }, 3000);
            } else {
                statusEl.style.color = '#f38ba8';
                statusEl.textContent = `❌ Error: ${data.error}`;
                setTimeout(() => { statusEl.style.color = '#a6adc8'; }, 5000);
            }
        }
    } catch (e) {
        const statusEl = document.getElementById('moduleFilterStatus');
        if (statusEl) {
            statusEl.style.color = '#f38ba8';
            statusEl.textContent = `❌ Error: ${e.message}`;
            setTimeout(() => { statusEl.style.color = '#a6adc8'; }, 5000);
        }
    }
}

async function resetModuleFilter() {
    // Reset to default filtered modules
    const defaults = ['typing_indicator', 'token_tracker'];
    const textarea = document.getElementById('moduleFilterInput');
    if (textarea) {
        textarea.value = defaults.join(', ');
    }
    await saveModuleFilter();
}

function closeDebugPanel() {
    // Since debug page is now a full-page tab, just inform the user
    // They can close the tab manually or navigate back to main page
    window.close();
    // Fallback if window.close() is blocked by browser
    if (!window.closed) {
        document.body.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100vh;color:#cdd6f4;font-family:sans-serif;"><p>Debug panel closed. You may close this tab.</p></div>';
    }
}
