import dataManager from './data-manager';

class ContactImporter {
  constructor() {
    this.isImporting = false;
    this.importStats = {
      total: 0,
      success: 0,
      duplicates: 0,
      errors: 0
    };
  }

  /**
   * 从手机通讯录导入联系人
   */
  async importFromPhoneBook() {
    if (this.isImporting) {
      throw new Error('正在导入中，请稍候...');
    }

    try {
      this.isImporting = true;
      this.resetImportStats();

      // 显示导入说明
      const userConfirmed = await this.showImportGuide();
      if (!userConfirmed) {
        return null;
      }

      // 开始选择联系人
      const contact = await this.selectContactFromPhoneBook();
      if (!contact) {
        return null;
      }

      // 检查重复
      const duplicateCheck = await this.checkDuplicate(contact);
      if (duplicateCheck.isDuplicate) {
        const userAction = await this.handleDuplicate(duplicateCheck);
        if (userAction === 'skip') {
          this.importStats.duplicates++;
          return await this.askContinueImport();
        }
      }

      // 让用户确认/编辑联系人信息
      const finalContact = await this.confirmContactInfo(contact);
      if (!finalContact) {
        return null;
      }

      // 创建联系人
      const result = await this.createImportedContact(finalContact);
      if (result) {
        this.importStats.success++;
        // 询问是否继续导入
        return await this.askContinueImport();
      }

    } catch (error) {
      console.error('通讯录导入失败:', error);
      this.importStats.errors++;
      
      wx.showToast({
        title: '导入失败: ' + (error.message || '未知错误'),
        icon: 'none',
        duration: 3000
      });
      
      return null;
    } finally {
      this.isImporting = false;
    }
  }

  /**
   * 显示导入说明和征求用户同意
   */
  showImportGuide() {
    return new Promise((resolve) => {
      wx.showModal({
        title: '从通讯录导入',
        content: '由于隐私保护，您需要逐个选择联系人进行导入。点击确定开始选择联系人。',
        confirmText: '开始导入',
        cancelText: '取消',
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
   * 从手机通讯录选择联系人
   */
  selectContactFromPhoneBook() {
    return new Promise((resolve) => {
      wx.chooseContact({
        success: (res) => {
          console.log('选择联系人成功:', res);
          resolve({
            name: res.displayName,
            phone: res.phoneNumber
          });
        },
        fail: (error) => {
          console.error('选择联系人失败:', error);
          
          if (error.errMsg.includes('auth deny')) {
            wx.showToast({
              title: '需要授权访问通讯录',
              icon: 'none',
              duration: 2000
            });
          } else if (error.errMsg.includes('cancel')) {
            // 用户取消选择
            console.log('用户取消选择联系人');
          } else {
            wx.showToast({
              title: '选择联系人失败',
              icon: 'none',
              duration: 2000
            });
          }
          
          resolve(null);
        }
      });
    });
  }

  /**
   * 检查联系人是否重复
   */
  async checkDuplicate(contact) {
    try {
      if (!contact.phone) {
        return { isDuplicate: false };
      }

      // 格式化手机号，移除特殊字符
      const formattedPhone = contact.phone.replace(/[\s\-\(\)]/g, '');
      
      // 获取现有联系人列表
      const existingContacts = dataManager.contacts || [];
      
      // 查找重复（基于手机号）
      const duplicateContact = existingContacts.find(existingContact => {
        if (!existingContact.phone) return false;
        const existingFormattedPhone = existingContact.phone.replace(/[\s\-\(\)]/g, '');
        return existingFormattedPhone === formattedPhone;
      });

      return {
        isDuplicate: !!duplicateContact,
        existingContact: duplicateContact
      };
    } catch (error) {
      console.error('检查重复联系人失败:', error);
      return { isDuplicate: false };
    }
  }

  /**
   * 处理重复联系人
   */
  handleDuplicate(duplicateInfo) {
    return new Promise((resolve) => {
      const existingContact = duplicateInfo.existingContact;
      
      wx.showModal({
        title: '发现重复联系人',
        content: `联系人"${existingContact.profile_name}"已存在，是否覆盖更新？`,
        confirmText: '覆盖',
        cancelText: '跳过',
        success: (res) => {
          resolve(res.confirm ? 'overwrite' : 'skip');
        },
        fail: () => {
          resolve('skip');
        }
      });
    });
  }

  /**
   * 确认联系人信息
   */
  confirmContactInfo(contact) {
    return new Promise((resolve) => {
      // 显示确认对话框
      wx.showModal({
        title: '确认导入',
        content: `姓名：${contact.name || '未知'}\n手机：${contact.phone || '未知'}\n\n确认导入这个联系人吗？`,
        confirmText: '导入',
        cancelText: '跳过',
        success: (res) => {
          if (res.confirm) {
            // 用户确认导入，格式化数据
            const contactData = {
              profile_name: contact.name || '',
              phone: contact.phone || '',
              wechat_id: '',
              email: '',
              company: '',
              position: '',
              location: '',
              notes: '从通讯录导入',
              tags: [],
              gender: '',
              age: '',
              marital_status: '',
              education: '',
              asset_level: '',
              personality: ''
            };
            resolve(contactData);
          } else {
            // 用户取消，跳过此联系人
            resolve(null);
          }
        },
        fail: () => {
          resolve(null);
        }
      });
    });
  },

  /**
   * 创建导入的联系人
   */
  async createImportedContact(contactData) {
    try {
      console.log('创建导入的联系人:', contactData);
      
      const result = await dataManager.createProfile(contactData);
      
      if (result.success) {
        wx.showToast({
          title: '导入成功',
          icon: 'success',
          duration: 1500
        });
        
        return result;
      } else {
        throw new Error(result.message || '创建失败');
      }
    } catch (error) {
      console.error('创建导入联系人失败:', error);
      throw error;
    }
  }

  /**
   * 询问用户是否继续导入
   */
  askContinueImport() {
    return new Promise((resolve) => {
      const { success, duplicates, errors } = this.importStats;
      const statsText = `已导入: ${success}个, 重复: ${duplicates}个, 失败: ${errors}个`;
      
      wx.showModal({
        title: '导入进度',
        content: `${statsText}\n\n是否继续导入更多联系人？`,
        confirmText: '继续',
        cancelText: '完成',
        success: (res) => {
          if (res.confirm) {
            // 继续导入
            this.importFromPhoneBook().then(resolve);
          } else {
            // 完成导入，显示最终统计
            this.showFinalStats();
            resolve(null);
          }
        },
        fail: () => {
          this.showFinalStats();
          resolve(null);
        }
      });
    });
  }

  /**
   * 显示最终导入统计
   */
  showFinalStats() {
    const { success, duplicates, errors } = this.importStats;
    
    if (success === 0 && duplicates === 0 && errors === 0) {
      return; // 没有实际操作，不显示统计
    }
    
    let message = `导入完成！\n`;
    if (success > 0) message += `成功导入: ${success}个\n`;
    if (duplicates > 0) message += `跳过重复: ${duplicates}个\n`;
    if (errors > 0) message += `导入失败: ${errors}个`;
    
    wx.showToast({
      title: message,
      icon: success > 0 ? 'success' : 'none',
      duration: 3000
    });
  }

  /**
   * 重置导入统计
   */
  resetImportStats() {
    this.importStats = {
      total: 0,
      success: 0,
      duplicates: 0,
      errors: 0
    };
  }

  /**
   * 批量导入联系人（预留接口）
   */
  async batchImportContacts(contacts) {
    // 此功能需要用户逐个确认，暂时不实现
    // 可以在未来版本中添加
    throw new Error('批量导入功能暂未实现');
  }

  /**
   * 获取导入统计信息
   */
  getImportStats() {
    return { ...this.importStats };
  }

  /**
   * 检查导入状态
   */
  isCurrentlyImporting() {
    return this.isImporting;
  }
}

// 创建单例实例
const contactImporter = new ContactImporter();

export default contactImporter;