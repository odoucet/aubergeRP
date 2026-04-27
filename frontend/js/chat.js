/**
 * chat.js — Conversation management, SSE streaming, message rendering.
 */
import {
  fetchConversations,
  fetchConversation,
  createConversation,
  deleteConversation,
  sendMessage,
  fetchHealth,
} from './api.js';

// ── State ────────────────────────────────────────────────────────────────────

let _activeConversationId = null;
let _activeCharacter = null;
let _streaming = false;
let _healthInterval = null;
let _lastUserMessage = null;

// ── Init ─────────────────────────────────────────────────────────────────────

export function initChat() {
  const sendBtn = document.getElementById('send-btn');
  const input = document.getElementById('msg-input');

  sendBtn.addEventListener('click', () => handleSend());
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 200) + 'px';
  });

  document.getElementById('new-conv-btn').addEventListener('click', handleNewConversation);

  // Health polling
  startHealthPolling();

  // Lightbox
  initLightbox();
}

// ── Lightbox ─────────────────────────────────────────────────────────────────

function initLightbox() {
  const lb = document.createElement('div');
  lb.id = 'lightbox';
  lb.setAttribute('role', 'dialog');
  lb.setAttribute('aria-modal', 'true');
  lb.setAttribute('aria-label', 'Image lightbox');
  lb.innerHTML = '<img id="lightbox-img" alt="Full-size image"><button id="lightbox-close" aria-label="Close lightbox">✕</button>';
  document.body.appendChild(lb);

  lb.addEventListener('click', e => {
    if (e.target === lb || e.target.id === 'lightbox-close') closeLightbox();
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeLightbox();
  });
}

function openLightbox(src) {
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  const lb = document.getElementById('lightbox');
  if (lb) lb.classList.remove('open');
  document.body.style.overflow = '';
}

// ── Character selection ───────────────────────────────────────────────────────

export async function onCharacterSelected(character) {
  _activeCharacter = character;
  _activeConversationId = null;

  updateCharHeader(character);
  showChatUI();
  clearMessages();

  await loadConversations(character.id);
}

function updateCharHeader(character) {
  const header = document.getElementById('char-header');
  const avatar = header.querySelector('.char-avatar');
  const name = header.querySelector('.char-name');

  avatar.src = character.has_avatar
    ? character.avatar_url
    : 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" fill="%230f3460"/><text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-size="18" fill="%23e0e0e0">' + encodeURIComponent(character.name[0] || '?') + '</text></svg>';
  avatar.alt = character.name;
  name.textContent = character.name;
}

function showChatUI() {
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('char-header').style.display = 'flex';
  document.getElementById('message-list').style.display = 'flex';
  document.getElementById('input-area').style.display = 'flex';
}

// ── Conversations ─────────────────────────────────────────────────────────────

async function loadConversations(characterId) {
  let convs;
  try {
    convs = await fetchConversations(characterId);
  } catch (err) {
    showToast('Failed to load conversations: ' + err.message);
    return;
  }
  renderConvList(convs);

  if (convs.length > 0) {
    await selectConversation(convs[0].id);
  } else {
    await handleNewConversation();
  }
}

function renderConvList(convs) {
  const list = document.getElementById('conv-list');
  list.innerHTML = '';

  for (const conv of convs) {
    const li = document.createElement('li');
    li.className = 'conv-item';
    li.dataset.id = conv.id;
    if (conv.id === _activeConversationId) li.classList.add('active');
    li.setAttribute('role', 'button');
    li.setAttribute('tabindex', '0');

    const titleSpan = document.createElement('span');
    titleSpan.className = 'conv-title';
    titleSpan.textContent = conv.title;
    titleSpan.title = conv.title;

    const countSpan = document.createElement('span');
    countSpan.className = 'conv-count';
    countSpan.textContent = conv.message_count;

    const delBtn = document.createElement('button');
    delBtn.className = 'conv-delete';
    delBtn.textContent = '✕';
    delBtn.setAttribute('aria-label', 'Delete conversation');
    delBtn.addEventListener('click', async e => {
      e.stopPropagation();
      if (!confirm('Delete this conversation?')) return;
      try {
        await deleteConversation(conv.id);
        if (_activeConversationId === conv.id) {
          _activeConversationId = null;
          clearMessages();
        }
        await loadConversations(_activeCharacter.id);
      } catch (err) {
        showToast('Delete failed: ' + err.message);
      }
    });

    li.appendChild(titleSpan);
    li.appendChild(countSpan);
    li.appendChild(delBtn);

    li.addEventListener('click', () => selectConversation(conv.id));
    li.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') selectConversation(conv.id); });

    list.appendChild(li);
  }
}

async function selectConversation(id) {
  _activeConversationId = id;
  highlightActiveConv(id);
  clearMessages();

  // Close sidebar on small mobile screens after selecting a conversation
  if (window.innerWidth < 768) {
    document.dispatchEvent(new CustomEvent('closeSidebar'));
  }

  let conv;
  try {
    conv = await fetchConversation(id);
  } catch (err) {
    showToast('Failed to load conversation: ' + err.message);
    return;
  }

  for (const msg of conv.messages) {
    appendMessage(msg.role, msg.content, msg.images || []);
  }
  scrollToBottom();
}

function highlightActiveConv(id) {
  document.querySelectorAll('#conv-list li').forEach(li => {
    li.classList.toggle('active', li.dataset.id === id);
  });
}

async function handleNewConversation() {
  if (!_activeCharacter) return;
  let conv;
  try {
    conv = await createConversation(_activeCharacter.id);
  } catch (err) {
    showToast('Failed to create conversation: ' + err.message);
    return;
  }
  // Refresh list and select the new one
  const convs = await fetchConversations(_activeCharacter.id);
  renderConvList(convs);
  await selectConversation(conv.id);
}

// ── Messages ─────────────────────────────────────────────────────────────────

function clearMessages() {
  document.getElementById('message-list').innerHTML = '';
}

/**
 * Create an image wrapper element with lightbox-click and copy-to-clipboard button.
 */
function createImageElement(url) {
  const wrapper = document.createElement('div');
  wrapper.className = 'img-wrapper';

  const img = document.createElement('img');
  img.className = 'msg-image';
  img.src = url;
  img.alt = 'Generated image';
  img.addEventListener('click', () => openLightbox(url));

  const copyBtn = document.createElement('button');
  copyBtn.className = 'img-copy-btn';
  copyBtn.setAttribute('aria-label', 'Copy image to clipboard');
  copyBtn.textContent = '⧉';
  copyBtn.addEventListener('click', e => {
    e.stopPropagation();
    copyImageToClipboard(url);
  });

  wrapper.appendChild(img);
  wrapper.appendChild(copyBtn);
  return wrapper;
}

async function copyImageToClipboard(url) {
  try {
    const res = await fetch(url);
    const blob = await res.blob();
    await navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })]);
    showToast('Image copied to clipboard');
  } catch (err) {
    showToast('Copy failed: ' + err.message);
  }
}

/**
 * Append a fully-formed message and return the bubble element.
 */
function appendMessage(role, content, images = []) {
  const list = document.getElementById('message-list');

  const wrapper = document.createElement('article');
  wrapper.className = `msg ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = renderMarkdown(content);
  wrapper.appendChild(bubble);

  if (images && images.length > 0) {
    const imgContainer = document.createElement('div');
    imgContainer.className = 'msg-images';
    for (const url of images) {
      imgContainer.appendChild(createImageElement(url));
    }
    wrapper.appendChild(imgContainer);
  }

  list.appendChild(wrapper);
  scrollToBottom();
  return bubble;
}

/**
 * Create a streaming assistant message bubble.
 * Returns { bubble, imagesContainer, finalize(content, images) }
 */
function createStreamingMessage() {
  const list = document.getElementById('message-list');

  // Typing indicator
  const typingEl = document.createElement('div');
  typingEl.className = 'msg assistant';
  const indicator = document.createElement('div');
  indicator.className = 'typing-indicator';
  indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
  typingEl.appendChild(indicator);
  list.appendChild(typingEl);
  scrollToBottom();

  const wrapper = document.createElement('article');
  wrapper.className = 'msg assistant';
  wrapper.style.display = 'none'; // hidden until first token

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  wrapper.appendChild(bubble);

  const imagesContainer = document.createElement('div');
  imagesContainer.className = 'msg-images';
  wrapper.appendChild(imagesContainer);

  list.appendChild(wrapper);

  let rawText = '';

  return {
    onToken(token) {
      rawText += token;
      typingEl.remove();
      wrapper.style.display = '';
      bubble.innerHTML = renderMarkdown(rawText);
      scrollToBottom();
    },
    onImageStart(genId, prompt) {
      const ph = document.createElement('div');
      ph.className = 'img-placeholder';
      ph.id = `img-ph-${genId}`;
      ph.innerHTML = '<div class="spinner"></div><span>Generating image…</span>';
      imagesContainer.appendChild(ph);
      scrollToBottom();
    },
    onImageComplete(genId, imageUrl) {
      const ph = document.getElementById(`img-ph-${genId}`);
      if (ph) {
        ph.replaceWith(createImageElement(imageUrl));
      }
      scrollToBottom();
    },
    onImageFailed(genId, detail) {
      const ph = document.getElementById(`img-ph-${genId}`);
      if (ph) {
        const errEl = document.createElement('div');
        errEl.className = 'img-error';
        errEl.textContent = '⚠ ' + (detail || 'Image generation failed');
        ph.replaceWith(errEl);
      }
    },
    finalize() {
      typingEl.remove();
      wrapper.style.display = '';
    },
  };
}

// ── Sending ──────────────────────────────────────────────────────────────────

async function handleSend(contentOverride) {
  if (_streaming || !_activeConversationId) return;

  const input = document.getElementById('msg-input');
  const content = contentOverride !== undefined ? contentOverride : input.value.trim();
  if (!content) return;

  if (contentOverride === undefined) {
    input.value = '';
    input.style.height = 'auto';
  }

  _lastUserMessage = content;
  setStreaming(true);

  // Append user message only on initial send, not on retry
  if (contentOverride === undefined) {
    appendMessage('user', content);
  }

  const streaming = createStreamingMessage();

  let res;
  try {
    res = await sendMessage(_activeConversationId, content);
  } catch (err) {
    streaming.finalize();
    appendErrorMessage('Send failed: ' + err.message, () => handleSend(_lastUserMessage));
    setStreaming(false);
    return;
  }

  try {
    await readSSE(res, streaming);
  } catch (err) {
    streaming.finalize();
    appendErrorMessage('Stream error: ' + err.message, () => handleSend(_lastUserMessage));
  }

  setStreaming(false);
}

/** Read SSE frames from the fetch Response body and dispatch events. */
async function readSSE(response, handlers) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    // SSE frames are separated by \n\n; each frame is "data: <json>"
    const frames = buf.split('\n\n');
    buf = frames.pop(); // keep partial last frame

    for (const frame of frames) {
      const line = frame.trim();
      if (!line) continue;
      if (!line.startsWith('data:')) continue;
      const jsonStr = line.slice('data:'.length).trim();
      if (!jsonStr) continue;

      let event;
      try {
        event = JSON.parse(jsonStr);
      } catch (_) {
        continue;
      }

      dispatchSSEEvent(event, handlers);
    }
  }
}

function dispatchSSEEvent(event, handlers) {
  switch (event.type) {
    case 'token':
      handlers.onToken(event.content || '');
      break;
    case 'image_start':
      handlers.onImageStart(event.generation_id, event.prompt);
      break;
    case 'image_complete':
      handlers.onImageComplete(event.generation_id, event.image_url);
      break;
    case 'image_failed':
      handlers.onImageFailed(event.generation_id, event.detail);
      break;
    case 'done':
      handlers.finalize();
      break;
    case 'error':
      handlers.finalize();
      appendErrorMessage(event.detail || 'Unknown error', () => handleSend(_lastUserMessage));
      break;
  }
}

function appendErrorMessage(detail, onRetry) {
  const list = document.getElementById('message-list');
  const el = document.createElement('div');
  el.className = 'msg-error';

  const text = document.createElement('span');
  text.textContent = '⚠ ' + detail;
  el.appendChild(text);

  if (onRetry) {
    const retryBtn = document.createElement('button');
    retryBtn.className = 'msg-retry-btn';
    retryBtn.textContent = 'Retry';
    retryBtn.addEventListener('click', () => {
      el.remove();
      onRetry();
    });
    el.appendChild(retryBtn);
  }

  list.appendChild(el);
  scrollToBottom();
}

function setStreaming(streaming) {
  _streaming = streaming;
  document.getElementById('msg-input').disabled = streaming;
  document.getElementById('send-btn').disabled = streaming;
  if (!streaming) {
    document.getElementById('msg-input').focus();
  }
}

// ── Health polling ────────────────────────────────────────────────────────────

function startHealthPolling() {
  updateHealth();
  _healthInterval = setInterval(() => {
    if (!document.hidden) updateHealth();
  }, 30000);

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) updateHealth();
  });
}

async function updateHealth() {
  let data;
  try {
    data = await fetchHealth();
  } catch (_) {
    setStatusItem('text', null);
    setStatusItem('image', null);
    return;
  }
  const c = data.connectors || {};
  setStatusItem('text', c.text);
  setStatusItem('image', c.image);
  setStatusItem('video', c.video);
  setStatusItem('audio', c.audio);
}

function setStatusItem(type, info) {
  const el = document.getElementById(`status-${type}`);
  if (!el) return;
  const dot = el.querySelector('.status-dot');
  const label = el.querySelector('.status-label');
  if (!info) {
    dot.className = 'status-dot na';
    label.textContent = `${capitalize(type)} —`;
  } else if (info.connected) {
    dot.className = 'status-dot ok';
    label.textContent = `${capitalize(type)} ✓`;
  } else {
    dot.className = 'status-dot err';
    label.textContent = `${capitalize(type)} ✕`;
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderMarkdown(text) {
  if (typeof marked !== 'undefined') {
    return marked.parse(text, { breaks: true });
  }
  // Fallback: escape HTML
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
}

function scrollToBottom() {
  const list = document.getElementById('message-list');
  list.scrollTop = list.scrollHeight;
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function showToast(message, duration = 4000) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), duration);
}
