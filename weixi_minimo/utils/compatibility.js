/**
 * 兼容性检查工具
 * 检查微信小程序API的可用性
 */

class CompatibilityChecker {
  constructor() {
    this.apiSupport = {};
    this.checkAPIs();
  }

  /**
   * 检查API支持情况
   */
  checkAPIs() {
    // 检查振动API
    this.apiSupport.vibrate = this.checkAPI('vibrateShort');
    
    // 检查音频API
    this.apiSupport.audio = this.checkAPI('createInnerAudioContext');
    
    // 检查垃圾回收API
    this.apiSupport.gc = this.checkAPI('triggerGC');
    
    // 检查存储API
    this.apiSupport.storage = this.checkAPI('getStorageSync');
    
    // 检查网络API
    this.apiSupport.request = this.checkAPI('request');
    
    // 检查TabBar API
    this.apiSupport.tabBar = this.checkAPI('setTabBarBadge');
    
    console.log('API兼容性检查结果:', this.apiSupport);
  }

  /**
   * 检查单个API是否可用
   */
  checkAPI(apiName) {
    try {
      return typeof wx !== 'undefined' && typeof wx[apiName] === 'function';
    } catch (error) {
      return false;
    }
  }

  /**
   * 安全调用振动
   */
  safeVibrate(options = {}) {
    if (this.apiSupport.vibrate) {
      try {
        wx.vibrateShort({
          type: options.type || 'medium',
          success: () => {
            console.log('振动成功');
          },
          fail: (error) => {
            console.log('振动失败:', error);
          }
        });
      } catch (error) {
        console.log('振动API调用失败:', error);
      }
    } else {
      console.log('振动API不可用');
    }
  }

  /**
   * 安全播放音频
   */
  safePlayAudio(src, options = {}) {
    if (this.apiSupport.audio) {
      try {
        const innerAudioContext = wx.createInnerAudioContext();
        innerAudioContext.src = src;
        innerAudioContext.volume = options.volume || 0.8;
        
        innerAudioContext.onError((res) => {
          console.log('音频播放失败:', res);
          if (options.onError) {
            options.onError(res);
          }
        });
        
        innerAudioContext.onEnded(() => {
          if (options.onEnded) {
            options.onEnded();
          }
        });
        
        innerAudioContext.play();
        return innerAudioContext;
      } catch (error) {
        console.log('音频API调用失败:', error);
        return null;
      }
    } else {
      console.log('音频API不可用');
      return null;
    }
  }

  /**
   * 安全触发垃圾回收
   */
  safeTriggerGC() {
    if (this.apiSupport.gc) {
      try {
        wx.triggerGC();
        console.log('垃圾回收触发成功');
        return true;
      } catch (error) {
        console.log('垃圾回收触发失败:', error);
        return false;
      }
    } else {
      console.log('垃圾回收API不可用');
      return false;
    }
  }

  /**
   * 安全设置TabBar Badge
   */
  safeSetTabBarBadge(index, text) {
    if (this.apiSupport.tabBar) {
      try {
        if (text && text !== '0') {
          wx.setTabBarBadge({
            index: index,
            text: text.toString(),
            fail: (error) => {
              console.log('设置TabBar Badge失败:', error);
            }
          });
        } else {
          wx.removeTabBarBadge({
            index: index,
            fail: (error) => {
              console.log('移除TabBar Badge失败:', error);
            }
          });
        }
        return true;
      } catch (error) {
        console.log('TabBar Badge API调用失败:', error);
        return false;
      }
    } else {
      console.log('TabBar Badge API不可用');
      return false;
    }
  }

  /**
   * 获取API支持情况
   */
  getAPISupport() {
    return this.apiSupport;
  }

  /**
   * 检查是否支持某个API
   */
  isSupported(apiName) {
    return this.apiSupport[apiName] || false;
  }
}

// 创建单例
const compatibility = new CompatibilityChecker();

export default compatibility;