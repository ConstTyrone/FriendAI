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
  }

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
   * 批量导入联系人
   */
  async batchImportContacts(contacts, importMode = 'create') {
    if (this.isImporting) {
      throw new Error('正在导入中，请稍候...');
    }

    try {
      this.isImporting = true;
      this.resetImportStats();
      this.importStats.total = contacts.length;

      console.log('开始批量导入联系人:', contacts.length, '个');

      const result = await dataManager.batchImportProfiles(contacts, importMode);
      
      // 更新统计信息
      this.importStats.success = result.success_count || 0;
      this.importStats.errors = result.failed_count || 0;
      this.importStats.duplicates = result.skipped_count || 0;

      console.log('批量导入完成:', this.importStats);

      return {
        success: result.success,
        stats: this.importStats,
        details: result
      };
    } catch (error) {
      console.error('批量导入失败:', error);
      throw error;
    } finally {
      this.isImporting = false;
    }
  }

  /**
   * 解析文本格式的联系人数据
   */
  parseTextContacts(text) {
    try {
      const lines = text.trim().split('\n');
      const contacts = [];
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        
        // 尝试解析不同格式
        const contact = this.parseContactLine(line);
        if (contact) {
          contacts.push(contact);
        }
      }
      
      return contacts;
    } catch (error) {
      console.error('解析文本联系人失败:', error);
      return [];
    }
  }

  /**
   * 解析单行联系人数据
   */
  parseContactLine(line) {
    try {
      // 支持多种格式：
      // 1. "姓名,手机号,公司,职位"
      // 2. "姓名 手机号 公司 职位"
      // 3. "姓名\t手机号\t公司\t职位"
      
      let parts = [];
      
      // 尝试逗号分隔
      if (line.includes(',')) {
        parts = line.split(',').map(p => p.trim());
      }
      // 尝试制表符分隔
      else if (line.includes('\t')) {
        parts = line.split('\t').map(p => p.trim());
      }
      // 尝试空格分隔（至少2个空格）
      else if (line.includes('  ')) {
        parts = line.split(/\s{2,}/).map(p => p.trim());
      }
      // 单个空格分隔（可能不准确）
      else if (line.includes(' ')) {
        parts = line.split(' ').map(p => p.trim());
      }
      // 只有一个字段，作为姓名
      else {
        parts = [line];
      }
      
      if (parts.length === 0 || !parts[0]) {
        return null;
      }
      
      const contact = {
        name: parts[0],
        phone: parts[1] || '',
        company: parts[2] || '',
        position: parts[3] || '',
        address: parts[4] || '',
        notes: parts[5] || '批量导入',
        tags: [],
        gender: '',
        age: '',
        marital_status: '',
        education: '',
        asset_level: '',
        personality: ''
      };
      
      return contact;
    } catch (error) {
      console.error('解析联系人行失败:', error);
      return null;
    }
  }

  /**
   * 显示批量导入引导
   */
  showBatchImportGuide() {
    return new Promise((resolve) => {
      wx.showModal({
        title: '批量导入联系人',
        content: '支持以下格式：\n1. 姓名,手机,公司,职位\n2. 每行一个联系人\n3. 用逗号或制表符分隔字段\n\n点击确定开始导入',
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