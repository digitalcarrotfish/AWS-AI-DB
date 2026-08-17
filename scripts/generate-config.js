/**
 * Netlify 构建时根据环境变量生成 config.js（勿把密钥提交到 Git）
 */
const fs = require('fs');
const path = require('path');

const tianditu = (process.env.TIANDITU_KEY || '').trim() || '您的天地图API密钥';
const aiEnabled = /^true|1|yes$/i.test(process.env.BRIDGE_AI_ENABLED || '');
const aiKey = (process.env.BRIDGE_AI_API_KEY || '').trim();
const aiBase = (process.env.BRIDGE_AI_API_BASE || 'https://api.moonshot.cn/v1').trim();
const aiModel = (process.env.BRIDGE_AI_MODEL || 'moonshot-v1-8k').trim();
const aiProvider = (process.env.BRIDGE_AI_PROVIDER || 'kimi').trim();
const agentEnabled = !/^false|0|no$/i.test(process.env.QIANHONG_AGENT_ENABLED || 'true');
const agentApi = (process.env.QIANHONG_AGENT_API_BASE != null
  ? process.env.QIANHONG_AGENT_API_BASE
  : '').trim();
const agentUi = (process.env.QIANHONG_AGENT_UI || '/agent/').trim().replace(/\/?$/, '/');

const content =
  '// 由 Netlify 构建脚本自动生成，请勿手动提交\n' +
  "window.TIANDITU_KEY = " + JSON.stringify(tianditu) + ";\n\n" +
  'window.BRIDGE_AI = {\n' +
  '  enabled: ' + (aiEnabled && !!aiKey) + ',\n' +
  '  provider: ' + JSON.stringify(aiProvider) + ',\n' +
  '  apiBase: ' + JSON.stringify(aiBase) + ',\n' +
  '  apiKey: ' + JSON.stringify(aiKey) + ',\n' +
  '  model: ' + JSON.stringify(aiModel) + '\n' +
  '};\n\n' +
  'window.QIANHONG_AGENT = {\n' +
  '  enabled: ' + agentEnabled + ',\n' +
  '  apiBase: ' + JSON.stringify(agentApi.replace(/\/$/, '')) + ',\n' +
  '  agentUi: ' + JSON.stringify(agentUi) + '\n' +
  '};\n';

const out = path.join(__dirname, '..', 'config.js');
fs.writeFileSync(out, content, 'utf8');
console.log('Wrote config.js (TIANDITU_KEY:', tianditu !== '您的天地图API密钥' ? 'set' : 'placeholder', ')');
