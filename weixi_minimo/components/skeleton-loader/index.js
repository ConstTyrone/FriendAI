Component({
  properties: {
    // 骨架屏类型
    type: {
      type: String,
      value: 'list' // list, card, detail
    },
    // 显示的项目数
    count: {
      type: Number,
      value: 3
    },
    // 是否显示骨架屏
    loading: {
      type: Boolean,
      value: true
    },
    // 动画类型
    animation: {
      type: String,
      value: 'wave' // wave, pulse, none
    }
  },

  data: {
    items: []
  },

  lifetimes: {
    attached() {
      this.initSkeleton();
    }
  },

  methods: {
    initSkeleton() {
      const items = [];
      for (let i = 0; i < this.properties.count; i++) {
        items.push({
          id: `skeleton-${i}`,
          index: i
        });
      }
      this.setData({ items });
    }
  },

  observers: {
    'count': function(count) {
      this.initSkeleton();
    }
  }
});