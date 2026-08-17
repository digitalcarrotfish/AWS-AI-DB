(function () {
  'use strict';

  var API = '';
  var sessionId = localStorage.getItem('qh_session_id') || '';
  var focusBridge = localStorage.getItem('qh_focus_bridge') || '';
  var bridges = [];
  var pendingQuery = '';
  var returnFrom = '';
  var greeted = false;
  var lastEvents = [];

  var SOURCE_LABEL = {
    knowledge_graph: '知识图谱',
    bridge_detail: '桥梁档案',
    museum_map: '地图大屏',
    word_cloud: '文化热词',
    bridge_3d: '三维模型',
    museum: '数字博物馆',
    agent: '档案员'
  };

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
    trailList: document.getElementById('trailList'),
    statusPill: document.getElementById('statusPill'),
    clearFocus: document.getElementById('clearFocus'),
    chips: document.getElementById('chips'),
    memoryBanner: document.getElementById('memoryBanner'),
    navBackExplore: document.getElementById('navBackExplore'),
    interestBox: document.getElementById('interestBox'),
    exportS3Btn: document.getElementById('exportS3Btn'),
    exportS3Status: document.getElementById('exportS3Status'),
    opsHealth: document.getElementById('opsHealth'),
    opsRefresh: document.getElementById('opsRefresh'),
    opsScore: document.getElementById('opsScore'),
    opsVerdict: document.getElementById('opsVerdict'),
    opsCaptured: document.getElementById('opsCaptured'),
    opsMetrics: document.getElementById('opsMetrics'),
    opsStorage: document.getElementById('opsStorage'),
    opsVector: document.getElementById('opsVector'),
    opsCloud: document.getElementById('opsCloud'),
    opsInsights: document.getElementById('opsInsights'),
    opsAudit: document.getElementById('opsAudit'),
    opsNext: document.getElementById('opsNext')
  };

  var BASE_CHIPS = [
    '我的档案',
    '推荐下一座',
    '根据浏览规划研学路线',
    '规划一条宋代桥梁研学路线',
    '对比赵州桥和卢沟桥',
    '数据库集群状态',
    '继续'
  ];

  function parseUrlParams() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('session')) sessionId = params.get('session');
    if (params.get('bridge')) focusBridge = params.get('bridge');
    if (params.get('q')) pendingQuery = params.get('q');
    if (params.get('from')) returnFrom = params.get('from');
    if (sessionId) localStorage.setItem('qh_session_id', sessionId);
    if (focusBridge) localStorage.setItem('qh_focus_bridge', focusBridge);
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
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

  function createTraceMessage() {
    var div = document.createElement('div');
    div.className = 'ai-msg bot whitebox-msg';
    div.innerHTML =
      '<div class="trace-card">' +
        '<div class="trace-head">' +
          '<span><i></i>SSE 白盒执行</span>' +
          '<small class="trace-clock">连接中…</small>' +
        '</div>' +
        '<ol class="trace-steps">' +
          '<li class="trace-empty">等待 Agent 返回执行事件…</li>' +
        '</ol>' +
        '<p class="trace-note">展示可审计工具轨迹，不展示模型私有思维链</p>' +
      '</div>';
    div._traceItems = {};
    els.messages.appendChild(div);
    els.messages.scrollTop = els.messages.scrollHeight;
    return div;
  }

  function updateTraceMessage(container, payload) {
    var list = container.querySelector('.trace-steps');
    var empty = list.querySelector('.trace-empty');
    if (empty) empty.remove();
    var stage = payload.stage || ('step-' + payload.seq);
    var item = container._traceItems[stage];
    if (!item || (item.dataset.status !== 'running' && payload.status === 'running')) {
      item = document.createElement('li');
      item.className = 'trace-step';
      item.dataset.stage = stage;
      item.innerHTML =
        '<span class="trace-dot"></span>' +
        '<div class="trace-step-body">' +
          '<strong></strong><p></p><details><summary>查看证据</summary><pre></pre></details>' +
        '</div>' +
        '<time></time>';
      list.appendChild(item);
      container._traceItems[stage] = item;
    }
    item.dataset.status = payload.status || 'done';
    item.className = 'trace-step is-' + (payload.status || 'done');
    item.querySelector('strong').textContent = payload.title || stage;
    item.querySelector('p').textContent = payload.detail || '';
    item.querySelector('time').textContent = (payload.elapsed_ms || 0) + 'ms';
    var details = item.querySelector('details');
    var evidence = payload.data || {};
    if (Object.keys(evidence).length) {
      details.classList.remove('is-hidden');
      item.querySelector('pre').textContent = JSON.stringify(evidence, null, 2);
    } else {
      details.classList.add('is-hidden');
    }
    container.querySelector('.trace-clock').textContent =
      payload.status === 'running' ? '执行中' : ((payload.elapsed_ms || 0) + ' ms');
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  function finishTraceMessage(container, elapsed) {
    container.querySelector('.trace-head span').lastChild.textContent = 'SSE 白盒执行完成';
    container.querySelector('.trace-clock').textContent = elapsed + ' ms';
    container.classList.add('is-complete');
  }

  function parseSseBlock(block) {
    var eventName = 'message';
    var dataLines = [];
    block.split(/\r?\n/).forEach(function (line) {
      if (line.indexOf('event:') === 0) eventName = line.slice(6).trim();
      if (line.indexOf('data:') === 0) dataLines.push(line.slice(5).trim());
    });
    if (!dataLines.length) return null;
    return { event: eventName, data: JSON.parse(dataLines.join('\n')) };
  }

  async function streamChat(payload, onEvent) {
    var res = await fetch(API + '/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    if (!res.body || !res.body.getReader) throw new Error('浏览器不支持流式响应');

    var reader = res.body.getReader();
    var decoder = new TextDecoder('utf-8');
    var buffer = '';
    while (true) {
      var part = await reader.read();
      buffer += decoder.decode(part.value || new Uint8Array(), { stream: !part.done });
      var boundary;
      while ((boundary = buffer.search(/\r?\n\r?\n/)) >= 0) {
        var block = buffer.slice(0, boundary);
        var match = buffer.slice(boundary).match(/^\r?\n\r?\n/);
        buffer = buffer.slice(boundary + (match ? match[0].length : 2));
        var parsed = parseSseBlock(block);
        if (parsed) onEvent(parsed.event, parsed.data);
      }
      if (part.done) break;
    }
    if (buffer.trim()) {
      var tail = parseSseBlock(buffer.trim());
      if (tail) onEvent(tail.event, tail.data);
    }
  }

  function setFocus(name, opts) {
    opts = opts || {};
    focusBridge = name || '';
    if (focusBridge) localStorage.setItem('qh_focus_bridge', focusBridge);
    else localStorage.removeItem('qh_focus_bridge');
    els.focusLabel.textContent = focusBridge || '未选择';
    renderBridgeList(els.bridgeSearch.value);
    if (opts.fillIntro && focusBridge) {
      els.input.value = '介绍' + focusBridge;
      els.input.focus();
    }
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
          escapeHtml(b.name) +
          '<span class="meta">' +
          escapeHtml([b.dynasty, b.type, b.province].filter(Boolean).join(' · ')) +
          '</span>';
        li.addEventListener('click', function () {
          setFocus(b.name, { fillIntro: true });
        });
        els.bridgeList.appendChild(li);
      });
  }

  function modeLabel(mode) {
    if (mode === 'study_path') return '研学路线';
    if (mode === 'memory') return '记忆驱动';
    if (mode === 'bedrock') return 'AWS Bedrock';
    if (mode === 'openai') return '大模型增强';
    if (mode === 'ccloud') return 'ccloud CLI';
    return '本地检索 + 记忆';
  }

  function eventLabel(ev) {
    var src = SOURCE_LABEL[ev.source] || ev.source || '图鉴';
    var type = ev.event_type || 'view';
    var bridge = ev.bridge ? '「' + ev.bridge + '」' : '';
    if (type === 'view_detail' || type === 'open_detail') return src + ' · 查看' + bridge;
    if (type === 'view_3d') return src + ' · 三维' + bridge;
    if (type === 'open_archivist') return src + ' · 打开档案员' + bridge;
    if (type === 'select_bridge') return src + ' · 选中' + bridge;
    if (type === 'view_map') return '进入地图大屏';
    if (type === 'view_knowledge') return '进入智能驿站';
    return src + (bridge ? ' · ' + bridge : '') + ' · ' + type;
  }

  function renderTrail(events) {
    if (!els.trailList) return;
    lastEvents = events || [];
    var list = lastEvents.filter(function (ev) {
      return ev && ev.bridge && ev.event_type !== 'open_archivist';
    }).slice().reverse().slice(0, 8);
    if (!list.length) {
      els.trailList.innerHTML =
        '<li class="trail-empty">在图鉴中点开桥梁后，轨迹会出现在这里</li>';
      return;
    }
    els.trailList.innerHTML = '';
    list.forEach(function (ev) {
      var li = document.createElement('li');
      li.className = 'trail-item';
      li.innerHTML =
        '<button type="button" class="trail-btn">' +
        escapeHtml(eventLabel(ev)) +
        '</button>';
      li.querySelector('button').addEventListener('click', function () {
        setFocus(ev.bridge, { fillIntro: true });
      });
      els.trailList.appendChild(li);
    });
  }

  function showMemoryBanner(events) {
    if (!els.memoryBanner) return;
    var withBridge = (events || []).filter(function (e) {
      return e && e.bridge && e.event_type !== 'open_archivist';
    });
    if (!withBridge.length) {
      els.memoryBanner.classList.add('is-hidden');
      els.memoryBanner.textContent = '';
      return;
    }
    var last = withBridge[withBridge.length - 1];
    var src = SOURCE_LABEL[last.source] || last.source || '图鉴';
    els.memoryBanner.innerHTML =
      '记忆已同步：你刚从【' + escapeHtml(src) + '】关注了「' +
      escapeHtml(last.bridge) +
      '」 · <button type="button" class="banner-link" id="bannerAsk">就此讲解</button>' +
      ' · <button type="button" class="banner-link" id="bannerNext">推荐下一座</button>';
    els.memoryBanner.classList.remove('is-hidden');
    var ask = document.getElementById('bannerAsk');
    var next = document.getElementById('bannerNext');
    if (ask) {
      ask.addEventListener('click', function () {
        setFocus(last.bridge);
        sendMessage('介绍' + last.bridge);
      });
    }
    if (next) {
      next.addEventListener('click', function () {
        sendMessage('推荐下一座');
      });
    }
  }

  function renderInterests(interests) {
    if (!els.interestBox) return;
    var list = interests || [];
    if (!list.length) {
      els.interestBox.innerHTML = '<span class="muted">尚无兴趣标签</span>';
      return;
    }
    els.interestBox.innerHTML = list
      .slice(0, 8)
      .map(function (t) {
        return '<span class="dossier-tag">' + escapeHtml(t) + '</span>';
      })
      .join('');
  }

  function refreshChips() {
    if (!els.chips) return;
    els.chips.innerHTML = '';
    var chips = BASE_CHIPS.slice();
    if (focusBridge) {
      chips.unshift('介绍' + focusBridge);
    }
    chips.forEach(function (q) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ai-chip';
      btn.textContent = q;
      btn.addEventListener('click', function () {
        sendMessage(q);
      });
      els.chips.appendChild(btn);
    });
  }

  async function ensureSession() {
    if (sessionId) {
      try {
        var check = await fetch(API + '/api/sessions/' + encodeURIComponent(sessionId));
        if (check.ok) return sessionId;
        sessionId = '';
        localStorage.removeItem('qh_session_id');
      } catch (e) {
        return sessionId;
      }
    }
    var res = await fetch(API + '/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ focus_bridge: focusBridge || null })
    });
    if (!res.ok) throw new Error('无法创建会话');
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
    els.dossierLearned.innerHTML = '';
    (d.learned_bridges || []).slice(0, 10).forEach(function (n) {
      var a = document.createElement('a');
      a.className = 'dossier-tag dossier-tag--link';
      a.href = '/bridge-detail.html?name=' + encodeURIComponent(n);
      a.textContent = n;
      a.title = '打开博物馆档案';
      a.addEventListener('click', function (e) {
        // 同时设为焦点，方便回来继续问
        setFocus(n);
      });
      els.dossierLearned.appendChild(a);
    });
    renderInterests(d.interests || []);
    if (data.study_path && data.study_path.stops) {
      var sp = data.study_path;
      var step = sp.current_step || 0;
      els.studyPathBox.textContent =
        (sp.title || '研学路线') + ' — 第 ' + (step + 1) + '/' + sp.stops.length + ' 站';
    } else {
      els.studyPathBox.textContent = '暂无进行中的路线（可问：根据浏览规划研学路线）';
    }
    renderTrail(data.events || []);
    showMemoryBanner(data.events || []);
    refreshChips();
  }

  async function refreshDossier() {
    if (!sessionId) return;
    try {
      var res = await fetch(API + '/api/dossier/' + encodeURIComponent(sessionId));
      if (!res.ok) return;
      renderDossier(await res.json());
    } catch (e) { /* ignore */ }
  }

  function compactNumber(value) {
    var n = Number(value || 0);
    if (n >= 10000) return (n / 10000).toFixed(n >= 100000 ? 0 : 1) + '万';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
    return String(n);
  }

  function shortTime(value) {
    if (!value) return '刚刚';
    var date = new Date(value);
    if (isNaN(date.getTime())) return '';
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }

  function renderMemoryOps(data) {
    var memory = data.memory || {};
    var counts = memory.counts || {};
    var vector = memory.vector_index || {};
    var cloud = data.ccloud || {};
    var healthy = data.status === 'healthy';

    els.opsHealth.className = 'ops-health ' + (healthy ? 'healthy' : 'attention');
    els.opsHealth.innerHTML = '<i></i>' + (healthy ? '记忆层健康' : '需要关注');
    els.opsScore.textContent = String(data.health_score == null ? '--' : data.health_score);
    els.opsVerdict.textContent = healthy ? '生产记忆链路运行中' : '记忆链路尚未完整';
    els.opsCaptured.textContent = '快照 ' + shortTime(memory.captured_at);

    var metrics = [
      ['古桥知识', counts.bridges],
      ['向量记忆', counts.embeddings],
      ['探索事件', counts.events],
      ['工具审计', counts.tool_calls]
    ];
    els.opsMetrics.innerHTML = metrics.map(function (item) {
      return '<div class="ops-metric"><span>' + escapeHtml(item[0]) +
        '</span><strong>' + escapeHtml(compactNumber(item[1])) + '</strong></div>';
    }).join('');

    els.opsStorage.textContent =
      memory.backend === 'cockroach' ? 'CockroachDB · 持久化' : 'JSON · 回退模式';
    els.opsStorage.className = memory.backend === 'cockroach' ? 'ok' : 'warn';
    els.opsVector.textContent = vector.active
      ? (vector.name || 'Distributed Vector Index')
      : '未检测到';
    els.opsVector.className = vector.active ? 'ok' : 'warn';
    els.opsCloud.textContent = cloud.ok
      ? ((cloud.cluster_count || 0) + ' 个 Cloud 集群')
      : (cloud.error === 'ccloud_not_installed' ? '待接 ccloud / MCP' : '认证待完成');
    els.opsCloud.className = cloud.ok ? 'ok' : 'warn';

    els.opsInsights.innerHTML = (data.insights || []).map(function (text) {
      return '<li title="' + escapeHtml(text) + '">' + escapeHtml(text) + '</li>';
    }).join('') || '<li>暂无判断</li>';
    els.opsAudit.innerHTML = (memory.recent_tools || []).slice(0, 4).map(function (call) {
      var marker = call.ok ? '✓' : '!';
      return '<li title="' + escapeHtml(call.tool_name || '') + '">' +
        marker + ' ' + escapeHtml(call.tool_name || 'unknown') +
        ' · ' + escapeHtml(shortTime(call.created_at)) + '</li>';
    }).join('') || '<li>暂无审计记录</li>';
    els.opsNext.textContent = '下一步：' + (data.next_action || '继续积累可行动的长期记忆');
  }

  async function refreshMemoryOps() {
    if (!els.opsRefresh) return;
    els.opsRefresh.disabled = true;
    els.opsRefresh.textContent = '读取中…';
    try {
      var res = await fetch(API + '/api/memory/ops', { cache: 'no-store' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      renderMemoryOps(await res.json());
    } catch (e) {
      els.opsHealth.className = 'ops-health error';
      els.opsHealth.innerHTML = '<i></i>快照失败';
      els.opsVerdict.textContent = '无法读取记忆层运行状态';
      els.opsNext.textContent = '请确认 CockroachDB 与 API 已启动';
    } finally {
      els.opsRefresh.disabled = false;
      els.opsRefresh.textContent = '刷新快照';
    }
  }

  async function loadSessionHistory() {
    if (!sessionId) return false;
    try {
      var res = await fetch(API + '/api/sessions/' + encodeURIComponent(sessionId));
      if (!res.ok) {
        sessionId = '';
        localStorage.removeItem('qh_session_id');
        return false;
      }
      var data = await res.json();
      if (data.session && data.session.focus_bridge && !focusBridge) {
        setFocus(data.session.focus_bridge);
      }
      var msgs = data.messages || [];
      msgs.forEach(function (m) {
        if (m.role === 'user' || m.role === 'assistant') {
          var meta = m.mode ? modeLabel(m.mode) : '';
          if (m.sources && m.sources.length) {
            meta += (meta ? ' · ' : '') + '引用：' + m.sources.slice(0, 3).join('、');
          }
          appendMessage(m.role === 'user' ? 'user' : 'bot', m.content, meta || undefined);
        }
      });
      renderTrail(data.events || []);
      showMemoryBanner(data.events || []);
      await refreshDossier();
      return msgs.length > 0;
    } catch (e) {
      console.warn('load session', e);
      return false;
    }
  }

  async function sendMessage(textOverride) {
    var text = (textOverride || els.input.value || '').trim();
    if (!text) return;
    els.send.disabled = true;
    appendMessage('user', text);
    if (!textOverride) els.input.value = '';
    var traceView = createTraceMessage();

    try {
      await ensureSession();
      var data = null;
      await streamChat({
        session_id: sessionId,
        message: text,
        focus_bridge: focusBridge || null
      }, function (eventName, payload) {
        if (eventName === 'start') {
          traceView.querySelector('.trace-clock').textContent = '0 ms';
        } else if (eventName === 'trace') {
          updateTraceMessage(traceView, payload);
        } else if (eventName === 'final') {
          data = payload;
          finishTraceMessage(traceView, payload.elapsed_ms || 0);
        } else if (eventName === 'error') {
          throw new Error(payload.message || payload.code || '流式执行失败');
        }
      });
      if (!data) throw new Error('SSE 已结束，但未收到最终回答');
      if (data.session_id) {
        sessionId = data.session_id;
        localStorage.setItem('qh_session_id', sessionId);
      }
      var meta = modeLabel(data.mode);
      if (data.sources && data.sources.length) {
        meta += ' · 引用：' + data.sources.slice(0, 3).join('、');
      }
      appendMessage('bot', data.text, meta);
      if (data.focus_bridge) setFocus(data.focus_bridge);
      await refreshDossier();
      await refreshMemoryOps();
    } catch (err) {
      traceView.classList.add('has-error');
      traceView.querySelector('.trace-clock').textContent = '执行失败';
      appendMessage(
        'bot',
        '请求失败：' + err.message + '\n请确认已运行 python -m api.main，并打开 http://127.0.0.1:8787/',
        '连接档案员'
      );
    } finally {
      els.send.disabled = false;
    }
  }

  function setupReturnLink() {
    if (!els.navBackExplore) return;
    if (!returnFrom) {
      els.navBackExplore.classList.add('is-hidden');
      return;
    }
    var href = returnFrom;
    if (href.charAt(0) !== '/' && href.indexOf('http') !== 0) href = '/' + href.replace(/^\.\//, '');
    if (href.indexOf('/agent') === 0) {
      els.navBackExplore.classList.add('is-hidden');
      return;
    }
    els.navBackExplore.href = href;
    els.navBackExplore.textContent = '← 返回浏览';
    els.navBackExplore.classList.remove('is-hidden');
  }

  function welcomeText() {
    return (
      '您好，我是飞虹智忆档案员。记忆不只是聊天记录：\n\n' +
      '· 图鉴浏览会写入轨迹，左侧档案会累计「已了解」\n' +
      '· 可问「我的档案」「推荐下一座」「根据浏览规划研学路线」\n' +
      '· 讲解后会提示尚未探索的相关桥；发送「继续」推进研学站'
    );
  }

  async function init() {
    parseUrlParams();
    setupReturnLink();
    refreshChips();

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
      refreshChips();
    });
    if (els.opsRefresh) {
      els.opsRefresh.addEventListener('click', refreshMemoryOps);
    }
    if (els.exportS3Btn) {
      els.exportS3Btn.addEventListener('click', async function () {
        if (!sessionId) {
          els.exportS3Status.textContent = '请先产生会话（浏览或对话一次）';
          return;
        }
        els.exportS3Btn.disabled = true;
        els.exportS3Status.textContent = '上传中…';
        try {
          var res = await fetch(API + '/api/reports/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
          });
          var data = await res.json().catch(function () { return {}; });
          if (!res.ok) {
            els.exportS3Status.textContent = data.detail || ('导出失败 ' + res.status);
            return;
          }
          els.exportS3Status.textContent = data.uri || '已写入 S3';
        } catch (e) {
          els.exportS3Status.textContent = '网络错误';
        } finally {
          els.exportS3Btn.disabled = false;
        }
      });
    }

    try {
      var health = await fetch(API + '/api/health').then(function (r) { return r.json(); });
      var awsBit = '';
      if (health.aws) {
        if (health.aws.s3) awsBit = ' · S3';
        else if (health.aws.bedrock) awsBit = ' · Bedrock';
      }
      var llmBit = health.llm_mode;
      if (health.llm_mode === 'openai') {
        llmBit = health.llm_configured
          ? 'Kimi' + (health.llm_model ? ' · ' + health.llm_model : '')
          : 'openai（未填密钥）';
      }
      els.statusPill.textContent =
        '存储：' + health.storage_mode + ' · LLM：' + llmBit +
        (health.museum ? ' · 同域博物馆' : '') + awsBit;
      els.statusPill.classList.add('ok');
    } catch (e) {
      els.statusPill.textContent = '后端未连接';
      els.statusPill.classList.add('err');
    }

    try {
      var bRes = await fetch(API + '/api/bridges');
      var bData = await bRes.json();
      bridges = bData.items || [];
      renderBridgeList('');
    } catch (e) {
      els.bridgeList.innerHTML = '<li>桥梁列表加载失败</li>';
    }
    await refreshMemoryOps();

    if (focusBridge) setFocus(focusBridge);

    var hadHistory = false;
    if (sessionId) {
      hadHistory = await loadSessionHistory();
    }

    if (!sessionId) {
      try {
        await ensureSession();
        await refreshDossier();
      } catch (e) { /* shown on send */ }
    }

    if (!hadHistory && !greeted) {
      appendMessage('bot', welcomeText(), '千古飞虹 · Agentic Memory');
      greeted = true;
    }

    if (pendingQuery) {
      var q = pendingQuery;
      pendingQuery = '';
      await sendMessage(q);
    } else if (focusBridge && !hadHistory) {
      els.input.value = '介绍' + focusBridge;
      els.input.focus();
    }
    refreshChips();
  }

  init();
})();
