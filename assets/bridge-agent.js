/**
 * 千古飞虹 → 飞虹智忆
 * 同域优先：博物馆与 Agent 共享 localStorage 会话。
 */
(function (global) {
  'use strict';

  var SESSION_KEY = 'qh_session_id';
  var FOCUS_KEY = 'qh_focus_bridge';
  var recentTracks = Object.create(null);
  var online = null;

  function defaults() {
    var port = String(global.location.port || '');
    // 纯静态 :8080 预览时回退到本机 Agent；同域 :8787 则走相对路径
    var staticPreview = port === '8080' || port === '5500' || port === '3000';
    return {
      enabled: true,
      apiBase: staticPreview ? 'http://127.0.0.1:8787' : '',
      agentUi: staticPreview ? 'http://127.0.0.1:8787/agent/' : '/agent/'
    };
  }

  function cfg() {
    var d = defaults();
    var c = global.QIANHONG_AGENT || {};
    var apiBase = c.apiBase;
    if (apiBase == null) apiBase = d.apiBase;
    apiBase = String(apiBase).replace(/\/$/, '');
    var agentUi = c.agentUi != null ? String(c.agentUi) : d.agentUi;
    if (!/\/$/.test(agentUi) && agentUi.indexOf('?') === -1) agentUi += '/';
    return {
      enabled: c.enabled !== false,
      apiBase: apiBase,
      agentUi: agentUi
    };
  }

  function t(key, fallback) {
    if (global.BridgeI18n && typeof global.BridgeI18n.t === 'function') {
      var v = global.BridgeI18n.t(key);
      if (v && v !== key) return v;
    }
    return fallback;
  }

  function getSessionId() {
    return localStorage.getItem(SESSION_KEY) || '';
  }

  function setSessionId(id) {
    if (id) localStorage.setItem(SESSION_KEY, id);
    else localStorage.removeItem(SESSION_KEY);
  }

  function getFocusBridge() {
    return localStorage.getItem(FOCUS_KEY) || '';
  }

  function setFocusBridge(name) {
    if (name) localStorage.setItem(FOCUS_KEY, name);
    else localStorage.removeItem(FOCUS_KEY);
  }

  function apiUrl(path) {
    var base = cfg().apiBase;
    if (!path) path = '/';
    if (path.charAt(0) !== '/') path = '/' + path;
    return base + path;
  }

  function api(path, options) {
    return fetch(apiUrl(path), options);
  }

  function createSession(focusBridge) {
    return api('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ focus_bridge: focusBridge || null })
    }).then(function (res) {
      if (!res.ok) throw new Error('session ' + res.status);
      return res.json();
    }).then(function (data) {
      setSessionId(data.id);
      return data.id;
    });
  }

  function ensureSession(focusBridge) {
    var c = cfg();
    if (!c.enabled) return Promise.resolve('');
    var existing = getSessionId();
    if (!existing) {
      return createSession(focusBridge).catch(function (err) {
        console.warn('[QianhongAgent] createSession', err);
        setOnline(false);
        return '';
      });
    }
    return api('/api/sessions/' + encodeURIComponent(existing))
      .then(function (res) {
        if (res.status === 404) {
          setSessionId('');
          return createSession(focusBridge);
        }
        if (!res.ok) throw new Error('session check ' + res.status);
        setOnline(true);
        return existing;
      })
      .catch(function (err) {
        // 网络失败时保留本地 session，仍尝试上报
        console.warn('[QianhongAgent] ensureSession', err);
        setOnline(false);
        return existing;
      });
  }

  function trackKey(eventType, source, bridge) {
    return [eventType || '', source || '', bridge || ''].join('|');
  }

  function shouldDedupe(eventType, source, bridge) {
    var key = trackKey(eventType, source, bridge);
    var now = Date.now();
    var last = recentTracks[key] || 0;
    if (now - last < 1800) return true;
    recentTracks[key] = now;
    return false;
  }

  function track(eventType, source, bridge, meta) {
    var c = cfg();
    if (!c.enabled) return Promise.resolve(null);
    if (shouldDedupe(eventType, source, bridge)) {
      return Promise.resolve({ ok: true, deduped: true, session_id: getSessionId() });
    }
    if (bridge) setFocusBridge(bridge);
    return ensureSession(bridge).then(function (sessionId) {
      if (!sessionId) return null;
      return api('/api/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          event_type: eventType || 'view',
          source: source || 'museum',
          bridge: bridge || null,
          meta: meta || null
        })
      })
        .then(function (res) {
          if (!res.ok) throw new Error('event ' + res.status);
          setOnline(true);
          return res.json();
        })
        .then(function (data) {
          if (data && data.session_id) setSessionId(data.session_id);
          return data;
        })
        .catch(function (err) {
          console.warn('[QianhongAgent] track', err);
          setOnline(false);
          return null;
        });
    });
  }

  function wait(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function openArchivist(opts) {
    opts = opts || {};
    if (global.BridgeAssistant && typeof global.BridgeAssistant.open === 'function' && opts.forcePage !== true) {
      global.BridgeAssistant.open({
        bridge: opts.bridge || getFocusBridge() || undefined,
        q: opts.q || '',
        autoAsk: opts.autoAsk === true,
        tab: opts.tab || 'chat'
      });
      return Promise.resolve();
    }
    var c = cfg();
    var bridge = opts.bridge || getFocusBridge() || '';
    var q = opts.q || '';
    var autoAsk = opts.autoAsk === true;
    if (bridge) setFocusBridge(bridge);

    var go = function () {
      var url;
      try {
        url = new URL(c.agentUi, global.location.href);
      } catch (e) {
        global.location.href = c.agentUi;
        return;
      }
      var sid = getSessionId();
      if (sid) url.searchParams.set('session', sid);
      if (bridge) url.searchParams.set('bridge', bridge);
      // 仅显式要求时自动发问，避免每次打开都刷「介绍X」
      if (autoAsk && q) url.searchParams.set('q', q);
      if (opts.from) url.searchParams.set('from', opts.from);
      else url.searchParams.set('from', global.location.pathname + global.location.search);
      global.location.href = url.toString();
    };

    if (!c.enabled) {
      go();
      return Promise.resolve();
    }

    var p = track('open_archivist', opts.source || pageSource(), bridge || null, {
      q: q || null,
      autoAsk: autoAsk,
      page: global.location.pathname
    });
    return Promise.race([p, wait(2000)]).then(go).catch(go);
  }

  function detailUrl(name, fromYear) {
    var url = 'bridge-detail.html?name=' + encodeURIComponent(name || '');
    if (fromYear != null && fromYear !== '') url += '&fromYear=' + encodeURIComponent(fromYear);
    return url;
  }

  function goDetail(name, fromYear, source) {
    var src = source || 'museum_map';
    // 标记：详情页 autoTrack 跳过紧随其后的重复 open
    recentTracks[trackKey('open_detail', src, name)] = Date.now();
    return track('open_detail', src, name, { fromYear: fromYear }).then(function () {
      global.location.href = detailUrl(name, fromYear);
    }).catch(function () {
      global.location.href = detailUrl(name, fromYear);
    });
  }

  function parseNameFromHref(href) {
    try {
      var u = new URL(href, global.location.href);
      if (u.pathname.indexOf('bridge-detail') === -1) return null;
      return u.searchParams.get('name');
    } catch (e) {
      return null;
    }
  }

  function bindLinkDelegation() {
    if (global.__qhAgentLinkBound) return;
    global.__qhAgentLinkBound = true;
    document.addEventListener(
      'click',
      function (e) {
        var a = e.target && e.target.closest ? e.target.closest('a[href*="bridge-detail.html"]') : null;
        if (!a) return;
        // 已被页面 preventDefault 的卡片点击会走 goDetail；此处只覆盖地图弹窗等真链跳转
        if (e.defaultPrevented) return;
        var name = parseNameFromHref(a.getAttribute('href'));
        if (!name) return;
        var source = pageSource() === 'knowledge_graph' ? 'knowledge_graph' : 'museum_map';
        // 不拦截跳转，只异步记一笔（去重）
        track('open_detail', source, name, { via: 'link' });
      },
      true
    );
  }

  function pageSource() {
    var path = (global.location.pathname || '').toLowerCase();
    if (path.indexOf('bridge-detail') >= 0) return 'bridge_detail';
    if (path.indexOf('knowledge') >= 0) return 'knowledge_graph';
    if (path.indexOf('bridge-3d') >= 0) return 'bridge_3d';
    if (path.indexOf('museum') >= 0) return 'museum_map';
    if (path.indexOf('closing') >= 0) return 'closing';
    if (path.indexOf('/agent') >= 0) return 'agent';
    return 'museum';
  }

  function autoTrackPage() {
    var params = new URLSearchParams(global.location.search);
    var name = params.get('name') || '';
    var source = pageSource();
    if (source === 'bridge_detail' && name) {
      track('view_detail', 'bridge_detail', name, { fromYear: params.get('fromYear') });
      return;
    }
    if (source === 'bridge_3d' && name) {
      track('view_3d', 'bridge_3d', name, { model: params.get('model') });
      return;
    }
    if (source === 'museum_map') {
      track('view_map', 'museum_map', null, null);
      return;
    }
    if (source === 'knowledge_graph') {
      track('view_knowledge', 'knowledge_graph', null, null);
    }
  }

  function setOnline(flag) {
    online = !!flag;
    var fab = document.getElementById('qhAsstFab') || document.getElementById('qhAgentFab');
    if (!fab) return;
    fab.classList.toggle('is-offline', !online);
    fab.classList.toggle('is-online', online);
    var tip = online
      ? t('agent.fabTitle', '打开飞虹智忆档案员（带浏览记忆）')
      : t('agent.offlineTitle', '档案员未连接 — 仍可打开，需先启动后端');
    fab.title = tip;
  }

  function updateFabLabel(btn) {
    btn.textContent = t('agent.fab', '问档案员');
    btn.setAttribute('aria-label', btn.textContent);
    if (online === false) {
      btn.title = t('agent.offlineTitle', '档案员未连接 — 仍可打开，需先启动后端');
    } else {
      btn.title = t('agent.fabTitle', '打开飞虹智忆档案员（带浏览记忆）');
    }
  }

  function mountFab(options) {
    options = options || {};
    var c = cfg();
    if (!c.enabled && options.force !== true) return null;
    // 优先悬浮小助手（对话 + 扫桥）
    if (global.BridgeAssistant && typeof global.BridgeAssistant.mount === 'function') {
      return global.BridgeAssistant.mount(options);
    }
    if (document.getElementById('qhAgentFab')) return document.getElementById('qhAgentFab');

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'qhAgentFab';
    btn.className = 'qh-agent-fab';
    btn.setAttribute('data-i18n', 'agent.fab');
    updateFabLabel(btn);
    btn.addEventListener('click', function () {
      var bridge =
        options.bridge ||
        (typeof options.getBridge === 'function' ? options.getBridge() : '') ||
        getFocusBridge() ||
        new URLSearchParams(global.location.search).get('name') ||
        '';
      openArchivist({
        bridge: bridge || undefined,
        q: options.q || '',
        autoAsk: options.autoAsk === true,
        source: options.source || pageSource()
      });
    });
    document.body.appendChild(btn);

    if (global.BridgeI18n && typeof global.BridgeI18n.apply === 'function') {
      global.BridgeI18n.apply(btn);
      updateFabLabel(btn);
    }
    document.addEventListener('bridge:langchange', function () {
      updateFabLabel(btn);
    });
    return btn;
  }

  function ping() {
    var c = cfg();
    if (!c.enabled) {
      setOnline(false);
      return Promise.resolve({ ok: false, skipped: true });
    }
    return api('/api/health')
      .then(function (r) {
        if (!r.ok) throw new Error('health ' + r.status);
        return r.json();
      })
      .then(function (data) {
        setOnline(!!data.ok);
        return data;
      })
      .catch(function () {
        setOnline(false);
        return { ok: false };
      });
  }

  function init(options) {
    options = options || {};
    bindLinkDelegation();
    if (options.autoTrack !== false) autoTrackPage();
    if (options.fab !== false) {
      mountFab({
        getBridge: options.getBridge,
        source: options.source,
        q: options.q,
        autoAsk: options.autoAsk
      });
    }
    ping();
  }

  global.QianhongAgent = {
    cfg: cfg,
    getSessionId: getSessionId,
    getFocusBridge: getFocusBridge,
    setFocusBridge: setFocusBridge,
    ensureSession: ensureSession,
    track: track,
    openArchivist: openArchivist,
    goDetail: goDetail,
    detailUrl: detailUrl,
    mountFab: mountFab,
    pageSource: pageSource,
    ping: ping,
    init: init,
    isOnline: function () {
      return online;
    }
  };
})(typeof window !== 'undefined' ? window : this);
