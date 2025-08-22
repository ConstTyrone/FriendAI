import dataManager from './data-manager';

class ContactImporter {
  constructor() {
    this.isImporting = false;
    this.isBatchMode = false;  // 批量导入模式标识
    this.batchQueue = [];      // 批量导入队列
    this.importStats = {
      total: 0,
      success: 0,
      duplicates: 0,
      errors: 0
    };
    this.progressCallback = null; // 进度回调函数
    this.maxRetries = 3;         // 最大重试次数
    this.batchSize = 5;          // 批量处理大小（适合小程序性能）
    this.maxSelectionsPerSession = 20; // 单次最大选择数量限制
  }

  /**
   * 从手机通讯录导入联系人
   */
  async importFromPhoneBook() {
    console.log('📱 [ContactImporter] importFromPhoneBook 方法开始');
    
    if (this.isImporting) {
      console.log('⚠️ [ContactImporter] 正在导入中，抛出错误');
      throw new Error('正在导入中，请稍候...');
    }

    try {
      console.log('✅ [ContactImporter] 设置导入状态');
      this.isImporting = true;
      this.resetImportStats();

      // 显示导入说明
      console.log('📋 [ContactImporter] 显示导入说明');
      const userConfirmed = await this.showImportGuide();
      console.log('🔍 [ContactImporter] 用户确认结果:', userConfirmed);
      if (!userConfirmed) {
        console.log('❌ [ContactImporter] 用户取消导入');
        return null;
      }

      // 开始选择联系人
      console.log('📲 [ContactImporter] 开始选择联系人');
      const contact = await this.selectContactFromPhoneBook();
      console.log('🔍 [ContactImporter] 选择联系人结果:', contact);
      if (!contact) {
        console.log('❌ [ContactImporter] 未选择联系人');
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
   * 快速批量导入从手机通讯录
   */
  async quickBatchImportFromPhoneBook(progressCallback = null) {
    console.log('🚀 [ContactImporter] quickBatchImportFromPhoneBook 方法开始');
    
    // 如果正在导入，先尝试重置状态
    if (this.isImporting) {
      console.log('⚠️ [ContactImporter] 检测到导入状态异常，尝试重置');
      this.resetImportState();
      // 短暂延迟确保状态重置
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    try {
      console.log('✅ [ContactImporter] 设置批量导入状态');
      this.isImporting = true;
      this.isBatchMode = true;
      this.batchQueue = [];
      this.progressCallback = progressCallback;
      this.resetImportStats();

      // 显示快速批量导入说明
      console.log('📋 [ContactImporter] 显示快速批量导入说明');
      const userConfirmed = await this.showQuickBatchImportGuide();
      console.log('🔍 [ContactImporter] 用户确认结果:', userConfirmed);
      if (!userConfirmed) {
        console.log('❌ [ContactImporter] 用户取消批量导入');
        return {
          success: false,
          cancelled: true,
          stats: this.importStats
        };
      }

      // 开始快速连续选择联系人
      console.log('🔄 [ContactImporter] 开始快速连续选择');
      await this.startQuickSelection();
      console.log('✅ [ContactImporter] 快速选择完成，队列长度:', this.batchQueue.length);

      return {
        success: true,
        stats: this.importStats
      };

    } catch (error) {
      console.error('❌ [ContactImporter] 快速批量导入失败:', error);
      console.error('❌ [ContactImporter] 错误堆栈:', error.stack);
      this.showErrorDialog('快速批量导入失败', error.message);
      return {
        success: false,
        error: error.message,
        stats: this.importStats
      };
    } finally {
      console.log('🏁 [ContactImporter] 重置导入状态');
      this.isImporting = false;
      this.isBatchMode = false;
      this.progressCallback = null;
    }
  }

  /**
   * 显示快速批量导入说明
   */
  showQuickBatchImportGuide() {
    return new Promise((resolve) => {
      console.log('🎯 [ContactImporter] 准备显示快速批量导入说明弹窗');
      
      wx.showModal({
        title: '🚀 快速批量导入',
        content: `🎯 快速导入模式特点：\n\n✅ 连续选择多个联系人\n⚡ 自动跳过重复联系人\n🔄 智能重试失败请求\n📊 实时进度反馈\n📈 导入完成后显示详细统计\n\n💡 性能建议：\n• 单次导入 5-10 个效果最佳\n• 最大支持 ${this.maxSelectionsPerSession} 个联系人\n• 建议在 WiFi 环境下操作`,
        confirmText: '开始快速导入',
        cancelText: '取消',
        success: (res) => {
          console.log('🎯 [ContactImporter] 用户选择结果:', res);
          console.log('🎯 [ContactImporter] res.confirm:', res.confirm);
          console.log('🎯 [ContactImporter] res.cancel:', res.cancel);
          resolve(res.confirm);
        },
        fail: (error) => {
          console.error('❌ [ContactImporter] 弹窗显示失败:', error);
          resolve(false);
        }
      });
    });
  }

  /**
   * 开始快速连续选择
   */
  async startQuickSelection() {
    let continueSelection = true;
    
    while (continueSelection) {
      try {
        // 选择联系人
        const contact = await this.selectContactFromPhoneBook();
        
        if (!contact) {
          // 用户取消选择，询问是否完成导入
          continueSelection = await this.askFinishQuickImport();
          break;
        }

        // 检查重复
        const duplicateCheck = await this.checkDuplicate(contact);
        if (duplicateCheck.isDuplicate) {
          this.importStats.duplicates++;
          
          // 显示跳过提示
          wx.showToast({
            title: `${contact.name} 已存在，已跳过`,
            icon: 'none',
            duration: 1500
          });
        } else {
          // 验证联系人数据
          const validation = this.validateContactData(contact);
          if (!validation.isValid) {
            this.importStats.errors++;
            wx.showToast({
              title: `⚠️ ${contact.name}: ${validation.errors[0]}`,
              icon: 'none',
              duration: 2000
            });
          } else {
            // 添加到导入队列
            this.batchQueue.push(contact);
            this.importStats.total++;
            
            // 显示添加成功提示（更优雅的反馈）
            wx.showToast({
              title: `✅ 已添加 ${contact.name} (${this.batchQueue.length})`,
              icon: 'none',
              duration: 800
            });
          }
        }

        // 检查是否达到最大选择数量
        if (this.batchQueue.length >= this.maxSelectionsPerSession) {
          wx.showModal({
            title: '⚠️ 选择数量已达上限',
            content: `为保证导入性能，单次最多选择 ${this.maxSelectionsPerSession} 个联系人。\n\n当前已选择 ${this.batchQueue.length} 个联系人，是否开始导入？`,
            confirmText: '开始导入',
            cancelText: '继续选择',
            success: (res) => {
              continueSelection = !res.confirm;
            }
          });
        } else {
          // 询问是否继续选择
          continueSelection = await this.askContinueQuickSelection();
        }

      } catch (error) {
        console.error('选择联系人失败:', error);
        this.importStats.errors++;
        
        // 询问是否继续
        continueSelection = await this.askContinueAfterError(error);
      }
    }

    // 如果有待导入的联系人，执行批量导入
    if (this.batchQueue.length > 0) {
      await this.executeBatchImportFromQueue();
    } else {
      wx.showToast({
        title: '未选择任何联系人',
        icon: 'none',
        duration: 2000
      });
    }
  }

  /**
   * 询问是否继续快速选择
   */
  askContinueQuickSelection() {
    return new Promise((resolve) => {
      const { total, duplicates } = this.importStats;
      const selectedCount = this.batchQueue.length;
      
      wx.showModal({
        title: '继续选择联系人',
        content: `已选择: ${selectedCount}个\n跳过重复: ${duplicates}个\n\n继续选择更多联系人？`,
        confirmText: '继续选择',
        cancelText: '开始导入',
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
   * 询问是否完成快速导入
   */
  askFinishQuickImport() {
    return new Promise((resolve) => {
      const selectedCount = this.batchQueue.length;
      
      if (selectedCount === 0) {
        resolve(false);
        return;
      }
      
      wx.showModal({
        title: '完成选择',
        content: `已选择 ${selectedCount} 个联系人\n\n是否开始导入？`,
        confirmText: '开始导入',
        cancelText: '继续选择',
        success: (res) => {
          resolve(!res.confirm); // 注意：这里返回的是是否继续选择
        },
        fail: () => {
          resolve(false);
        }
      });
    });
  }

  /**
   * 询问错误后是否继续
   */
  askContinueAfterError(error) {
    return new Promise((resolve) => {
      wx.showModal({
        title: '选择失败',
        content: `${error.message || '选择联系人失败'}\n\n是否继续选择其他联系人？`,
        confirmText: '继续',
        cancelText: '结束导入',
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
   * 执行批量导入队列
   */
  async executeBatchImportFromQueue() {
    let loadingShown = false;
    
    try {
      this.importStartTime = Date.now();
      
      wx.showLoading({
        title: `📥 准备导入 ${this.batchQueue.length} 个联系人...`,
        mask: true
      });
      loadingShown = true;
      
      // 回调开始导入
      if (this.progressCallback) {
        this.progressCallback({
          phase: 'starting',
          total: this.batchQueue.length
        });
      }

      let successCount = 0;
      let errorCount = 0;

      // 分批并行导入联系人
      const batches = this.chunkArray(this.batchQueue, this.batchSize);
      
      for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
        const batch = batches[batchIndex];
        
        // 更新总体进度
        const overallProgress = Math.floor((batchIndex / batches.length) * 100);
        wx.showLoading({
          title: `批次 ${batchIndex + 1}/${batches.length} (${overallProgress}%)\n正在导入 ${batch.length} 个联系人...`,
          mask: true
        });
        
        // 回调进度更新
        if (this.progressCallback) {
          this.progressCallback({
            phase: 'importing',
            batchIndex: batchIndex + 1,
            totalBatches: batches.length,
            currentBatch: batch.length,
            overallProgress
          });
        }
        
        // 并行处理当前批次
        const batchPromises = batch.map(async (contact, index) => {
          const absoluteIndex = batchIndex * this.batchSize + index;
          return this.importSingleContactWithRetry(contact, absoluteIndex + 1, this.batchQueue.length);
        });
        
        const batchResults = await Promise.allSettled(batchPromises);
        
        // 统计当前批次结果
        batchResults.forEach(result => {
          if (result.status === 'fulfilled' && result.value.success) {
            successCount++;
          } else {
            errorCount++;
          }
        });
        
        // 批次间的短暂延迟
        if (batchIndex < batches.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 200));
        }
      }

      if (loadingShown) {
        wx.hideLoading();
        loadingShown = false;
      }
      this.importEndTime = Date.now();

      // 更新统计
      this.importStats.success = successCount;
      this.importStats.errors = errorCount;

      // 显示最终结果
      this.showQuickBatchImportResult();

    } catch (error) {
      if (loadingShown) {
        wx.hideLoading();
        loadingShown = false;
      }
      console.error('批量导入执行失败:', error);
      
      wx.showModal({
        title: '批量导入失败',
        content: error.message || '导入过程中出现错误',
        showCancel: false
      });
    }
  }

  /**
   * 格式化联系人数据
   */
  formatContactData(contact) {
    // 先清理数据
    const sanitizedContact = this.sanitizeContactData(contact);
    
    // 验证数据
    const validation = this.validateContactData(sanitizedContact);
    if (!validation.isValid) {
      throw new Error(`联系人数据无效: ${validation.errors.join(', ')}`);
    }
    
    return {
      name: sanitizedContact.name || '',  // 修正：使用 name 而不是 profile_name
      phone: sanitizedContact.phone || '',
      wechat_id: '',
      email: '',
      company: sanitizedContact.company || '',
      position: sanitizedContact.position || '',
      location: '',
      notes: '快速批量导入自通讯录',
      tags: [],
      gender: '',
      age: '',
      marital_status: '',
      education: '',
      asset_level: '',
      personality: ''
    };
  }

  /**
   * 显示快速批量导入结果
   */
  showQuickBatchImportResult() {
    const { total, success, duplicates, errors } = this.importStats;
    const successRate = total > 0 ? Math.round((success / total) * 100) : 0;
    
    let title = '🎉 快速批量导入完成';
    let icon = '📊';
    
    if (successRate === 100) {
      title = '✅ 导入完美成功！';
      icon = '🎯';
    } else if (successRate >= 80) {
      title = '✨ 导入基本成功';
      icon = '👍';
    } else if (successRate >= 50) {
      title = '⚠️ 导入部分成功';
      icon = '📈';
    } else if (successRate > 0) {
      title = '⚠️ 导入遇到困难';
      icon = '🔧';
    } else {
      title = '❌ 导入失败';
      icon = '🆘';
    }
    
    let message = `${icon} 导入统计报告\n\n`;
    message += `📱 选择联系人: ${total}个\n`;
    message += `✅ 成功导入: ${success}个 (${successRate}%)\n`;
    if (duplicates > 0) message += `⏭️ 跳过重复: ${duplicates}个\n`;
    if (errors > 0) message += `❌ 导入失败: ${errors}个\n`;
    
    // 添加性能统计
    const duration = Date.now() - this.importStartTime;
    if (duration && total > 0) {
      const avgTime = Math.round(duration / total);
      message += `\n⏱️ 平均用时: ${avgTime}ms/联系人`;
    }

    wx.showModal({
      title: title,
      content: message,
      showCancel: false,
      confirmText: '知道了',
      success: () => {
        // 触发数据刷新事件
        if (dataManager && dataManager.emit) {
          dataManager.emit('dataChanged', { 
            type: 'contacts', 
            action: 'quick_batch_import',
            stats: this.importStats
          });
        }
        
        // 回调最终结果
        if (this.progressCallback) {
          this.progressCallback({
            phase: 'completed',
            stats: this.importStats,
            successRate
          });
        }
      }
    });
  }

  /**
   * 显示导入说明和征求用户同意
   */
  showImportGuide() {
    return new Promise((resolve) => {
      wx.showModal({
        title: '从通讯录导入',
        content: '选择导入方式：\n\n• 单个导入：逐个选择并确认联系人信息\n• 快速批量导入：连续选择多个联系人快速导入',
        confirmText: '单个导入',
        cancelText: '取消',
        success: (res) => {
          if (res.confirm) {
            resolve(true);
          } else {
            // 显示快速批量导入选项
            this.showBatchImportOption().then(resolve);
          }
        },
        fail: () => {
          resolve(false);
        }
      });
    });
  }

  /**
   * 显示快速批量导入选项
   */
  showBatchImportOption() {
    return new Promise((resolve) => {
      wx.showModal({
        title: '选择导入方式',
        content: '您想要快速批量导入联系人吗？\n\n快速模式会连续选择多个联系人并自动导入，无需逐个确认。',
        confirmText: '快速批量导入',
        cancelText: '取消',
        success: (res) => {
          if (res.confirm) {
            // 启动快速批量导入
            this.quickBatchImportFromPhoneBook().then(() => resolve(false));
          } else {
            resolve(false);
          }
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
    console.log('📞 [ContactImporter] selectContactFromPhoneBook 开始');
    
    return new Promise((resolve) => {
      console.log('📞 [ContactImporter] 调用 wx.chooseContact');
      
      wx.chooseContact({
        success: (res) => {
          console.log('✅ [ContactImporter] 选择联系人成功:', res);
          const contact = {
            name: res.displayName,
            phone: res.phoneNumber
          };
          console.log('🔍 [ContactImporter] 格式化后的联系人:', contact);
          resolve(contact);
        },
        fail: (error) => {
          console.error('❌ [ContactImporter] 选择联系人失败:', error);
          console.error('❌ [ContactImporter] 错误详情:', {
            errMsg: error.errMsg,
            errCode: error.errCode
          });
          
          if (error.errMsg.includes('auth deny')) {
            console.log('🚫 [ContactImporter] 权限被拒绝');
            wx.showModal({
              title: '权限申请',
              content: '需要授权访问通讯录才能导入联系人。请在小程序设置中开启通讯录权限。',
              showCancel: false,
              confirmText: '知道了'
            });
          } else if (error.errMsg.includes('cancel')) {
            // 用户取消选择
            console.log('🚫 [ContactImporter] 用户取消选择联系人');
          } else {
            console.log('❌ [ContactImporter] 其他错误');
            wx.showModal({
              title: '选择失败',
              content: `选择联系人失败：${error.errMsg}\n\n请确保已授权通讯录权限`,
              showCancel: false,
              confirmText: '知道了'
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
              name: contact.name || '',  // 修正：使用 name 而不是 profile_name
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
    console.log('💾 [ContactImporter] createImportedContact 开始');
    
    try {
      console.log('🔍 [ContactImporter] 准备创建联系人:', contactData);
      console.log('🔍 [ContactImporter] dataManager 检查:', {
        exists: !!dataManager,
        hasCreateProfile: !!dataManager?.createProfile,
        type: typeof dataManager?.createProfile
      });
      
      if (!dataManager || !dataManager.createProfile) {
        throw new Error('dataManager 或 createProfile 方法不可用');
      }
      
      console.log('📡 [ContactImporter] 调用 dataManager.createProfile');
      const result = await dataManager.createProfile(contactData);
      console.log('🔍 [ContactImporter] dataManager.createProfile 结果:', result);
      
      if (result && result.success) {
        console.log('✅ [ContactImporter] 联系人创建成功');
        wx.showToast({
          title: '导入成功',
          icon: 'success',
          duration: 1500
        });
        
        return result;
      } else {
        console.log('❌ [ContactImporter] 联系人创建失败:', result);
        throw new Error(result?.message || result?.detail || '创建失败');
      }
    } catch (error) {
      console.error('❌ [ContactImporter] 创建导入联系人失败:', error);
      console.error('❌ [ContactImporter] 错误堆栈:', error.stack);
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
      
      // 定义需要过滤的提示文字模式
      const filterPatterns = [
        /请粘贴联系人数据/,
        /每行一个联系人/,
        /姓名.*手机.*公司.*职位/,
        /格式.*示例/,
        /支持.*格式/,
        /导入.*说明/,
        /^[\s\u3000]*$/,  // 空行或仅包含空格的行
        /^[：:：。，,；;！!？?""''"'（）()【】\[\]]*$/,  // 仅包含标点符号的行
      ];
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        
        // 检查是否为提示文字
        let isPromptText = false;
        for (const pattern of filterPatterns) {
          if (pattern.test(line)) {
            console.log('过滤提示文字:', line);
            isPromptText = true;
            break;
          }
        }
        
        if (isPromptText) continue;
        
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
      
      // 验证姓名的有效性
      const name = parts[0];
      
      // 过滤明显的非联系人数据
      const invalidNamePatterns = [
        /^[0-9]+$/,  // 纯数字
        /^[a-zA-Z]{1,2}$/,  // 1-2个英文字母
        /^[\s\u3000]*$/,  // 仅空格
        /^[：:：。，,；;！!？?""''"'（）()【】\[\]]+$/,  // 仅标点符号
        /请.*粘贴/,  // 包含"请...粘贴"
        /格式.*示例/,  // 包含"格式...示例"
        /每行.*联系人/,  // 包含"每行...联系人"
        /支持.*格式/,  // 包含"支持...格式"
      ];
      
      for (const pattern of invalidNamePatterns) {
        if (pattern.test(name)) {
          console.log('过滤无效姓名:', name);
          return null;
        }
      }
      
      // 姓名长度检查（通常1-20个字符）
      if (name.length < 1 || name.length > 20) {
        console.log('姓名长度不合理:', name);
        return null;
      }
      
      const contact = {
        name: name,
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

  /**
   * 重置导入状态
   */
  resetImportState() {
    console.log('🔄 [ContactImporter] 强制重置导入状态');
    this.isImporting = false;
    this.isBatchMode = false;
    this.progressCallback = null;
    this.batchQueue = [];
    this.importStats = {
      total: 0,
      success: 0,
      errors: 0,
      duplicates: 0
    };
  }

  /**
   * 快速批量导入（跳过说明弹窗）
   */
  async quickBatchImportFromPhoneBookDirect(progressCallback = null) {
    console.log('🚀 [ContactImporter] quickBatchImportFromPhoneBookDirect 方法开始 - 跳过说明');
    
    // 如果正在导入，先尝试重置状态
    if (this.isImporting) {
      console.log('⚠️ [ContactImporter] 检测到导入状态异常，尝试重置');
      this.resetImportState();
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    try {
      console.log('✅ [ContactImporter] 设置批量导入状态');
      this.isImporting = true;
      this.isBatchMode = true;
      this.batchQueue = [];
      this.progressCallback = progressCallback;
      this.resetImportStats();

      // 跳过说明弹窗，直接开始快速选择
      console.log('⚡ [ContactImporter] 跳过说明，直接开始快速连续选择');
      const result = await this.startQuickSelection();
      
      if (result && result.success) {
        console.log('✅ [ContactImporter] 快速批量导入完成');
        return {
          success: true,
          stats: this.importStats
        };
      } else {
        console.log('⚠️ [ContactImporter] 快速批量导入未完成或被取消');
        return {
          success: false,
          cancelled: result?.cancelled || false,
          stats: this.importStats
        };
      }
      
    } catch (error) {
      console.error('❌ [ContactImporter] 快速批量导入失败:', error);
      return {
        success: false,
        error: error.message,
        stats: this.importStats
      };
    } finally {
      console.log('🏁 [ContactImporter] 重置导入状态');
      this.isImporting = false;
      this.isBatchMode = false;
      this.progressCallback = null;
    }
  }

  /**
   * 将数组分块
   */
  chunkArray(array, chunkSize) {
    const chunks = [];
    for (let i = 0; i < array.length; i += chunkSize) {
      chunks.push(array.slice(i, i + chunkSize));
    }
    return chunks;
  }

  /**
   * 带重试的单个联系人导入
   */
  async importSingleContactWithRetry(contact, index, total, retryCount = 0) {
    try {
      // 更新单个联系人进度
      if (this.progressCallback) {
        this.progressCallback({
          phase: 'importing_contact',
          contact: contact.name,
          index,
          total,
          attempt: retryCount + 1
        });
      }

      // 格式化联系人数据
      const contactData = this.formatContactData(contact);
      
      // 创建联系人
      const result = await dataManager.createProfile(contactData);
      
      if (result.success) {
        return { success: true, contact: contactData };
      } else {
        throw new Error(result.message || '创建失败');
      }
      
    } catch (error) {
      console.error(`导入联系人 ${contact.name} 失败 (尝试 ${retryCount + 1}/${this.maxRetries + 1}):`, error);
      
      // 如果还有重试机会，进行重试
      if (retryCount < this.maxRetries) {
        console.log(`正在重试导入 ${contact.name}...`);
        
        // 指数退避延迟
        const delay = Math.min(1000 * Math.pow(2, retryCount), 5000);
        await new Promise(resolve => setTimeout(resolve, delay));
        
        return this.importSingleContactWithRetry(contact, index, total, retryCount + 1);
      }
      
      // 超过最大重试次数，返回失败
      return { 
        success: false, 
        error: error.message,
        contact: contact.name,
        attempts: retryCount + 1
      };
    }
  }

  /**
   * 显示错误对话框
   */
  showErrorDialog(title, message) {
    wx.showModal({
      title: title || '操作失败',
      content: message || '发生未知错误',
      showCancel: false,
      confirmText: '知道了',
      confirmColor: '#ff4757'
    });
  }

  /**
   * 设置进度回调函数
   */
  setProgressCallback(callback) {
    this.progressCallback = callback;
  }

  /**
   * 获取导入性能统计
   */
  getPerformanceStats() {
    const duration = this.importEndTime ? (this.importEndTime - this.importStartTime) : 0;
    const { total, success, errors, duplicates } = this.importStats;
    
    return {
      duration,
      totalContacts: total,
      successRate: total > 0 ? (success / total) * 100 : 0,
      avgTimePerContact: total > 0 ? duration / total : 0,
      throughput: duration > 0 ? (total / duration) * 1000 : 0, // 联系人/秒
      retryRate: errors > 0 ? (errors / total) * 100 : 0
    };
  }

  /**
   * 验证联系人数据
   */
  validateContactData(contact) {
    const errors = [];
    
    if (!contact.name || contact.name.trim().length === 0) {
      errors.push('联系人姓名不能为空');
    }
    
    if (contact.phone && !/^[\d\s\-\(\)\+]{7,20}$/.test(contact.phone)) {
      errors.push('手机号格式不正确');
    }
    
    if (contact.name && contact.name.length > 50) {
      errors.push('联系人姓名过长');
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * 清理并优化联系人数据
   */
  sanitizeContactData(contact) {
    return {
      ...contact,
      name: contact.name ? contact.name.trim().substring(0, 50) : '',
      phone: contact.phone ? contact.phone.replace(/[^\d\s\-\(\)\+]/g, '') : '',
      company: contact.company ? contact.company.trim().substring(0, 100) : '',
      position: contact.position ? contact.position.trim().substring(0, 100) : ''
    };
  }
}

// 创建单例实例
const contactImporter = new ContactImporter();

export default contactImporter;