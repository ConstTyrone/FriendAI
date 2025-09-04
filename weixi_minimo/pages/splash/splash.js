// 启动页面
const authManager = require('../../utils/auth-manager');

Page({
  data: {
    animationRunning: true,
    logoAnimation: null,
    textAnimation: null,
    backgroundAnimation: null,
    progress: 0,
    showProgress: false,
    loadingText: '初始化中...',
    particles: []
  },

  onLoad() {
    this.initAnimations();
    this.generateParticles();
    this.startLoadingSequence();
  },

  // 初始化动画对象
  initAnimations() {
    // Logo动画
    const logoAnimation = wx.createAnimation({
      duration: 1000,
      timingFunction: 'ease-out'
    });
    
    // 文字动画
    const textAnimation = wx.createAnimation({
      duration: 800,
      timingFunction: 'ease-out'
    });

    // 背景动画
    const backgroundAnimation = wx.createAnimation({
      duration: 2000,
      timingFunction: 'ease-in-out'
    });

    this.setData({
      logoAnimation: logoAnimation.export(),
      textAnimation: textAnimation.export(),
      backgroundAnimation: backgroundAnimation.export()
    });
  },

  // 生成粒子动画
  generateParticles() {
    const particles = [];
    for (let i = 0; i < 20; i++) {
      particles.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 6 + 2,
        duration: Math.random() * 3 + 2,
        delay: Math.random() * 2
      });
    }
    this.setData({ particles });
  },

  // 开始加载序列
  async startLoadingSequence() {
    try {
      // 第一阶段：Logo淡入和缩放
      setTimeout(() => {
        this.playLogoAnimation();
      }, 300);

      // 第二阶段：标题文字淡入
      setTimeout(() => {
        this.playTextAnimation();
      }, 800);

      // 第三阶段：显示进度条
      setTimeout(() => {
        this.setData({ 
          showProgress: true,
          loadingText: '正在加载...' 
        });
        this.simulateLoading();
      }, 1500);

      // 第四阶段：检查登录状态
      setTimeout(async () => {
        await this.checkAuthAndNavigate();
      }, 3000);

    } catch (error) {
      console.error('启动序列失败:', error);
      this.navigateToMain();
    }
  },

  // Logo动画
  playLogoAnimation() {
    const animation = wx.createAnimation({
      duration: 1000,
      timingFunction: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'
    });

    animation.scale(1).opacity(1).translateY(0).step();
    
    this.setData({
      logoAnimation: animation.export()
    });
  },

  // 文字动画
  playTextAnimation() {
    const animation = wx.createAnimation({
      duration: 800,
      timingFunction: 'ease-out',
      delay: 100
    });

    animation.opacity(1).translateY(0).step();
    
    this.setData({
      textAnimation: animation.export()
    });
  },

  // 模拟加载过程
  simulateLoading() {
    const steps = [
      { progress: 20, text: '正在初始化...' },
      { progress: 50, text: '正在加载资源...' },
      { progress: 80, text: '正在检查更新...' },
      { progress: 100, text: '准备就绪' }
    ];

    let currentStep = 0;

    const updateProgress = () => {
      if (currentStep < steps.length) {
        const step = steps[currentStep];
        this.setData({
          progress: step.progress,
          loadingText: step.text
        });
        
        currentStep++;
        setTimeout(updateProgress, 400);
      }
    };

    updateProgress();
  },

  // 检查登录状态并导航
  async checkAuthAndNavigate() {
    try {
      this.setData({ loadingText: '正在验证身份...' });
      
      const isLoggedIn = await authManager.checkAutoLogin();
      
      // 添加退出动画
      setTimeout(() => {
        this.playExitAnimation(() => {
          if (isLoggedIn) {
            // 已登录，跳转到联系人列表
            wx.reLaunch({
              url: '/pages/contact-list/contact-list'
            });
          } else {
            // 未登录，跳转到设置页面
            wx.reLaunch({
              url: '/pages/settings/settings'
            });
          }
        });
      }, 500);

    } catch (error) {
      console.error('登录检查失败:', error);
      this.navigateToMain();
    }
  },

  // 退出动画
  playExitAnimation(callback) {
    const logoAnimation = wx.createAnimation({
      duration: 600,
      timingFunction: 'ease-in'
    });

    const textAnimation = wx.createAnimation({
      duration: 400,
      timingFunction: 'ease-in'
    });

    // Logo缩小淡出
    logoAnimation.scale(0.8).opacity(0).step();
    textAnimation.opacity(0).translateY(-20).step();

    this.setData({
      logoAnimation: logoAnimation.export(),
      textAnimation: textAnimation.export()
    });

    setTimeout(callback, 600);
  },

  // 直接导航到主页面（fallback）
  navigateToMain() {
    wx.reLaunch({
      url: '/pages/settings/settings'
    });
  },

  // 点击跳过
  onSkip() {
    if (!this.data.animationRunning) return;
    
    this.setData({ animationRunning: false });
    this.navigateToMain();
  }
});