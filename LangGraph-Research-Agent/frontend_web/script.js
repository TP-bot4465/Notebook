// frontend_web/script.js

const API_BASE_URL = "http://localhost:8000"; 
let sessionId = crypto.randomUUID(); 
let selectedFiles = []; // Mảng chứa danh sách file đang chọn

// DOM Elements
const chatHistory = document.getElementById('chat-history');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const fileUpload = document.getElementById('file-upload');
const sourceList = document.getElementById('source-list');
const sourceCount = document.getElementById('source-count');
const webSearchToggle = document.getElementById('web-search-toggle');

// --- 1. Load Sources ---
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents/`);
        const docs = await response.json();
        renderSources(docs);
    } catch (error) {
        console.error("Load docs error:", error);
    }
}

function renderSources(docs) {
    sourceList.innerHTML = '';
    sourceCount.textContent = docs.length;
    
    docs.forEach(doc => {
        const div = document.createElement('div');
        // Kiểm tra xem file có trong danh sách selectedFiles không (để giữ trạng thái khi reload list)
        const isSelected = selectedFiles.includes(doc);
        div.className = `source-item ${isSelected ? 'selected' : ''}`;
        
        // Icon check màu xanh nếu selected
        const checkIcon = isSelected ? '<span class="material-icons-outlined" style="margin-left:auto; font-size:16px; color:var(--secondary-blue);">check_circle</span>' : '';

        div.innerHTML = `
            <span class="material-icons-outlined icon">description</span>
            <span class="name">${doc}</span>
            ${checkIcon}
        `;
        
        // Sự kiện Click chọn file
        div.addEventListener('click', () => {
            toggleFileSelection(doc, div);
        });

        sourceList.appendChild(div);
    });
}

// Logic chọn/bỏ chọn file
function toggleFileSelection(filename, divElement) {
    if (selectedFiles.includes(filename)) {
        // Nếu đã có -> Bỏ chọn
        selectedFiles = selectedFiles.filter(f => f !== filename);
        divElement.classList.remove('selected');
        // Xóa icon check
        const icon = divElement.querySelector('.material-icons-outlined[style*="margin-left:auto"]');
        if(icon) icon.remove();
    } else {
        // Nếu chưa có -> Chọn thêm
        selectedFiles.push(filename);
        divElement.classList.add('selected');
        // Thêm icon check
        divElement.insertAdjacentHTML('beforeend', '<span class="material-icons-outlined" style="margin-left:auto; font-size:16px; color:var(--secondary-blue);">check_circle</span>');
    }
    console.log("Files Selected:", selectedFiles);
}

// --- 2. File Upload ---
fileUpload.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const btnText = document.querySelector('.btn-primary').innerHTML;
    document.querySelector('.btn-primary').innerHTML = `<span class="material-icons-outlined">hourglass_top</span> Uploading...`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE_URL}/upload-document/`, {
            method: 'POST',
            body: formData
        });
        if (response.ok) {
            loadDocuments(); // Reload list sau khi upload
        } else {
            alert("Upload failed.");
        }
    } catch (err) {
        console.error(err);
        alert("Error connecting to server.");
    } finally {
        document.querySelector('.btn-primary').innerHTML = btnText;
        fileUpload.value = '';
    }
});

// --- 3. Chat Logic ---
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // UI Updates
    addMessage(text, 'user');
    userInput.value = '';
    userInput.style.height = 'auto';
    sendBtn.disabled = true;

    // Loading State
    const loadingId = addLoadingMessage();

    try {
        const response = await fetch(`${API_BASE_URL}/chat/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                query: text,
                enable_web_search: webSearchToggle.checked,
                selected_files: selectedFiles // Gửi danh sách file hiện tại
            })
        });

        const data = await response.json();
        removeMessage(loadingId);
        
        // Render Response
        addMessage(data.response, 'assistant', data.trace_events);

    } catch (error) {
        removeMessage(loadingId);
        addMessage("Sorry, I encountered an error connecting to the server.", 'assistant');
        console.error(error);
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
}

// --- Helper Functions ---
function addMessage(text, role, traces = []) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    
    let avatarIcon = role === 'user' ? 'person' : 'smart_toy';
    let contentHtml = '';

    if (role === 'assistant' && traces.length > 0) {
        contentHtml += buildThinkingBlock(traces);
    }

    if (role === 'assistant') {
        contentHtml += `<div class="markdown-body">${marked.parse(text)}</div>`;
    } else {
        contentHtml += `<div class="markdown-body"><p>${text}</p></div>`;
    }

    div.innerHTML = `
        <div class="avatar"><span class="material-icons-outlined">${avatarIcon}</span></div>
        <div class="message-content">${contentHtml}</div>
    `;

    chatHistory.appendChild(div);
    scrollToBottom();
    
    div.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
}

function buildThinkingBlock(traces) {
    let stepsHtml = traces.map(t => {
        let iconMap = {
            'router': 'alt_route',
            'rag_lookup': 'library_books',
            'web_search': 'public',
            'answer': 'psychology',
            '__end__': 'flag'
        };
        let icon = iconMap[t.node_name] || 'settings';
        let detailText = t.description;
        
        if (t.details && t.details.summary) detailText += `<br><span class="step-desc">found: "${t.details.summary}..."</span>`;
        if (t.details && t.details.decision) detailText += `<br><span class="step-desc">decision: <strong>${t.details.decision}</strong></span>`;

        return `
            <div class="step-item">
                <span class="material-icons-outlined step-icon">${icon}</span>
                <div class="step-content">
                    <strong>${formatNodeName(t.node_name)}</strong>
                    <div style="font-size:0.8em; color:#555;">${detailText}</div>
                </div>
            </div>
        `;
    }).join('');

    return `
        <details class="thinking-process">
            <summary class="thinking-summary">
                <span class="material-icons-outlined">tips_and_updates</span>
                Thinking Process (${traces.length} steps)
            </summary>
            <div class="thinking-details">
                ${stepsHtml}
            </div>
        </details>
    `;
}

function formatNodeName(name) {
    return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function addLoadingMessage() {
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.id = 'loading-msg';
    div.innerHTML = `
        <div class="avatar"><span class="material-icons-outlined">smart_toy</span></div>
        <div class="message-content">
            <div style="display:flex; align-items:center; gap:8px; color:#7F8C8D;">
                <span class="material-icons-outlined" style="animation: spin 1s infinite linear;">sync</span>
                Thinking...
            </div>
        </div>
    `;
    chatHistory.appendChild(div);
    scrollToBottom();
    return div.id;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
userInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    sendBtn.disabled = this.value.trim() === '';
});

// Load CSS Spinner
const style = document.createElement('style');
style.innerHTML = `@keyframes spin { 100% { transform: rotate(360deg); } }`;
document.head.appendChild(style);

// Init
loadDocuments();