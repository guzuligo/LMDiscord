// ==================== Server Configuration Module (FEAT-001) ====================
// Self-contained server configuration management

const serverConfigState = {
    currentServerId: null,
    currentAllowedChannels: [],
    currentDeniedChannels: [],
    allServers: {}
};

async function loadServerConfig() {
    try {
        const response = await fetch('/api/servers');
        const data = await response.json();
        if (data.success) {
            serverConfigState.allServers = data.servers || {};
            renderServerList();
        }
    } catch (e) {
        console.error('Failed to load server config:', e);
    }
}

function renderServerList() {
    const container = document.getElementById('serverListContainer');
    const placeholder = document.getElementById('serverListPlaceholder');
    const servers = serverConfigState.allServers;
    const serverIds = Object.keys(servers);
    
    if (serverIds.length === 0) {
        if (placeholder) placeholder.style.display = 'block';
        container?.querySelectorAll('.server-list-item').forEach(el => el.remove());
        return;
    }
    
    if (placeholder) placeholder.style.display = 'none';
    container?.querySelectorAll('.server-list-item').forEach(el => el.remove());
    
    serverIds.forEach(serverId => {
        const server = servers[serverId];
        const item = document.createElement('div');
        item.className = 'server-list-item';
        item.dataset.serverId = serverId;
        if (serverConfigState.currentServerId === serverId) {
            item.classList.add('active');
        }
        
        item.innerHTML = `
            <div class="server-list-info">
                <div class="server-list-name">Server: ${serverId}</div>
                <div class="server-list-id">
                    Allowed: ${server.allowed_channels?.length || 0} | 
                    Denied: ${server.denied_channels?.length || 0}
                </div>
            </div>
            <div class="server-list-status">
                <span class="server-status-badge ${server.enabled ? 'enabled' : 'disabled'}">
                    ${server.enabled ? 'Enabled' : 'Disabled'}
                </span>
                <div class="server-list-actions">
                    <button class="btn btn-secondary btn-small" onclick="editServer('${serverId}')">✏️</button>
                    <button class="btn btn-danger btn-small" onclick="quickRemoveServer('${serverId}')">🗑️</button>
                </div>
            </div>
        `;
        
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.server-list-actions') && !e.target.closest('button')) {
                editServer(serverId);
            }
        });
        
        container.appendChild(item);
    });
}

async function editServer(serverId) {
    const server = serverConfigState.allServers[serverId];
    if (!server) return;
    
    serverConfigState.currentServerId = serverId;
    serverConfigState.currentAllowedChannels = [...(server.allowed_channels || [])];
    serverConfigState.currentDeniedChannels = [...(server.denied_channels || [])];
    
    document.getElementById('serverIdInput').value = serverId;
    document.getElementById('serverNameInput').value = `Server: ${serverId}`;
    document.getElementById('serverEnabledCheckbox').checked = server.enabled;
    document.getElementById('serverFormTitle').textContent = '✏️ Edit Server';
    
    document.getElementById('cancelServerBtn').style.display = 'inline-block';
    document.getElementById('deleteServerBtn').style.display = 'inline-block';
    
    const channelMode = server.allowed_channels && server.allowed_channels.length > 0 ? 'specific' : 'all';
    const channelModeRadio = document.querySelector(`input[name="channelMode"][value="${channelMode}"]`);
    if (channelModeRadio) channelModeRadio.checked = true;
    
    renderChannelList('allowedChannelList', serverConfigState.currentAllowedChannels);
    renderChannelList('deniedChannelList', serverConfigState.currentDeniedChannels);
    
    document.querySelectorAll('.server-list-item').forEach(el => {
        el.classList.toggle('active', el.dataset.serverId === serverId);
    });
}

async function saveServerConfig() {
    const serverId = document.getElementById('serverIdInput').value.trim();
    
    if (!serverId) {
        addMessage('⚠️ Please enter a Server ID', 'error');
        return;
    }
    
    const enabled = document.getElementById('serverEnabledCheckbox').checked;
    const channelMode = document.querySelector('input[name="channelMode"]:checked').value;
    
    let allowedChannels = [];
    if (channelMode === 'specific') {
        allowedChannels = [...serverConfigState.currentAllowedChannels];
    }
    
    const config = {
        enabled: enabled,
        allowed_channels: allowedChannels,
        denied_channels: [...serverConfigState.currentDeniedChannels]
    };
    
    try {
        const response = await fetch('/api/servers/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ server_id: serverId, config })
        });
        
        const data = await response.json();
        if (data.success) {
            serverConfigState.allServers[serverId] = config;
            serverConfigState.currentServerId = serverId;
            renderServerList();
            addMessage(`✅ Server ${serverId} configuration saved`, 'system');
        } else {
            addMessage(`Failed to save server config: ${data.error}`, 'error');
        }
    } catch (e) {
        addMessage(`Error saving server config: ${e.message}`, 'error');
    }
}

function cancelServerEdit() {
    resetServerForm();
    renderServerList();
}

function resetServerForm() {
    serverConfigState.currentServerId = null;
    serverConfigState.currentAllowedChannels = [];
    serverConfigState.currentDeniedChannels = [];
    
    document.getElementById('serverIdInput').value = '';
    document.getElementById('serverNameInput').value = '';
    document.getElementById('serverEnabledCheckbox').checked = true;
    document.getElementById('serverFormTitle').textContent = '➕ Add New Server';
    document.getElementById('cancelServerBtn').style.display = 'none';
    document.getElementById('deleteServerBtn').style.display = 'none';
    const allRadio = document.querySelector('input[name="channelMode"][value="all"]');
    if (allRadio) allRadio.checked = true;
    
    renderChannelList('allowedChannelList', []);
    renderChannelList('deniedChannelList', []);
}

function renderChannelList(containerId, channels) {
    const container = document.getElementById(containerId);
    
    if (!channels || channels.length === 0) {
        const placeholderText = containerId === 'allowedChannelList' 
            ? 'No allowed channels configured' 
            : 'No denied channels configured';
        container.innerHTML = `<div class="channel-list-placeholder">${placeholderText}</div>`;
        return;
    }
    
    container.innerHTML = '';
    channels.forEach((channelId) => {
        const item = document.createElement('div');
        item.className = 'channel-list-item';
        const listType = containerId === 'allowedChannelList' ? 'allowed' : 'denied';
        item.innerHTML = `
            <span class="channel-id-text">${channelId}</span>
            <button class="channel-remove-btn" onclick="removeChannelFromServer('${listType}', '${channelId}')">✕</button>
        `;
        container.appendChild(item);
    });
}

async function addChannelToServer(listType) {
    const inputId = listType === 'allowed' ? 'allowedChannelInput' : 'deniedChannelInput';
    const channelId = document.getElementById(inputId).value.trim();
    
    if (!channelId) {
        addMessage('⚠️ Please enter a Channel ID', 'error');
        return;
    }
    
    if (listType === 'allowed') {
        if (!serverConfigState.currentAllowedChannels.includes(channelId)) {
            serverConfigState.currentAllowedChannels.push(channelId);
            renderChannelList('allowedChannelList', serverConfigState.currentAllowedChannels);
        }
    } else {
        if (!serverConfigState.currentDeniedChannels.includes(channelId)) {
            serverConfigState.currentDeniedChannels.push(channelId);
            renderChannelList('deniedChannelList', serverConfigState.currentDeniedChannels);
        }
    }
    
    document.getElementById(inputId).value = '';
}

async function removeChannelFromServer(listType, channelId) {
    if (listType === 'allowed') {
        serverConfigState.currentAllowedChannels = serverConfigState.currentAllowedChannels.filter(c => c !== channelId);
        renderChannelList('allowedChannelList', serverConfigState.currentAllowedChannels);
    } else {
        serverConfigState.currentDeniedChannels = serverConfigState.currentDeniedChannels.filter(c => c !== channelId);
        renderChannelList('deniedChannelList', serverConfigState.currentDeniedChannels);
    }
}

async function deleteCurrentServer() {
    const serverId = serverConfigState.currentServerId;
    if (!serverId) return;
    
    if (!confirm(`Delete server configuration for ${serverId}?`)) return;
    
    try {
        const response = await fetch('/api/servers/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ server_id: serverId })
        });
        
        const data = await response.json();
        if (data.success) {
            delete serverConfigState.allServers[serverId];
            resetServerForm();
            renderServerList();
            addMessage(`✅ Server ${serverId} removed from configuration`, 'system');
        } else {
            addMessage(`Failed to delete server: ${data.error}`, 'error');
        }
    } catch (e) {
        addMessage(`Error deleting server: ${e.message}`, 'error');
    }
}

async function quickRemoveServer(serverId) {
    if (!confirm(`Delete server configuration for ${serverId}?`)) return;
    
    try {
        const response = await fetch('/api/servers/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ server_id: serverId })
        });
        
        const data = await response.json();
        if (data.success) {
            delete serverConfigState.allServers[serverId];
            if (serverConfigState.currentServerId === serverId) {
                resetServerForm();
            }
            renderServerList();
            addMessage(`✅ Server ${serverId} removed from configuration`, 'system');
        } else {
            addMessage(`Failed to delete server: ${data.error}`, 'error');
        }
    } catch (e) {
        addMessage(`Error deleting server: ${e.message}`, 'error');
    }
}