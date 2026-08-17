/**
 * 古桥雅韵 · 中英双语
 * localStorage key: gaoqiao_lang = 'zh' | 'en'
 */
(function (global) {
  'use strict';

  var STORAGE_KEY = 'gaoqiao_lang';
  var dict = {
    zh: {},
    en: {}
  };

  var BRIDGE_EN = {
    '赵州桥': 'Zhaozhou Bridge',
    '卢沟桥': 'Lugou Bridge',
    '广济桥': 'Guangji Bridge',
    '洛阳桥': 'Luoyang Bridge',
    '安平桥': 'Anping Bridge',
    '泸定桥': 'Luding Bridge',
    '霁虹桥': 'Jihong Bridge',
    '二十四桥': 'Twenty-Four Bridge',
    '枫桥': 'Fengqiao Bridge',
    '玉带桥': 'Jade Belt Bridge',
    '程阳永济桥': 'Chengyang Yongji Bridge',
    '普济桥': 'Puji Bridge',
    '通济桥': 'Tongji Bridge',
    '八字桥': 'Bazi Bridge',
    '断桥': 'Broken Bridge',
    '淇水石梁遗址': 'Qishui Stone Beam Site',
    '蓝桥': 'Lanqiao Bridge',
    '灞桥': 'Baqiao Bridge',
    '河桥': 'Heqiao Bridge',
    '观音桥': 'Guanyin Bridge',
    '永通桥': 'Yongtong Bridge',
    '朝宗桥': 'Chaozong Bridge',
    '双龙桥': 'Shuanglong Bridge',
    '纤道桥': 'Towpath Bridge',
    '宝带桥': 'Precious Belt Bridge',
    '五亭桥': 'Five-Pavilion Bridge',
    '十七孔桥': 'Seventeen-Arch Bridge',
    '小商桥': 'Xiaoshang Bridge',
    '鱼沼飞梁': 'Yuzhao Flying Bridge',
    '万安桥': 'Wan\'an Bridge',
    '彩虹桥': 'Rainbow Bridge',
    '放生桥': 'Fangsheng Bridge',
    '龙脑桥': 'Longnao Bridge',
    '江东桥': 'Jiangdong Bridge'
  };

  var FIELD_EN = {
    '夏': 'Xia', '商': 'Shang', '周': 'Zhou', '汉': 'Han', '晋': 'Jin',
    '隋': 'Sui', '唐': 'Tang', '宋': 'Song', '南宋': 'Southern Song',
    '金': 'Jin', '元': 'Yuan', '明': 'Ming', '清': 'Qing',
    '拱桥': 'Arch bridge', '梁桥': 'Beam bridge', '索桥': 'Cable bridge', '浮桥': 'Pontoon bridge',
    '石': 'Stone', '木': 'Wood', '铁': 'Iron', '木/石': 'Wood/Stone', '石/木': 'Stone/Wood', '其他': 'Other',
    '国保': 'National heritage', '省保': 'Provincial heritage',
    '第一批': '1st batch', '第二批': '2nd batch', '第三批': '3rd batch',
    '第四批': '4th batch', '第五批': '5th batch', '第六批': '6th batch',
    '第七批': '7th batch', '第八批': '8th batch',
    '江南水乡': 'Jiangnan water towns', '西南峡谷': 'Southwest canyons',
    '北方·中原': 'North & Central Plains', '岭南及其他': 'Lingnan & others',
    '北京市': 'Beijing', '河北省': 'Hebei', '山西省': 'Shanxi', '陕西省': 'Shaanxi',
    '河南省': 'Henan', '江苏省': 'Jiangsu', '浙江省': 'Zhejiang', '安徽省': 'Anhui',
    '江西省': 'Jiangxi', '上海市': 'Shanghai', '福建省': 'Fujian', '广东省': 'Guangdong',
    '四川省': 'Sichuan', '云南省': 'Yunnan', '贵州省': 'Guizhou', '西藏': 'Tibet',
    '广西壮族自治区': 'Guangxi', '湖南省': 'Hunan', '湖北省': 'Hubei',
    '山东省': 'Shandong', '天津市': 'Tianjin', '辽宁省': 'Liaoning'
  };

  var INTRO_EN = {
    '赵州桥': 'Zhaozhou Bridge (Anji Bridge) in Zhao County, Hebei, was built under Li Chun in the Sui dynasty. It is among the world\'s earliest and best-preserved open-spandrel stone arch bridges. The large main span and two small arches on each shoulder reduce weight and ease flood flow—an outstanding feat of structural design.\n\nTwenty-eight parallel arch rings form the vault, strengthened with iron clamps and keyed stones. Dragon carvings on the railings are of high artistic value. It entered China\'s first National Key Cultural Relics list in 1961.'
  };

  function mergeDict(lang, map) {
    if (!dict[lang]) dict[lang] = {};
    Object.keys(map || {}).forEach(function (k) {
      dict[lang][k] = map[k];
    });
  }

  function getLang() {
    try {
      var v = localStorage.getItem(STORAGE_KEY);
      if (v === 'en' || v === 'zh') return v;
    } catch (e) {}
    return 'en';
  }

  function setLang(lang) {
    lang = lang === 'en' ? 'en' : 'zh';
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) {}
    document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';
    document.documentElement.setAttribute('data-lang', lang);
    apply(document);
    try {
      document.dispatchEvent(new CustomEvent('bridge:langchange', { detail: { lang: lang } }));
    } catch (e) {}
    return lang;
  }

  function toggleLang() {
    return setLang(getLang() === 'en' ? 'zh' : 'en');
  }

  function interpolate(str, vars) {
    if (!vars) return str;
    return String(str).replace(/\{(\w+)\}/g, function (_, k) {
      return vars[k] != null ? vars[k] : '{' + k + '}';
    });
  }

  function t(key, vars) {
    var lang = getLang();
    var pack = dict[lang] || {};
    var fallback = dict.zh || {};
    var val = pack[key] != null ? pack[key] : fallback[key];
    if (val == null) return key;
    return interpolate(val, vars);
  }

  function field(zh) {
    if (zh == null || zh === '') return zh;
    if (getLang() !== 'en') return zh;
    return FIELD_EN[zh] || zh;
  }

  function bridgeName(zh) {
    if (!zh) return zh;
    if (getLang() !== 'en') return zh;
    return BRIDGE_EN[zh] || zh;
  }

  function bridgeIntro(b) {
    if (!b) return '';
    if (getLang() === 'en' && INTRO_EN[b.name]) return INTRO_EN[b.name];
    return b.intro || '';
  }

  function yearLabel(year) {
    if (year == null || year === '') return '';
    if (year < 0) return t('year.bce', { n: -year });
    return t('year.ce', { n: year });
  }

  function applyNode(el) {
    if (!el || el.nodeType !== 1) return;
    var key = el.getAttribute('data-i18n');
    if (key) {
      if (el.hasAttribute('data-i18n-html')) el.innerHTML = t(key);
      else el.textContent = t(key);
    }
    var ph = el.getAttribute('data-i18n-placeholder');
    if (ph) el.setAttribute('placeholder', t(ph));
    var title = el.getAttribute('data-i18n-title');
    if (title) el.setAttribute('title', t(title));
    var aria = el.getAttribute('data-i18n-aria');
    if (aria) el.setAttribute('aria-label', t(aria));
    var fieldKey = el.getAttribute('data-i18n-field');
    if (fieldKey) el.textContent = field(fieldKey);
    var bridgeKey = el.getAttribute('data-i18n-bridge');
    if (bridgeKey) el.textContent = bridgeName(bridgeKey);
  }

  function apply(root) {
    root = root || document;
    var nodes = root.querySelectorAll('[data-i18n], [data-i18n-placeholder], [data-i18n-title], [data-i18n-aria], [data-i18n-field], [data-i18n-bridge]');
    for (var i = 0; i < nodes.length; i++) applyNode(nodes[i]);
    var toggles = root.querySelectorAll('[data-lang-toggle]');
    for (var j = 0; j < toggles.length; j++) {
      var btn = toggles[j];
      var lang = getLang();
      btn.textContent = lang === 'en' ? '中文' : 'EN';
      btn.setAttribute('aria-label', lang === 'en' ? 'Switch to Chinese' : '切换到英文');
      btn.setAttribute('title', lang === 'en' ? '中文' : 'English');
    }
    var titleEl = document.querySelector('title[data-i18n]');
    if (titleEl) document.title = t(titleEl.getAttribute('data-i18n'));
  }

  function bindToggles(root) {
    root = root || document;
    root.addEventListener('click', function (e) {
      var btn = e.target.closest && e.target.closest('[data-lang-toggle]');
      if (!btn) return;
      e.preventDefault();
      toggleLang();
    });
  }

  /* —— dictionary —— */
  mergeDict('zh', {
    'nav.cover': '封面',
    'nav.coverBack': '← 封面',
    'nav.museum': '图鉴主展区',
    'nav.museumShort': '地图大屏',
    'nav.knowledge': '智能驿站',
    'nav.archivist': '档案员',
    'nav.closing': '余韵',
    'nav.closingAlt': '结束语',
    'nav.site': '站内导航',
    'agent.fab': '问档案员',
    'agent.fabTitle': '打开飞虹智忆档案员（带浏览记忆）',
    'agent.offlineTitle': '档案员未连接 — 请先运行 python -m api.main',
    'agent.askMemory': '问档案员',
    'knowledge.askArchivist': '问档案员',
    'asst.title': '飞虹智忆',
    'asst.tabChat': '对话',
    'asst.tabScan': '扫桥',
    'asst.ph': '问古桥，或先扫一扫…',
    'asst.send': '发送',
    'asst.scan': '扫桥识别',
    'asst.scanHint': '对准古桥外观（或上传图鉴截图），识别后写入浏览记忆',
    'asst.capture': '拍照识别',
    'asst.upload': '上传图片',
    'asst.welcome': '我是飞虹智忆档案员。可在本页直接提问，或点「扫桥」拍照识别古桥——识别结果会写入浏览记忆。',
    'asst.focus': '焦点：',
    'asst.noFocus': '尚未设定焦点桥',
    'asst.chipDossier': '我的档案',
    'asst.chipRecommend': '推荐下一座',
    'asst.chipScan': '去扫桥',
    'asst.chipIntro': '介绍',
    'asst.thinking': '正在思考…',
    'asst.error': '请求失败：',
    'asst.errorHint': '请确认已运行 python -m api.main',
    'asst.noCamera': '当前浏览器不支持摄像头，请改用上传图片。',
    'asst.camDenied': '无法打开摄像头，请允许权限或改用上传。',
    'asst.identifying': '正在识别…',
    'asst.identifyFail': '识别失败：',
    'asst.noMatch': '未匹配到图鉴中的桥，请换角度或上传更清晰的外观图。',
    'asst.matchOk': '识别成功',
    'asst.matchMaybe': '最接近候选',
    'asst.askThis': '讲解此桥',
    'asst.openDetail': '打开档案',
    'asst.scanSuccess': '扫桥识别：',
    'asst.scanMaybe': '扫桥候选：',
    'asst.scanMemory': '已写入浏览记忆。可继续提问，或点「讲解此桥」。',
    'asst.captureFail': '拍照失败，请先允许摄像头或改用上传。',
    'music.label': '音乐',
    'music.pause': '暂停',
    'music.aria': '背景音乐：高山流水',
    'music.title': '背景音乐《高山流水》',
    'brand.title': '古桥 雅韵',
    'brand.sub': '中国古代桥梁 · 数字博物馆',
    'index.title': '古桥雅韵 · 中国古代桥梁数字博物馆',
    'index.searchAria': '寻桥',
    'index.searchPh': '寻桥 · 名称或地域',
    'index.searchInputAria': '寻桥，将跳转至图鉴内搜索',
    'index.searchHint': '回车跳转图鉴',
    'index.searchSeal': '鉴',
    'index.searchSealTitle': '寻桥',
    'index.stamp': '千年遗韵',
    'index.hero': '连接古今<br>的纽带',
    'index.lead': '从赵州桥的巧夺天工到卢沟桥的晓月风光，每一座古桥都是凝固的诗、立体的画；在此以图鉴与数据，致敬跨越千年的营造与智慧。',
    'index.cta': '开始探索',
    'index.ctaNote': '进入交互地图与桥梁档案',
    'index.sideTitle': '千古飞虹',
    'index.sideCaption': '石梁铁索承风雨',
    'index.footer': '《千古飞虹》交互图鉴 · 数据可视化与数字展陈',
    'closing.title': '余韵 · 古桥雅韵',
    'closing.stamp': '余韵悠长',
    'closing.hero': '感谢走进<br>古桥世界',
    'closing.lead': '愿这些跨越千年的桥影与数据，曾在您心中激起一丝涟漪。<br>山河依旧，飞虹如昨。',
    'closing.backMuseum': '返回图鉴主展区',
    'closing.backCover': '返回封面',
    'closing.footnote': '《千古飞虹：中国古代桥梁工程图鉴》<br>数据可视化与数字展陈 · 仅供学习交流',
    'closing.sideTitle': '谢谢观展',
    'closing.sideCaption': '桥影入梦水长流',
    'closing.summaryEn': 'Across more than thirty historic bridges—from the Shang–Zhou era to Ming and Qing—these spans stretch across China\'s rivers and gorges. They hold imperial gardens and folk craft, war memories and love legends, engineering peaks and literary inspiration. Together they form a rich genealogy of Chinese bridge culture, embodying harmony between heaven and humanity.',
    'museum.title': '千古飞虹：中国古代桥梁工程图鉴',
    'museum.sub': '从「小溪木桥」到「千古飞虹」',
    'museum.searchAria': '搜索桥梁',
    'museum.searchPh': '搜索桥梁名称、朝代、类型、省份…',
    'museum.searchTitle': '图鉴检索',
    'museum.searchSeal': '鉴',
    'museum.timelineTitle': '桥梁时光 · 左右滑动，桥在眼前依次出现',
    'museum.chartTech': '技术与材料的演进',
    'museum.chartTechTip': '按朝代统计建桥数量，柱内按主要材质堆叠（明清铁索桥增多）',
    'museum.chartRegion': '区域桥梁类型分布',
    'museum.chartRegionTip': '全国分四区，每区为该区域内各类型桥梁数量（含全部桥梁），图例为桥梁类型',
    'museum.chartSpan': '年份 × 跨度：科技跃迁',
    'museum.chartSpanTip': '赵州桥（隋）曾拉高当时跨度上限，如科技奇迹',
    'museum.resizeLeft': '拖动调整左侧边栏宽度',
    'museum.resizeRight': '拖动调整右侧边栏宽度',
    'museum.zoomGroup': '地图缩放',
    'museum.zoomIn': '放大',
    'museum.zoomOut': '缩小',
    'museum.models': '三大名桥 · 三维建模',
    'museum.types': '桥梁类型',
    'museum.dotTip': '点大小 ≈ 最大单孔跨度',
    'museum.yearAxis': '时间轴（公元）',
    'museum.yearAxisTip': '整条年份横轴点到哪跳到哪；拖圆钮可微调。',
    'museum.yearAxisTitle': '整条年份横轴点到哪跳到哪；也可拖动圆钮',
    'museum.yearAria': '年份时间轴，整条横轴点到哪跳到哪',
    'museum.rank': '跨度 / 长度 Top 10',
    'museum.rankSpan': '按跨度',
    'museum.rankLength': '按长度',
    'museum.footerData': '数据：1911 年以前中国古代桥梁 · 主题：中华优秀传统文化系列之六',
    'museum.tianditu': '国家地理信息公共服务平台 天地图',
    'museum.footerMap': '审图号：使用天地图在线服务时以天地图官网公布为准；若使用标准地图，请标注自然资源部标准地图审图号（如 GS(2019)xxxx 号）',
    'museum.ok': '确定',
    'museum.cancel': '取消',
    'museum.noMatch': '未找到匹配的桥梁',
    'museum.detailLink': '详细介绍 →',
    'museum.confirmJump': '是否跳转到「{name}」的详情页？',
    'museum.confirmDefault': '是否继续？',
    'museum.previewTitle': '时间轴对应桥梁 · 点击图翻转线稿（可拖动标题）',
    'museum.previewFlip': '点击翻转：外观 ↔ 线稿',
    'museum.previewEmpty': '拖动时间轴查看该年份对应桥梁',
    'museum.previewNoYear': '该年份暂无桥梁',
    'museum.previewMetaFlip': '点击上图翻转线稿',
    'museum.noWireframe': '该桥暂无线稿图资源',
    'museum.altAppearance': '外观',
    'museum.altWireframe': '线稿',
    'museum.mapKeyMissing': '请在 config.js 中填写天地图 API Key',
    'museum.mapFail': '天地图加载失败，请检查 Key 是否正确或网络连接。',
    'museum.dataMissing': '请将 data/bridges.json 或 data/bridges-data.js 放在正确路径并刷新。',
    'museum.buildCount': '建桥数',
    'museum.bridgeUnit': '座',
    'museum.yearAxisName': '年份',
    'museum.spanAxisName': '最大单孔跨度(m)',
    'museum.other': '其他',
    'museum.typeLabel': '类型',
    'museum.maxSpan': '最大单孔跨度',
    'detail.title': '桥梁档案 - 千古飞虹',
    'detail.back': '← 返回地图大屏',
    'detail.backShort': '返回地图',
    'detail.notFound': '未找到该桥梁信息。',
    'detail.entry3d': '进入 →',
    'detail.basic': '基础信息',
    'detail.intro': '详细介绍',
    'detail.speak': '朗读讲解',
    'detail.pause': '暂停',
    'detail.stop': '结束',
    'detail.videos': '科普视频',
    'detail.videoDesc': '精选与古桥、桥梁史相关的公开科普资源（来源见各平台）。',
    'detail.images': '桥体图像 · 外观与线稿',
    'detail.imagesDesc': '左侧为桥体外观图，右侧为结构线稿图，便于对照观赏。',
    'detail.appearance': '外观图',
    'detail.wireframe': '线稿图',
    'detail.compare': '外观与线稿对比',
    'detail.compareHint': '拖动中间竖线，可左右对比外观图与线稿图',
    'detail.poetry': '诗词与典故',
    'detail.noPoetry': '暂无诗词典故',
    'detail.anecdote': '历史典故',
    'detail.poetryRefs': '相关诗词与文章',
    'detail.insight': '内在深意',
    'detail.playVideo': '点击播放视频',
    'detail.playHint': '进入页面不会自动播放',
    'detail.lightboxHint': '点击空白处或按 Esc 关闭',
    'detail.close': '关闭',
    'detail.imgSource': '图源：网络',
    'detail.dynasty': '朝代',
    'detail.year': '年代',
    'detail.place': '地点',
    'detail.length': '桥长',
    'detail.span': '跨度',
    'detail.width': '桥宽',
    'detail.type': '类型',
    'detail.material': '材质',
    'detail.protection': '保护级别',
    'detail.noIntro': '暂无详细介绍。',
    'detail.cultureZhNote': '（文化原文暂以中文呈现）',
    'detail.nationalHeritage': '全国重点文物保护单位（{batch}）',
    'detail.nationalHeritageDefault': '全国重点文物保护单位（国家级）',
    '3d.title': '桥梁 - 千古飞虹',
    '3d.canvasAria': '三维桥梁模型',
    '3d.hint': '拖拽旋转 · 滚轮缩放 · 右键平移',
    '3d.back': '← 返回地图大屏',
    '3d.backDetail': '← 返回桥梁档案',
    '3d.init': '正在初始化…',
    '3d.loading': '正在加载模型…',
    '3d.ready': '加载完成 · 可拖拽浏览',
    '3d.fail': '模型加载失败',
    'knowledge.title': '智能文化驿站 — 千古飞虹',
    'knowledge.h1': '智能文化驿站',
    'knowledge.sub': '知识图谱与热词洞察 + 古桥智能问答。',
    'knowledge.tabViz': '数据洞察',
    'knowledge.tabAi': 'AI 智能助手',
    'knowledge.loading': '正在加载数据…',
    'knowledge.graphTitle': '知识图谱',
    'knowledge.graphSub': '探索古桥与朝代、地域、桥型、材质的关联网络',
    'knowledge.graphSearch': '搜索桥名、朝代、省份…',
    'knowledge.zoomOut': '缩小',
    'knowledge.zoomIn': '放大',
    'knowledge.reset': '重置视图',
    'knowledge.askAi': '问 AI',
    'knowledge.graphHint': '拖拽节点 · 滚轮或工具栏缩放 · 点击桥梁或属性节点查看详情',
    'knowledge.layers': '图层筛选',
    'knowledge.graphTip': '点击图谱中的<strong style="color:#d4a050">桥梁节点</strong>（金色）查看档案；点击朝代、省份等节点可列出相关古桥。',
    'knowledge.hotTitle': '文化热词',
    'knowledge.hotSub': '字号越大权重越高；点击热词可跳转 AI 助手并填入提问',
    'knowledge.aiTitle': '古桥 AI 助手',
    'knowledge.aiSub': '可问桥史、结构、诗词文化、朝代列表与名桥对比；在「数据洞察」页点击桥梁后，回答将结合该桥档案',
    'knowledge.aiPh': '例如：介绍赵州桥 / 宋代有哪些拱桥 / 对比赵州桥和卢沟桥',
    'knowledge.send': '发送',
    'knowledge.engine': '引擎与快捷问',
    'knowledge.localEngine': '本地知识引擎',
    'knowledge.localEngineHint': '：基于本馆古桥图鉴与文献摘要即时检索作答。',
    'knowledge.kimi': '启用 Kimi 大模型增强',
    'knowledge.clear': '清除',
    'knowledge.viewArchive': '查看档案',
    'knowledge.related': '关联 {n} 座古桥',
    'knowledge.noRelated': '暂无可见关联（或被图层筛选隐藏）',
    'knowledge.noGraph': '暂无图谱数据',
    'knowledge.nodeBridge': '桥梁 · 点击查看详情',
    'knowledge.nodeCat': '点击查看关联桥梁',
    'knowledge.localEngineCount': '：基于本馆 {n} 座古桥与文献摘要即时检索作答。',
    'year.ce': '公元 {n} 年',
    'year.bce': '公元前 {n} 年',
    'cat.dynasty': '朝代',
    'cat.province': '省份',
    'cat.type': '桥型',
    'cat.material': '材质'
  });

  mergeDict('en', {
    'nav.cover': 'Cover',
    'nav.coverBack': '← Cover',
    'nav.museum': 'Atlas Gallery',
    'nav.museumShort': 'Map Gallery',
    'nav.knowledge': 'Knowledge Hub',
    'nav.archivist': 'Archivist',
    'nav.closing': 'Epilogue',
    'nav.closingAlt': 'Epilogue',
    'nav.site': 'Site navigation',
    'agent.fab': 'Ask Archivist',
    'agent.fabTitle': 'Open Qianhong Archivist (with visit memory)',
    'agent.offlineTitle': 'Archivist offline — run python -m api.main first',
    'agent.askMemory': 'Ask Archivist',
    'knowledge.askArchivist': 'Ask Archivist',
    'asst.title': 'Qianhong Archivist',
    'asst.tabChat': 'Chat',
    'asst.tabScan': 'Scan',
    'asst.ph': 'Ask about a bridge, or scan first…',
    'asst.send': 'Send',
    'asst.scan': 'Scan bridge',
    'asst.scanHint': 'Point at a historic bridge (or upload a gallery photo). Matches are saved to visit memory.',
    'asst.capture': 'Capture',
    'asst.upload': 'Upload',
    'asst.welcome': 'I am the Qianhong archivist. Chat here, or use Scan to identify a bridge — results go into visit memory.',
    'asst.focus': 'Focus: ',
    'asst.noFocus': 'No bridge in focus',
    'asst.chipDossier': 'My dossier',
    'asst.chipRecommend': 'Recommend next',
    'asst.chipScan': 'Scan bridge',
    'asst.chipIntro': 'Introduce ',
    'asst.thinking': 'Thinking…',
    'asst.error': 'Request failed: ',
    'asst.errorHint': 'Make sure python -m api.main is running',
    'asst.noCamera': 'Camera not supported — please upload an image.',
    'asst.camDenied': 'Camera blocked — allow permission or upload instead.',
    'asst.identifying': 'Identifying…',
    'asst.identifyFail': 'Identify failed: ',
    'asst.noMatch': 'No gallery match. Try another angle or a clearer appearance photo.',
    'asst.matchOk': 'Matched',
    'asst.matchMaybe': 'Closest candidate',
    'asst.askThis': 'Explain this bridge',
    'asst.openDetail': 'Open archive',
    'asst.scanSuccess': 'Scan match: ',
    'asst.scanMaybe': 'Scan candidate: ',
    'asst.scanMemory': 'Saved to visit memory. Ask more, or tap Explain.',
    'asst.captureFail': 'Capture failed — allow camera or upload instead.',
    'music.label': 'Music',
    'music.pause': 'Pause',
    'music.aria': 'Background music: High Mountains Flowing Water',
    'music.title': 'Background music: High Mountains Flowing Water',
    'brand.title': 'Ancient Bridges',
    'brand.sub': 'Chinese Historic Bridges · Digital Museum',
    'index.title': 'Ancient Bridges · Chinese Historic Bridges Digital Museum',
    'index.searchAria': 'Find a bridge',
    'index.searchPh': 'Search · name or region',
    'index.searchInputAria': 'Search bridges; opens the atlas',
    'index.searchHint': 'Press Enter to open the atlas',
    'index.searchSeal': 'Go',
    'index.searchSealTitle': 'Search',
    'index.stamp': 'Millennia of Grace',
    'index.hero': 'A Bond Across<br>Ages',
    'index.lead': 'From the ingenuity of Zhaozhou Bridge to the dawn moon over Lugou Bridge, each historic bridge is poetry cast in stone. Explore maps and data that honor craftsmanship spanning a thousand years.',
    'index.cta': 'Begin Exploring',
    'index.ctaNote': 'Interactive map & bridge archives',
    'index.sideTitle': 'Eternal Rainbows',
    'index.sideCaption': 'Stone beams & iron cables endure',
    'index.footer': 'Eternal Rainbows · Interactive atlas & digital exhibition',
    'closing.title': 'Epilogue · Ancient Bridges',
    'closing.stamp': 'Lasting Echoes',
    'closing.hero': 'Thank You for<br>Visiting',
    'closing.lead': 'May these millennia-old spans and stories leave a gentle ripple.<br>Mountains and rivers remain; the rainbows still soar.',
    'closing.backMuseum': 'Back to Atlas Gallery',
    'closing.backCover': 'Back to Cover',
    'closing.footnote': 'Eternal Rainbows: Atlas of Ancient Chinese Bridge Engineering<br>Data visualization & digital exhibition · For learning only',
    'closing.sideTitle': 'Thank You',
    'closing.sideCaption': 'Bridge shadows drift into dreams',
    'closing.summaryEn': 'Across more than thirty historic bridges—from the Shang–Zhou era to Ming and Qing—these spans stretch across China\'s rivers and gorges. They hold imperial gardens and folk craft, war memories and love legends, engineering peaks and literary inspiration. Together they form a rich genealogy of Chinese bridge culture, embodying harmony between heaven and humanity.',
    'museum.title': 'Eternal Rainbows: Atlas of Ancient Chinese Bridges',
    'museum.sub': 'From wooden creek spans to eternal rainbows',
    'museum.searchAria': 'Search bridges',
    'museum.searchPh': 'Search name, dynasty, type, province…',
    'museum.searchTitle': 'Atlas search',
    'museum.searchSeal': 'Go',
    'museum.timelineTitle': 'Bridge timeline · swipe to browse spans in sequence',
    'museum.chartTech': 'Evolution of technique & materials',
    'museum.chartTechTip': 'Bridge counts by dynasty, stacked by main material (iron cables rise in Ming–Qing)',
    'museum.chartRegion': 'Regional bridge types',
    'museum.chartRegionTip': 'Four regions nationwide; each shows type counts. Legend = bridge type',
    'museum.chartSpan': 'Year × span: leaps in technology',
    'museum.chartSpanTip': 'Zhaozhou Bridge (Sui) raised the span ceiling of its age',
    'museum.resizeLeft': 'Drag to resize left sidebar',
    'museum.resizeRight': 'Drag to resize right sidebar',
    'museum.zoomGroup': 'Map zoom',
    'museum.zoomIn': 'Zoom in',
    'museum.zoomOut': 'Zoom out',
    'museum.models': 'Three landmarks · 3D models',
    'museum.types': 'Bridge types',
    'museum.dotTip': 'Dot size ≈ max single span',
    'museum.yearAxis': 'Timeline (CE)',
    'museum.yearAxisTip': 'Click anywhere on the year axis to jump; drag the knob to fine-tune.',
    'museum.yearAxisTitle': 'Click the year axis to jump; or drag the knob',
    'museum.yearAria': 'Year timeline',
    'museum.rank': 'Top 10 by span / length',
    'museum.rankSpan': 'By span',
    'museum.rankLength': 'By length',
    'museum.footerData': 'Data: Chinese bridges before 1911 · Theme: Fine Traditional Chinese Culture Series VI',
    'museum.tianditu': 'National Platform for Common Geospatial Information Services · Tianditu',
    'museum.footerMap': 'Map review no.: follow Tianditu’s published terms for online services; for standard maps, cite the Ministry of Natural Resources review number (e.g. GS(2019)xxxx).',
    'museum.ok': 'OK',
    'museum.cancel': 'Cancel',
    'museum.noMatch': 'No matching bridges',
    'museum.detailLink': 'Details →',
    'museum.confirmJump': 'Open the archive for “{name}”?',
    'museum.confirmDefault': 'Continue?',
    'museum.previewTitle': 'Timeline bridge · click image to flip to wireframe (drag title)',
    'museum.previewFlip': 'Click to flip: photo ↔ wireframe',
    'museum.previewEmpty': 'Drag the timeline to see bridges of that year',
    'museum.previewNoYear': 'No bridges for this year',
    'museum.previewMetaFlip': 'Click image above to flip wireframe',
    'museum.noWireframe': 'No wireframe image for this bridge yet',
    'museum.altAppearance': 'Appearance',
    'museum.altWireframe': 'Wireframe',
    'museum.mapKeyMissing': 'Please set your Tianditu API Key in config.js',
    'museum.mapFail': 'Failed to load Tianditu. Check your Key or network.',
    'museum.dataMissing': 'Place data/bridges.json or data/bridges-data.js in the correct path and refresh.',
    'museum.buildCount': 'Bridges built',
    'museum.bridgeUnit': '',
    'museum.yearAxisName': 'Year',
    'museum.spanAxisName': 'Max span (m)',
    'museum.other': 'Other',
    'museum.typeLabel': 'Type',
    'museum.maxSpan': 'Max single span',
    'detail.title': 'Bridge Archive - Eternal Rainbows',
    'detail.back': '← Back to map gallery',
    'detail.backShort': 'Back to map',
    'detail.notFound': 'Bridge not found.',
    'detail.entry3d': 'Enter →',
    'detail.basic': 'Basics',
    'detail.intro': 'Introduction',
    'detail.speak': 'Read aloud',
    'detail.pause': 'Pause',
    'detail.stop': 'Stop',
    'detail.videos': 'Videos',
    'detail.videoDesc': 'Selected public educational videos on historic bridges (see each platform for sources).',
    'detail.images': 'Bridge imagery · photo & wireframe',
    'detail.imagesDesc': 'Photo on the left, structural wireframe on the right for comparison.',
    'detail.appearance': 'Appearance',
    'detail.wireframe': 'Wireframe',
    'detail.compare': 'Photo ↔ wireframe compare',
    'detail.compareHint': 'Drag the vertical handle to compare photo and wireframe',
    'detail.poetry': 'Poetry & lore',
    'detail.noPoetry': 'No poetry or lore yet',
    'detail.anecdote': 'Historical lore',
    'detail.poetryRefs': 'Related poems & texts',
    'detail.insight': 'Cultural insight',
    'detail.playVideo': 'Click to play',
    'detail.playHint': 'Videos do not autoplay',
    'detail.lightboxHint': 'Click empty area or press Esc to close',
    'detail.close': 'Close',
    'detail.imgSource': 'Source: web',
    'detail.dynasty': 'Dynasty',
    'detail.year': 'Year',
    'detail.place': 'Location',
    'detail.length': 'Length',
    'detail.span': 'Span',
    'detail.width': 'Width',
    'detail.type': 'Type',
    'detail.material': 'Material',
    'detail.protection': 'Protection',
    'detail.noIntro': 'No detailed introduction yet.',
    'detail.cultureZhNote': '(Cultural texts shown in Chinese)',
    'detail.nationalHeritage': 'National Key Cultural Relics ({batch})',
    'detail.nationalHeritageDefault': 'National Key Cultural Relics (national level)',
    '3d.title': 'Bridge - Eternal Rainbows',
    '3d.canvasAria': '3D bridge model',
    '3d.hint': 'Drag to orbit · scroll to zoom · right-drag to pan',
    '3d.back': '← Back to map gallery',
    '3d.backDetail': '← Back to archive',
    '3d.init': 'Initializing…',
    '3d.loading': 'Loading model…',
    '3d.ready': 'Ready · drag to explore',
    '3d.fail': 'Failed to load model',
    'knowledge.title': 'Knowledge Hub — Eternal Rainbows',
    'knowledge.h1': 'Knowledge Hub',
    'knowledge.sub': 'Knowledge graph, hot words & Q&A on historic bridges.',
    'knowledge.tabViz': 'Insights',
    'knowledge.tabAi': 'AI Assistant',
    'knowledge.loading': 'Loading data…',
    'knowledge.graphTitle': 'Knowledge graph',
    'knowledge.graphSub': 'Explore links among bridges, dynasties, regions, types & materials',
    'knowledge.graphSearch': 'Search bridge, dynasty, province…',
    'knowledge.zoomOut': 'Zoom out',
    'knowledge.zoomIn': 'Zoom in',
    'knowledge.reset': 'Reset view',
    'knowledge.askAi': 'Ask AI',
    'knowledge.graphHint': 'Drag nodes · scroll or toolbar to zoom · click a bridge or attribute for details',
    'knowledge.layers': 'Layer filters',
    'knowledge.graphTip': 'Click a <strong style="color:#d4a050">bridge node</strong> (gold) for its archive; click dynasty, province, etc. to list related bridges.',
    'knowledge.hotTitle': 'Cultural hot words',
    'knowledge.hotSub': 'Larger type = higher weight; click a word to ask the AI',
    'knowledge.aiTitle': 'Bridge AI assistant',
    'knowledge.aiSub': 'Ask about history, structure, poetry, dynasty lists & comparisons; answers use the selected bridge archive when set from Insights',
    'knowledge.aiPh': 'e.g. Introduce Zhaozhou Bridge / Song arch bridges / Compare Zhaozhou & Lugou',
    'knowledge.send': 'Send',
    'knowledge.engine': 'Engine & quick asks',
    'knowledge.localEngine': 'Local knowledge engine',
    'knowledge.localEngineHint': ': instant answers from this museum’s atlas and text summaries.',
    'knowledge.kimi': 'Enable Kimi LLM enhancement',
    'knowledge.clear': 'Clear',
    'knowledge.viewArchive': 'Open archive',
    'knowledge.related': '{n} related bridges',
    'knowledge.noRelated': 'No visible links (or hidden by layer filters)',
    'knowledge.noGraph': 'No graph data',
    'knowledge.nodeBridge': 'Bridge · click for details',
    'knowledge.nodeCat': 'Click to see related bridges',
    'knowledge.localEngineCount': ': instant answers from {n} bridges and text summaries in this museum.',
    'year.ce': '{n} CE',
    'year.bce': '{n} BCE',
    'cat.dynasty': 'Dynasty',
    'cat.province': 'Province',
    'cat.type': 'Type',
    'cat.material': 'Material'
  });

  /* init */
  document.documentElement.lang = getLang() === 'en' ? 'en' : 'zh-CN';
  document.documentElement.setAttribute('data-lang', getLang());

  function boot() {
    bindToggles(document);
    apply(document);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  global.BridgeI18n = {
    t: t,
    getLang: getLang,
    setLang: setLang,
    toggleLang: toggleLang,
    apply: apply,
    field: field,
    bridgeName: bridgeName,
    bridgeIntro: bridgeIntro,
    yearLabel: yearLabel,
    BRIDGE_EN: BRIDGE_EN,
    FIELD_EN: FIELD_EN,
    mergeDict: mergeDict
  };
})(typeof window !== 'undefined' ? window : this);
