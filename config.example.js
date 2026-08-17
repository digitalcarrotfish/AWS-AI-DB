// 复制本文件为 config.js 并填入你的密钥（config.js 已加入 .gitignore，不会上传到 GitHub）

// 天地图：https://lbs.tianditu.gov.cn/
window.TIANDITU_KEY = '您的天地图API密钥';

// 可选：智能驿站大模型（OpenAI 兼容接口，默认关闭）
window.BRIDGE_AI = {
  enabled: false,
  provider: 'kimi',
  apiBase: 'https://api.moonshot.cn/v1',
  apiKey: '',
  model: 'moonshot-v1-8k'
};

// 飞虹智忆 Agent（同域优先：python -m api.main → http://127.0.0.1:8787/）
// apiBase 留空表示同域；仅用 python -m http.server 8080 时才需填绝对地址
window.QIANHONG_AGENT = {
  enabled: true,
  apiBase: '',
  agentUi: '/agent/'
};
