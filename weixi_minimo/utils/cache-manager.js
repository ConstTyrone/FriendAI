/**
 * 缓存管理器 - 支持分级缓存和智能预加载
 */

import { UI_CONFIG } from './constants';

class CacheManager {
  constructor() {
    this.cache = new Map();
    this.cacheTimestamps = new Map();
    this.preloadQueue = [];
    this.isPreloading = false;
  }

  /**
   * 设置缓存数据
   * @param {string} key - 缓存键
   * @param {any} data - 缓存数据
   * @param {string} level - 缓存级别
   */
  set(key, data, level = 'default') {
    const expireTime = this.getExpireTime(level);
    
    try {
      // 内存缓存
      this.cache.set(key, data);
      this.cacheTimestamps.set(key, {
        timestamp: Date.now(),
        expireTime: expireTime,
        level: level
      });
      
      // 持久化缓存（异步，不阻塞）
      wx.setStorage({
        key: `cache_${key}`,
        data: {
          data: data,
          timestamp: Date.now(),
          expireTime: expireTime,
          level: level
        }
      });
      
      console.log(`缓存设置成功: ${key}, 级别: ${level}, 过期时间: ${expireTime / 1000}秒`);
    } catch (error) {
      console.error('设置缓存失败:', error);
    }
  }

  /**
   * 获取缓存数据
   * @param {string} key - 缓存键
   * @param {any} defaultValue - 默认值
   * @returns {any} 缓存数据或默认值
   */
  get(key, defaultValue = null) {
    // 先检查内存缓存
    if (this.cache.has(key)) {
      const timestamp = this.cacheTimestamps.get(key);
      if (timestamp && !this.isExpired(timestamp)) {
        console.log(`内存缓存命中: ${key}`);
        return this.cache.get(key);
      }
    }
    
    // 检查持久化缓存
    try {
      const storageData = wx.getStorageSync(`cache_${key}`);
      if (storageData && storageData.data) {
        if (!this.isExpired(storageData)) {
          console.log(`存储缓存命中: ${key}`);
          // 恢复到内存缓存
          this.cache.set(key, storageData.data);
          this.cacheTimestamps.set(key, {
            timestamp: storageData.timestamp,
            expireTime: storageData.expireTime,
            level: storageData.level
          });
          return storageData.data;
        }
      }
    } catch (error) {
      console.error('读取缓存失败:', error);
    }
    
    console.log(`缓存未命中: ${key}`);
    return defaultValue;
  }

  /**
   * 检查缓存是否过期
   * @param {object} cacheInfo - 缓存信息
   * @returns {boolean} 是否过期
   */
  isExpired(cacheInfo) {
    const now = Date.now();
    const age = now - cacheInfo.timestamp;
    return age > cacheInfo.expireTime;
  }

  /**
   * 获取缓存过期时间
   * @param {string} level - 缓存级别
   * @returns {number} 过期时间（毫秒）
   */
  getExpireTime(level) {
    if (UI_CONFIG.CACHE_LEVELS && UI_CONFIG.CACHE_LEVELS[level]) {
      return UI_CONFIG.CACHE_LEVELS[level];
    }
    
    // 根据缓存类型返回不同的过期时间
    switch (level) {
      case 'CONTACT_LIST':
        return UI_CONFIG.CACHE_LEVELS?.CONTACT_LIST || 5 * 60 * 1000;
      case 'CONTACT_DETAIL':
        return UI_CONFIG.CACHE_LEVELS?.CONTACT_DETAIL || 3 * 60 * 1000;
      case 'SEARCH_RESULT':
        return UI_CONFIG.CACHE_LEVELS?.SEARCH_RESULT || 10 * 60 * 1000;
      case 'STATS':
        return UI_CONFIG.CACHE_LEVELS?.STATS || 60 * 60 * 1000;
      case 'USER_INFO':
        return UI_CONFIG.CACHE_LEVELS?.USER_INFO || 24 * 60 * 60 * 1000;
      case 'RELATIONSHIPS':
        return UI_CONFIG.CACHE_LEVELS?.RELATIONSHIPS || 20 * 60 * 1000;
      case 'RELATIONSHIP_DETAIL':
        return UI_CONFIG.CACHE_LEVELS?.RELATIONSHIP_DETAIL || 15 * 60 * 1000;
      case 'RELATIONSHIP_STATS':
        return UI_CONFIG.CACHE_LEVELS?.RELATIONSHIP_STATS || 10 * 60 * 1000;
      default:
        return UI_CONFIG.CACHE_EXPIRE_TIME || 30 * 60 * 1000;
    }
  }

  /**
   * 清除指定缓存
   * @param {string} key - 缓存键
   */
  clear(key) {
    this.cache.delete(key);
    this.cacheTimestamps.delete(key);
    
    try {
      wx.removeStorageSync(`cache_${key}`);
    } catch (error) {
      console.error('清除缓存失败:', error);
    }
  }

  /**
   * 清除所有缓存
   */
  clearAll() {
    this.cache.clear();
    this.cacheTimestamps.clear();
    
    try {
      // 获取所有缓存键
      const res = wx.getStorageInfoSync();
      res.keys.forEach(key => {
        if (key.startsWith('cache_')) {
          wx.removeStorageSync(key);
        }
      });
    } catch (error) {
      console.error('清除所有缓存失败:', error);
    }
  }

  /**
   * 预加载数据
   * @param {array} items - 预加载项列表
   */
  async preload(items) {
    if (this.isPreloading) {
      console.log('预加载已在进行中');
      return;
    }
    
    this.isPreloading = true;
    this.preloadQueue = [...items];
    
    console.log('开始预加载数据:', items.length, '项');
    
    for (const item of this.preloadQueue) {
      try {
        // 检查是否已有有效缓存
        const cached = this.get(item.key);
        if (cached !== null) {
          console.log(`跳过预加载（已有缓存）: ${item.key}`);
          continue;
        }
        
        // 执行预加载
        if (item.loader && typeof item.loader === 'function') {
          const data = await item.loader();
          this.set(item.key, data, item.level || 'default');
          console.log(`预加载完成: ${item.key}`);
        }
      } catch (error) {
        console.error(`预加载失败: ${item.key}`, error);
      }
    }
    
    this.isPreloading = false;
    this.preloadQueue = [];
    console.log('预加载全部完成');
  }

  /**
   * 获取缓存统计信息
   */
  getStats() {
    const stats = {
      memoryItems: this.cache.size,
      storageItems: 0,
      totalSize: 0,
      expiredItems: 0
    };
    
    try {
      const res = wx.getStorageInfoSync();
      res.keys.forEach(key => {
        if (key.startsWith('cache_')) {
          stats.storageItems++;
          
          const data = wx.getStorageSync(key);
          if (data && this.isExpired(data)) {
            stats.expiredItems++;
          }
        }
      });
      stats.totalSize = res.currentSize;
    } catch (error) {
      console.error('获取缓存统计失败:', error);
    }
    
    return stats;
  }

  /**
   * 关系数据缓存管理方法
   */

  /**
   * 生成关系数据缓存键
   * @param {string} contactId - 联系人ID
   * @returns {string} 缓存键
   */
  getRelationshipsCacheKey(contactId) {
    return `relationships_${contactId}`;
  }

  /**
   * 生成关系详情缓存键
   * @param {string} relationshipId - 关系ID
   * @returns {string} 缓存键
   */
  getRelationshipDetailCacheKey(relationshipId) {
    return `relationship_detail_${relationshipId}`;
  }

  /**
   * 生成关系统计缓存键
   * @param {string} contactId - 联系人ID
   * @returns {string} 缓存键
   */
  getRelationshipStatsCacheKey(contactId) {
    return `relationship_stats_${contactId}`;
  }

  /**
   * 设置关系数据缓存
   * @param {string} contactId - 联系人ID
   * @param {Object} relationshipsData - 关系数据
   */
  setRelationships(contactId, relationshipsData) {
    const cacheKey = this.getRelationshipsCacheKey(contactId);
    this.set(cacheKey, relationshipsData, 'RELATIONSHIPS');
  }

  /**
   * 获取关系数据缓存
   * @param {string} contactId - 联系人ID
   * @returns {Object|null} 关系数据或null
   */
  getRelationships(contactId) {
    const cacheKey = this.getRelationshipsCacheKey(contactId);
    return this.get(cacheKey, null);
  }

  /**
   * 设置关系详情缓存
   * @param {string} relationshipId - 关系ID
   * @param {Object} detailData - 关系详情数据
   */
  setRelationshipDetail(relationshipId, detailData) {
    const cacheKey = this.getRelationshipDetailCacheKey(relationshipId);
    this.set(cacheKey, detailData, 'RELATIONSHIP_DETAIL');
  }

  /**
   * 获取关系详情缓存
   * @param {string} relationshipId - 关系ID
   * @returns {Object|null} 关系详情数据或null
   */
  getRelationshipDetail(relationshipId) {
    const cacheKey = this.getRelationshipDetailCacheKey(relationshipId);
    return this.get(cacheKey, null);
  }

  /**
   * 清除联系人的所有关系缓存
   * @param {string} contactId - 联系人ID
   */
  clearRelationshipCache(contactId) {
    const relationshipsKey = this.getRelationshipsCacheKey(contactId);
    const statsKey = this.getRelationshipStatsCacheKey(contactId);
    
    this.clear(relationshipsKey);
    this.clear(statsKey);
    
    console.log(`已清除联系人 ${contactId} 的关系缓存`);
  }

  /**
   * 清除特定关系的详情缓存
   * @param {string} relationshipId - 关系ID
   */
  clearRelationshipDetailCache(relationshipId) {
    const detailKey = this.getRelationshipDetailCacheKey(relationshipId);
    this.clear(detailKey);
    
    console.log(`已清除关系 ${relationshipId} 的详情缓存`);
  }

  /**
   * 批量清除关系缓存
   * @param {Array} relationshipIds - 关系ID数组
   */
  batchClearRelationshipCache(relationshipIds) {
    relationshipIds.forEach(id => {
      this.clearRelationshipDetailCache(id);
    });
    
    console.log(`批量清除了 ${relationshipIds.length} 个关系的缓存`);
  }

  /**
   * 清理过期缓存
   */
  cleanExpired() {
    let cleanedCount = 0;
    
    // 清理内存缓存
    this.cacheTimestamps.forEach((info, key) => {
      if (this.isExpired(info)) {
        this.cache.delete(key);
        this.cacheTimestamps.delete(key);
        cleanedCount++;
      }
    });
    
    // 清理存储缓存
    try {
      const res = wx.getStorageInfoSync();
      res.keys.forEach(key => {
        if (key.startsWith('cache_')) {
          const data = wx.getStorageSync(key);
          if (data && this.isExpired(data)) {
            wx.removeStorageSync(key);
            cleanedCount++;
          }
        }
      });
    } catch (error) {
      console.error('清理过期缓存失败:', error);
    }
    
    console.log(`清理了 ${cleanedCount} 个过期缓存项`);
    return cleanedCount;
  }
}

// 创建单例
const cacheManager = new CacheManager();

// 延迟启动清理定时器，并绑定到应用生命周期
let cleanupTimer = null;

cacheManager.startAutoCleanup = function() {
  if (cleanupTimer) return;
  
  // 定期清理过期缓存（每10分钟）
  cleanupTimer = setInterval(() => {
    this.cleanExpired();
  }, 10 * 60 * 1000);
  
  console.log('缓存自动清理已启动');
};

cacheManager.stopAutoCleanup = function() {
  if (cleanupTimer) {
    clearInterval(cleanupTimer);
    cleanupTimer = null;
    console.log('缓存自动清理已停止');
  }
};

export default cacheManager;