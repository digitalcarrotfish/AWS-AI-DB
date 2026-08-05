(function () {
  'use strict';

  var API = '';
  var sessionId = localStorage.getItem('qh_session_id') || '';
  var focusBridge = localStorage.getItem('qh_focus_bridge') || '';
  var bridges = [];
  var pendingQuery = '';

  var els = {
    messages: document.getElementById('messages'),
    input: document.getElementById('chatInput'),
    send: document.getElementById('sendBtn'),
    bridgeList: document.getElementById('bridgeList'),
    bridgeSearch: document.getElementById('bridgeSearch'),
    focusLabel: document.getElementById('focusLabel'),
    dossierProgress: document.getElementById('dossierProgress'),
    dossierLearned: document.getElementById('dossierLearned'),
    studyPathBox: document.getElementById('studyPathBox'),
    statusPill: document.getElementById('statusPill'),
    clearFocus: document.getElementById('clearFocus'),
    chips: document.getElementById('chips')
  };

  var CHIPS = [
    '介绍赵州桥',
    '规划一条宋代桥梁研学路线',
    '卢沟桥的历史意义',
    '对比赵州桥和卢沟桥',
    '继续'
  ];

  function parseUrlParams() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('session')) sessionId = params.get('session');
    if (params.get('bridge')) focusBridge = params.get('bridge');
    if (params.get('q')) pendingQuery = params.get('q');
    if (sessionId) localStorage.setItem('qh_session_id', sessionId);
    if (focusBridge) localStorage.setItem('qh_focus_bridge', focusBridge);
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function appendMessage(role, text, meta) {
    var div = document.createElement('div');
    div.className = 'ai-msg ' + (role === 'user' ? 'user' : 'bot');
    div.innerHTML =
      '<div class="bubble">' + escapeHtml(text) + '</div>' +
      (meta ? '<div class="meta">' + escapeHtml(meta) + '</div>' : '');
    els.messages.appendChild(div);
    els.messages.scrollTop = els.messages.scrollHeight;
    return div;
  }

  function setFocus(name) {
    focusBridge = name || '';
    if (focusBridge) {
      localStorage.setItem('qh_focus_bridge', focusBridge);
    } else {
      localStorage.removeItem('qh_focus_bridge');
    }
    els.focusLabel.textContent = focusBridge || '未选择';
    renderBridgeList(els.bridgeSearch.value);
  }

  function renderBridgeList(filter) {
    var q = (filter || '').trim().toLowerCase();
    els.bridgeList.innerHTML = '';
    bridges
      .filter(function (b) {
        if (!q) return true;
        var blob = [b.name, b.dynasty, b.province, b.type].join(' ').toLowerCase();
        return blob.indexOf(q) >= 0;
      })
      .forEach(function (b) {
        var li = document.createElement('li');
        li.className = b.name === focusBridge ? 'active' : '';
        li.innerHTML =
          b.name +
          '<span class="meta">' +
          [b.dynasty, b.type, b.province].filter(Boolean).join(' · ') +
          '</span>';
        li.addEventListener('click', function () {
          setFocus(b.name);
        });
        els.bridgeList.appendChild(li);
      });
  }

  function modeLabel(mode) {
    if (mode === 'study_path') return '研学路线';
    if (mode === 'bedrock') return 'AWS Bedrock';
    if (mode === 'openai') return '大模型增强';
    return '本地检索 + 记忆';
  }

  async function ensureSession() {
    if (sessionId) return sessionId;
    var res = await fetch(API + '/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ focus_bridge: focusBridge || null })
    });
    var data = await res.json();
    sessionId = data.id;
    localStorage.setItem('qh_session_id', sessionId);
    return sessionId;
  }

  function renderDossier(data) {
    if (!data || !data.dossier) return;
    var d = data.dossier;
    var total = d.total_bridges || bridges.length || 34;
    els.dossierProgress.textContent =
      '已了解 ' + d.learned_count + ' / ' + total + ' 座';
    els.dossierLearned.innerHTML = (d.learned_bridges || [])
      .slice(0, 8)
      .map(function (n) {
        return '<span class="dossier-tag">' + escapeHtml(n) + '</span>';
      })
      .join('');
    if (data.study_path && data.study_path.stops) {
      var sp = data.study_path;
      var step = sp.current_step || 0;
      els.studyPathBox.textContent =
        (sp.title || '研学路线') + ' — 第 ' + (step + 1) + '/' + sp.stops.length + ' 站';
    } else {
      els.studyPathBox.textContent = '暂无进行中的路线（可问：规划宋代桥梁研学路线）';
    }
  }

  async function refreshDossier() {
    if (!sessionId) return;
    try {
      var res = await fetch(API + '/api/dossier/' + sessionId);
      if (!res.ok) return;
      renderDossier(await res.json());
    } catch (e) { /* ignore */ }
  }

  async function loadSessionHistory() {
    if (!sessionId) return;
    try {
      var res = await fetch(API + '/api/sessions/' + sessionId);
      if (!res.ok) {
        sessionId = '';
        localStorage.removeItem('qh_session_id');
        return;
      }
      var data = await res.json();
      if (data.session && data.session.focus_bridge) {
        setFocus(data.session.focus_bridge);
      }
      (data.messages || []).forEach(function (m) {
        if (m.role === 'user' || m.role === 'assistant') {
          var meta = m.mode ? modeLabel(m.mode) : '';
          if (m.sources && m.sources.length) {
            meta += (meta ? ' · ' : '') + '引用：' + m.sources.slice(0, 3).join('、');
          }
          appendMessage(m.role === 'user' ? 'user' : 'bot', m.content, meta || undefined);
        }
      });
      await refreshDossier();
    } catch (e) {
      console.warn('load session', e);
    }
  }

  async function sendMessage(textOverride) {
    var text = (textOverride || els.input.value || '').trim();
    if (!text) return;
    els.send.disabled = true;
    appendMessage('user', text);
    if (!textOverride) els.input.value = '';
    var typing = appendMessage('bot', '正在思考…', '请稍候');
    typing.classList.add('typing');

    try {
      await ensureSession();
      var res = await fetch(API + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
          focus_bridge: focusBridge || null
        })
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var data = await res.json();
      typing.remove();
      var meta = modeLabel(data.mode);
      if (data.sources && data.sources.length) {
        meta += ' · 引用：' + data.sources.slice(0, 3).join('、');
      }
      appendMessage('bot', data.text, meta);
      if (data.focus_bridge) setFocus(data.focus_bridge);
      await refreshDossier();
    } catch (err) {
      typing.remove();
      appendMessage('bot', '请求失败：' + err.message, '请确认后端已启动');
    } finally {
      els.send.disabled = false;
    }
  }

  async function init() {
    parseUrlParams();

    CHIPS.forEach(function (q) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ai-chip';
      btn.textContent = q;
      btn.addEventListener('click', function () {
        els.input.value = q;
        sendMessage();
      });
      els.chips.appendChild(btn);
    });

    els.send.addEventListener('click', function () { sendMessage(); });
    els.input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    els.bridgeSearch.addEventListener('input', function () {
      renderBridgeList(els.bridgeSearch.value);
    });
    els.clearFocus.addEventListener('click', function () {
      setFocus('');
    });

    try {
      var health = await fetch(API + '/api/health').then(function (r) { return r.json(); });
      els.statusPill.textContent =
        '存储：' + health.storage_mode + ' · LLM：' + health.llm_mode;
    } catch (e) {
      els.statusPill.textContent = '后端未连接';
    }

    try {
      var bRes = await fetch(API + '/api/bridges');
      var bData = await bRes.json();
      bridges = bData.items || [];
      renderBridgeList('');
    } catch (e) {
      els.bridgeList.innerHTML = '<li>桥梁列表加载失败</li>';
    }

    if (focusBridge) setFocus(focusBridge);

    if (!sessionId) {
      appendMessage(
        'bot',
        '您好，我是飞虹智忆档案员。\n\n' +
          '· 在 bridge 图鉴中点击桥梁，我会记住您的浏览轨迹\n' +
          '· 可规划研学路线，发送「继续」推进下一站\n' +
          '· 左侧档案面板会记录您已了解的古桥',
        '千古飞虹 · Agent 记忆层'
      );
      await ensureSession();
      await refreshDossier();
    } else {
      await loadSessionHistory();
    }

    if (pendingQuery) {
      await sendMessage(pendingQuery);
      pendingQuery = '';
    } else if (focusBridge && !sessionId) {
      /* handled above */
    } else if (focusBridge && sessionId) {
      var hist = els.messages.querySelectorAll('.ai-msg').length;
      if (hist <= 1) {
        await sendMessage('介绍' + focusBridge);
      }
    }
  }

  init();
})();
