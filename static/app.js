/**
 * Company Analysis IVA — Frontend Logic
 * Handles chat, voice input (Web Speech API), and TTS.
 */

// ---- State ----
let sessionId = localStorage.getItem('iva_session_id') || crypto.randomUUID();
localStorage.setItem('iva_session_id', sessionId);

let isRecording = false;
let recognition = null;

// ---- DOM Elements ----
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const voiceBtn = document.getElementById('voice-btn');
const clearBtn = document.getElementById('clear-btn');
const activeCompanyEl = document.getElementById('active-company');
const voiceStatus = document.getElementById('voice-status');

// ---- Chat Logic ----

async function sendMessage(text) {
    if (!text.trim()) return;

    // Add user message to UI
    addMessage(text, 'user');
    messageInput.value = '';
    sendBtn.disabled = true;

    // Show typing indicator
    const typingEl = showTyping();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                session_id: sessionId,
            }),
        });

        const data = await response.json();

        // Remove typing indicator
        typingEl.remove();

        if (response.ok) {
            // Update session ID (in case server created a new one)
            sessionId = data.session_id;
            localStorage.setItem('iva_session_id', sessionId);

            // Update active company indicator
            if (data.active_company_display) {
                activeCompanyEl.textContent = data.active_company_display;
                activeCompanyEl.classList.add('active');
            }

            // Add assistant response
            addMessage(data.response, 'assistant');

            // Speak the response (Phase 2 - TTS)
            speak(data.response);
        } else {
            addMessage('Sorry, something went wrong. Please try again.', 'assistant');
        }
    } catch (err) {
        typingEl.remove();
        addMessage('Unable to connect to the server. Please make sure it\'s running.', 'assistant');
        console.error('Chat error:', err);
    }

    sendBtn.disabled = false;
    messageInput.focus();
}

function addMessage(text, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';

    const content = document.createElement('div');
    content.className = 'message-content';
    // Simple markdown-like rendering
    content.innerHTML = formatMessage(text);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMessage(text) {
    // Convert basic markdown to HTML
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/^(.*)$/, '<p>$1</p>');
}

function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant-message';
    typingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return typingDiv;
}

// ---- Voice Input (Phase 2 — Web Speech API STT) ----

function initVoice() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        voiceBtn.title = 'Voice input not supported in this browser';
        voiceBtn.style.opacity = '0.5';
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        messageInput.value = transcript;
        stopRecording();
        // Auto-send after voice input
        sendMessage(transcript);
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        stopRecording();
        if (event.error === 'no-speech') {
            voiceStatus.textContent = 'No speech detected. Try again.';
            setTimeout(() => { voiceStatus.textContent = ''; }, 3000);
        }
    };

    recognition.onend = () => {
        stopRecording();
    };
}

function startRecording() {
    if (!recognition) return;
    isRecording = true;
    voiceBtn.classList.add('recording');
    voiceStatus.textContent = '🔴 Listening...';
    recognition.start();
}

function stopRecording() {
    isRecording = false;
    voiceBtn.classList.remove('recording');
    voiceStatus.textContent = '';
    try { recognition.stop(); } catch (e) {}
}

function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

// ---- TTS (Phase 2 — Web Speech Synthesis) ----

function speak(text) {
    // Only speak if browser supports it
    if (!('speechSynthesis' in window)) return;

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    // Clean text for speech (remove markdown)
    const cleanText = text
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/\*(.*?)\*/g, '$1')
        .replace(/#+\s/g, '');

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 0.8;

    window.speechSynthesis.speak(utterance);
}

// ---- Clear Conversation ----

async function clearConversation() {
    try {
        await fetch(`/api/session/${sessionId}`, { method: 'DELETE' });
    } catch (e) {}

    // Reset session
    sessionId = crypto.randomUUID();
    localStorage.setItem('iva_session_id', sessionId);

    // Clear UI (keep the welcome message)
    const messages = chatMessages.querySelectorAll('.message');
    messages.forEach((msg, i) => {
        if (i > 0) msg.remove(); // Keep first (welcome) message
    });

    activeCompanyEl.textContent = 'None';
    activeCompanyEl.classList.remove('active');

    // Stop any ongoing speech
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
}

// ---- Event Listeners ----

sendBtn.addEventListener('click', () => sendMessage(messageInput.value));

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(messageInput.value);
    }
});

voiceBtn.addEventListener('click', toggleRecording);
clearBtn.addEventListener('click', clearConversation);

// ---- Initialize ----

initVoice();
messageInput.focus();
