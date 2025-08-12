import { UI_CONFIG } from './constants';

/**
 * 同步获取存储数据
 */
export function getStorageSync(key, defaultValue = null) {
  try {
    const value = wx.getStorageSync(key);
    if (value === '') return defaultValue;
    
    // 检查是否是带过期时间的数据
    if (typeof value === 'object' && value.expireTime) {
      if (Date.now() > value.expireTime) {
        wx.removeStorageSync(key);
        return defaultValue;
      }
      return value.data;
    }
    
    return value || defaultValue;
  } catch (error) {
    console.error('获取存储数据失败:', key, error);
    return defaultValue;
  }
}

/**
 * 同步设置存储数据
 */
export function setStorageSync(key, value, expireTime = null) {
  try {
    let dataToStore = value;
    
    // 如果设置了过期时间，包装数据
    if (expireTime) {
      dataToStore = {
        data: value,
        expireTime: Date.now() + expireTime
      };
    }
    
    wx.setStorageSync(key, dataToStore);
    return true;
  } catch (error) {
    console.error('设置存储数据失败:', key, error);
    return false;
  }
}

/**
 * 同步删除存储数据
 */
export function removeStorageSync(key) {
  try {
    wx.removeStorageSync(key);
    return true;
  } catch (error) {
    console.error('删除存储数据失败:', key, error);
    return false;
  }
}

/**
 * 异步获取存储数据
 */
export function getStorage(key, defaultValue = null) {
  return new Promise((resolve) => {
    wx.getStorage({
      key,
      success: (res) => {
        const value = res.data;
        
        // 检查是否是带过期时间的数据
        if (typeof value === 'object' && value.expireTime) {
          if (Date.now() > value.expireTime) {
            wx.removeStorage({ key });
            resolve(defaultValue);
            return;
          }
          resolve(value.data);
          return;
        }
        
        resolve(value || defaultValue);
      },
      fail: () => {
        resolve(defaultValue);
      }
    });
  });
}

/**
 * 异步设置存储数据
 */
export function setStorage(key, value, expireTime = null) {
  return new Promise((resolve) => {
    let dataToStore = value;
    
    // 如果设置了过期时间，包装数据
    if (expireTime) {
      dataToStore = {
        data: value,
        expireTime: Date.now() + expireTime
      };
    }
    
    wx.setStorage({
      key,
      data: dataToStore,
      success: () => resolve(true),
      fail: () => resolve(false)
    });
  });
}

/**
 * 异步删除存储数据
 */
export function removeStorage(key) {
  return new Promise((resolve) => {
    wx.removeStorage({
      key,
      success: () => resolve(true),
      fail: () => resolve(false)
    });
  });
}

/**
 * 清除所有存储数据
 */
export function clearStorage() {
  return new Promise((resolve) => {
    wx.clearStorage({
      success: () => resolve(true),
      fail: () => resolve(false)
    });
  });
}

/**
 * 获取存储信息
 */
export function getStorageInfo() {
  return new Promise((resolve) => {
    wx.getStorageInfo({
      success: resolve,
      fail: () => resolve({
        keys: [],
        currentSize: 0,
        limitSize: 0
      })
    });
  });
}

/**
 * 缓存数据（带默认过期时间）
 */
export function cacheData(key, data) {
  return setStorageSync(key, data, UI_CONFIG.CACHE_EXPIRE_TIME);
}

/**
 * 获取缓存数据
 */
export function getCachedData(key, defaultValue = null) {
  return getStorageSync(key, defaultValue);
}

/**
 * 批量设置存储
 */
export function setBatchStorage(dataMap) {
  const promises = Object.entries(dataMap).map(([key, value]) => {
    return setStorage(key, value);
  });
  return Promise.all(promises);
}

/**
 * 批量获取存储
 */
export function getBatchStorage(keys, defaultValue = null) {
  const promises = keys.map(key => getStorage(key, defaultValue));
  return Promise.all(promises);
}

/**
 * 存储管理器类
 */
export class StorageManager {
  constructor(prefix = '') {
    this.prefix = prefix;
  }
  
  getKey(key) {
    return this.prefix ? `${this.prefix}_${key}` : key;
  }
  
  get(key, defaultValue = null) {
    return getStorageSync(this.getKey(key), defaultValue);
  }
  
  set(key, value, expireTime = null) {
    return setStorageSync(this.getKey(key), value, expireTime);
  }
  
  remove(key) {
    return removeStorageSync(this.getKey(key));
  }
  
  cache(key, data) {
    return this.set(key, data, UI_CONFIG.CACHE_EXPIRE_TIME);
  }
  
  async getAsync(key, defaultValue = null) {
    return await getStorage(this.getKey(key), defaultValue);
  }
  
  async setAsync(key, value, expireTime = null) {
    return await setStorage(this.getKey(key), value, expireTime);
  }
  
  async removeAsync(key) {
    return await removeStorage(this.getKey(key));
  }
}

// 创建默认存储管理器实例
export const defaultStorage = new StorageManager('social_app');