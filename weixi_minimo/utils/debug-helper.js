/**
 * 调试辅助工具
 * 用于快速诊断和测试各种功能
 */

class DebugHelper {
  constructor() {
    this.testResults = [];
  }

  /**
   * 测试通讯录权限
   */
  async testContactPermission() {
    console.log('🧪 [Debug] 测试通讯录权限');
    
    return new Promise((resolve) => {
      wx.getSetting({
        success: (res) => {
          console.log('🔍 [Debug] 当前权限设置:', res.authSetting);
          
          const contactPermission = res.authSetting['scope.addPhoneContact'];
          
          if (contactPermission === undefined) {
            console.log('📋 [Debug] 通讯录权限未请求过');
            resolve({ status: 'not_requested', message: '通讯录权限未请求过' });
          } else if (contactPermission === true) {
            console.log('✅ [Debug] 通讯录权限已授权');
            resolve({ status: 'granted', message: '通讯录权限已授权' });
          } else {
            console.log('❌ [Debug] 通讯录权限被拒绝');
            resolve({ status: 'denied', message: '通讯录权限被拒绝' });
          }
        },
        fail: (error) => {
          console.error('❌ [Debug] 获取权限设置失败:', error);
          resolve({ status: 'error', message: '获取权限设置失败', error });
        }
      });
    });
  }

  /**
   * 测试wx.chooseContact API
   */
  async testChooseContactAPI() {
    console.log('🧪 [Debug] 测试 wx.chooseContact API');
    
    return new Promise((resolve) => {
      wx.chooseContact({
        success: (res) => {
          console.log('✅ [Debug] wx.chooseContact 成功:', res);
          resolve({ 
            status: 'success', 
            message: '选择联系人成功',
            contact: {
              name: res.displayName,
              phone: res.phoneNumber
            }
          });
        },
        fail: (error) => {
          console.error('❌ [Debug] wx.chooseContact 失败:', error);
          resolve({ 
            status: 'failed', 
            message: `选择联系人失败: ${error.errMsg}`,
            error 
          });
        }
      });
    });
  }

  /**
   * 测试contactImporter模块
   */
  async testContactImporter() {
    console.log('🧪 [Debug] 测试 contactImporter 模块');
    
    try {
      const contactImporter = await import('./contact-importer');
      const importer = contactImporter.default;
      
      console.log('🔍 [Debug] contactImporter 检查:', {
        exists: !!importer,
        isCurrentlyImporting: typeof importer?.isCurrentlyImporting,
        importFromPhoneBook: typeof importer?.importFromPhoneBook,
        quickBatchImportFromPhoneBook: typeof importer?.quickBatchImportFromPhoneBook,
        selectContactFromPhoneBook: typeof importer?.selectContactFromPhoneBook
      });
      
      return {
        status: 'success',
        message: 'contactImporter 模块导入成功',
        methods: {
          isCurrentlyImporting: typeof importer?.isCurrentlyImporting,
          importFromPhoneBook: typeof importer?.importFromPhoneBook,
          quickBatchImportFromPhoneBook: typeof importer?.quickBatchImportFromPhoneBook,
          selectContactFromPhoneBook: typeof importer?.selectContactFromPhoneBook
        }
      };
    } catch (error) {
      console.error('❌ [Debug] contactImporter 模块导入失败:', error);
      return {
        status: 'failed',
        message: `contactImporter 模块导入失败: ${error.message}`,
        error
      };
    }
  }

  /**
   * 测试dataManager模块
   */
  async testDataManager() {
    console.log('🧪 [Debug] 测试 dataManager 模块');
    
    try {
      const dataManager = await import('./data-manager');
      const manager = dataManager.default;
      
      console.log('🔍 [Debug] dataManager 检查:', {
        exists: !!manager,
        createProfile: typeof manager?.createProfile,
        getContacts: typeof manager?.getContacts
      });
      
      return {
        status: 'success',
        message: 'dataManager 模块导入成功',
        methods: {
          createProfile: typeof manager?.createProfile,
          getContacts: typeof manager?.getContacts
        }
      };
    } catch (error) {
      console.error('❌ [Debug] dataManager 模块导入失败:', error);
      return {
        status: 'failed',
        message: `dataManager 模块导入失败: ${error.message}`,
        error
      };
    }
  }

  /**
   * 测试API连接
   */
  async testAPIConnection() {
    console.log('🧪 [Debug] 测试 API 连接');
    
    try {
      const apiClient = await import('./api-client');
      const client = apiClient.default;
      
      // 尝试获取统计信息作为连接测试
      const result = await client.getStats();
      
      console.log('✅ [Debug] API 连接成功:', result);
      
      return {
        status: 'success',
        message: 'API 连接正常',
        data: result
      };
    } catch (error) {
      console.error('❌ [Debug] API 连接失败:', error);
      return {
        status: 'failed',
        message: `API 连接失败: ${error.message}`,
        error
      };
    }
  }

  /**
   * 运行完整诊断
   */
  async runFullDiagnosis() {
    console.log('🏥 [Debug] 开始完整诊断');
    
    const results = {
      timestamp: new Date().toISOString(),
      tests: {}
    };
    
    // 测试权限
    results.tests.permission = await this.testContactPermission();
    
    // 测试模块导入
    results.tests.contactImporter = await this.testContactImporter();
    results.tests.dataManager = await this.testDataManager();
    
    // 测试API连接
    results.tests.apiConnection = await this.testAPIConnection();
    
    // 汇总结果
    const failedTests = Object.keys(results.tests).filter(
      key => results.tests[key].status === 'failed' || results.tests[key].status === 'error'
    );
    
    results.summary = {
      total: Object.keys(results.tests).length,
      passed: Object.keys(results.tests).length - failedTests.length,
      failed: failedTests.length,
      failedTests
    };
    
    console.log('📊 [Debug] 诊断完成:', results);
    
    return results;
  }

  /**
   * 显示诊断结果
   */
  showDiagnosisResults(results) {
    const { summary, tests } = results;
    
    let content = `诊断结果汇总：\n\n`;
    content += `✅ 通过: ${summary.passed}/${summary.total}\n`;
    content += `❌ 失败: ${summary.failed}/${summary.total}\n\n`;
    
    // 显示详细结果
    content += `详细结果：\n`;
    Object.keys(tests).forEach(testName => {
      const test = tests[testName];
      const icon = test.status === 'success' ? '✅' : '❌';
      content += `${icon} ${testName}: ${test.message}\n`;
    });
    
    // 给出建议
    if (summary.failed > 0) {
      content += `\n🔧 建议：\n`;
      
      if (tests.permission?.status === 'denied') {
        content += `• 在微信设置中允许通讯录权限\n`;
      }
      
      if (tests.permission?.status === 'not_requested') {
        content += `• 需要先请求通讯录权限\n`;
      }
      
      if (tests.contactImporter?.status === 'failed') {
        content += `• 检查 contactImporter 模块导入\n`;
      }
      
      if (tests.apiConnection?.status === 'failed') {
        content += `• 检查网络连接和API服务\n`;
      }
    } else {
      content += `\n🎉 所有测试都通过了！`;
    }
    
    wx.showModal({
      title: '🏥 系统诊断报告',
      content: content,
      showCancel: false,
      confirmText: '知道了'
    });
  }

  /**
   * 请求通讯录权限
   */
  async requestContactPermission() {
    console.log('🔐 [Debug] 请求通讯录权限');
    
    return new Promise((resolve) => {
      wx.authorize({
        scope: 'scope.addPhoneContact',
        success: () => {
          console.log('✅ [Debug] 通讯录权限授权成功');
          resolve({ status: 'success', message: '权限授权成功' });
        },
        fail: (error) => {
          console.error('❌ [Debug] 通讯录权限授权失败:', error);
          
          // 引导用户到设置页面
          wx.showModal({
            title: '权限申请',
            content: '需要通讯录权限才能导入联系人，请在设置中手动开启',
            confirmText: '去设置',
            cancelText: '取消',
            success: (res) => {
              if (res.confirm) {
                wx.openSetting({
                  success: (settingRes) => {
                    console.log('🔍 [Debug] 用户设置结果:', settingRes.authSetting);
                    resolve({ 
                      status: 'redirected', 
                      message: '已跳转到设置页面',
                      authSetting: settingRes.authSetting
                    });
                  }
                });
              } else {
                resolve({ status: 'cancelled', message: '用户取消授权' });
              }
            }
          });
        }
      });
    });
  }
}

// 创建单例实例
const debugHelper = new DebugHelper();

export default debugHelper;