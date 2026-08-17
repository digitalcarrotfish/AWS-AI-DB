/**
 * 悬浮小助手：同页对话 + 扫桥识别
 * 依赖 window.QianhongAgent（bridge-agent.js）
 */
(function (global) {
  'use strict';

  var panel = null;
  var stream = null;
  var opts = {};

  function t(key, fallback) {
    if (global.BridgeI18n && typeof global.BridgeI18n.t === 'function') {
      var v = global.BridgeI18n.t(key);
      if (v && v !== key) return v;
    }
    return fallback;
  }

  function QA() {
    return global.QianhongAgent;
  }

  function api(path, options) {
    return QA().cfg && fetch(
      (function () {
        var base = QA().cfg().apiBase || '';
        return base + path;
      })(),
      options
    );
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function ensureDom() {
    if (panel) return panel;
    var wrap = document.createElement('div');
    wrap.id = 'qhAssistant';
    wrap.className = 'qh-asst';
    wrap.innerHTML =
      '<button type="button" class="qh-asst-fab" id="qhAsstFab" aria-expanded="false">' +
      '<span class="qh-asst-fab-dot" aria-hidden="true"></span>' +
      '<span class="qh-asst-fab-label" data-i18n="agent.fab">档案员</span>' +
      '</button>' +
      '<div class="qh-asst-panel" id="qhAsstPanel" hidden>' +
      '  <header class="qh-asst-head">' +
      '    <div class="qh-asst-titles">' +
      '      <strong data-i18n="asst.title">飞虹智忆</strong>' +
      '      <span class="qh-asst-sub" id="qhAsstFocus"></span>' +
      '    </div>' +
      '    <div class="qh-asst-head-actions">' +
      '      <button type="button" class="qh-asst-icon" id="qhAsstScanBtn" data-i18n-title="asst.scan" title="扫桥识别">扫</button>' +
      '      <a class="qh-asst-icon" id="qhAsstExpand" href="/agent/" title="展开全屏">↗</a>' +
      '      <button type="button" class="qh-asst-icon" id="qhAsstClose" aria-label="关闭">×</button>' +
      '    </div>' +
      '  </header>' +
      '  <div class="qh-asst-tabs" role="tablist">' +
      '    <button type="button" class="qh-asst-tab is-active" data-tab="chat" data-i18n="asst.tabChat">对话</button>' +
      '    <button type="button" class="qh-asst-tab" data-tab="scan" data-i18n="asst.tabScan">扫桥</button>' +
      '  </div>' +
      '  <div class="qh-asst-body" data-pane="chat">' +
      '    <div class="qh-asst-msgs" id="qhAsstMsgs" aria-live="polite"></div>' +
      '    <div class="qh-asst-chips" id="qhAsstChips"></div>' +
      '    <div class="qh-asst-input-row">' +
      '      <textarea id="qhAsstInput" rows="2" data-i18n-placeholder="asst.ph" placeholder="问古桥，或先扫一扫…"></textarea>' +
      '      <button type="button" class="qh-asst-send" id="qhAsstSend" data-i18n="asst.send">发送</button>' +
      '    </div>' +
      '  </div>' +
      '  <div class="qh-asst-body" data-pane="scan" hidden>' +
      '    <div class="qh-asst-scan">' +
      '      <div class="qh-asst-cam-wrap">' +
      '        <video id="qhAsstVideo" playsinline muted></video>' +
      '        <canvas id="qhAsstCanvas" hidden></canvas>' +
      '        <div class="qh-asst-cam-frame" aria-hidden="true"></div>' +
      '      </div>' +
      '      <p class="qh-asst-hint" data-i18n="asst.scanHint">对准古桥外观（或上传图鉴截图），识别后写入浏览记忆</p>' +
      '      <div class="qh-asst-scan-actions">' +
      '        <button type="button" class="qh-asst-primary" id="qhAsstCapture" data-i18n="asst.capture">拍照识别</button>' +
      '        <label class="qh-asst-ghost" id="qhAsstUploadLabel">' +
      '          <input type="file" id="qhAsstFile" accept="image/*" capture="environment" hidden>' +
      '          <span data-i18n="asst.upload">上传图片</span>' +
      '        </label>' +
      '      </div>' +
      '      <div class="qh-asst-scan-result" id="qhAsstScanResult" hidden></div>' +
      '    </div>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(wrap);
    panel = wrap;
    bind(wrap);
    if (global.BridgeI18n && global.BridgeI18n.apply) global.BridgeI18n.apply(wrap);
    return wrap;
  }

  function setTab(name) {
    var root = ensureDom();
    root.querySelectorAll('.qh-asst-tab').forEach(function (btn) {
      btn.classList.toggle('is-active', btn.getAttribute('data-tab') === name);
    });
    root.querySelectorAll('.qh-asst-body').forEach(function (pane) {
      var on = pane.getAttribute('data-pane') === name;
      pane.hidden = !on;
    });
    if (name === 'scan') startCamera();
    else stopCamera();
  }

  function openPanel(extra) {
    extra = extra || {};
    var root = ensureDom();
    var p = root.querySelector('#qhAsstPanel');
    var fab = root.querySelector('#qhAsstFab');
    p.hidden = false;
    root.classList.add('is-open');
    fab.setAttribute('aria-expanded', 'true');
    updateFocusLabel();
    refreshChips();
    if (extra.tab) setTab(extra.tab);
    if (extra.bridge) {
      QA().setFocusBridge(extra.bridge);
      updateFocusLabel();
    }
    if (extra.q && extra.autoAsk) {
      sendChat(extra.q);
    } else if (extra.q) {
      var input = root.querySelector('#qhAsstInput');
      if (input) {
        input.value = extra.q;
        input.focus();
      }
    }
    if (!root.dataset.welcomed) {
      appendMsg('bot', t('asst.welcome',
        '我是飞虹智忆档案员。可在本页直接提问，或点「扫桥」拍照识别古桥——识别结果会写入浏览记忆。'));
      root.dataset.welcomed = '1';
    }
    QA().track(
      'open_assistant',
      (QA().pageSource && QA().pageSource()) || 'museum',
      QA().getFocusBridge() || null,
      { mode: 'float' }
    );
  }

  function closePanel() {
    var root = ensureDom();
    root.querySelector('#qhAsstPanel').hidden = true;
    root.classList.remove('is-open');
    root.querySelector('#qhAsstFab').setAttribute('aria-expanded', 'false');
    stopCamera();
  }

  function togglePanel() {
    var root = ensureDom();
    if (root.classList.contains('is-open')) closePanel();
    else openPanel();
  }

  function updateFocusLabel() {
    var el = document.getElementById('qhAsstFocus');
    if (!el) return;
    var name = QA().getFocusBridge();
    el.textContent = name
      ? t('asst.focus', '焦点：') + name
      : t('asst.noFocus', '尚未设定焦点桥');
  }

  function appendMsg(role, text, meta) {
    var box = document.getElementById('qhAsstMsgs');
    if (!box) return;
    var div = document.createElement('div');
    div.className = 'qh-asst-msg ' + (role === 'user' ? 'user' : 'bot');
    div.innerHTML =
      '<div class="bubble">' + escapeHtml(text) + '</div>' +
      (meta ? '<div class="meta">' + escapeHtml(meta) + '</div>' : '');
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    return div;
  }

  function refreshChips() {
    var box = document.getElementById('qhAsstChips');
    if (!box) return;
    var focus = QA().getFocusBridge();
    var chips = [
      t('asst.chipDossier', '我的档案'),
      t('asst.chipRecommend', '推荐下一座'),
      t('asst.chipScan', '去扫桥')
    ];
    if (focus) chips.unshift(t('asst.chipIntro', '介绍') + focus);
    box.innerHTML = '';
    chips.forEach(function (label) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'qh-asst-chip';
      btn.textContent = label;
      btn.addEventListener('click', function () {
        if (label === t('asst.chipScan', '去扫桥') || label.indexOf('扫') >= 0 && label.length <= 4) {
          setTab('scan');
          return;
        }
        var map = {};
        map[t('asst.chipDossier', '我的档案')] = '我的档案';
        map[t('asst.chipRecommend', '推荐下一座')] = '推荐下一座';
        sendChat(map[label] || label);
      });
      box.appendChild(btn);
    });
  }

  function sendChat(textOverride) {
    var input = document.getElementById('qhAsstInput');
    var text = (textOverride || (input && input.value) || '').trim();
    if (!text) return;
    if (input && !textOverride) input.value = '';
    appendMsg('user', text);
    var typing = appendMsg('bot', t('asst.thinking', '正在思考…'), '…');
    typing.classList.add('typing');

    QA().ensureSession(QA().getFocusBridge()).then(function (sid) {
      if (!sid) throw new Error('no session');
      return api('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sid,
          message: text,
          focus_bridge: QA().getFocusBridge() || null
        })
      });
    })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        typing.remove();
        if (data.session_id) {
          localStorage.setItem('qh_session_id', data.session_id);
        }
        if (data.focus_bridge) {
          QA().setFocusBridge(data.focus_bridge);
          updateFocusLabel();
          refreshChips();
        }
        var meta = data.mode || '';
        if (data.sources && data.sources.length) {
          meta += (meta ? ' · ' : '') + data.sources.slice(0, 3).join('、');
        }
        appendMsg('bot', data.text, meta);
      })
      .catch(function (err) {
        typing.remove();
        appendMsg('bot', t('asst.error', '请求失败：') + err.message +
          '\n' + t('asst.errorHint', '请确认已运行 python -m api.main'));
      });
  }

  function startCamera() {
    var video = document.getElementById('qhAsstVideo');
    if (!video || stream) return;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      appendScanNote(t('asst.noCamera', '当前浏览器不支持摄像头，请改用上传图片。'));
      return;
    }
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
      .then(function (s) {
        stream = s;
        video.srcObject = s;
        return video.play();
      })
      .catch(function () {
        appendScanNote(t('asst.camDenied', '无法打开摄像头，请允许权限或改用上传。'));
      });
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(function (tr) { tr.stop(); });
      stream = null;
    }
    var video = document.getElementById('qhAsstVideo');
    if (video) video.srcObject = null;
  }

  function appendScanNote(text) {
    var box = document.getElementById('qhAsstScanResult');
    if (!box) return;
    box.hidden = false;
    box.innerHTML = '<p class="qh-asst-scan-note">' + escapeHtml(text) + '</p>';
  }

  function blobFromVideo() {
    var video = document.getElementById('qhAsstVideo');
    var canvas = document.getElementById('qhAsstCanvas');
    if (!video || !canvas || !video.videoWidth) {
      return Promise.reject(new Error('camera not ready'));
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    var ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    return new Promise(function (resolve, reject) {
      canvas.toBlob(function (blob) {
        if (blob) resolve(blob);
        else reject(new Error('capture failed'));
      }, 'image/jpeg', 0.92);
    });
  }

  function identifyBlob(blob, filename) {
    appendScanNote(t('asst.identifying', '正在识别…'));
    return QA().ensureSession(QA().getFocusBridge()).then(function (sid) {
      var fd = new FormData();
      fd.append('file', blob, filename || 'scan.jpg');
      if (sid) fd.append('session_id', sid);
      return api('/api/identify', { method: 'POST', body: fd }).then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      });
    }).then(function (data) {
      if (data.session_id) localStorage.setItem('qh_session_id', data.session_id);
      renderIdentifyResult(data);
      return data;
    }).catch(function (err) {
      appendScanNote(t('asst.identifyFail', '识别失败：') + err.message);
    });
  }

  function renderIdentifyResult(data) {
    var box = document.getElementById('qhAsstScanResult');
    if (!box) return;
    box.hidden = false;
    var top = data.top;
    if (!top) {
      box.innerHTML = '<p class="qh-asst-scan-note">' +
        escapeHtml(t('asst.noMatch', '未匹配到图鉴中的桥，请换角度或上传更清晰的外观图。')) +
        '</p>';
      return;
    }
    var pct = Math.round((top.score || 0) * 100);
    var ok = data.matched;
    var html =
      '<div class="qh-asst-match ' + (ok ? 'is-hit' : 'is-maybe') + '">' +
      (top.preview
        ? '<img src="' + escapeHtml(top.preview) + '" alt="">'
        : '') +
      '<div class="qh-asst-match-body">' +
      '<strong>' + escapeHtml(top.name) + '</strong>' +
      '<span>' +
      (ok
        ? t('asst.matchOk', '识别成功')
        : t('asst.matchMaybe', '最接近候选')) +
      ' · ' + pct + '%</span>';
    if (data.bridge) {
      html +=
        '<span class="meta">' +
        escapeHtml(
          [data.bridge.dynasty, data.bridge.type, data.bridge.province]
            .filter(Boolean)
            .join(' · ')
        ) +
        '</span>';
    }
    html +=
      '<div class="qh-asst-match-actions">' +
      '<button type="button" class="qh-asst-primary" data-act="ask">' +
      escapeHtml(t('asst.askThis', '讲解此桥')) +
      '</button>' +
      '<a class="qh-asst-ghost" href="bridge-detail.html?name=' +
      encodeURIComponent(top.name) +
      '">' +
      escapeHtml(t('asst.openDetail', '打开档案')) +
      '</a>' +
      '</div></div></div>';

    if (data.candidates && data.candidates.length > 1) {
      html += '<ul class="qh-asst-cands">';
      data.candidates.slice(0, 4).forEach(function (c, i) {
        if (i === 0) return;
        html +=
          '<li><button type="button" data-name="' +
          escapeHtml(c.name) +
          '">' +
          escapeHtml(c.name) +
          ' · ' +
          Math.round((c.score || 0) * 100) +
          '%</button></li>';
      });
      html += '</ul>';
    }
    box.innerHTML = html;

    QA().setFocusBridge(top.name);
    updateFocusLabel();
    refreshChips();

    var askBtn = box.querySelector('[data-act="ask"]');
    if (askBtn) {
      askBtn.addEventListener('click', function () {
        setTab('chat');
        sendChat('介绍' + top.name);
      });
    }
    box.querySelectorAll('.qh-asst-cands button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var name = btn.getAttribute('data-name');
        QA().setFocusBridge(name);
        QA().track('scan_pick', 'camera_scan', name, null);
        updateFocusLabel();
        setTab('chat');
        sendChat('介绍' + name);
      });
    });

    // 同步一条系统提示到对话区
    setTab('chat');
    appendMsg(
      'bot',
      (ok ? t('asst.scanSuccess', '扫桥识别：') : t('asst.scanMaybe', '扫桥候选：')) +
        top.name +
        '（' + pct + '%）\n' +
        t('asst.scanMemory', '已写入浏览记忆。可继续提问，或点「讲解此桥」。'),
      'scan'
    );
  }

  function bind(root) {
    root.querySelector('#qhAsstFab').addEventListener('click', togglePanel);
    root.querySelector('#qhAsstClose').addEventListener('click', closePanel);
    root.querySelector('#qhAsstScanBtn').addEventListener('click', function () {
      openPanel({ tab: 'scan' });
    });
    root.querySelectorAll('.qh-asst-tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        setTab(btn.getAttribute('data-tab'));
      });
    });
    root.querySelector('#qhAsstSend').addEventListener('click', function () {
      sendChat();
    });
    root.querySelector('#qhAsstInput').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChat();
      }
    });
    root.querySelector('#qhAsstCapture').addEventListener('click', function () {
      blobFromVideo()
        .then(function (blob) { return identifyBlob(blob, 'capture.jpg'); })
        .catch(function () {
          appendScanNote(t('asst.captureFail', '拍照失败，请先允许摄像头或改用上传。'));
        });
    });
    root.querySelector('#qhAsstFile').addEventListener('change', function (e) {
      var file = e.target.files && e.target.files[0];
      if (!file) return;
      identifyBlob(file, file.name);
      e.target.value = '';
    });

    var expand = root.querySelector('#qhAsstExpand');
    expand.addEventListener('click', function (e) {
      e.preventDefault();
      QA().openArchivist({
        bridge: QA().getFocusBridge() || undefined,
        source: 'float_assistant'
      });
    });

    document.addEventListener('bridge:langchange', function () {
      if (global.BridgeI18n) global.BridgeI18n.apply(root);
      updateFocusLabel();
      refreshChips();
    });
  }

  function mount(options) {
    opts = options || {};
    // 若旧 FAB 存在则移除，避免双按钮
    var old = document.getElementById('qhAgentFab');
    if (old) old.remove();
    ensureDom();
    QA().ping && QA().ping().then(function (h) {
      var fab = document.getElementById('qhAsstFab');
      if (!fab) return;
      fab.classList.toggle('is-online', !!(h && h.ok));
      fab.classList.toggle('is-offline', !(h && h.ok));
    });
    // 导航「档案员」统一打开悬浮窗
    document.querySelectorAll('#navArchivist, .qh-agent-nav').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        var bridge =
          (typeof opts.getBridge === 'function' && opts.getBridge()) ||
          QA().getFocusBridge() ||
          new URLSearchParams(location.search).get('name') ||
          '';
        openPanel({ bridge: bridge || undefined, tab: 'chat' });
      });
    });
    return panel;
  }

  global.BridgeAssistant = {
    mount: mount,
    open: openPanel,
    close: closePanel,
    openScan: function () { openPanel({ tab: 'scan' }); }
  };
})(typeof window !== 'undefined' ? window : this);
