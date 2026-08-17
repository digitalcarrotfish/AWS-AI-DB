/**
 * 古桥智能助手：本地知识检索（默认可用）+ 可选 OpenAI 兼容大模型 API
 */
(function (global) {
  'use strict';

  var STOP = '的了吗呢啊吧呀与及在是有了和';

  function norm(s) {
    return String(s || '').trim().toLowerCase();
  }

  function tokens(text) {
    var t = [];
    var s = String(text || '');
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      if (/[\u4e00-\u9fff]/.test(c)) t.push(c);
    }
    var words = s.split(/[\s，。；、？！,.;:!?]+/).filter(Boolean);
    words.forEach(function (w) {
      if (w.length >= 2) t.push(w);
      if (w.length >= 4) {
        for (var j = 0; j <= w.length - 2; j++) t.push(w.slice(j, j + 2));
      }
    });
    return t;
  }

  function scoreText(queryTok, text) {
    if (!text) return 0;
    var score = 0;
    var hay = String(text);
    queryTok.forEach(function (tok) {
      if (tok.length < 2 && STOP.indexOf(tok) >= 0) return;
      if (hay.indexOf(tok) >= 0) score += tok.length >= 3 ? 4 : 2;
    });
    return score;
  }

  function BridgeAI(bridges, culture) {
    this.bridges = bridges || [];
    this.culture = culture || null;
    this.byName = {};
    var self = this;
    this.bridges.forEach(function (b) {
      if (b && b.name) self.byName[b.name] = b;
    });
  }

  BridgeAI.prototype.findBridges = function (query, limit) {
    var q = norm(query);
    var qt = tokens(q);
    var list = this.bridges.map(function (b) {
      var blob = [b.name, b.dynasty, b.province, b.city, b.type, b.material, b.poetry, b.intro].join(' ');
      var s = scoreText(qt, blob);
      if (q && b.name && q.indexOf(norm(b.name)) >= 0) s += 30;
      return { bridge: b, score: s };
    }).filter(function (x) { return x.score > 0; });
    list.sort(function (a, b) { return b.score - a.score; });
    return list.slice(0, limit || 5).map(function (x) { return x.bridge; });
  }

  BridgeAI.prototype.formatBridgeBrief = function (b) {
    if (!b) return '';
    var y = b.year != null ? (b.year < 0 ? '约公元前' + (-b.year) + '年' : '约公元' + b.year + '年') : '';
    var lines = [
      '【' + b.name + '】',
      [b.dynasty, y, b.province + (b.city ? ' ' + b.city : ''), b.type, b.material].filter(Boolean).join(' · ')
    ];
    if (b.span != null) lines.push('最大单孔跨度约 ' + b.span + ' 米' + (b.length != null ? '，桥长约 ' + b.length + ' 米' : ''));
    if (b.poetry) lines.push('名句：「' + b.poetry + '」');
    if (b.intro) lines.push(b.intro.slice(0, 280) + (b.intro.length > 280 ? '…' : ''));
    var cult = this.culture && this.culture.entries && this.culture.entries[b.name];
    if (cult && cult.culturalInsight) lines.push('文化解读：' + cult.culturalInsight.slice(0, 200) + (cult.culturalInsight.length > 200 ? '…' : ''));
    return lines.join('\n');
  }

  BridgeAI.prototype.filterByField = function (field, value) {
    return this.bridges.filter(function (b) {
      return b[field] === value || (field === 'dynasty' && b.dynasty === value);
    });
  }

  BridgeAI.prototype.localAnswer = function (query, selectedBridge) {
    var q = String(query || '').trim();
    if (!q) return { text: '请输入问题，例如：介绍赵州桥、宋代有哪些拱桥、对比赵州桥和卢沟桥。', sources: [] };

    if (selectedBridge && (/^(介绍|讲解|说说|谈谈)/.test(q) || q.length <= 8)) {
      var b0 = this.byName[selectedBridge] || selectedBridge;
      if (typeof b0 === 'object') {
        return {
          text: this.formatBridgeBrief(b0),
          sources: [b0.name],
          mode: 'local'
        };
      }
    }

    var compareMatch = q.match(/(.+?)(和|与|、)(.+?)(对比|比较|区别|异同)/) ||
      q.match(/对比(.+?)(和|与)(.+)/);
    if (compareMatch) {
      var n1 = compareMatch[1].trim();
      var n2 = compareMatch[3] ? compareMatch[3].trim() : compareMatch[2].trim();
      var found = this.findBridges(n1, 1).concat(this.findBridges(n2, 1));
      if (found.length >= 2) {
        return {
          text: '—— 对比概览 ——\n\n' + this.formatBridgeBrief(found[0]) + '\n\n---\n\n' + this.formatBridgeBrief(found[1]),
          sources: [found[0].name, found[1].name],
          mode: 'local'
        };
      }
    }

    var dynastyMatch = q.match(/(夏|商|周|汉|晋|隋|唐|宋|南宋|金|元|明|清|秦|魏|蜀|吴|南北朝|五代)/);
    var typeMatch = q.match(/(拱桥|梁桥|索桥|浮桥)/);
    var listMatch = q.match(/有哪些|列举|列出|都有什么/);

    if (listMatch && (dynastyMatch || typeMatch)) {
      var filtered = this.bridges.slice();
      if (dynastyMatch) filtered = filtered.filter(function (b) { return b.dynasty === dynastyMatch[1]; });
      if (typeMatch) filtered = filtered.filter(function (b) { return b.type === typeMatch[1]; });
      filtered.sort(function (a, b) { return (a.year || 0) - (b.year || 0); });
      if (filtered.length) {
        var names = filtered.map(function (b) {
          var y = b.year != null ? (b.year < 0 ? '前' + (-b.year) : b.year) : '?';
          return '· ' + b.name + '（' + (b.dynasty || '') + '，' + y + '，' + (b.type || '') + '）';
        }).join('\n');
        return {
          text: '符合条件的桥梁共 ' + filtered.length + ' 座：\n' + names,
          sources: filtered.map(function (b) { return b.name; }),
          mode: 'local'
        };
      }
    }

    var hits = this.findBridges(q, 3);
    if (hits.length === 1) {
      return { text: this.formatBridgeBrief(hits[0]), sources: [hits[0].name], mode: 'local' };
    }
    if (hits.length > 1) {
      var multi = hits.map(function (b, i) {
        return (i + 1) + '. ' + b.name + ' — ' + [b.dynasty, b.type, b.province].filter(Boolean).join(' · ');
      }).join('\n');
      return {
        text: '为您找到多座相关古桥，请指定桥名或点击图谱节点：\n' + multi,
        sources: hits.map(function (b) { return b.name; }),
        mode: 'local'
      };
    }

    if (/推荐|最值得|著名|名桥/.test(q)) {
      var top = this.bridges.slice().sort(function (a, b) { return (b.span || 0) - (a.span || 0); }).slice(0, 5);
      return {
        text: '按跨度与文献知名度，推荐了解：\n' + top.map(function (b) {
          return '· ' + b.name + '（' + (b.dynasty || '') + '，跨度 ' + (b.span != null ? b.span + 'm' : '—') + '）';
        }).join('\n'),
        sources: top.map(function (b) { return b.name; }),
        mode: 'local'
      };
    }

    return {
      text: '暂未在图鉴中匹配到明确结果。可尝试：\n· 直接输入桥名（如赵州桥）\n· 「宋代有哪些拱桥」\n· 「对比赵州桥和卢沟桥」\n· 在左侧图谱点击桥梁后再提问',
      sources: [],
      mode: 'local'
    };
  };

  BridgeAI.prototype.buildSystemContext = function (maxChars) {
    maxChars = maxChars || 6000;
    var parts = ['你是「千古飞虹」古桥数字图鉴的智能讲解助手，仅根据下列资料回答，勿编造不存在的桥梁。'];
    this.bridges.forEach(function (b) {
      var line = b.name + '|' + [b.dynasty, b.year, b.province, b.type, b.material].join(',');
      if (b.poetry) line += '|诗:' + b.poetry;
      if (b.intro) line += '|' + b.intro.slice(0, 120);
      parts.push(line);
    });
    var text = parts.join('\n');
    return text.length > maxChars ? text.slice(0, maxChars) + '…' : text;
  };

  var AI_PRESETS = {
    kimi: {
      label: 'Kimi（月之暗面）',
      apiBase: 'https://api.moonshot.cn/v1',
      model: 'moonshot-v1-8k'
    },
    deepseek: {
      label: 'DeepSeek',
      apiBase: 'https://api.deepseek.com',
      model: 'deepseek-chat'
    }
  };

  BridgeAI.prototype.getAiConfig = function () {
    var cfg = global.BRIDGE_AI || {};
    var key = (cfg.apiKey || '').trim();
    if (!cfg.enabled || !key) return null;
    var preset = AI_PRESETS[cfg.provider] || null;
    var base = (cfg.apiBase || (preset && preset.apiBase) || '').trim().replace(/\/$/, '');
    if (!base) return null;
    var model = (cfg.model || (preset && preset.model) || 'moonshot-v1-8k').trim();
    return {
      apiBase: base,
      apiKey: key,
      model: model,
      providerLabel: (preset && preset.label) || cfg.provider || '大模型'
    };
  };

  BridgeAI.prototype.llmAnswer = function (query, selectedBridge) {
    var cfg = this.getAiConfig();
    if (!cfg) return Promise.reject(new Error('未配置大模型 API'));

    var extra = selectedBridge && this.byName[selectedBridge]
      ? '\n用户当前选中桥梁：' + this.formatBridgeBrief(this.byName[selectedBridge])
      : '';

    var messages = [
      { role: 'system', content: this.buildSystemContext() + extra },
      { role: 'user', content: query }
    ];

    return fetch(cfg.apiBase + '/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + cfg.apiKey
      },
      body: JSON.stringify({
        model: cfg.model,
        messages: messages,
        temperature: 0.6,
        max_tokens: 1024
      })
    }).then(function (res) {
      if (!res.ok) return res.text().then(function (t) {
        throw new Error('API ' + res.status + (t ? ': ' + t.slice(0, 120) : ''));
      });
      return res.json();
    }).then(function (data) {
      var text = data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
      if (!text) throw new Error('模型返回为空');
      return {
        text: text.trim(),
        sources: [],
        mode: 'llm',
        providerLabel: cfg.providerLabel
      };
    });
  };

  BridgeAI.prototype.ask = function (query, selectedBridge, preferLlm) {
    var self = this;
    if (preferLlm && this.getAiConfig()) {
      return this.llmAnswer(query, selectedBridge).catch(function (err) {
        var local = self.localAnswer(query, selectedBridge);
        local.text = '（大模型暂时不可用：' + err.message + '）\n\n' + local.text;
        local.fallback = true;
        return local;
      });
    }
    return Promise.resolve(this.localAnswer(query, selectedBridge));
  };

  global.BridgeAI = BridgeAI;
})(typeof window !== 'undefined' ? window : this);
