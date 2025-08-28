// UI工具函数
// 提供统一的UI交互方法

/**
 * 显示提示消息
 * @param {string} title - 提示标题
 * @param {string} icon - 图标类型 (success, error, loading, none)
 * @param {number} duration - 显示时长（毫秒）
 * @param {boolean} mask - 是否显示透明蒙层，防止触摸穿透
 */
export function showToast(title, icon = 'none', duration = 2000, mask = false) {
  wx.showToast({
    title: title,
    icon: icon,
    duration: duration,
    mask: mask
  });
}

/**
 * 显示成功提示
 * @param {string} title - 提示内容
 * @param {number} duration - 显示时长
 */
export function showSuccessToast(title, duration = 2000) {
  showToast(title, 'success', duration);
}

/**
 * 显示错误提示
 * @param {string} title - 提示内容
 * @param {number} duration - 显示时长
 */
export function showErrorToast(title, duration = 3000) {
  showToast(title, 'error', duration);
}

/**
 * 显示加载提示
 * @param {string} title - 提示内容
 * @param {boolean} mask - 是否显示蒙层
 */
export function showLoading(title = '加载中...', mask = true) {
  wx.showLoading({
    title: title,
    mask: mask
  });
}

/**
 * 隐藏加载提示
 */
export function hideLoading() {
  wx.hideLoading();
}

/**
 * 显示确认对话框
 * @param {string} title - 对话框标题
 * @param {string} content - 对话框内容
 * @param {string} confirmText - 确认按钮文字
 * @param {string} cancelText - 取消按钮文字
 * @param {boolean} confirmColor - 确认按钮颜色
 * @returns {Promise<boolean>} 用户是否点击了确认
 */
export function showConfirm(
  title = '提示',
  content = '',
  confirmText = '确定',
  cancelText = '取消',
  confirmColor = '#0052d9'
) {
  return new Promise((resolve) => {
    wx.showModal({
      title: title,
      content: content,
      confirmText: confirmText,
      cancelText: cancelText,
      confirmColor: confirmColor,
      success: (res) => {
        resolve(res.confirm);
      },
      fail: () => {
        resolve(false);
      }
    });
  });
}

/**
 * 显示操作菜单
 * @param {Array} itemList - 按钮文字数组
 * @param {string} alertText - 接口调用失败的回调函数
 * @returns {Promise<number|null>} 用户点击的按钮序号（从0开始），取消则返回null
 */
export function showActionSheet(itemList, alertText = null) {
  return new Promise((resolve) => {
    wx.showActionSheet({
      itemList: itemList,
      alertText: alertText,
      success: (res) => {
        resolve(res.tapIndex);
      },
      fail: () => {
        resolve(null);
      }
    });
  });
}

/**
 * 显示顶部导航栏加载动画
 */
export function showNavigationBarLoading() {
  wx.showNavigationBarLoading();
}

/**
 * 隐藏顶部导航栏加载动画
 */
export function hideNavigationBarLoading() {
  wx.hideNavigationBarLoading();
}

/**
 * 设置顶部导航栏标题
 * @param {string} title - 页面标题
 */
export function setNavigationBarTitle(title) {
  wx.setNavigationBarTitle({
    title: title
  });
}

/**
 * 设置顶部导航栏颜色
 * @param {string} frontColor - 前景颜色值，包括按钮、标题、状态栏的颜色，仅支持 #ffffff 和 #000000
 * @param {string} backgroundColor - 背景颜色值，有效值为十六进制颜色
 * @param {Object} animation - 动画效果
 */
export function setNavigationBarColor(frontColor, backgroundColor, animation = {}) {
  wx.setNavigationBarColor({
    frontColor: frontColor,
    backgroundColor: backgroundColor,
    animation: animation
  });
}

/**
 * 动态设置下拉刷新状态
 * @param {boolean} enabled - 是否启用下拉刷新
 */
export function setEnablePullDownRefresh(enabled) {
  if (enabled) {
    wx.startPullDownRefresh();
  } else {
    wx.stopPullDownRefresh();
  }
}

/**
 * 显示分享菜单
 * @param {boolean} withShareTicket - 是否使用带 shareTicket 的转发
 * @param {Array} menus - 分享方式数组
 */
export function showShareMenu(withShareTicket = false, menus = ['shareAppMessage', 'shareTimeline']) {
  wx.showShareMenu({
    withShareTicket: withShareTicket,
    menus: menus
  });
}

/**
 * 隐藏分享菜单
 */
export function hideShareMenu() {
  wx.hideShareMenu();
}

/**
 * 设置页面分享信息
 * @param {string} title - 分享标题
 * @param {string} path - 分享路径
 * @param {string} imageUrl - 分享图片路径
 * @returns {Object} 分享配置对象
 */
export function getShareInfo(title, path = '', imageUrl = '') {
  return {
    title: title,
    path: path,
    imageUrl: imageUrl
  };
}

/**
 * 复制文本到剪贴板
 * @param {string} data - 需要复制的内容
 * @returns {Promise<boolean>} 是否复制成功
 */
export function copyToClipboard(data) {
  return new Promise((resolve) => {
    wx.setClipboardData({
      data: data,
      success: () => {
        showSuccessToast('已复制到剪贴板');
        resolve(true);
      },
      fail: () => {
        showErrorToast('复制失败');
        resolve(false);
      }
    });
  });
}

/**
 * 获取剪贴板内容
 * @returns {Promise<string|null>} 剪贴板内容，失败返回null
 */
export function getClipboardData() {
  return new Promise((resolve) => {
    wx.getClipboardData({
      success: (res) => {
        resolve(res.data);
      },
      fail: () => {
        resolve(null);
      }
    });
  });
}

/**
 * 震动反馈
 * @param {string} type - 震动强度类型 (heavy, medium, light)
 */
export function vibrateShort(type = 'medium') {
  wx.vibrateShort({
    type: type
  });
}

/**
 * 长时间震动
 */
export function vibrateLong() {
  wx.vibrateLong();
}

/**
 * 保存图片到相册
 * @param {string} filePath - 图片文件路径
 * @returns {Promise<boolean>} 是否保存成功
 */
export function saveImageToPhotosAlbum(filePath) {
  return new Promise((resolve) => {
    wx.saveImageToPhotosAlbum({
      filePath: filePath,
      success: () => {
        showSuccessToast('已保存到相册');
        resolve(true);
      },
      fail: (error) => {
        console.error('保存图片失败:', error);
        if (error.errMsg.includes('auth deny')) {
          showErrorToast('请授权访问相册');
        } else {
          showErrorToast('保存失败');
        }
        resolve(false);
      }
    });
  });
}

/**
 * 预览图片
 * @param {Array} urls - 图片链接数组
 * @param {number} current - 当前显示图片的索引
 */
export function previewImage(urls, current = 0) {
  wx.previewImage({
    urls: urls,
    current: typeof current === 'number' ? urls[current] : current
  });
}

/**
 * 打电话
 * @param {string} phoneNumber - 电话号码
 */
export function makePhoneCall(phoneNumber) {
  if (!phoneNumber || phoneNumber === '未知') {
    showErrorToast('无效的电话号码');
    return;
  }
  
  // 清理电话号码中的特殊字符
  const cleanNumber = phoneNumber.replace(/[^\d\+\-]/g, '');
  
  wx.makePhoneCall({
    phoneNumber: cleanNumber,
    fail: (error) => {
      console.error('拨打电话失败:', error);
      showErrorToast('拨打失败');
    }
  });
}

/**
 * 显示位置
 * @param {number} latitude - 纬度
 * @param {number} longitude - 经度
 * @param {string} name - 位置名
 * @param {string} address - 地址
 */
export function openLocation(latitude, longitude, name = '', address = '') {
  if (!latitude || !longitude) {
    showErrorToast('无效的位置信息');
    return;
  }
  
  wx.openLocation({
    latitude: parseFloat(latitude),
    longitude: parseFloat(longitude),
    name: name,
    address: address,
    fail: (error) => {
      console.error('打开地图失败:', error);
      showErrorToast('打开地图失败');
    }
  });
}

/**
 * 获取位置信息
 * @param {string} type - 定位类型 (wgs84, gcj02)
 * @returns {Promise<Object|null>} 位置信息，失败返回null
 */
export function getLocation(type = 'gcj02') {
  return new Promise((resolve) => {
    wx.getLocation({
      type: type,
      success: (res) => {
        resolve({
          latitude: res.latitude,
          longitude: res.longitude,
          speed: res.speed,
          accuracy: res.accuracy,
          altitude: res.altitude,
          verticalAccuracy: res.verticalAccuracy,
          horizontalAccuracy: res.horizontalAccuracy
        });
      },
      fail: (error) => {
        console.error('获取位置失败:', error);
        if (error.errMsg.includes('auth deny')) {
          showErrorToast('请授权位置信息');
        } else {
          showErrorToast('获取位置失败');
        }
        resolve(null);
      }
    });
  });
}

/**
 * 扫码
 * @param {boolean} onlyFromCamera - 是否只能从相机扫码
 * @param {Array} scanType - 扫码类型 ['barCode', 'qrCode', 'datamatrix', 'pdf417']
 * @returns {Promise<Object|null>} 扫码结果，失败返回null
 */
export function scanCode(onlyFromCamera = true, scanType = ['qrCode', 'barCode']) {
  return new Promise((resolve) => {
    wx.scanCode({
      onlyFromCamera: onlyFromCamera,
      scanType: scanType,
      success: (res) => {
        resolve({
          result: res.result,
          scanType: res.scanType,
          charSet: res.charSet,
          path: res.path
        });
      },
      fail: (error) => {
        console.error('扫码失败:', error);
        resolve(null);
      }
    });
  });
}

// 默认导出常用函数
export default {
  showToast,
  showSuccessToast,
  showErrorToast,
  showLoading,
  hideLoading,
  showConfirm,
  showActionSheet,
  showNavigationBarLoading,
  hideNavigationBarLoading,
  setNavigationBarTitle,
  setNavigationBarColor,
  copyToClipboard,
  getClipboardData,
  vibrateShort,
  vibrateLong,
  saveImageToPhotosAlbum,
  previewImage,
  makePhoneCall,
  openLocation,
  getLocation,
  scanCode
};