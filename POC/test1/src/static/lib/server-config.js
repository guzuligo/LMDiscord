// ==================== Server Configuration Module (FEAT-001 + UX-001 + FEAT-002) ====================
// Self-contained server configuration management with auto-discovery and channel search/filter

// ==================== Channel Search/Filter (FEAT-002) ====================

/**
 * Filter channel list items based on search term.
 * Matches against channel name, ID, and category.
 */
function filterChannelList(listType) {
    const searchId = listType === 'allowed' ? 'allowedChannelSearch' : 'deniedChannelSearch';
    const listId = listType === 'allowed' ? 'allowedChannelList' : 'deniedChannelList';
    const searchRowId = listType === 'allowed' ? 'allowedChannelSearchRow' : 'deniedChannelSearchRow';
    
    const searchTerm = document.getElementById(searchId).value.toLowerCase().trim();
    const container = document.getElementById(listId);
    const searchRow = document.getElementById(searchRowId);
    
    if (!container || !searchRow) return;
    
    // Show search row only when channels are discovered
    searchRow.style.display = serverConfigState.currentChannels.length > 0 ? 'block' : 'none';
    
    if (!searchTerm) {
        // No filter - show all items
        container.querySelectorAll('.channel-list-item').forEach(item => {
            item.classList.remove('hidden');
        });
        return;
    }
    
    // Filter channel items by name, category, or ID
    container.querySelectorAll('.channel-list-item').forEach(item => {
        const channelName = (item.querySelector('[data-channel-name]')?.dataset.channelName || '').toLowerCase();
        const channelId = (item.querySelector('[data-channel-id]')?.dataset.channelId || '').toLowerCase();
        const category = (item.querySelector('[data-channel-category]')?.dataset.channelCategory || '').toLowerCase();
        const displayText = (item.querySelector('.channel-id-text')?.textContent || '').toLowerCase();
        
        const matches = channelName.includes(searchTerm) || 
                       channelId.includes(searchTerm) || 
                       category.includes(searchTerm) ||
                       displayText.includes(searchTerm);
        
        item.classList.toggle('hidden', !matches);
    });
}


const serverConfigState = {
    currentServerId: null,
    currentAllowedChannels: [],
    currentDeniedChannels: [],
    allServers: {},
    discordServers: [],    // Auto-discovered Discord servers (UX-001)
    currentChannels: []    // Auto-discovered channels for current server (UX-001)
};

// ==================== Load Initial Data ====================

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

// ==================== Auto-Discover Discord Servers (UX-001) ====================

async function loadDiscordServers() {
    try {
        addMessage('🔍 Loading Discord servers...', 'system');
        const response = await fetch('/api/discord/servers');
        const data = await response.json();
        
        if (data.success) {
            serverConfigState.discordServers = data.servers || [];
            renderDiscordServerPicker();
            addMessage(`✅ Found ${serverConfigState.discordServers.length} Discord server(s)`, 'system');
        } else {
            addMessage(`❌ Failed to load servers: ${data.message}`, 'error');
        }
    } catch (e) {
        addMessage(`❌ Error loading servers: ${e.message}`, 'error');
        console.error('Failed to load Discord servers:', e);
    }
}

function renderDiscordServerPicker() {
    let picker = document.getElementById('discordServerPicker');
    if (!picker) {
        // Create picker container if it doesn't exist
        picker = document.createElement('div');
        picker.id = 'discordServerPicker';
        picker.className = 'discord-server-picker';
        
        const header = document.querySelector('.server-config-header');
        if (header) {
            header.after(document.createElement('br'));
            header.after(picker);
        }
    }
    
    if (serverConfigState.discordServers.length === 0) {
        picker.innerHTML = '<p style="color: #6c7086; font-size: 12px;">No Discord servers found. Make sure the bot is connected to servers.</p>';
        return;
    }
    
    picker.innerHTML = `
        <div style="margin: 10px 0; padding: 10px; background: #1e1e2e; border-radius: 6px;">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <label style="font-size: 12px; color: #cdd6f4;">📡 Quick Add Server:</label>
                <select id="discordServerSelect" style="flex: 1; min-width: 200px; padding: 4px 8px; background: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px;">
                    ${serverConfigState.discordServers.map(s => 
                        `<option value="${s.id}">${s.name} (${s.id}) - ${s.member_count || '?'} members</option>`
                    ).join('')}
                </select>
                <button class="btn btn-primary btn-small" onclick="quickAddServer()">➕ Add to Config</button>
            </div>
        </div>
    `;
}

async function quickAddServer() {
    const select = document.getElementById('discordServerSelect');
    if (!select) {
        addMessage('⚠️ No servers available to add', 'error');
        return;
    }
    
    const serverId = select.value;
    if (!serverId) {
        addMessage('⚠️ Please select a server', 'error');
        return;
    }
    
    // Check if already in config
    if (serverConfigState.allServers[serverId]) {
        // If already exists, just edit it
        editServer(serverId);
        return;
    }
    
    // Add new server to config with default settings
    const serverName = serverConfigState.discordServers.find(s => s.id == serverId)?.name || 'Unknown';
    const config = {
        enabled: true,
        allowed_channels: [],
        denied_channels: []
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
            renderServerList();
            editServer(serverId); // Open edit form for the newly added server
            addMessage(`✅ Added server "${serverName}" (${serverId}) to configuration`, 'system');
        } else {
            addMessage(`Failed to add server: ${data.error}`, 'error');
        }
    } catch (e) {
        addMessage(`Error adding server: ${e.message}`, 'error');
    }
}

// ==================== Load Channels for Server (UX-001) ====================

async function loadDiscordChannels(guildId) {
    try {
        addMessage(`🔍 Loading channels for server ${guildId}...`, 'system');
        const response = await fetch(`/api/discord/channels/${guildId}`);
        const data = await response.json();
        
        if (data.success) {
            serverConfigState.currentChannels = data.channels || [];
            renderChannelPicker();
            
            // FEAT-002: Show search rows when channels are loaded
            const allowedSearchRow = document.getElementById('allowedChannelSearchRow');
            const deniedSearchRow = document.getElementById('deniedChannelSearchRow');
            if (allowedSearchRow) allowedSearchRow.style.display = serverConfigState.currentChannels.length > 0 ? 'block' : 'none';
            if (deniedSearchRow) deniedSearchRow.style.display = serverConfigState.currentChannels.length > 0 ? 'block' : 'none';
            
            addMessage(`✅ Found ${serverConfigState.currentChannels.length} text channel(s)`, 'system');
        } else {
            addMessage(`❌ Failed to load channels: ${data.message}`, 'error');
        }
    } catch (e) {
        addMessage(`❌ Error loading channels: ${e.message}`, 'error');
        console.error('Failed to load Discord channels:', e);
    }
}

function renderChannelPicker() {
    // Add channel picker to both allowed and denied channel sections
    renderChannelPickerFor('allowed');
    renderChannelPickerFor('denied');
}

function renderChannelPickerFor(listType) {
    let pickerId = listType === 'allowed' ? 'allowedChannelPicker' : 'deniedChannelPicker';
    let addButtonId = listType === 'allowed' ? 'allowedChannelAddBtn' : 'deniedChannelAddBtn';
    
    let picker = document.getElementById(pickerId);
    if (!picker) {
        picker = document.createElement('div');
        picker.id = pickerId;
        picker.className = 'channel-picker';
        
        // Find the channel section and insert picker before the input row
        const channelSections = document.querySelectorAll('.server-channels-section');
        let targetSection = null;
        for (let section of channelSections) {
            const h5 = section.querySelector('h5');
            if (h5) {
                const isDenied = h5.textContent.includes('Denied');
                const isAllowed = !isDenied && h5.textContent.includes('Allowed');
                if ((listType === 'allowed' && isAllowed) || (listType === 'denied' && isDenied)) {
                    targetSection = section;
                    break;
                }
            }
        }
        
        if (targetSection) {
            const inputRowEl = targetSection.querySelector('.channel-input-row');
            if (inputRowEl) {
                targetSection.insertBefore(picker, inputRowEl);
            }
        }
    }
    
    // Always render the picker content (even when empty, so it exists for later population)
    if (serverConfigState.currentChannels.length === 0) {
        picker.innerHTML = `
            <div style="margin: 5px 0; padding: 6px; background: #1e1e2e; border-radius: 4px;">
                <div style="display: flex; align-items: center; gap: 6px;">
                    <label style="font-size: 11px; color: #6c7086;">🔍 Click "Load Channels" above to discover channels</label>
                </div>
            </div>
        `;
        return;
    }
    
    picker.innerHTML = `
        <div style="margin: 5px 0; padding: 6px; background: #1e1e2e; border-radius: 4px;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <label style="font-size: 11px; color: #6c7086;">Select:</label>
                <select id="discordChannelSelect" style="flex: 1; min-width: 180px; padding: 3px 6px; background: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; font-size: 11px;">
                    ${serverConfigState.currentChannels.map(c => 
                        `<option value="${c.id}"># ${c.name} ${c.category !== 'Uncategorized' ? `(${c.category})` : ''}</option>`
                    ).join('')}
                </select>
                <button class="btn btn-secondary btn-small" id="${addButtonId}" onclick="quickAddChannel('${listType}')">➕</button>
            </div>
        </div>
    `;
}

async function quickAddChannel(listType) {
    const select = document.getElementById('discordChannelSelect');
    if (!select) return;
    
    const channelId = select.value;
    if (!channelId) {
        addMessage('⚠️ Please select a channel', 'error');
        return;
    }
    
    // Add to current state
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
    
    addMessage(`✅ Added channel ${channelId} to ${listType} list`, 'system');
}

// ==================== Server List Rendering ====================

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
        
        // Try to get server name from discordServers
        const discordServer = serverConfigState.discordServers.find(s => s.id == serverId);
        const displayName = discordServer ? `${discordServer.name} (${serverId})` : `Server: ${serverId}`;
        
        item.innerHTML = `
            <div class="server-list-info">
                <div class="server-list-name">${displayName}</div>
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

// ==================== Edit Server ====================

async function editServer(serverId) {
    const server = serverConfigState.allServers[serverId];
    if (!server) return;
    
    serverConfigState.currentServerId = serverId;
    serverConfigState.currentAllowedChannels = [...(server.allowed_channels || [])];
    serverConfigState.currentDeniedChannels = [...(server.denied_channels || [])];
    serverConfigState.currentChannels = []; // Reset channel discovery
    
    document.getElementById('serverIdInput').value = serverId;
    document.getElementById('serverNameInput').value = serverId;
    document.getElementById('serverEnabledCheckbox').checked = server.enabled;
    document.getElementById('serverFormTitle').textContent = '✏️ Edit Server';
    
    document.getElementById('cancelServerBtn').style.display = 'inline-block';
    document.getElementById('deleteServerBtn').style.display = 'inline-block';
    
    const channelMode = server.allowed_channels && server.allowed_channels.length > 0 ? 'specific' : 'all';
    const channelModeRadio = document.querySelector(`input[name="channelMode"][value="${channelMode}"]`);
    if (channelModeRadio) channelModeRadio.checked = true;
    
    renderChannelList('allowedChannelList', serverConfigState.currentAllowedChannels);
    renderChannelList('deniedChannelList', serverConfigState.currentDeniedChannels);
    
    // Clear channel pickers
    const allowedPicker = document.getElementById('allowedChannelPicker');
    const deniedPicker = document.getElementById('deniedChannelPicker');
    if (allowedPicker) allowedPicker.innerHTML = '';
    if (deniedPicker) deniedPicker.innerHTML = '';
    
    document.querySelectorAll('.server-list-item').forEach(el => {
        el.classList.toggle('active', el.dataset.serverId === serverId);
    });
    
    // Add load channels button if we have discord servers data
    if (serverConfigState.discordServers.length > 0 || serverId) {
        addLoadChannelsButton(serverId);
    }
}

function addLoadChannelsButton(serverId) {
    // Ensure currentServerId is set before creating the button
    if (serverId && !serverConfigState.currentServerId) {
        serverConfigState.currentServerId = serverId;
    }
    
    let loadBtn = document.getElementById('loadChannelsBtn');
    if (!loadBtn) {
        loadBtn = document.createElement('button');
        loadBtn.id = 'loadChannelsBtn';
        loadBtn.className = 'btn btn-secondary btn-small';
        loadBtn.style.marginTop = '8px';
        loadBtn.style.marginBottom = '8px';
        loadBtn.textContent = '🔍 Load Channels from Discord';
        // Use a closure that captures the serverId parameter
        loadBtn.onclick = () => loadDiscordChannels(serverId);
        
        // Add after the form title (h4) for visibility
        const formTitle = document.getElementById('serverFormTitle');
        if (formTitle) {
            formTitle.after(document.createElement('br'));
            formTitle.after(loadBtn);
        }
    } else {
        // Update onclick to use the current serverId
        loadBtn.onclick = () => loadDiscordChannels(serverId);
    }
    loadBtn.style.display = 'inline-block';
    loadBtn.disabled = false;
    loadBtn.title = 'Load text channels from this Discord server';
}

// ==================== Save Server Config ====================

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

// ==================== Cancel / Reset ====================

function cancelServerEdit() {
    resetServerForm();
    renderServerList();
}

function resetServerForm() {
    serverConfigState.currentServerId = null;
    serverConfigState.currentAllowedChannels = [];
    serverConfigState.currentDeniedChannels = [];
    serverConfigState.currentChannels = [];
    
    document.getElementById('serverIdInput').value = '';
    document.getElementById('serverNameInput').value = '';
    document.getElementById('serverEnabledCheckbox').checked = true;
    document.getElementById('serverFormTitle').textContent = '➕ Add New Server';
    document.getElementById('cancelServerBtn').style.display = 'none';
    document.getElementById('deleteServerBtn').style.display = 'none';
    const loadBtn = document.getElementById('loadChannelsBtn');
    if (loadBtn) loadBtn.style.display = 'none';
    const allRadio = document.querySelector('input[name="channelMode"][value="all"]');
    if (allRadio) allRadio.checked = true;
    
    renderChannelList('allowedChannelList', []);
    renderChannelList('deniedChannelList', []);
    
    // Clear pickers
    const allowedPicker = document.getElementById('allowedChannelPicker');
    const deniedPicker = document.getElementById('deniedChannelPicker');
    if (allowedPicker) allowedPicker.innerHTML = '';
    if (deniedPicker) deniedPicker.innerHTML = '';
}

// ==================== Channel List Rendering ====================

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
        
        // Try to get channel name from discovered channels
        const discordChannel = serverConfigState.currentChannels.find(c => c.id === channelId);
        const displayName = discordChannel ? `# ${discordChannel.name}` : channelId;
        
        item.innerHTML = `
            <span class="channel-id-text" 
                  data-channel-name="${discordChannel?.name || ''}" 
                  data-channel-category="${discordChannel?.category || ''}" 
                  data-channel-id="${channelId}">
                ${displayName}
            </span>
            <button class="channel-remove-btn" onclick="removeChannelFromServer('${listType}', '${channelId}')">✕</button>
        `;
        container.appendChild(item);
    });
}

// ==================== Manual Channel Add/Remove ====================

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

// ==================== Delete Server ====================

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