import { PROFILE_CONFIG } from '../../utils/constants';

Component({
  /**
   * 组件的属性列表
   */
  properties: {
    // 是否显示编辑器
    visible: {
      type: Boolean,
      value: false
    },
    // 初始个人资料数据
    initialData: {
      type: Object,
      value: {}
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    // 表单数据
    profileData: {
      displayName: '',
      nickname: '',
      avatar: 'default',
      bio: ''
    },
    // 头像选项
    avatarOptions: PROFILE_CONFIG.DEFAULT_AVATARS,
    // 当前头像颜色
    currentAvatarColor: PROFILE_CONFIG.DEFAULT_AVATARS[0].color,
    // 头像文本
    avatarText: 'U',
    // 字段长度计数
    displayNameLength: 0,
    nicknameLength: 0,
    bioLength: 0,
    // 字段长度限制
    maxDisplayNameLength: PROFILE_CONFIG.MAX_DISPLAY_NAME_LENGTH,
    maxNicknameLength: PROFILE_CONFIG.MAX_NICKNAME_LENGTH,
    maxBioLength: PROFILE_CONFIG.MAX_BIO_LENGTH,
    // 错误信息
    errors: {}
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 初始化数据
     */
    initData() {
      const initialData = this.properties.initialData || {};
      const profileData = {
        displayName: initialData.displayName || '',
        nickname: initialData.nickname || '',
        avatar: initialData.avatar || 'default',
        bio: initialData.bio || ''
      };

      // 获取当前头像颜色
      const avatarInfo = PROFILE_CONFIG.DEFAULT_AVATARS.find(a => a.id === profileData.avatar);
      const currentAvatarColor = avatarInfo ? avatarInfo.color : PROFILE_CONFIG.DEFAULT_AVATARS[0].color;

      // 获取头像文本
      const avatarText = this.getAvatarTextFromDisplayName(profileData.displayName);

      // 计算字段长度
      const displayNameLength = (profileData.displayName || '').length;
      const nicknameLength = (profileData.nickname || '').length;
      const bioLength = (profileData.bio || '').length;

      this.setData({
        profileData,
        currentAvatarColor,
        avatarText,
        displayNameLength,
        nicknameLength,
        bioLength,
        errors: {}
      });
    },

    /**
     * 获取头像文本
     */
    getAvatarTextFromDisplayName(displayName) {
      if (displayName && displayName.length > 0) {
        return displayName.charAt(0).toUpperCase();
      }
      return 'U';
    },

    /**
     * 头像选择
     */
    onAvatarSelect(e) {
      const avatarId = e.currentTarget.dataset.avatar;
      const avatarInfo = PROFILE_CONFIG.DEFAULT_AVATARS.find(a => a.id === avatarId);
      
      if (avatarInfo) {
        this.setData({
          'profileData.avatar': avatarId,
          currentAvatarColor: avatarInfo.color
        });
      }
    },

    /**
     * 显示名称输入
     */
    onDisplayNameInput(e) {
      const value = e.detail.value;
      const avatarText = this.getAvatarTextFromDisplayName(value);
      const displayNameLength = (value || '').length;
      
      this.setData({
        'profileData.displayName': value,
        avatarText: avatarText,
        displayNameLength: displayNameLength
      });
      
      // 清除错误信息
      if (this.data.errors.displayName) {
        this.setData({
          'errors.displayName': ''
        });
      }
    },

    /**
     * 显示名称失去焦点
     */
    onDisplayNameBlur(e) {
      this.validateDisplayName();
    },

    /**
     * 昵称输入
     */
    onNicknameInput(e) {
      const value = e.detail.value;
      const nicknameLength = (value || '').length;
      
      this.setData({
        'profileData.nickname': value,
        nicknameLength: nicknameLength
      });
    },

    /**
     * 个人简介输入
     */
    onBioInput(e) {
      const value = e.detail.value;
      const bioLength = (value || '').length;
      
      this.setData({
        'profileData.bio': value,
        bioLength: bioLength
      });
    },

    /**
     * 验证显示名称
     */
    validateDisplayName() {
      const displayName = this.data.profileData.displayName;
      if (!displayName || displayName.trim().length === 0) {
        this.setData({
          'errors.displayName': '显示名称不能为空'
        });
        return false;
      }
      
      if (displayName.length > this.data.maxDisplayNameLength) {
        this.setData({
          'errors.displayName': `显示名称不能超过${this.data.maxDisplayNameLength}个字符`
        });
        return false;
      }
      
      // 清除错误信息
      this.setData({
        'errors.displayName': ''
      });
      return true;
    },

    /**
     * 验证所有表单数据
     */
    validateForm() {
      let isValid = true;
      
      // 验证显示名称
      if (!this.validateDisplayName()) {
        isValid = false;
      }
      
      // 验证昵称长度
      const nickname = this.data.profileData.nickname;
      if (nickname && nickname.length > this.data.maxNicknameLength) {
        this.setData({
          'errors.nickname': `昵称不能超过${this.data.maxNicknameLength}个字符`
        });
        isValid = false;
      }
      
      // 验证个人简介长度
      const bio = this.data.profileData.bio;
      if (bio && bio.length > this.data.maxBioLength) {
        this.setData({
          'errors.bio': `个人简介不能超过${this.data.maxBioLength}个字符`
        });
        isValid = false;
      }
      
      return isValid;
    },

    /**
     * 保存
     */
    onSave() {
      if (!this.validateForm()) {
        return;
      }

      const profileData = { ...this.data.profileData };
      
      // 触发保存事件
      this.triggerEvent('save', {
        profileData
      });
    },

    /**
     * 取消
     */
    onCancel() {
      this.triggerEvent('cancel');
    },

    /**
     * 点击遮罩层
     */
    onMaskTap() {
      // 点击遮罩关闭
      this.onCancel();
    },

    /**
     * 点击内容区域（阻止冒泡）
     */
    onContentTap() {
      // 阻止事件冒泡到遮罩层
    }
  },

  /**
   * 组件生命周期
   */
  observers: {
    'visible,initialData': function(visible, initialData) {
      if (visible) {
        this.initData();
      }
    },
    // 监听显示名称变化，实时更新头像文字
    'profileData.displayName': function(displayName) {
      const avatarText = this.getAvatarTextFromDisplayName(displayName);
      if (this.data.avatarText !== avatarText) {
        this.setData({ avatarText });
      }
    }
  }
});