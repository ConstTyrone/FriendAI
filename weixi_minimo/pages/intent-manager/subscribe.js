/**
 * 订阅消息管理模块
 * 处理用户订阅意图匹配通知
 */

const TEMPLATE_ID = 'YOUR_TEMPLATE_ID'; // 需要替换为实际的模板ID

/**
 * 请求订阅消息权限
 * @param {Object} options 订阅选项
 * @returns {Promise} 订阅结果
 */
function requestSubscription(options = {}) {
  return new Promise((resolve, reject) => {
    // 检查是否支持订阅消息
    if (!wx.requestSubscribeMessage) {
      wx.showToast({
        title: '当前版本不支持订阅消息',
        icon: 'none'
      });
      reject(new Error('不支持订阅消息'));
      return;
    }

    // 请求订阅权限
    wx.requestSubscribeMessage({
      tmplIds: [TEMPLATE_ID],
      success(res) {
        console.log('订阅结果:', res);
        
        if (res[TEMPLATE_ID] === 'accept') {
          // 用户同意订阅
          console.log('用户同意订阅');
          
          // 保存订阅状态到服务器
          saveSubscriptionToServer({
            template_id: TEMPLATE_ID,
            status: 'accept'
          }).then(() => {
            wx.showToast({
              title: '订阅成功',
              icon: 'success'
            });
            resolve(true);
          }).catch(err => {
            console.error('保存订阅状态失败:', err);
            reject(err);
          });
          
        } else if (res[TEMPLATE_ID] === 'reject') {
          // 用户拒绝订阅
          console.log('用户拒绝订阅');
          wx.showToast({
            title: '您已拒绝接收通知',
            icon: 'none'
          });
          resolve(false);
          
        } else {
          // 其他情况（如ban）
          console.log('订阅状态异常:', res[TEMPLATE_ID]);
          wx.showToast({
            title: '订阅设置异常',
            icon: 'none'
          });
          resolve(false);
        }
      },
      fail(err) {
        console.error('请求订阅失败:', err);
        
        // 处理特殊错误
        if (err.errCode === 20004) {
          wx.showToast({
            title: '请在设置中开启通知权限',
            icon: 'none'
          });
        } else {
          wx.showToast({
            title: '订阅请求失败',
            icon: 'none'
          });
        }
        reject(err);
      }
    });
  });
}

/**
 * 保存订阅状态到服务器
 * @param {Object} subscriptionData 订阅数据
 */
function saveSubscriptionToServer(subscriptionData) {
  return new Promise((resolve, reject) => {
    // 获取用户openid
    const userInfo = wx.getStorageSync('userInfo') || {};
    const token = wx.getStorageSync('token');
    
    if (!userInfo.openid) {
      // 如果没有openid，需要先获取
      wx.login({
        success: (res) => {
          if (res.code) {
            // 调用后端API保存订阅信息
            wx.request({
              url: 'https://weixin.dataelem.com/api/subscription/save',
              method: 'POST',
              header: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              },
              data: {
                code: res.code,
                template_id: subscriptionData.template_id,
                status: subscriptionData.status
              },
              success: (res) => {
                if (res.data.code === 200) {
                  resolve(res.data);
                } else {
                  reject(new Error(res.data.message || '保存失败'));
                }
              },
              fail: reject
            });
          }
        },
        fail: reject
      });
    } else {
      // 直接保存
      wx.request({
        url: 'https://weixin.dataelem.com/api/subscription/save',
        method: 'POST',
        header: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        data: {
          openid: userInfo.openid,
          template_id: subscriptionData.template_id,
          status: subscriptionData.status
        },
        success: (res) => {
          if (res.data.code === 200) {
            resolve(res.data);
          } else {
            reject(new Error(res.data.message || '保存失败'));
          }
        },
        fail: reject
      });
    }
  });
}

/**
 * 检查订阅状态
 * @returns {Promise} 订阅状态
 */
function checkSubscriptionStatus() {
  return new Promise((resolve) => {
    wx.getSetting({
      withSubscriptions: true,
      success(res) {
        console.log('订阅设置:', res);
        
        if (res.subscriptionsSetting) {
          // 总开关
          const mainSwitch = res.subscriptionsSetting.mainSwitch;
          
          // 具体模板的状态
          const itemSettings = res.subscriptionsSetting.itemSettings || {};
          const templateStatus = itemSettings[TEMPLATE_ID];
          
          resolve({
            mainSwitch: mainSwitch,
            templateStatus: templateStatus,
            isSubscribed: templateStatus === 'accept'
          });
        } else {
          resolve({
            mainSwitch: false,
            templateStatus: 'unknown',
            isSubscribed: false
          });
        }
      },
      fail() {
        resolve({
          mainSwitch: false,
          templateStatus: 'unknown',
          isSubscribed: false
        });
      }
    });
  });
}

/**
 * 引导用户开启订阅
 */
function guideToSubscribe() {
  wx.showModal({
    title: '开启匹配通知',
    content: '开启后，当有新的匹配时会及时通知您',
    confirmText: '立即开启',
    success(res) {
      if (res.confirm) {
        requestSubscription().then(result => {
          if (result) {
            console.log('订阅成功');
          }
        }).catch(err => {
          console.error('订阅失败:', err);
        });
      }
    }
  });
}

// 导出模块
module.exports = {
  TEMPLATE_ID,
  requestSubscription,
  checkSubscriptionStatus,
  guideToSubscribe,
  saveSubscriptionToServer
};