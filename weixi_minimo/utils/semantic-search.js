/**
 * 本地智能语义搜索引擎
 * 不依赖AI API，通过本地算法实现智能搜索
 */

// 关键词映射库
const KEYWORD_MAPPINGS = {
  // 职业/行业映射
  职业: {
    '程序员': ['程序员', '开发', '工程师', 'developer', 'engineer', 'coder', '码农', '技术'],
    '金融': ['银行', '投资', '证券', '保险', '基金', '金融', '财务', '会计', '审计'],
    '医生': ['医生', '医师', '大夫', '医疗', '护士', '药师', '医院'],
    '老师': ['老师', '教师', '教授', '讲师', '教育', '培训师', '导师'],
    '销售': ['销售', '市场', '营销', '推广', '客户经理', '业务员'],
    '设计': ['设计师', '美工', 'UI', 'UX', '视觉', '平面', '产品设计'],
    '管理': ['经理', '总监', '主管', '领导', '管理', 'CEO', 'CTO', 'VP'],
    '法律': ['律师', '法务', '法律', '司法', '检察', '法官', '仲裁'],
    '媒体': ['记者', '编辑', '媒体', '新闻', '广告', '传媒', '公关'],
    '咨询': ['咨询', '顾问', '分析师', '策略', '麦肯锡', '德勤', 'BCG']
  },
  
  // 地域映射
  地域: {
    '北京': ['北京', '京', '帝都', '中关村', '朝阳', '海淀', '西城', '东城'],
    '上海': ['上海', '沪', '魔都', '浦东', '黄浦', '静安', '徐汇'],
    '广州': ['广州', '穗', '羊城', '天河', '越秀', '荔湾'],
    '深圳': ['深圳', '鹏城', '南山', '福田', '罗湖', '宝安'],
    '杭州': ['杭州', '西湖', '滨江', '余杭', '萧山'],
    '成都': ['成都', '蓉城', '锦江', '青羊', '金牛', '武侯'],
    '南京': ['南京', '宁', '金陵', '鼓楼', '玄武', '建邺'],
    '武汉': ['武汉', '汉', '江城', '武昌', '汉口', '汉阳']
  },
  
  // 年龄特征映射
  年龄: {
    '年轻': { min: 0, max: 30, keywords: ['年轻', '青年', '小伙', '姑娘', '90后', '95后', '00后'] },
    '中年': { min: 30, max: 50, keywords: ['中年', '成熟', '80后', '85后'] },
    '资深': { min: 45, max: 70, keywords: ['资深', '经验丰富', '老练', '70后', '75后'] }
  },
  
  // 学历映射
  学历: {
    '高学历': ['博士', 'PhD', '硕士', '研究生', '清华', '北大', '985', '211', '海归'],
    '本科': ['本科', '学士', '大学', '学院'],
    '专科': ['专科', '大专', '职业', '技术学院']
  },
  
  // 性格特征映射
  性格: {
    '外向': ['外向', '开朗', '活泼', '健谈', '社交', '热情', '积极'],
    '内向': ['内向', '安静', '沉稳', '深思', '专注', '细致'],
    '领导': ['领导力', '决策', '管理', '指挥', '组织', '统筹'],
    '专业': ['专业', '技术', '专家', '精通', '资深', '权威']
  },
  
  // 资产水平映射
  资产: {
    '富有': ['有钱', '富有', '土豪', '高收入', '豪车', '别墅', '投资'],
    '中产': ['中产', '小康', '稳定', '房产', '理财'],
    '普通': ['普通', '一般', '工薪', '上班族']
  }
};

// 查询意图识别模式
const QUERY_PATTERNS = {
  // 年龄模式：30岁、三十岁、30-35岁
  age: [
    /(\d+)岁/, 
    /([三四五六七八九十]+)岁/,
    /(\d+)[-到至](\d+)岁/,
    /(20|30|40|50|60)多岁/
  ],
  
  // 性别模式
  gender: [
    /(男|女|先生|女士|小姐|帅哥|美女|大叔|阿姨)/
  ],
  
  // 地域模式：在北京、北京的、来自上海
  location: [
    /在([京沪穗深杭蓉宁汉津渝青厦昆贵南太石郑长合福]|北京|上海|广州|深圳|杭州|成都|南京|武汉|天津|重庆)/,
    /([京沪穗深杭蓉宁汉津渝青厦昆贵南太石郑长合福]|北京|上海|广州|深圳|杭州|成都|南京|武汉|天津|重庆)的/,
    /来自([京沪穗深杭蓉宁汉津渝青厦昆贵南太石郑长合福]|北京|上海|广州|深圳|杭州|成都|南京|武汉|天津|重庆)/
  ],
  
  // 职业模式：做XX的、从事XX、XX行业
  profession: [
    /做(.+?)的/,
    /从事(.+)/,
    /(.+?)行业/,
    /(.+?)工作/,
    /是(.+?)$/
  ]
};

class SemanticSearchEngine {
  constructor() {
    this.mappings = KEYWORD_MAPPINGS;
    this.patterns = QUERY_PATTERNS;
  }

  /**
   * 解析自然语言查询，转换为结构化搜索条件
   * @param {string} query - 用户输入的查询字符串
   * @returns {Object} 解析后的搜索条件
   */
  parseQuery(query) {
    const conditions = {
      keywords: [],
      age: null,
      gender: null,
      location: [],
      profession: [],
      education: [],
      personality: [],
      assets: [],
      original: query.trim()
    };

    const lowerQuery = query.toLowerCase();

    // 1. 年龄解析
    this.patterns.age.forEach(pattern => {
      const match = query.match(pattern);
      if (match) {
        if (match[2]) {
          // 年龄范围：30-35岁
          conditions.age = { min: parseInt(match[1]), max: parseInt(match[2]) };
        } else if (match[1]) {
          const age = this.parseAge(match[1]);
          conditions.age = { exact: age, range: [age - 2, age + 2] };
        }
      }
    });

    // 2. 性别解析
    this.patterns.gender.forEach(pattern => {
      const match = query.match(pattern);
      if (match) {
        const gender = match[1];
        if (['男', '先生', '帅哥', '大叔'].includes(gender)) {
          conditions.gender = '男';
        } else if (['女', '女士', '小姐', '美女', '阿姨'].includes(gender)) {
          conditions.gender = '女';
        }
      }
    });

    // 3. 地域解析
    this.patterns.location.forEach(pattern => {
      const match = query.match(pattern);
      if (match && match[1]) {
        const location = match[1];
        conditions.location.push(...this.expandLocation(location));
      }
    });

    // 4. 职业解析
    this.patterns.profession.forEach(pattern => {
      const match = query.match(pattern);
      if (match && match[1]) {
        const profession = match[1].trim();
        conditions.profession.push(...this.expandProfession(profession));
      }
    });

    // 5. 关键词扩展
    Object.keys(this.mappings.职业).forEach(key => {
      if (lowerQuery.includes(key.toLowerCase())) {
        conditions.profession.push(...this.mappings.职业[key]);
      }
    });

    Object.keys(this.mappings.学历).forEach(key => {
      this.mappings.学历[key].forEach(keyword => {
        if (lowerQuery.includes(keyword.toLowerCase())) {
          conditions.education.push(keyword);
        }
      });
    });

    Object.keys(this.mappings.性格).forEach(key => {
      this.mappings.性格[key].forEach(keyword => {
        if (lowerQuery.includes(keyword.toLowerCase())) {
          conditions.personality.push(keyword);
        }
      });
    });

    // 6. 年龄特征解析
    Object.keys(this.mappings.年龄).forEach(key => {
      const ageGroup = this.mappings.年龄[key];
      ageGroup.keywords.forEach(keyword => {
        if (lowerQuery.includes(keyword.toLowerCase())) {
          conditions.age = { min: ageGroup.min, max: ageGroup.max };
        }
      });
    });

    // 7. 通用关键词提取
    const words = query.split(/[，,。.！!？?\s]+/).filter(word => word.length > 0);
    conditions.keywords = [...new Set([...conditions.keywords, ...words])];

    // 8. 确保至少有查询关键词（兜底逻辑）
    if (conditions.keywords.length === 0 && query.trim()) {
      conditions.keywords.push(query.trim());
    }

    return conditions;
  }

  /**
   * 扩展职业关键词
   */
  expandProfession(profession) {
    const expanded = new Set([profession]);
    
    Object.keys(this.mappings.职业).forEach(key => {
      if (profession.includes(key) || key.includes(profession)) {
        this.mappings.职业[key].forEach(keyword => expanded.add(keyword));
      }
    });

    return Array.from(expanded);
  }

  /**
   * 扩展地域关键词
   */
  expandLocation(location) {
    const expanded = new Set([location]);
    
    Object.keys(this.mappings.地域).forEach(key => {
      if (location.includes(key) || key.includes(location)) {
        this.mappings.地域[key].forEach(keyword => expanded.add(keyword));
      }
    });

    return Array.from(expanded);
  }

  /**
   * 解析中文数字年龄
   */
  parseAge(ageStr) {
    const chineseNumbers = {
      '十': 10, '二十': 20, '三十': 30, '四十': 40, '五十': 50, '六十': 60,
      '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9
    };

    if (/^\d+$/.test(ageStr)) {
      return parseInt(ageStr);
    }

    // 解析中文数字
    let age = 0;
    if (ageStr.includes('十')) {
      const parts = ageStr.split('十');
      if (parts[0]) age += (chineseNumbers[parts[0]] || 0) * 10;
      else age += 10;
      if (parts[1]) age += chineseNumbers[parts[1]] || 0;
    } else {
      age = chineseNumbers[ageStr] || 0;
    }

    return age;
  }

  /**
   * 计算联系人与搜索条件的匹配度
   * @param {Object} contact - 联系人信息
   * @param {Object} conditions - 解析后的搜索条件
   * @returns {number} 匹配度分数 (0-1)
   */
  calculateMatchScore(contact, conditions) {
    let score = 0;
    let totalWeight = 0;

    // 1. 直接文本匹配（最重要）- 对原始查询进行全字段匹配
    const originalQuery = conditions.original.toLowerCase();
    let directMatch = 0;
    
    // 姓名直接匹配（权重最高）
    if (contact.profile_name && contact.profile_name.toLowerCase().includes(originalQuery)) {
      directMatch = Math.max(directMatch, 1.0);
    }
    
    // 公司匹配
    if (contact.company && contact.company.toLowerCase().includes(originalQuery)) {
      directMatch = Math.max(directMatch, 0.8);
    }
    
    // 职位匹配
    if (contact.position && contact.position.toLowerCase().includes(originalQuery)) {
      directMatch = Math.max(directMatch, 0.7);
    }
    
    // 地域匹配
    if (contact.location && contact.location.toLowerCase().includes(originalQuery)) {
      directMatch = Math.max(directMatch, 0.6);
    }
    
    // 其他字段匹配
    const otherFields = [contact.education, contact.personality, contact.ai_summary];
    otherFields.forEach(field => {
      if (field && field.toLowerCase().includes(originalQuery)) {
        directMatch = Math.max(directMatch, 0.4);
      }
    });

    // 如果有直接匹配，给它很高的权重
    if (directMatch > 0) {
      score += directMatch * 10; // 直接匹配权重10
      totalWeight += 10;
    }

    // 2. 关键词匹配（权重1.0）
    if (conditions.keywords.length > 0) {
      totalWeight += 1.0;
      const nameMatch = this.matchKeywords(contact.profile_name || '', conditions.keywords);
      score += nameMatch * 1.0;
    }

    // 3. 年龄匹配（权重0.8）
    if (conditions.age) {
      totalWeight += 0.8;
      const ageMatch = this.matchAge(contact.age, conditions.age);
      score += ageMatch * 0.8;
    }

    // 4. 性别匹配（权重0.6）
    if (conditions.gender) {
      totalWeight += 0.6;
      if (contact.gender === conditions.gender) {
        score += 0.6;
      }
    }

    // 5. 地域匹配（权重0.7）
    if (conditions.location.length > 0) {
      totalWeight += 0.7;
      const locationMatch = this.matchKeywords(contact.location || '', conditions.location);
      score += locationMatch * 0.7;
    }

    // 6. 职业匹配（权重0.9）
    if (conditions.profession.length > 0) {
      totalWeight += 0.9;
      const professionMatch = Math.max(
        this.matchKeywords(contact.company || '', conditions.profession),
        this.matchKeywords(contact.position || '', conditions.profession)
      );
      score += professionMatch * 0.9;
    }

    // 7. 学历匹配（权重0.5）
    if (conditions.education.length > 0) {
      totalWeight += 0.5;
      const educationMatch = this.matchKeywords(contact.education || '', conditions.education);
      score += educationMatch * 0.5;
    }

    // 8. 性格匹配（权重0.4）
    if (conditions.personality.length > 0) {
      totalWeight += 0.4;
      const personalityMatch = this.matchKeywords(contact.personality || '', conditions.personality);
      score += personalityMatch * 0.4;
    }

    // 如果没有任何匹配条件，返回0
    if (totalWeight === 0) return 0;

    // 返回标准化分数
    return Math.min(score / totalWeight, 1.0);
  }

  /**
   * 关键词匹配
   */
  matchKeywords(text, keywords) {
    if (!text || keywords.length === 0) return 0;
    
    const lowerText = text.toLowerCase();
    let matches = 0;
    
    keywords.forEach(keyword => {
      if (lowerText.includes(keyword.toLowerCase())) {
        matches++;
      }
    });
    
    return matches / keywords.length;
  }

  /**
   * 年龄匹配
   */
  matchAge(contactAge, ageCondition) {
    if (!contactAge || !ageCondition) return 0;
    
    const age = parseInt(contactAge);
    if (isNaN(age)) return 0;
    
    if (ageCondition.exact !== undefined) {
      // 精确年龄匹配，允许±2岁误差
      const diff = Math.abs(age - ageCondition.exact);
      return Math.max(0, 1 - diff / 5);
    }
    
    if (ageCondition.min !== undefined && ageCondition.max !== undefined) {
      // 年龄范围匹配
      if (age >= ageCondition.min && age <= ageCondition.max) {
        return 1.0;
      } else {
        // 超出范围的惩罚
        const distance = Math.min(
          Math.abs(age - ageCondition.min),
          Math.abs(age - ageCondition.max)
        );
        return Math.max(0, 1 - distance / 10);
      }
    }
    
    return 0;
  }

  /**
   * 生成搜索分析
   */
  generateAnalysis(results, conditions) {
    const totalResults = results.length;
    const highMatchResults = results.filter(r => r.matchScore > 0.7).length;
    
    if (totalResults === 0) {
      return `没有找到与"${conditions.original}"匹配的联系人。建议尝试更通用的关键词。`;
    }

    let analysis = `找到 ${totalResults} 个相关联系人`;
    
    if (highMatchResults > 0) {
      analysis += `，其中 ${highMatchResults} 个高度匹配`;
    }

    // 分析匹配特征
    const features = [];
    if (conditions.age) features.push('年龄');
    if (conditions.gender) features.push('性别');
    if (conditions.location.length > 0) features.push('地域');
    if (conditions.profession.length > 0) features.push('职业');
    
    if (features.length > 0) {
      analysis += `。匹配维度：${features.join('、')}`;
    }

    // 地域分布
    const locations = [...new Set(results.map(r => r.location).filter(Boolean))];
    if (locations.length > 0) {
      analysis += `。主要分布：${locations.slice(0, 3).join('、')}`;
    }

    // 职业分布
    const companies = [...new Set(results.map(r => r.company).filter(Boolean))];
    if (companies.length > 0) {
      analysis += `。主要来自：${companies.slice(0, 3).join('、')}`;
    }

    return analysis + '。';
  }

  /**
   * 执行智能搜索
   * @param {Array} contacts - 联系人列表
   * @param {string} query - 搜索查询
   * @returns {Object} 搜索结果
   */
  search(contacts, query) {
    // 1. 解析查询
    const conditions = this.parseQuery(query);
    
    // 调试输出
    console.log('搜索调试信息:', {
      query: query,
      conditions: conditions,
      contactsCount: contacts.length
    });
    
    // 2. 计算匹配度
    const results = contacts.map(contact => {
      const matchScore = this.calculateMatchScore(contact, conditions);
      return {
        ...contact,
        matchScore,
        searchConditions: conditions
      };
    }).filter(contact => contact.matchScore > 0.01); // 降低过滤阈值，保留更多可能的匹配

    // 调试输出前5个匹配结果
    console.log('匹配结果调试:', results.slice(0, 5).map(r => ({
      name: r.profile_name,
      score: r.matchScore,
      company: r.company,
      position: r.position
    })));

    // 按匹配度排序
    results.sort((a, b) => b.matchScore - a.matchScore);

    // 3. 生成分析
    const analysis = this.generateAnalysis(results, conditions);

    return {
      results,
      analysis,
      conditions,
      total: results.length
    };
  }
}

// 导出单例
const semanticSearchEngine = new SemanticSearchEngine();

export default semanticSearchEngine;