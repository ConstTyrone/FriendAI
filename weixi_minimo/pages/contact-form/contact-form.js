import { PAGE_ROUTES } from '../../utils/constants';
import { isPhone, isEmail, isNotEmpty, isValidMaritalStatus, isValidAssetLevel, isValidGender } from '../../utils/validator';
import authManager from '../../utils/auth-manager';
import dataManager from '../../utils/data-manager';

// 引入语音识别插件
const WechatSI = requirePlugin('WechatSI');
const recordManager = WechatSI.getRecordRecognitionManager();

Page({
  data: {
    // 表单模式：'add' 新增，'edit' 编辑
    mode: 'add',
    contactId: '',
    
    // 表单数据
    formData: {
      name: '',
      phone: '',
      wechat_id: '',
      email: '',
      company: '',
      position: '',
      address: '',
      notes: '',
      tags: [],
      // 新增字段
      gender: '',
      age: '',
      marital_status: '',
      education: '',
      asset_level: '',
      personality: ''
    },
    
    // 原始数据（编辑模式下用于比较变化）
    originalData: {},
    
    // 表单验证状态
    formErrors: {},
    
    // 页面状态
    loading: false,
    saving: false, // 确保初始状态为false
    
    // 标签相关
    tagInputValue: '',
    showTagInput: false,
    
    // 对话框状态
    showCancelDialog: false,
    showIntentMatchingHint: false, // 意图匹配提示
    
    // 选择器选项
    genderOptions: ['男', '女', '未知'],
    genderIndex: -1,
    maritalOptions: ['未婚', '已婚已育', '已婚未育', '离异', '未知'],
    maritalIndex: -1,
    assetOptions: ['高', '中', '低', '未知'],
    assetIndex: -1,
    
    // 语音输入相关
    isRecording: false, // 是否正在录音
    isParsing: false // 是否正在解析
  },

  onLoad(options) {
    console.log('联系人表单页面加载', options);
    
    const mode = options.mode || 'add';
    const contactId = options.id || '';
    
    this.setData({ 
      mode, 
      contactId,
      saving: false // 确保按钮可点击
    });
    
    // 设置页面标题
    wx.setNavigationBarTitle({
      title: mode === 'edit' ? '编辑联系人' : '新增联系人'
    });
    
    // 初始化语音识别事件监听
    this.initVoiceRecognition();
    
    // 初始化页面数据
    this.initPageData();
  },

  onShow() {
    console.log('联系人表单页面显示');
  },

  onReady() {
    console.log('联系人表单页面准备就绪');
  },

  onHide() {
    console.log('联系人表单页面隐藏');
  },

  onUnload() {
    console.log('联系人表单页面卸载');
  },

  /**
   * 初始化页面数据
   */
  async initPageData() {
    try {
      // 检查登录状态
      if (!authManager.isLoggedIn()) {
        wx.showModal({
          title: '未登录',
          content: '请先登录再编辑联系人',
          showCancel: false,
          success: () => {
            wx.navigateBack();
          }
        });
        return;
      }
      
      // 如果是编辑模式，加载联系人数据
      if (this.data.mode === 'edit' && this.data.contactId) {
        await this.loadContactData();
      }
      
      console.log('页面数据初始化完成');
    } catch (error) {
      console.error('初始化页面数据失败:', error);
      
      wx.showModal({
        title: '加载失败',
        content: error.message || '无法加载联系人信息',
        showCancel: false,
        success: () => {
          wx.navigateBack();
        }
      });
    }
  },

  /**
   * 加载联系人数据（编辑模式）
   */
  async loadContactData() {
    try {
      this.setData({ loading: true });
      
      const contact = await dataManager.getContactDetail(this.data.contactId);
      
      if (!contact) {
        throw new Error('联系人不存在');
      }
      
      // 处理联系人数据 - 适配后端字段名
      const formData = {
        name: contact.profile_name || contact.name || '',
        phone: contact.phone || '',
        wechat_id: contact.wechat_id || '',
        email: contact.email || '',
        company: contact.company || '',
        position: contact.position || '',
        address: contact.location || contact.address || '',
        notes: contact.ai_summary || contact.notes || '',
        tags: Array.isArray(contact.tags) ? contact.tags : [],
        // 额外字段
        gender: contact.gender || '',
        age: contact.age || '',
        marital_status: contact.marital_status || '',
        education: contact.education || '',
        asset_level: contact.asset_level || '',
        personality: contact.personality || ''
      };
      
      // 设置选择器索引
      const genderIndex = this.data.genderOptions.indexOf(formData.gender);
      const maritalIndex = this.data.maritalOptions.indexOf(formData.marital_status);
      const assetIndex = this.data.assetOptions.indexOf(formData.asset_level);
      
      this.setData({
        formData,
        originalData: JSON.parse(JSON.stringify(formData)),
        loading: false,
        genderIndex: genderIndex >= 0 ? genderIndex : -1,
        maritalIndex: maritalIndex >= 0 ? maritalIndex : -1,
        assetIndex: assetIndex >= 0 ? assetIndex : -1
      });
      
      console.log('联系人数据加载完成:', formData);
    } catch (error) {
      console.error('加载联系人数据失败:', error);
      
      this.setData({ loading: false });
      
      throw error;
    }
  },

  /**
   * 表单字段变化处理
   */
  onFieldChange(event) {
    const { field } = event.currentTarget.dataset;
    const value = event.detail.value;
    
    this.setData({
      [`formData.${field}`]: value,
      [`formErrors.${field}`]: '' // 清除该字段的错误信息
    });
    
    console.log(`字段 ${field} 更新为:`, value);
  },

  /**
   * 添加标签
   */
  onAddTag() {
    console.log('点击添加标签按钮');
    console.log('当前showTagInput状态:', this.data.showTagInput);
    this.setData({ 
      showTagInput: true,
      tagInputValue: '' // 清空之前的输入
    });
    console.log('设置后showTagInput状态:', true);
  },

  /**
   * 标签输入变化
   */
  onTagInputChange(event) {
    console.log('标签输入变化:', event.detail.value);
    this.setData({
      tagInputValue: event.detail.value
    });
  },
  
  /**
   * 选择器变化处理
   */
  onPickerChange(event) {
    const { field } = event.currentTarget.dataset;
    const index = event.detail.value;
    
    if (field === 'gender') {
      this.setData({
        [`formData.gender`]: this.data.genderOptions[index],
        genderIndex: index
      });
    } else if (field === 'marital_status') {
      this.setData({
        [`formData.marital_status`]: this.data.maritalOptions[index],
        maritalIndex: index
      });
    } else if (field === 'asset_level') {
      this.setData({
        [`formData.asset_level`]: this.data.assetOptions[index],
        assetIndex: index
      });
    }
    
    console.log(`${field} 更新为:`, event.detail.value);
  },

  /**
   * 确认添加标签
   */
  onConfirmAddTag() {
    console.log('确认添加标签被调用');
    console.log('当前输入值:', this.data.tagInputValue);
    
    const tagValue = this.data.tagInputValue.trim();
    console.log('处理后的标签值:', tagValue);
    
    if (!tagValue) {
      wx.showToast({
        title: '请输入标签内容',
        icon: 'none'
      });
      return;
    }
    
    const currentTags = this.data.formData.tags;
    console.log('当前标签列表:', currentTags);
    
    // 检查标签是否已存在
    if (currentTags.includes(tagValue)) {
      wx.showToast({
        title: '标签已存在',
        icon: 'none'
      });
      return;
    }
    
    // 添加标签
    const newTags = [...currentTags, tagValue];
    console.log('新标签列表:', newTags);
    
    this.setData({
      'formData.tags': newTags,
      tagInputValue: '',
      showTagInput: false
    });
    
    console.log('标签添加成功:', tagValue);
    console.log('更新后的标签列表:', this.data.formData.tags);
    
    wx.showToast({
      title: '标签已添加',
      icon: 'success'
    });
  },

  /**
   * 取消添加标签
   */
  onCancelAddTag() {
    this.setData({
      tagInputValue: '',
      showTagInput: false
    });
  },

  /**
   * 删除标签
   */
  onDeleteTag(event) {
    const { index } = event.currentTarget.dataset;
    const currentTags = this.data.formData.tags;
    const newTags = currentTags.filter((_, i) => i !== index);
    
    this.setData({
      'formData.tags': newTags
    });
    
    console.log('删除标签，索引:', index);
  },

  /**
   * 验证表单
   */
  validateForm() {
    const { formData } = this.data;
    const errors = {};
    
    // 验证必填字段
    if (!isNotEmpty(formData.name)) {
      errors.name = '请输入联系人姓名';
    }
    
    // 验证手机号
    if (formData.phone && !isPhone(formData.phone)) {
      errors.phone = '请输入正确的手机号码';
    }
    
    // 验证邮箱
    if (formData.email && !isEmail(formData.email)) {
      errors.email = '请输入正确的邮箱地址';
    }
    
    // 验证微信号
    if (formData.wechat_id && formData.wechat_id.length < 6) {
      errors.wechat_id = '微信号长度至少6位';
    }
    
    // 验证性别
    if (formData.gender && !isValidGender(formData.gender)) {
      errors.gender = '请选择正确的性别';
    }
    
    // 验证婚姻状况
    if (formData.marital_status && !isValidMaritalStatus(formData.marital_status)) {
      errors.marital_status = '请选择正确的婚姻状况';
    }
    
    // 验证资产水平
    if (formData.asset_level && !isValidAssetLevel(formData.asset_level)) {
      errors.asset_level = '请选择正确的资产水平';
    }
    
    
    this.setData({ formErrors: errors });
    
    return Object.keys(errors).length === 0;
  },

  /**
   * 检查表单是否有变化
   */
  hasFormChanged() {
    if (this.data.mode === 'add') {
      // 新增模式下，检查是否有任何非空字段
      const { formData } = this.data;
      return Object.values(formData).some(value => {
        if (Array.isArray(value)) {
          return value.length > 0;
        }
        return value && value.trim();
      });
    } else {
      // 编辑模式下，比较与原始数据的差异
      return JSON.stringify(this.data.formData) !== JSON.stringify(this.data.originalData);
    }
  },

  /**
   * 保存联系人
   */
  async onSave() {
    console.log('保存联系人...');
    
    if (this.data.saving) {
      console.log('正在保存中，忽略重复点击');
      return;
    }
    
    
    // 验证表单
    if (!this.validateForm()) {
      wx.showToast({
        title: '请检查表单内容',
        icon: 'none'
      });
      return;
    }
    
    try {
      this.setData({ saving: true });
      
      wx.showLoading({
        title: this.data.mode === 'edit' ? '保存中...' : '创建中...',
        mask: true
      });
      
      const { formData } = this.data;
      
      // 准备提交的数据 - 安全处理字符串
      const submitData = {
        name: (formData.name || '').trim(),
        phone: (formData.phone || '').trim(),
        wechat_id: (formData.wechat_id || '').trim(),
        email: (formData.email || '').trim(),
        company: (formData.company || '').trim(),
        position: (formData.position || '').trim(),
        address: (formData.address || '').trim(),
        notes: (formData.notes || '').trim(),
        tags: formData.tags || [],
        // 新增字段
        gender: formData.gender || '未知',
        age: (formData.age || '').trim(),
        marital_status: formData.marital_status || '未知',
        education: (formData.education || '').trim(),
        asset_level: formData.asset_level || '未知',
        personality: (formData.personality || '').trim()
      };
      
      console.log('提交的数据包含标签:', submitData.tags);
      console.log('完整提交数据:', submitData);
      
      let result;
      
      if (this.data.mode === 'edit') {
        console.log('编辑模式，联系人ID:', this.data.contactId);
        result = await dataManager.updateProfile(this.data.contactId, submitData);
      } else {
        console.log('创建模式');
        result = await dataManager.createProfile(submitData);
      }
      
      // 立即隐藏加载提示
      wx.hideLoading();
      
      // 显示保存成功提示
      wx.showToast({
        title: this.data.mode === 'edit' ? '保存成功' : '创建成功',
        icon: 'success',
        duration: 1500
      });
      
      // 触发数据刷新
      if (dataManager && dataManager.emit) {
        dataManager.emit('dataChanged', { type: 'profile', action: this.data.mode });
      }
      
      // 显示意图匹配提示（可选，5秒后自动消失）
      this.setData({ showIntentMatchingHint: true });
      setTimeout(() => {
        this.setData({ showIntentMatchingHint: false });
      }, 5000);
      
      // 延迟返回，让用户看到成功提示
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
      
      console.log('联系人保存成功:', result);
    } catch (error) {
      console.error('保存联系人失败:', error);
      console.error('错误详情:', {
        message: error.message,
        stack: error.stack,
        data: error.data
      });
      
      wx.hideLoading();
      
      this.setData({ saving: false });
      
      wx.showModal({
        title: '保存失败',
        content: error.message || '请检查网络连接后重试',
        showCancel: false
      });
    }
  },

  /**
   * 取消编辑
   */
  onCancel() {
    // 检查是否有未保存的变化
    if (this.hasFormChanged()) {
      this.setData({ showCancelDialog: true });
    } else {
      wx.navigateBack();
    }
  },

  /**
   * 确认取消
   */
  onConfirmCancel() {
    this.setData({ showCancelDialog: false });
    wx.navigateBack();
  },

  /**
   * 取消取消
   */
  onCancelCancel() {
    this.setData({ showCancelDialog: false });
  },

  /**
   * 清空表单
   */
  onClearForm() {
    wx.showModal({
      title: '清空表单',
      content: '确定要清空所有表单内容吗？',
      success: (res) => {
        if (res.confirm) {
          const emptyFormData = {
            name: '',
            phone: '',
            wechat_id: '',
            email: '',
            company: '',
            position: '',
            address: '',
            notes: '',
            tags: []
          };
          
          this.setData({
            formData: emptyFormData,
            formErrors: {}
          });
          
          wx.showToast({
            title: '表单已清空',
            icon: 'success'
          });
        }
      }
    });
  },

  /**
   * 获取错误信息
   */
  getFieldError(field) {
    return this.data.formErrors[field] || '';
  },

  /**
   * 获取标签颜色主题
   */
  getTagTheme(index) {
    const themes = ['primary', 'success', 'warning', 'danger', 'default'];
    return themes[index % themes.length];
  },

  /**
   * 阻止事件冒泡
   */
  onStopPropagation() {
    // 阻止事件冒泡
  },

  /**
   * 初始化语音识别
   */
  initVoiceRecognition() {
    // 识别结束事件
    recordManager.onStop = async (res) => {
      console.log('录音停止', res);
      
      if (res.result) {
        // 显示识别结果
        wx.showToast({
          title: '识别成功，正在解析...',
          icon: 'loading',
          duration: 10000
        });
        
        this.setData({
          isRecording: false,
          isParsing: true
        });
        
        // 调用后端API解析文本
        await this.parseVoiceText(res.result);
      } else {
        wx.showToast({
          title: '未识别到内容',
          icon: 'none'
        });
        
        this.setData({
          isRecording: false
        });
      }
    };
    
    // 识别错误事件
    recordManager.onError = (res) => {
      console.error('语音识别错误', res);
      
      wx.showToast({
        title: res.msg || '识别失败',
        icon: 'none'
      });
      
      this.setData({
        isRecording: false
      });
    };
    
    // 开始录音事件
    recordManager.onStart = () => {
      console.log('开始录音');
      wx.showToast({
        title: '请说话...',
        icon: 'none',
        duration: 60000 // 持续显示
      });
    };
  },

  /**
   * 语音输入
   */
  onVoiceInput() {
    // 如果正在解析，不响应
    if (this.data.isParsing) {
      return;
    }
    
    // 如果正在录音，停止录音
    if (this.data.isRecording) {
      this.stopVoiceInput();
    } else {
      // 开始录音
      this.startVoiceInput();
    }
  },

  /**
   * 开始语音输入
   */
  startVoiceInput() {
    // 请求麦克风权限
    wx.authorize({
      scope: 'scope.record',
      success: () => {
        console.log('开始语音输入');
        
        // 提示用户如何使用
        wx.showModal({
          title: '语音输入',
          content: '请说出联系人信息，例如：“张三，男，35岁，在腾讯工作，是产品经理，住在深圳”',
          showCancel: false,
          confirmText: '开始录音',
          success: () => {
            this.setData({
              isRecording: true
            });
            
            // 开始录音识别
            recordManager.start({
              lang: 'zh_CN',
              duration: 60000 // 最长录音时间60秒
            });
          }
        });
      },
      fail: () => {
        wx.showModal({
          title: '需要授权',
          content: '请在设置中授权使用麦克风',
          confirmText: '去设置',
          success: (res) => {
            if (res.confirm) {
              wx.openSetting();
            }
          }
        });
      }
    });
  },

  /**
   * 停止语音输入
   */
  stopVoiceInput() {
    console.log('停止语音输入');
    wx.hideToast();
    recordManager.stop();
  },

  /**
   * 解析语音文本
   */
  async parseVoiceText(text) {
    try {
      console.log('解析语音文本:', text);
      
      // 调用后端API
      const result = await dataManager.parseVoiceText(text, this.data.mode === 'edit');
      
      if (!result || !result.success) {
        throw new Error(result?.message || '解析失败');
      }
      
      const parsedData = result.data;
      if (!parsedData) {
        throw new Error('未能识别出有效信息');
      }
      
      // 如果是编辑模式，合并数据
      if (this.data.mode === 'edit') {
        const mergedData = { ...this.data.formData };
        
        // 只更新非空字段
        Object.keys(parsedData).forEach(key => {
          if (parsedData[key] && parsedData[key] !== '') {
            // 如果是备注字段，追加内容
            if (key === 'notes' && mergedData.notes) {
              mergedData[key] = mergedData.notes + '\n' + parsedData[key];
            } else {
              mergedData[key] = parsedData[key];
            }
          }
        });
        
        this.setData({
          formData: mergedData,
          isParsing: false
        });
        
        wx.showToast({
          title: '信息已更新',
          icon: 'success'
        });
      } else {
        // 新增模式，直接替换
        const newFormData = {
          ...this.data.formData,
          ...parsedData
        };
        
        // 保留原有的标签
        if (this.data.formData.tags && this.data.formData.tags.length > 0) {
          newFormData.tags = this.data.formData.tags;
        }
        
        this.setData({
          formData: newFormData,
          isParsing: false
        });
        
        wx.showToast({
          title: '信息已填充',
          icon: 'success'
        });
      }
      
    } catch (error) {
      console.error('解析语音文本失败:', error);
      
      this.setData({
        isParsing: false
      });
      
      wx.showToast({
        title: error.message || '解析失败',
        icon: 'none',
        duration: 2000
      });
    }
  }
});