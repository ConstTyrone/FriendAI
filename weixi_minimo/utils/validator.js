/**
 * 数据验证工具类
 */

/**
 * 验证是否为空
 */
export function isEmpty(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string') return value.trim().length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'object') return Object.keys(value).length === 0;
  return false;
}

/**
 * 验证是否不为空
 */
export function isNotEmpty(value) {
  return !isEmpty(value);
}

/**
 * 验证邮箱格式
 */
export function isEmail(email) {
  if (!email) return false;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * 验证手机号格式
 */
export function isPhone(phone) {
  if (!phone) return false;
  
  // 移除所有非数字字符
  const cleaned = phone.replace(/\D/g, '');
  
  // 中国手机号：11位，以1开头
  if (cleaned.length === 11 && cleaned.startsWith('1')) {
    return true;
  }
  
  // 其他格式：7-15位数字
  if (cleaned.length >= 7 && cleaned.length <= 15) {
    return true;
  }
  
  return false;
}

/**
 * 验证身份证号格式
 */
export function isIdCard(idCard) {
  if (!idCard) return false;
  
  const idCardRegex = /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/;
  return idCardRegex.test(idCard);
}

/**
 * 验证URL格式
 */
export function isUrl(url) {
  if (!url) return false;
  
  try {
    new URL(url);
    return true;
  } catch {
    // 尝试添加协议后再验证
    try {
      new URL(`http://${url}`);
      return true;
    } catch {
      return false;
    }
  }
}

/**
 * 验证数字
 */
export function isNumber(value) {
  return !isNaN(value) && !isNaN(parseFloat(value));
}

/**
 * 验证整数
 */
export function isInteger(value) {
  return Number.isInteger(Number(value));
}

/**
 * 验证正整数
 */
export function isPositiveInteger(value) {
  return isInteger(value) && Number(value) > 0;
}

/**
 * 验证数字范围
 */
export function isNumberInRange(value, min, max) {
  const num = Number(value);
  if (isNaN(num)) return false;
  if (typeof min === 'number' && num < min) return false;
  if (typeof max === 'number' && num > max) return false;
  return true;
}

/**
 * 验证字符串长度
 */
export function isLengthInRange(str, min, max) {
  if (!str) return min === 0;
  const length = str.length;
  if (typeof min === 'number' && length < min) return false;
  if (typeof max === 'number' && length > max) return false;
  return true;
}

/**
 * 验证年龄
 */
export function isValidAge(age) {
  if (!age) return false;
  const ageNum = Number(age);
  return isInteger(ageNum) && ageNum >= 0 && ageNum <= 150;
}

/**
 * 验证姓名
 */
export function isValidName(name) {
  if (!name) return false;
  
  const trimmedName = name.trim();
  
  // 长度检查：1-50个字符
  if (trimmedName.length < 1 || trimmedName.length > 50) {
    return false;
  }
  
  // 不能全是数字
  if (/^\d+$/.test(trimmedName)) {
    return false;
  }
  
  // 不能包含特殊字符（除了空格、点号、连字符）
  if (/[<>{}[\]\\\/\?=+&%$#@!`~|]/.test(trimmedName)) {
    return false;
  }
  
  return true;
}

/**
 * 验证公司名称
 */
export function isValidCompany(company) {
  if (!company) return true; // 公司名称是可选的
  
  const trimmedCompany = company.trim();
  
  // 长度检查：1-100个字符
  if (trimmedCompany.length > 100) {
    return false;
  }
  
  return true;
}

/**
 * 验证职位
 */
export function isValidPosition(position) {
  if (!position) return true; // 职位是可选的
  
  const trimmedPosition = position.trim();
  
  // 长度检查：1-50个字符
  if (trimmedPosition.length > 50) {
    return false;
  }
  
  return true;
}

/**
 * 验证地址
 */
export function isValidLocation(location) {
  if (!location) return true; // 地址是可选的
  
  const trimmedLocation = location.trim();
  
  // 长度检查：1-200个字符
  if (trimmedLocation.length > 200) {
    return false;
  }
  
  return true;
}

/**
 * 验证性别
 */
export function isValidGender(gender) {
  if (!gender) return true; // 性别是可选的
  
  const validGenders = ['男', '女', '未知', 'male', 'female', 'unknown'];
  return validGenders.includes(gender);
}

/**
 * 验证教育程度
 */
export function isValidEducation(education) {
  if (!education) return true; // 教育程度是可选的
  
  const validEducations = [
    '小学', '初中', '高中', '大专', '本科', '硕士', '博士',
    'primary', 'middle', 'high', 'college', 'bachelor', 'master', 'doctor'
  ];
  
  return validEducations.includes(education);
}

/**
 * 验证婚姻状况
 */
export function isValidMaritalStatus(status) {
  if (!status) return true; // 婚姻状况是可选的
  
  const validStatuses = [
    '单身', '已婚', '离异', '丧偶', '已婚已育', '已婚未育',
    'single', 'married', 'divorced', 'widowed', 'married_with_children', 'married_no_children'
  ];
  
  return validStatuses.includes(status);
}

/**
 * 验证资产水平
 */
export function isValidAssetLevel(level) {
  if (!level) return true; // 资产水平是可选的
  
  const validLevels = ['低', '中等', '高', '很高', 'low', 'medium', 'high', 'very_high'];
  return validLevels.includes(level);
}

/**
 * 验证联系人对象
 */
export function validateContact(contact) {
  const errors = [];
  
  // 必填字段验证
  if (!isValidName(contact.profile_name || contact.name)) {
    errors.push('姓名格式不正确');
  }
  
  // 可选字段验证
  if (contact.phone && !isPhone(contact.phone)) {
    errors.push('手机号格式不正确');
  }
  
  if (contact.email && !isEmail(contact.email)) {
    errors.push('邮箱格式不正确');
  }
  
  if (contact.age && !isValidAge(contact.age)) {
    errors.push('年龄格式不正确');
  }
  
  if (contact.gender && !isValidGender(contact.gender)) {
    errors.push('性别格式不正确');
  }
  
  if (contact.education && !isValidEducation(contact.education)) {
    errors.push('教育程度格式不正确');
  }
  
  if (contact.marital_status && !isValidMaritalStatus(contact.marital_status)) {
    errors.push('婚姻状况格式不正确');
  }
  
  if (contact.asset_level && !isValidAssetLevel(contact.asset_level)) {
    errors.push('资产水平格式不正确');
  }
  
  if (contact.company && !isValidCompany(contact.company)) {
    errors.push('公司名称格式不正确');
  }
  
  if (contact.position && !isValidPosition(contact.position)) {
    errors.push('职位格式不正确');
  }
  
  if (contact.location && !isValidLocation(contact.location)) {
    errors.push('地址格式不正确');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * 验证搜索关键词
 */
export function isValidSearchQuery(query) {
  if (!query) return false;
  
  const trimmedQuery = query.trim();
  
  // 长度检查：1-100个字符
  if (trimmedQuery.length < 1 || trimmedQuery.length > 100) {
    return false;
  }
  
  // 不能全是特殊字符
  if (/^[^\w\u4e00-\u9fa5]+$/.test(trimmedQuery)) {
    return false;
  }
  
  return true;
}

/**
 * 验证分页参数
 */
export function validatePagination(page, pageSize) {
  const errors = [];
  
  if (!isPositiveInteger(page)) {
    errors.push('页码必须是正整数');
  }
  
  if (!isPositiveInteger(pageSize)) {
    errors.push('每页数量必须是正整数');
  } else if (pageSize > 100) {
    errors.push('每页数量不能超过100');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * 清理和验证输入字符串
 */
export function sanitizeString(str, maxLength = 255) {
  if (!str) return '';
  
  // 移除前后空白
  let cleaned = str.trim();
  
  // 限制长度
  if (cleaned.length > maxLength) {
    cleaned = cleaned.substring(0, maxLength);
  }
  
  // 移除危险字符
  cleaned = cleaned.replace(/[<>\"'&]/g, '');
  
  return cleaned;
}

/**
 * 验证对象是否包含必要属性
 */
export function hasRequiredFields(obj, requiredFields) {
  if (!obj || typeof obj !== 'object') {
    return false;
  }
  
  return requiredFields.every(field => {
    return obj.hasOwnProperty(field) && isNotEmpty(obj[field]);
  });
}

/**
 * 验证数组
 */
export function isValidArray(arr, minLength = 0, maxLength = Infinity) {
  if (!Array.isArray(arr)) return false;
  if (arr.length < minLength) return false;
  if (arr.length > maxLength) return false;
  return true;
}

/**
 * 创建验证器类
 */
export class Validator {
  constructor() {
    this.rules = [];
  }
  
  /**
   * 添加验证规则
   */
  addRule(field, validator, message) {
    this.rules.push({ field, validator, message });
    return this;
  }
  
  /**
   * 添加必填规则
   */
  required(field, message = `${field}是必填项`) {
    return this.addRule(field, isNotEmpty, message);
  }
  
  /**
   * 添加长度规则
   */
  length(field, min, max, message = `${field}长度必须在${min}-${max}之间`) {
    return this.addRule(field, (value) => isLengthInRange(value, min, max), message);
  }
  
  /**
   * 添加邮箱规则
   */
  email(field, message = `${field}格式不正确`) {
    return this.addRule(field, isEmail, message);
  }
  
  /**
   * 添加手机号规则
   */
  phone(field, message = `${field}格式不正确`) {
    return this.addRule(field, isPhone, message);
  }
  
  /**
   * 执行验证
   */
  validate(data) {
    const errors = [];
    
    this.rules.forEach(rule => {
      const value = data[rule.field];
      if (!rule.validator(value)) {
        errors.push({
          field: rule.field,
          message: rule.message
        });
      }
    });
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }
  
  /**
   * 清空规则
   */
  clear() {
    this.rules = [];
    return this;
  }
}