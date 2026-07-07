// ==================== Shared Utility Functions ====================
// Used by both script.js and debug_script.js

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function addMessage(text, type) {
    const chatContainer = document.getElementById('chatContainer');
    if (!chatContainer) return;
    
    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.textContent = text;
    chatContainer.appendChild(div);
    scrollToBottom();
}

function scrollToBottom() {
    const chatContainer = document.getElementById('chatContainer');
    if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
}

function setLMStatus(status) {
    const lmStatusDot = document.getElementById('lmStatusDot');
    const lmStatusText = document.getElementById('lmStatusText');
    if (!lmStatusDot || !lmStatusText) return;
    
    lmStatusDot.className = 'status-dot';
    switch (status) {
        case 'connected':
            lmStatusDot.classList.add('connected');
            lmStatusText.textContent = 'Connected';
            break;
        case 'error':
            lmStatusDot.classList.add('error');
            lmStatusText.textContent = 'Connection Failed';
            break;
        case 'connecting':
            lmStatusText.textContent = 'Connecting...';
            break;
        default:
            lmStatusText.textContent = 'Disconnected';
    }
}

function setDiscordStatus(status) {
    const discordStatusDot = document.getElementById('discordStatusDot');
    const discordStatusText = document.getElementById('discordStatusText');
    if (!discordStatusDot || !discordStatusText) return;
    
    discordStatusDot.className = 'status-dot';
    switch (status) {
        case 'connected':
            discordStatusDot.classList.add('connected');
            discordStatusText.textContent = 'Connected';
            break;
        case 'error':
            discordStatusDot.classList.add('error');
            discordStatusText.textContent = 'Connection Failed';
            break;
        case 'connecting':
            discordStatusText.textContent = 'Connecting...';
            break;
        case 'disconnected':
            discordStatusText.textContent = 'Not connected';
            break;
        default:
            discordStatusText.textContent = 'Not connected';
    }
}

function updateModelInfo(lmModel, lmModels, state) {
    const modelInfo = document.getElementById('modelInfo');
    if (!modelInfo) return;
    
    let text = '';
    const isConnected = state?.lmConnected || false;
    
    if (lmModel || isConnected) {
        text += lmModel ? `LM: ${lmModel}` : 'LM: Connected';
        text += lmModels ? ` (${lmModels.length} models)` : '';
    }
    
    if (text && state?.discordConnected) {
        text += ' | ';
    }
    
    if (state?.discordConnected) {
        text += 'Discord: Bot Online';
    } else if (state?.discordConnected === false || state?.discordConnected === undefined) {
        text += 'Discord: Not connected';
    }
    
    modelInfo.textContent = text || 'Not connected';
    
    // Update integration note if exists
    const note = document.getElementById('discordIntegrationNote');
    if (note) {
        if (isConnected) {
            note.style.color = '#a6e3a1';
            note.textContent = '✅ LM Studio connected - AI responses enabled';
        } else {
            note.style.color = '#f38ba8';
            note.textContent = '⚠️ Connect LM Studio first for AI responses';
        }
    }
}

function createLogElement(log) {
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const levelClass = log.level.toLowerCase();
    
    entry.innerHTML = `
        <span class="log-time">${log.timestamp_formatted}</span>
        <span class="log-level" style="color: ${log.level_color}">${log.level_icon} ${log.level}</span>
        <span class="log-module">${log.module || 'App'}</span>
        <span class="log-message ${levelClass}">${escapeHtml(log.message)}</span>
    `;
    
    return entry;
}

function getLogLevelColor(level) {
    const colors = {
        'DEBUG': '#89b4fa',
        'INFO': '#a6e3a1',
        'WARNING': '#f9e2af',
        'ERROR': '#f38ba8',
        'CRITICAL': '#eba0ac'
    };
    return colors[level] || '#cdd6f4';
}

function updateLogStats(stats) {
    if (!stats) return;
    
    const infoCount = stats.INFO || 0;
    const warnCount = (stats.WARNING || 0) + (stats.CRITICAL || 0);
    const errorCount = (stats.ERROR || 0);
    const total = stats.total || 0;
    
    const infoEl = document.getElementById('infoCount');
    const warnEl = document.getElementById('warnCount');
    const errorEl = document.getElementById('errorCount');
    const totalEl = document.getElementById('totalLogCount');
    
    if (infoEl) infoEl.textContent = infoCount;
    if (warnEl) warnEl.textContent = warnCount;
    if (errorEl) errorEl.textContent = errorCount;
    if (totalEl) totalEl.textContent = `Total: ${total}`;
}