(function () {
  var STORAGE_KEY = 'gaoqiao_bg_music_playing';
  var audio = document.getElementById('bgMusic');
  var btn = document.getElementById('musicToggle');
  if (!audio || !btn) return;

  function syncBtn() {
    var on = !audio.paused;
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.classList.toggle('on', on);
    var I = window.BridgeI18n;
    if (I) {
      btn.textContent = on ? I.t('music.pause') : I.t('music.label');
      btn.setAttribute('aria-label', I.t('music.aria'));
      btn.setAttribute('title', I.t('music.title'));
    } else {
      btn.textContent = on ? '暂停' : '音乐';
    }
  }

  document.addEventListener('bridge:langchange', syncBtn);

  function persistState() {
    try {
      sessionStorage.setItem(STORAGE_KEY, audio.paused ? '0' : '1');
    } catch (e) {}
  }

  btn.addEventListener('click', function () {
    if (audio.paused) {
      audio.play().then(function () {
        syncBtn();
        persistState();
      }).catch(function (err) {
        if (typeof console !== 'undefined' && console.warn) {
          console.warn('背景音乐 play() 被拒绝或失败：', err);
        }
      });
    } else {
      audio.pause();
      syncBtn();
      persistState();
    }
  });

  audio.addEventListener('play', function () {
    syncBtn();
    persistState();
  });
  audio.addEventListener('pause', function () {
    syncBtn();
    persistState();
  });
  audio.addEventListener('ended', syncBtn);
  audio.addEventListener('error', function () {
    var err = audio.error;
    var code = err ? err.code : '';
    var msg = '背景音乐未加载（MediaError ' + code + '）：请确认 assets/高山流水.mp3 存在且为有效 MP3。';
    if (typeof console !== 'undefined' && console.warn) console.warn(msg);
  });

  function tryResumeFromSession() {
    try {
      if (sessionStorage.getItem(STORAGE_KEY) === '1' && audio.paused) {
        audio.play().catch(function () {});
      }
    } catch (e) {}
  }

  tryResumeFromSession();

  function onFirstGesture() {
    tryResumeFromSession();
    document.removeEventListener('pointerdown', onFirstGesture, true);
    document.removeEventListener('keydown', onFirstGesture, true);
  }
  document.addEventListener('pointerdown', onFirstGesture, true);
  document.addEventListener('keydown', onFirstGesture, true);
})();
