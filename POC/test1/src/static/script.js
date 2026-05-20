// ==================== Main Page State ====================
const state = {
    lmConnected: false,
    discordConnected: false,
    statusPollInterval: null,
    logPollInterval: null,
    lastLogCount: 0,
    currentLogLevelFilter: 'ALL',
    newLogCount: 0,
    suppressWerkzeugLogging: false,
    messageDelay: 5,
    maxTokens: 2500,
    temperature: 0.7,
    maxResponseLength: 2000,
    // Token metrics state
    isStreaming: false,
    currentTokenStream: '',
    lastTokenUsage: null,
    // LM instance state
    currentLmHostname: 'localhost',
    currentLmPort: 1234
};

// ==================== DOM Elements ====================
const hostInput = document.getElementById('hostInput');
const portInput = document.getElementById('portInput');
const connectBtn = document.getElementById('connectBtn');
const discordTokenInput = document.getElementById('discordTokenInput');
const discordConnectBtn = document.getElementById('discordConnectBtn');
const discordDisconnectBtn = document.getElementById('discordDisconnectBtn');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');

// ==================== LM Studio Functions ====================

async function connectLM() {
    const hostname = hostInput.value.trim();
    const port = parseInt(portInput.value.trim());

    if (isNaN(port) || port < 1 || port > 65535) {
        addMessage('Error: Invalid port number', 'error');
        return;
    }

    connectBtn.disabled = true;
    connectBtn.textContent = 'Connecting...';
    setLMStatus('connecting');

    try {
        const response = await fetch('/api/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hostname, port })
        });

        const data = await response.json();

        if (data.success) {
            state.lmConnected = true;
            setLMStatus('connected');
            updateModelInfo(data.model, data.models, state);
            messageInput.disabled = false;
            sendBtn.disabled = false;
            messageInput.focus();
            addMessage(`✅ Connected to LM Studio at ${hostname}:${port}`, 'system');
        } else {
            setLMStatus('error');
            addMessage(data.message || 'Connection failed', 'error');
        }
    } catch (error) {
        setLMStatus('error');
        addMessage(`Connection error: ${error.message}`, 'error');
    } finally {
        connectBtn.disabled = false;
        connectBtn.textContent = 'Connect';
    }
}

// ==================== Chat Functions ====================

async function sendMessage() {
    sendStreamingMessage();
}

async function clearChat() {
    try {
        await fetch('/api/clear', { method: 'POST' });
        addMessage('Chat cleared.', 'system');
    } catch (e) {}
    const chatContainer = document.getElementById('chatContainer');
    if (chatContainer) chatContainer.innerHTML = '';
    addMessage('Chat cleared.', 'system');
}

// ==================== Discord Functions ====================

async function connectDiscord() {
    const token = discordTokenInput.value.trim();

    if (!state.lmConnected) {
        addMessage('⚠️ Please connect to LM Studio first before connecting the Discord bot for AI responses.', 'error');
        return;
    }

    discordConnectBtn.disabled = true;
    discordConnectBtn.textContent = 'Connecting...';
    setDiscordStatus('connecting');

    try {
        const body = {};
        if (token) {
            body.token = token;
        }

        const response = await fetch('/api/discord/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const data = await response.json();

        if (data.success) {
            addMessage(`🤖 Discord bot is starting with LM Studio AI integration...`, 'discord');
            if (state.statusPollInterval) clearInterval(state.statusPollInterval);
            state.statusPollInterval = setInterval(checkStatus, 2000);
            await checkStatus();
        } else {
            setDiscordStatus('error');
            addMessage(`❌ Discord connection failed: ${data.message}`, 'error');
        }
    } catch (error) {
        setDiscordStatus('error');
        addMessage(`Discord connection error: ${error.message}`, 'error');
    } finally {
        if (!state.discordConnected) {
            discordConnectBtn.disabled = false;
            discordConnectBtn.textContent = 'Connect';
        }
    }
}

async function disconnectDiscord() {
    try {
        const response = await fetch('/api/discord/disconnect', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            state.discordConnected = false;
            setDiscordStatus('disconnected');
            if (state.statusPollInterval) {
                clearInterval(state.statusPollInterval);
                state.statusPollInterval = null;
            }
            discordConnectBtn.disabled = false;
            discordConnectBtn.textContent = 'Connect';
            discordDisconnectBtn.disabled = true;
            updateModelInfo();
            addMessage(`🤖 Discord bot disconnected`, 'discord');
        } else {
            addMessage(`Disconnect failed: ${data.message}`, 'error');
        }
    } catch (error) {
        addMessage(`Disconnect error: ${error.message}`, 'error');
    }
}

async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        if (data.lm_connected !== undefined) {
            if (data.lm_connected && !state.lmConnected) {
                state.lmConnected = true;
                setLMStatus('connected');
                messageInput.disabled = false;
                sendBtn.disabled = false;
            } else if (!data.lm_connected && state.lmConnected) {
                state.lmConnected = false;
                setLMStatus('disconnected');
                messageInput.disabled = true;
                sendBtn.disabled = true;
            }
        }

        if (data.discord_connected !== undefined) {
            const wasConnected = state.discordConnected;
            state.discordConnected = data.discord_connected;

            if (data.discord_connected) {
                setDiscordStatus('connected');
                discordConnectBtn.disabled = true;
                discordDisconnectBtn.disabled = false;
                discordTokenInput.disabled = true;
            } else if (!data.discord_connected && wasConnected) {
                setDiscordStatus('disconnected');
                discordConnectBtn.disabled = false;
                discordConnectBtn.textContent = 'Connect';
                discordDisconnectBtn.disabled = true;
                discordTokenInput.disabled = false;
                if (state.statusPollInterval) {
                    clearInterval(state.statusPollInterval);
                    state.statusPollInterval = null;
                }
            }

            if (data.discord_status) {
                const discordStatusText = document.getElementById('discordStatusText');
                if (discordStatusText) discordStatusText.textContent = data.discord_status;
            }
        }

        updateModelInfo(data.lm_model, data.lm_models, state);
        
        // Update model select dropdown when connected
        if (data.lm_connected && data.lm_models && data.lm_models.length > 0) {
            updateModelSelect(data.lm_models, data.lm_hostname, data.lm_port);
        }
    } catch (e) {
        // Ignore errors during status check
    }
}

// ==================== Streaming Chat ====================

async function sendStreamingMessage() {
    const message = messageInput.value.trim();
    if (!message || !state.lmConnected) return;
    
    state.isStreaming = true;
    messageInput.disabled = true;
    sendBtn.disabled = false; // Keep send button for new messages during streaming
    messageInput.value = '';
    
    addMessage(message, 'user');
    
    // Show typing indicator
    const chatContainer = document.getElementById('chatContainer');
    if (chatContainer) {
        const typing = document.createElement('div');
        typing.className = 'typing-indicator';
        typing.id = 'typing';
        typing.innerHTML = '<span></span><span></span><span></span>';
        chatContainer.appendChild(typing);
        scrollToBottom();
    }
    
    setTokenGenerating();
    
    try {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let assistantContent = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            const events = buffer.split('\n\n');
            buffer = events.pop();
            
            for (const event of events) {
                if (!event.trim()) continue;
                
                const lines = event.split('\n');
                let eventType = '';
                let eventData = '';
                
                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        eventType = line.slice(7);
                    } else if (line.startsWith('data: ')) {
                        eventData = line.slice(6);
                    }
                }
                
                if (eventType === 'chunk' && eventData) {
                    const data = JSON.parse(eventData);
                    if (data.content) {
                        assistantContent += data.content;
                        appendTokenStream(data.content);
                    }
                    if (data.tokens_used > 0) {
                        const completionEl = document.getElementById('completionTokens');
                        const tpsEl = document.getElementById('tokensPerSecond');
                        const timeEl = document.getElementById('totalTime');
                        if (completionEl) completionEl.textContent = data.tokens_used.toLocaleString();
                        if (tpsEl) tpsEl.textContent = `${data.tokens_per_second} tok/s`;
                        if (timeEl) timeEl.textContent = `${data.elapsed}s`;
                        
                        completionEl?.classList.add('live');
                        setTimeout(() => completionEl?.classList.remove('live'), 500);
                    }
                } else if (eventType === 'usage' && eventData) {
                    const data = JSON.parse(eventData);
                    updateTokenMetrics(data);
                    showTokenUsageSummary(data);
                } else if (eventType === 'error' && eventData) {
                    const data = JSON.parse(eventData);
                    addMessage(`⚠️ Stream error: ${data.error}`, 'error');
                }
            }
        }
        
        const typingEl = document.getElementById('typing');
        if (typingEl) typingEl.remove();
        
        if (assistantContent) {
            addMessage(assistantContent, 'assistant');
        }
        
    } catch (error) {
        const typingEl = document.getElementById('typing');
        if (typingEl) typingEl.remove();
        addMessage(`Stream error: ${error.message}`, 'error');
        setTokenIdle();
    } finally {
        state.isStreaming = false;
        messageInput.disabled = false;
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

// ==================== Log Resize Handle ====================

(function initLogResize() {
    const handle = document.getElementById('logResizeHandle');
    const panel = document.getElementById('logPanel');
    if (!handle || !panel) return;
    
    let isResizing = false;

    handle.addEventListener('mousedown', (e) => {
        isResizing = true;
        document.body.style.cursor = 'ns-resize';
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        const windowHeight = window.innerHeight;
        const newHeight = windowHeight - e.clientY - 4;
        const clampedHeight = Math.max(100, Math.min(500, newHeight));
        panel.style.maxHeight = clampedHeight + 'px';
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    });
})();

// ==================== Tab Functions ====================

function switchTab(tabName) {
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    const buttons = document.querySelectorAll('.tab-button');
    if (tabName === 'chat') {
        buttons[0]?.classList.add('active');
        document.getElementById('chat-tab')?.classList.add('active');
    } else if (tabName === 'tokens') {
        buttons[1]?.classList.add('active');
        document.getElementById('tokens-tab')?.classList.add('active');
        loadLastTokenUsage();
    } else if (tabName === 'servers') {
        buttons[2]?.classList.add('active');
        document.getElementById('servers-tab')?.classList.add('active');
        loadServerConfig();
    } else if (tabName === 'lm-instances') {
        const idx = buttons.length - 3; // third to last (before tools-config and logs)
        buttons[idx]?.classList.add('active');
        document.getElementById('lm-instances-content')?.classList.add('active');
        loadLmInstances();
    } else if (tabName === 'tools-config') {
        const idx = buttons.length - 2; // second to last (before logs)
        buttons[idx]?.classList.add('active');
        document.getElementById('tools-config-tab')?.classList.add('active');
        loadToolsConfig();
    } else if (tabName === 'logs') {
        buttons[buttons.length - 1]?.classList.add('active');
        document.getElementById('logs-tab')?.classList.add('active');
        refreshLogs();
    }
}

// ==================== Model Selection ====================

function selectModel(modelId) {
    if (!modelId) return;
    
    fetch('/api/lm_instances/active/model', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({model_id: modelId})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            addMessage(`✅ Model changed to: ${modelId}`, 'system');
        } else {
            addMessage(`⚠️ Failed to select model: ${data.error || 'Unknown error'}`, 'error');
        }
    })
    .catch(err => addMessage(`⚠️ Error: ${err.message}`, 'error'));
}

function updateModelSelect(models, hostname, port) {
    const select = document.getElementById('modelSelect');
    if (!select) return;
    
    select.innerHTML = '<option value="">Select model...</option>';
    
    if (!models || models.length === 0) {
        select.style.display = 'none';
        return;
    }
    
    models.forEach(modelId => {
        const option = document.createElement('option');
        option.value = modelId;
        option.textContent = modelId;
        select.appendChild(option);
    });
    
    select.style.display = 'inline-block';
}

// ==================== Debug Panel ====================

function openDebugPanel() {
    window.open('/debug', '_blank', 'width=1200,height=800');
}

// ==================== Initialization ====================

window.addEventListener('load', async () => {
    // Load connection status
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        if (data.lm_connected) {
            state.lmConnected = true;
            setLMStatus('connected');
            messageInput.disabled = false;
            sendBtn.disabled = false;
            hostInput.value = data.lm_hostname;
            portInput.value = data.lm_port;
            state.currentLmHostname = data.lm_hostname;
            state.currentLmPort = data.lm_port;
        }

        if (data.discord_connected) {
            state.discordConnected = true;
            setDiscordStatus('connected');
            discordConnectBtn.disabled = true;
            discordDisconnectBtn.disabled = false;
            discordTokenInput.disabled = true;
            if (data.discord_status) {
                const discordStatusText = document.getElementById('discordStatusText');
                if (discordStatusText) discordStatusText.textContent = data.discord_status;
            }
        }

        updateModelInfo(data.lm_model, data.lm_models, state);
    } catch (e) {}

    // Load all settings
    await loadLoggingSettings();
    await loadDelaySettings();
    await loadMaxTokens();
    await loadTemperature();
    await loadMaxResponseLength();
    await loadSystemPrompt();
    await loadToolsConfig();

    // Start log polling
    fetchLogs();
    state.logPollInterval = setInterval(fetchLogs, 3000);
    updateModelInfo();
});

// ==================== Settings Loaders (called by initialization) ====================

async function loadLoggingSettings() {
    try {
        const response = await fetch('/api/settings/logging');
        const data = await response.json();
        if (data.success) {
            state.suppressWerkzeugLogging = data.suppress_werkzeug_logging;
            const toggle = document.getElementById('suppressLoggingToggle');
            if (toggle) toggle.checked = data.suppress_werkzeug_logging;
            updateLoggingStatusText(data.suppress_werkzeug_logging);
        }
    } catch (e) {
        console.error('Failed to load logging settings:', e);
    }
}

async function loadDelaySettings() {
    try {
        const response = await fetch('/api/settings/delay');
        const data = await response.json();
        if (data.success) {
            state.messageDelay = data.message_delay;
            const el = document.getElementById('delayInput');
            if (el) el.value = data.message_delay;
            updateDelayStatusText(data.message_delay);
        }
    } catch (e) {
        console.error('Failed to load delay settings:', e);
    }
}

async function loadMaxTokens() {
    try {
        const response = await fetch('/api/settings/max_tokens');
        const data = await response.json();
        if (data.success) {
            state.maxTokens = data.max_tokens;
            const el = document.getElementById('maxTokensInput');
            if (el) el.value = data.max_tokens;
            updateMaxTokensStatusText(data.max_tokens);
        }
    } catch (e) {
        console.error('Failed to load max tokens:', e);
    }
}

async function loadTemperature() {
    try {
        const response = await fetch('/api/settings/temperature');
        const data = await response.json();
        if (data.success) {
            state.temperature = data.temperature;
            const el = document.getElementById('temperatureInput');
            if (el) el.value = data.temperature;
            updateTemperatureStatusText(data.temperature);
        }
    } catch (e) {
        console.error('Failed to load temperature:', e);
    }
}

async function loadMaxResponseLength() {
    try {
        const response = await fetch('/api/settings/max_response_length');
        const data = await response.json();
        if (data.success) {
            state.maxResponseLength = data.max_response_length;
            const el = document.getElementById('maxResponseLengthInput');
            if (el) el.value = data.max_response_length;
            updateMaxResponseLengthStatusText(data.max_response_length);
        }
    } catch (e) {
        console.error('Failed to load max_response_length:', e);
    }
}

async function loadSystemPrompt() {
    try {
        const response = await fetch('/api/settings/system_prompt');
        const data = await response.json();
        if (data.success) {
            const textarea = document.getElementById('systemPromptTextarea');
            if (textarea) textarea.value = data.system_prompt;
            updateSystemPromptStatusText('Loaded');
        }
    } catch (e) {
        console.error('Failed to load system prompt:', e);
        updateSystemPromptStatusText('Error loading');
    }
}

// ==================== Tools Config Functions ====================

async function loadToolsConfig() {
    try {
        const response = await fetch('/api/tools_config');
        const data = await response.json();
        if (data.success && data.tools_config) {
            const cfg = data.tools_config;
            
            // Set form values
            const reasoningBrevity = document.getElementById('toolsReasoningBrevity');
            if (reasoningBrevity) reasoningBrevity.checked = cfg.reasoning_brevity;
            
            const toolMaxTokens = document.getElementById('toolMaxTokens');
            if (toolMaxTokens) toolMaxTokens.value = cfg.tool_max_tokens;
            
            const toolTemperature = document.getElementById('toolTemperature');
            if (toolTemperature) toolTemperature.value = cfg.tool_temperature;
            
            const finalMaxTokens = document.getElementById('finalMaxTokens');
            if (finalMaxTokens) finalMaxTokens.value = cfg.final_max_tokens;
            
            const useToolCalling = document.getElementById('toolsUseToolCalling');
            if (useToolCalling) useToolCalling.checked = cfg.use_tool_calling;
            
            updateToolsConfigStatusText('Loaded');
        }
    } catch (e) {
        console.error('Failed to load tools config:', e);
        updateToolsConfigStatusText('Error loading');
    }
}

async function saveToolsConfig() {
    const toolsConfig = {
        reasoning_brevity: document.getElementById('toolsReasoningBrevity').checked,
        tool_max_tokens: parseInt(document.getElementById('toolMaxTokens').value),
        tool_temperature: parseFloat(document.getElementById('toolTemperature').value),
        final_max_tokens: parseInt(document.getElementById('finalMaxTokens').value),
        use_tool_calling: document.getElementById('toolsUseToolCalling').checked
    };
    
    try {
        const response = await fetch('/api/tools_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tools_config: toolsConfig })
        });
        
        const data = await response.json();
        if (data.success) {
            updateToolsConfigStatusText('✅ Saved successfully!');
            setTimeout(() => updateToolsConfigStatusText('Loaded'), 3000);
        } else {
            updateToolsConfigStatusText('❌ Error: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        console.error('Failed to save tools config:', e);
        updateToolsConfigStatusText('❌ Network error');
    }
}

async function resetToolsConfig() {
    // Reset to defaults
    const reasoningBrevity = document.getElementById('toolsReasoningBrevity');
    if (reasoningBrevity) reasoningBrevity.checked = true;
    
    const toolMaxTokens = document.getElementById('toolMaxTokens');
    if (toolMaxTokens) toolMaxTokens.value = 2048;
    
    const toolTemperature = document.getElementById('toolTemperature');
    if (toolTemperature) toolTemperature.value = 0.3;
    
    const finalMaxTokens = document.getElementById('finalMaxTokens');
    if (finalMaxTokens) finalMaxTokens.value = 8192;
    
    const useToolCalling = document.getElementById('toolsUseToolCalling');
    if (useToolCalling) useToolCalling.checked = true;
    
    updateToolsConfigStatusText('Reset to defaults - click Save to apply');
}

function validateToolsConfig() {
    // No immediate validation needed - server validates on save
    updateToolsConfigStatusText('Modified - click Save to apply');
}

function updateToolsConfigStatusText(message) {
    const el = document.getElementById('toolsConfigStatusText');
    if (el) {
        el.textContent = message;
        el.style.color = message.includes('❌') ? '#f38ba8' : '#a6e3a1';
    }
}
