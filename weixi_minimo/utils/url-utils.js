// URL工具函数，兼容微信小程序环境

/**
 * 将对象转换为查询字符串
 * @param {Object} params - 参数对象
 * @returns {string} - 查询字符串（不包含?）
 */
export function objectToQueryString(params) {
  if (!params || typeof params !== 'object') {
    return '';
  }

  const pairs = [];
  
  for (const key in params) {
    if (params.hasOwnProperty(key)) {
      const value = params[key];
      
      // 跳过undefined和null值
      if (value === undefined || value === null) {
        continue;
      }
      
      // 对键和值进行URL编码
      pairs.push(`${encodeURIComponent(key)}=${encodeURIComponent(value)}`);
    }
  }
  
  return pairs.join('&');
}

/**
 * 解析查询字符串为对象
 * @param {string} queryString - 查询字符串
 * @returns {Object} - 参数对象
 */
export function queryStringToObject(queryString) {
  if (!queryString) {
    return {};
  }
  
  // 移除开头的?
  if (queryString.startsWith('?')) {
    queryString = queryString.slice(1);
  }
  
  const params = {};
  const pairs = queryString.split('&');
  
  for (const pair of pairs) {
    const [key, value] = pair.split('=');
    if (key) {
      params[decodeURIComponent(key)] = value ? decodeURIComponent(value) : '';
    }
  }
  
  return params;
}

/**
 * 构建完整的URL
 * @param {string} baseUrl - 基础URL
 * @param {Object} params - 查询参数
 * @returns {string} - 完整的URL
 */
export function buildUrl(baseUrl, params) {
  const queryString = objectToQueryString(params);
  
  if (!queryString) {
    return baseUrl;
  }
  
  // 检查baseUrl是否已经包含查询参数
  const separator = baseUrl.includes('?') ? '&' : '?';
  
  return `${baseUrl}${separator}${queryString}`;
}