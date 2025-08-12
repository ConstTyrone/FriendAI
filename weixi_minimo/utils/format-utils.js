/**
 * 格式化工具类
 */

/**
 * 格式化日期
 */
export function formatDate(date, format = 'YYYY-MM-DD') {
  if (!date) return '';
  
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';
  
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hour = String(d.getHours()).padStart(2, '0');
  const minute = String(d.getMinutes()).padStart(2, '0');
  const second = String(d.getSeconds()).padStart(2, '0');
  
  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hour)
    .replace('mm', minute)
    .replace('ss', second);
}

/**
 * 格式化相对时间
 */
export function formatRelativeTime(date) {
  if (!date) return '';
  
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';
  
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  const month = 30 * day;
  const year = 365 * day;
  
  if (diff < minute) {
    return '刚刚';
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)}分钟前`;
  } else if (diff < day) {
    return `${Math.floor(diff / hour)}小时前`;
  } else if (diff < month) {
    return `${Math.floor(diff / day)}天前`;
  } else if (diff < year) {
    return `${Math.floor(diff / month)}个月前`;
  } else {
    return `${Math.floor(diff / year)}年前`;
  }
}

/**
 * 格式化电话号码
 */
export function formatPhone(phone) {
  if (!phone) return '';
  
  // 移除所有非数字字符
  const cleaned = phone.replace(/\D/g, '');
  
  // 中国手机号码格式化
  if (cleaned.length === 11 && cleaned.startsWith('1')) {
    return `${cleaned.slice(0, 3)} ${cleaned.slice(3, 7)} ${cleaned.slice(7)}`;
  }
  
  // 其他格式保持原样
  return phone;
}

/**
 * 脱敏电话号码
 */
export function maskPhone(phone) {
  if (!phone) return '';
  
  const cleaned = phone.replace(/\D/g, '');
  
  if (cleaned.length === 11) {
    return `${cleaned.slice(0, 3)}****${cleaned.slice(7)}`;
  }
  
  if (cleaned.length >= 7) {
    const visibleStart = Math.min(3, Math.floor(cleaned.length / 3));
    const visibleEnd = Math.min(3, Math.floor(cleaned.length / 3));
    const start = cleaned.slice(0, visibleStart);
    const end = cleaned.slice(-visibleEnd);
    const middle = '*'.repeat(cleaned.length - visibleStart - visibleEnd);
    return `${start}${middle}${end}`;
  }
  
  return phone;
}

/**
 * 格式化姓名首字母
 */
export function getNameInitial(name) {
  if (!name) return '?';
  
  // 取第一个字符
  const firstChar = name.trim().charAt(0);
  
  // 如果是中文，直接返回
  if (/[\u4e00-\u9fa5]/.test(firstChar)) {
    return firstChar;
  }
  
  // 如果是英文，返回大写
  if (/[a-zA-Z]/.test(firstChar)) {
    return firstChar.toUpperCase();
  }
  
  // 其他情况返回问号
  return '?';
}

/**
 * 生成头像颜色
 */
export function getAvatarColor(name) {
  if (!name) return '#cccccc';
  
  const colors = [
    '#ff6b6b', '#ffa726', '#ffcc02', '#66bb6a',
    '#42a5f5', '#ab47bc', '#ef5350', '#ff7043',
    '#ffd54f', '#81c784', '#29b6f6', '#ba68c8'
  ];
  
  // 根据姓名生成一个稳定的索引
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  return colors[Math.abs(hash) % colors.length];
}

/**
 * 格式化置信度
 */
export function formatConfidence(score) {
  if (typeof score !== 'number') return '未知';
  
  const percentage = Math.round(score * 100);
  
  if (percentage >= 90) {
    return `${percentage}% 很高`;
  } else if (percentage >= 70) {
    return `${percentage}% 较高`;
  } else if (percentage >= 50) {
    return `${percentage}% 中等`;
  } else {
    return `${percentage}% 较低`;
  }
}

/**
 * 格式化资产水平
 */
export function formatAssetLevel(level) {
  const levelMap = {
    'low': '低',
    'medium': '中等',
    'high': '高',
    'very_high': '很高'
  };
  
  return levelMap[level] || level || '未知';
}

/**
 * 格式化婚姻状况
 */
export function formatMaritalStatus(status) {
  const statusMap = {
    'single': '单身',
    'married': '已婚',
    'divorced': '离异',
    'widowed': '丧偶',
    'married_with_children': '已婚已育',
    'married_no_children': '已婚未育'
  };
  
  return statusMap[status] || status || '未知';
}

/**
 * 格式化教育程度
 */
export function formatEducation(education) {
  const educationMap = {
    'primary': '小学',
    'middle': '初中',
    'high': '高中',
    'college': '大专',
    'bachelor': '本科',
    'master': '硕士',
    'doctor': '博士'
  };
  
  return educationMap[education] || education || '未知';
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 格式化数字
 */
export function formatNumber(num) {
  if (typeof num !== 'number') return '0';
  
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  
  return num.toString();
}

/**
 * 截断文本
 */
export function truncateText(text, maxLength = 50) {
  if (!text) return '';
  
  if (text.length <= maxLength) {
    return text;
  }
  
  return text.slice(0, maxLength) + '...';
}

/**
 * 高亮搜索关键词
 */
export function highlightKeyword(text, keyword) {
  if (!text || !keyword) return text;
  
  const regex = new RegExp(`(${keyword})`, 'gi');
  return text.replace(regex, '<mark>$1</mark>');
}

/**
 * 解析标签字符串
 */
export function parseTags(tagString) {
  if (!tagString) return [];
  
  if (typeof tagString === 'string') {
    return tagString.split(',').map(tag => tag.trim()).filter(tag => tag);
  }
  
  if (Array.isArray(tagString)) {
    return tagString;
  }
  
  return [];
}

/**
 * 格式化标签
 */
export function formatTags(tags) {
  if (!tags) return '';
  
  if (Array.isArray(tags)) {
    return tags.join(', ');
  }
  
  return tags.toString();
}

/**
 * 格式化联系人显示名称
 */
export function formatContactDisplayName(contact) {
  if (!contact) return '未知联系人';
  
  const name = contact.profile_name || contact.name;
  if (name) return name;
  
  if (contact.company && contact.position) {
    return `${contact.company} - ${contact.position}`;
  }
  
  if (contact.company) return contact.company;
  if (contact.position) return contact.position;
  if (contact.phone) return maskPhone(contact.phone);
  
  return '未知联系人';
}

/**
 * 格式化联系人简介
 */
export function formatContactSummary(contact) {
  if (!contact) return '';
  
  const parts = [];
  
  if (contact.age) parts.push(`${contact.age}岁`);
  if (contact.gender) parts.push(contact.gender);
  if (contact.location) parts.push(contact.location);
  if (contact.company) parts.push(contact.company);
  if (contact.position) parts.push(contact.position);
  
  return parts.join(' · ');
}

/**
 * 验证并格式化URL
 */
export function formatUrl(url) {
  if (!url) return '';
  
  if (!/^https?:\/\//i.test(url)) {
    return `http://${url}`;
  }
  
  return url;
}

/**
 * 格式化JSON为可读字符串
 */
export function formatJSON(obj, indent = 2) {
  try {
    return JSON.stringify(obj, null, indent);
  } catch (error) {
    return obj.toString();
  }
}

/**
 * 解析JSON字符串
 */
export function parseJSON(str, defaultValue = null) {
  try {
    return JSON.parse(str);
  } catch (error) {
    return defaultValue;
  }
}