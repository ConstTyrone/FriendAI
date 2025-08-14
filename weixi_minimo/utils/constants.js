// 常量定义
export const API_CONFIG = {
  BASE_URL: 'https://weixin.dataelem.com',
  TIMEOUT: 30000,  // 增加到30秒，特别是为AI匹配
  RETRY_COUNT: 3,
  MATCH_TIMEOUT: 60000  // AI匹配专用超时，60秒
};

export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  WECHAT_USER_ID: 'wechat_user_id',
  USER_INFO: 'user_info',
  CONTACT_CACHE: 'contact_cache',
  SEARCH_HISTORY: 'search_history',
  APP_SETTINGS: 'app_settings'
};

export const PAGE_ROUTES = {
  CONTACT_LIST: '/pages/contact-list/contact-list',
  AI_SEARCH: '/pages/ai-search/ai-search',
  CONTACT_DETAIL: '/pages/contact-detail/contact-detail',
  CONTACT_FORM: '/pages/contact-form/contact-form',
  SETTINGS: '/pages/settings/settings'
};

export const EVENT_TYPES = {
  LOGIN_SUCCESS: 'loginSuccess',
  LOGOUT: 'logout',
  CONTACT_UPDATED: 'contactUpdated',
  CONTACT_DELETED: 'contactDeleted',
  SEARCH_PERFORMED: 'searchPerformed'
};

export const UI_CONFIG = {
  PAGE_SIZE: 20,
  SEARCH_DEBOUNCE: 500,
  CACHE_EXPIRE_TIME: 5 * 60 * 1000, // 5分钟
  AUTO_REFRESH_INTERVAL: 30 * 1000, // 30秒
  // 企微客服配置
  CORP_ID: 'ww7b4256dcdcea9b3e', // 企业ID，需要配置
  KF_ID: 'kfc6fac668195f8389e' // 客服账号ID，需要配置
};

export const ERROR_MESSAGES = {
  NETWORK_ERROR: '网络连接失败，请检查网络设置',
  AUTH_FAILED: '认证失败，请重新登录',
  SERVER_ERROR: '服务器错误，请稍后重试',
  DATA_NOT_FOUND: '数据不存在',
  OPERATION_FAILED: '操作失败，请重试'
};

export const CONTACT_FIELDS = {
  PROFILE_NAME: 'profile_name',
  GENDER: 'gender',
  AGE: 'age',
  PHONE: 'phone',
  LOCATION: 'location',
  MARITAL_STATUS: 'marital_status',
  EDUCATION: 'education',
  COMPANY: 'company',
  POSITION: 'position',
  ASSET_LEVEL: 'asset_level',
  PERSONALITY: 'personality',
  AI_SUMMARY: 'ai_summary'
};

export const SEARCH_SUGGESTIONS = [
  '最近联系的重要客户',
  '上海地区的潜在客户',
  '需要跟进的联系人',
  '高净值人群',
  '有投资意向的客户',
  '企业高管',
  '创业者',
  '技术专家'
];