(function () {
  const LOCALES = ['cz', 'fr'];
  const pathMatch = location.pathname.match(/^\/(cz|fr)(\/|$)/);
  let currentLocale = pathMatch ? pathMatch[1] : 'cz';

  function getWsUrl(locale) {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    return proto + '//' + location.host + '/' + locale + '/api/v1/ws/chat';
  }

  const messagesEl = document.getElementById('messages');
  const textInput = document.getElementById('textInput');
  const sendBtn = document.getElementById('sendBtn');
  const recordBtn = document.getElementById('recordBtn');
  const recordStatus = document.getElementById('recordStatus');
  const statusEl = document.getElementById('status');

  let ws = null;
  let mediaRecorder = null;
  let stream = null;
  let onAudioCancelAck = null;
  let waitingForCancelAck = false;

  function setStatus(text, cls) {
    statusEl.textContent = text;
    statusEl.className = 'status' + (cls ? ' ' + cls : '');
  }

  function addMessage(role, content) {
    const div = document.createElement('div');
    div.className = 'message ' + role;
    div.innerHTML = '<div class="role">' + (role === 'user' ? 'You' : 'AI') + '</div><div class="content">' + escapeHtml(content) + '</div>';
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  let ttsChunks = [];
  let ttsPlaying = false;
  let ttsCurrentAudio = null;
  const TTS_MIN_BYTES = 4096;

  function stopTts() {
    ttsChunks = [];
    ttsPlaying = false;
    if (ttsCurrentAudio) {
      ttsCurrentAudio.pause();
      ttsCurrentAudio = null;
    }
  }

  function concatChunks(chunks) {
    let total = 0;
    for (const c of chunks) total += c.byteLength;
    const out = new Uint8Array(total);
    let off = 0;
    for (const c of chunks) {
      out.set(new Uint8Array(c), off);
      off += c.byteLength;
    }
    return new Blob([out], { type: 'audio/mp3' });
  }

  function playTtsQueue() {
    if (ttsChunks.length === 0) {
      ttsPlaying = false;
      ttsCurrentAudio = null;
      return;
    }
    const blob = concatChunks(ttsChunks);
    ttsChunks = [];
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    ttsCurrentAudio = audio;
    audio.onended = () => {
      URL.revokeObjectURL(url);
      ttsCurrentAudio = null;
      playTtsQueue();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      ttsCurrentAudio = null;
      playTtsQueue();
    };
    ttsPlaying = true;
    audio.play();
  }

  function pushTtsChunk(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    ttsChunks.push(bytes.buffer);
    const total = ttsChunks.reduce((s, c) => s + c.byteLength, 0);
    if (!ttsPlaying && total >= TTS_MIN_BYTES) {
      playTtsQueue();
    }
  }

  function flushTtsChunks() {
    if (ttsChunks.length > 0 && !ttsPlaying) {
      playTtsQueue();
    }
  }

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function connect() {
    if (ws) {
      ws.close();
      ws = null;
    }
    const url = getWsUrl(currentLocale);
    return new Promise((resolve, reject) => {
      ws = new WebSocket(url);
      ws.onopen = () => {
        setStatus('Connected', 'connected');
        sendBtn.disabled = false;
        resolve(ws);
      };
      ws.onclose = () => setStatus('Disconnected', 'error');
      ws.onerror = () => setStatus('Error', 'error');
      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'audio_chunk_received') return;
          if (data.type === 'interrupt') {
            waitingForCancelAck = false;
            if (onAudioCancelAck) {
              onAudioCancelAck();
              onAudioCancelAck = null;
            }
            return;
          }
          if (waitingForCancelAck && (data.type === 'audio_chunk' || data.type === 'audio_end')) return;
          if (data.type === 'text') {
            const lastUser = messagesEl.querySelector('.message.user:last-child');
            if (lastUser && data.user_message) lastUser.querySelector('.content').textContent = data.user_message;
            addMessage('assistant', data.ai_response || '');
            stopTts();
          } else if (data.type === 'audio_chunk') {
            if (data.chunk) pushTtsChunk(data.chunk);
          } else if (data.type === 'audio_end') {
            flushTtsChunks();
          } else if (data.type === 'audio') {
            const lastUser = messagesEl.querySelector('.message.user:last-child');
            if (lastUser && data.user_message) lastUser.querySelector('.content').textContent = data.user_message;
            if (!messagesEl.querySelector('.message.assistant:last-child .content')) {
              addMessage('assistant', data.ai_response || '');
            }
            if (data.audio) pushTtsChunk(data.audio);
          } else if (data.type === 'error') {
            addMessage('assistant', '❌ ' + (data.message || 'Error'));
          }
        } catch (err) {
          console.error(err);
        }
      };
      setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) reject(new Error('Connection timeout'));
      }, 5000);
    });
  }

  function ensureConnection() {
    if (ws && ws.readyState === WebSocket.OPEN) return Promise.resolve(ws);
    return connect();
  }

  function sendAudioCancelAndWait() {
    stopTts();
    if (!ws || ws.readyState !== WebSocket.OPEN) return Promise.resolve();
    waitingForCancelAck = true;
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        waitingForCancelAck = false;
        onAudioCancelAck = null;
        resolve();
      }, 3000);
      onAudioCancelAck = () => {
        clearTimeout(timeout);
        resolve();
      };
      ws.send(JSON.stringify({ type: 'audio_cancel' }));
    });
  }

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onloadend = () => {
        const s = r.result;
        resolve(s.includes(',') ? s.split(',')[1] : s);
      };
      r.onerror = reject;
      r.readAsDataURL(blob);
    });
  }

  function sendText(text) {
    ensureConnection().then(() => sendAudioCancelAndWait()).then(() => {
      addMessage('user', text);
      textInput.value = '';
      ws.send(JSON.stringify({ type: 'text', content: text }));
    }).catch(err => addMessage('assistant', '❌ ' + err.message));
  }

  async function startRecording() {
    try {
      await ensureConnection();
      await sendAudioCancelAndWait();
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      const CHUNK_MS = 500;
      addMessage('user', '🎤 Recording...');

      recordBtn.textContent = '⏹️ Stop';
      recordBtn.classList.add('recording');
      recordStatus.textContent = 'Sending chunks...';
      statusEl.classList.add('recording');

      mediaRecorder.ondataavailable = async (e) => {
        if (e.data.size > 0) {
          const b64 = await blobToBase64(e.data);
          ws.send(JSON.stringify({ type: 'audio_chunk', data: b64 }));
        }
      };

      mediaRecorder.onstop = async () => {
        recordBtn.textContent = '🎤 Record';
        recordBtn.classList.remove('recording');
        recordStatus.textContent = '';
        statusEl.classList.remove('recording');
        stream.getTracks().forEach(t => t.stop());

        ws.send(JSON.stringify({ type: 'audio_end' }));
        const last = messagesEl.querySelector('.message.user:last-child .content');
        if (last) last.textContent = '🎤 Audio sent...';
      };

      mediaRecorder.start(CHUNK_MS);
    } catch (err) {
      addMessage('assistant', '❌ Microphone: ' + err.message);
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  }

  sendBtn.addEventListener('click', () => {
    const t = textInput.value.trim();
    if (t) sendText(t);
  });

  textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const t = textInput.value.trim();
      if (t) sendText(t);
    }
  });

  recordBtn.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      stopRecording();
    } else {
      startRecording();
    }
  });

  function setActiveLocale(locale) {
    currentLocale = locale;
    document.querySelectorAll('.locale-btn').forEach((b) => b.classList.remove('active'));
    document.querySelector('.locale-btn[data-locale="' + locale + '"]')?.classList.add('active');
    setStatus('Reconnecting...');
    connect().catch(() => {});
  }

  document.querySelectorAll('.locale-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const locale = btn.dataset.locale;
      if (locale !== currentLocale) setActiveLocale(locale);
    });
  });

  document.querySelector('.locale-btn[data-locale="' + currentLocale + '"]')?.classList.add('active');

  connect();
})();
