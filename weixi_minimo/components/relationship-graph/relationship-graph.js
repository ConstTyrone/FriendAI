import GraphDataProcessor from '../../utils/graph-data-processor';

Component({
  properties: {
    // 关系数据
    relationships: {
      type: Array,
      value: []
    },
    
    // 联系人数据
    profiles: {
      type: Array,
      value: []
    },
    
    // 中心节点ID
    centerNodeId: {
      type: Number,
      value: null
    },
    
    // 组件宽度高度
    width: {
      type: Number,
      value: 350
    },
    
    height: {
      type: Number,
      value: 400
    }
  },
  
  data: {
    // 画布尺寸
    canvasWidth: 350,
    canvasHeight: 400,
    
    // 图谱数据
    graphData: {
      nodes: [],
      links: [],
      stats: {}
    },
    
    // 显示设置
    showStats: true,
    showLegend: true,
    showNodeDetail: false,
    showLinkDetail: false,
    showSettings: false,
    
    // 布局设置
    layoutType: 'circle',
    minConfidence: 0.3,
    maxDepth: 2,
    
    // 交互状态
    loading: false,
    selectedNode: null,
    selectedLink: null,
    
    // 画布状态
    scale: 1,
    translateX: 0,
    translateY: 0,
    
    // 触摸状态
    lastTouchX: 0,
    lastTouchY: 0,
    touching: false,
    multiTouch: false
  },
  
  lifetimes: {
    attached() {
      this.initCanvas();
      this.setData({
        canvasWidth: this.data.width,
        canvasHeight: this.data.height
      });
    },
    
    ready() {
      this.processGraphData();
    }
  },
  
  observers: {
    'relationships, profiles, centerNodeId': function() {
      this.processGraphData();
    }
  },
  
  methods: {
    /**
     * 初始化画布
     */
    initCanvas() {
      const query = this.createSelectorQuery();
      query.select('.graph-canvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          if (res[0]) {
            const canvas = res[0].node;
            const ctx = canvas.getContext('2d');
            this.canvas = canvas;
            this.ctx = ctx;
            
            // 设置画布尺寸
            const dpr = wx.getSystemInfoSync().pixelRatio;
            canvas.width = this.data.canvasWidth * dpr;
            canvas.height = this.data.canvasHeight * dpr;
            ctx.scale(dpr, dpr);
          }
        });
    },
    
    /**
     * 处理图谱数据
     */
    processGraphData() {
      if (!this.data.relationships || !this.data.profiles) {
        return;
      }
      
      this.setData({ loading: true });
      
      // 使用图谱数据处理器处理数据
      const graphData = GraphDataProcessor.processRelationshipData(
        this.data.relationships,
        this.data.profiles,
        {
          centerNodeId: this.data.centerNodeId,
          maxDepth: this.data.maxDepth,
          minConfidence: this.data.minConfidence
        }
      );
      
      // 计算布局
      const layoutData = GraphDataProcessor.calculateLayout(
        graphData.nodes,
        graphData.links,
        {
          width: this.data.canvasWidth,
          height: this.data.canvasHeight,
          layoutType: this.data.layoutType
        }
      );
      
      this.setData({
        graphData: {
          ...graphData,
          nodes: layoutData.nodes,
          links: layoutData.links
        },
        loading: false
      }, () => {
        this.renderGraph();
      });
    },
    
    /**
     * 渲染图谱
     */
    renderGraph() {
      if (!this.ctx || this.data.loading) return;
      
      const ctx = this.ctx;
      const { nodes, links } = this.data.graphData;
      const { scale, translateX, translateY } = this.data;
      
      // 清空画布
      ctx.clearRect(0, 0, this.data.canvasWidth, this.data.canvasHeight);
      
      // 应用变换
      ctx.save();
      ctx.translate(translateX, translateY);
      ctx.scale(scale, scale);
      
      // 绘制连接线
      links.forEach(link => {
        this.drawLink(ctx, link, nodes);
      });
      
      // 绘制节点
      nodes.forEach(node => {
        this.drawNode(ctx, node);
      });
      
      ctx.restore();
    },
    
    /**
     * 绘制节点
     */
    drawNode(ctx, node) {
      const { x, y, name, size, color, level } = node;
      
      // 节点大小
      const radius = size === 'large' ? 25 : 18;
      
      // 绘制节点圆圈
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = level === 0 ? '#1976d2' : '#fff';
      ctx.lineWidth = level === 0 ? 3 : 2;
      ctx.stroke();
      
      // 绘制节点文字
      ctx.fillStyle = '#fff';
      ctx.font = size === 'large' ? 'bold 12px sans-serif' : '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      // 绘制姓名首字母
      const initial = name ? name.charAt(0) : '?';
      ctx.fillText(initial, x, y);
      
      // 绘制姓名标签
      if (size === 'large' || this.data.scale > 1.2) {
        ctx.fillStyle = '#333';
        ctx.font = '11px sans-serif';
        ctx.fillText(name, x, y + radius + 15);
      }
    },
    
    /**
     * 绘制连接线
     */
    drawLink(ctx, link, nodes) {
      const sourceNode = nodes.find(n => n.id === link.source);
      const targetNode = nodes.find(n => n.id === link.target);
      
      if (!sourceNode || !targetNode) return;
      
      const { x1, y1 } = { x1: sourceNode.x, y1: sourceNode.y };
      const { x2, y2 } = { x2: targetNode.x, y2: targetNode.y };
      
      // 设置线条样式
      ctx.strokeStyle = link.color;
      ctx.lineWidth = link.width;
      
      if (link.style === 'dashed') {
        ctx.setLineDash([5, 5]);
      } else {
        ctx.setLineDash([]);
      }
      
      // 绘制连接线
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      
      // 绘制方向箭头（如果不是双向关系）
      if (link.direction !== 'bidirectional') {
        this.drawArrow(ctx, x1, y1, x2, y2, link.color);
      }
    },
    
    /**
     * 绘制箭头
     */
    drawArrow(ctx, x1, y1, x2, y2, color) {
      const angle = Math.atan2(y2 - y1, x2 - x1);
      const headLength = 10;
      
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(x2 - headLength * Math.cos(angle - Math.PI / 6), 
                 y2 - headLength * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(x2, y2);
      ctx.lineTo(x2 - headLength * Math.cos(angle + Math.PI / 6), 
                 y2 - headLength * Math.sin(angle + Math.PI / 6));
      ctx.fill();
    },
    
    /**
     * 触摸开始
     */
    onTouchStart(e) {
      const touch = e.touches[0];
      this.setData({
        lastTouchX: touch.x,
        lastTouchY: touch.y,
        touching: true,
        multiTouch: e.touches.length > 1
      });
    },
    
    /**
     * 触摸移动
     */
    onTouchMove(e) {
      if (!this.data.touching) return;
      
      const touch = e.touches[0];
      const deltaX = touch.x - this.data.lastTouchX;
      const deltaY = touch.y - this.data.lastTouchY;
      
      if (this.data.multiTouch && e.touches.length > 1) {
        // 双指缩放
        this.handlePinchZoom(e.touches);
      } else {
        // 单指拖拽
        this.setData({
          translateX: this.data.translateX + deltaX,
          translateY: this.data.translateY + deltaY,
          lastTouchX: touch.x,
          lastTouchY: touch.y
        }, () => {
          this.renderGraph();
        });
      }
    },
    
    /**
     * 触摸结束
     */
    onTouchEnd(e) {
      this.setData({
        touching: false,
        multiTouch: false
      });
    },
    
    /**
     * 画布点击
     */
    onCanvasTap(e) {
      const { x, y } = e.detail;
      const hitNode = this.hitTestNode(x, y);
      const hitLink = this.hitTestLink(x, y);
      
      if (hitNode) {
        this.setData({
          selectedNode: hitNode,
          showNodeDetail: true
        });
      } else if (hitLink) {
        this.setData({
          selectedLink: hitLink,
          showLinkDetail: true
        });
      }
    },
    
    /**
     * 节点命中测试
     */
    hitTestNode(x, y) {
      const { nodes } = this.data.graphData;
      const { scale, translateX, translateY } = this.data;
      
      // 转换坐标
      const canvasX = (x - translateX) / scale;
      const canvasY = (y - translateY) / scale;
      
      return nodes.find(node => {
        const radius = node.size === 'large' ? 25 : 18;
        const distance = Math.sqrt(
          Math.pow(canvasX - node.x, 2) + Math.pow(canvasY - node.y, 2)
        );
        return distance <= radius;
      });
    },
    
    /**
     * 连接线命中测试
     */
    hitTestLink(x, y) {
      const { links } = this.data.graphData;
      const { nodes } = this.data.graphData;
      const { scale, translateX, translateY } = this.data;
      
      // 转换坐标
      const canvasX = (x - translateX) / scale;
      const canvasY = (y - translateY) / scale;
      
      return links.find(link => {
        const sourceNode = nodes.find(n => n.id === link.source);
        const targetNode = nodes.find(n => n.id === link.target);
        
        if (!sourceNode || !targetNode) return false;
        
        // 计算点到线段的距离
        const distance = this.pointToLineDistance(
          canvasX, canvasY,
          sourceNode.x, sourceNode.y,
          targetNode.x, targetNode.y
        );
        
        return distance <= (link.width * 2 + 5);
      });
    },
    
    /**
     * 计算点到线段的距离
     */
    pointToLineDistance(px, py, x1, y1, x2, y2) {
      const dx = x2 - x1;
      const dy = y2 - y1;
      const length = Math.sqrt(dx * dx + dy * dy);
      
      if (length === 0) return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2);
      
      const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / (length * length)));
      const projection = { x: x1 + t * dx, y: y1 + t * dy };
      
      return Math.sqrt((px - projection.x) ** 2 + (py - projection.y) ** 2);
    },
    
    /**
     * 处理双指缩放
     */
    handlePinchZoom(touches) {
      if (touches.length !== 2) return;
      
      const touch1 = touches[0];
      const touch2 = touches[1];
      
      const currentDistance = Math.sqrt(
        Math.pow(touch2.x - touch1.x, 2) + Math.pow(touch2.y - touch1.y, 2)
      );
      
      if (this.lastPinchDistance) {
        const scaleChange = currentDistance / this.lastPinchDistance;
        const newScale = Math.max(0.5, Math.min(3, this.data.scale * scaleChange));
        
        this.setData({
          scale: newScale
        }, () => {
          this.renderGraph();
        });
      }
      
      this.lastPinchDistance = currentDistance;
    },
    
    /**
     * 刷新图谱
     */
    onRefresh() {
      this.processGraphData();
    },
    
    /**
     * 放大
     */
    onZoomIn() {
      const newScale = Math.min(3, this.data.scale * 1.2);
      this.setData({ scale: newScale }, () => {
        this.renderGraph();
      });
    },
    
    /**
     * 缩小
     */
    onZoomOut() {
      const newScale = Math.max(0.5, this.data.scale / 1.2);
      this.setData({ scale: newScale }, () => {
        this.renderGraph();
      });
    },
    
    /**
     * 全屏显示
     */
    onFullscreen() {
      this.triggerEvent('fullscreen');
    },
    
    /**
     * 打开设置
     */
    onOpenSettings() {
      this.setData({ showSettings: true });
    },
    
    /**
     * 关闭设置
     */
    onSettingsClose() {
      this.setData({ showSettings: false });
    },
    
    /**
     * 显示统计信息改变
     */
    onShowStatsChange(e) {
      this.setData({ showStats: e.detail.value });
    },
    
    /**
     * 显示图例改变
     */
    onShowLegendChange(e) {
      this.setData({ showLegend: e.detail.value });
    },
    
    /**
     * 布局类型改变
     */
    onLayoutTypeChange(e) {
      this.setData({ layoutType: e.detail.value }, () => {
        this.processGraphData();
      });
    },
    
    /**
     * 最小置信度改变
     */
    onMinConfidenceChange(e) {
      this.setData({ minConfidence: e.detail.value / 100 }, () => {
        this.processGraphData();
      });
    },
    
    /**
     * 最大层级改变
     */
    onMaxDepthChange(e) {
      this.setData({ maxDepth: e.detail.value }, () => {
        this.processGraphData();
      });
    },
    
    /**
     * 关闭节点详情
     */
    onNodeDetailClose() {
      this.setData({ 
        showNodeDetail: false,
        selectedNode: null 
      });
    },
    
    /**
     * 关闭关系详情
     */
    onLinkDetailClose() {
      this.setData({ 
        showLinkDetail: false,
        selectedLink: null 
      });
    },
    
    /**
     * 查看节点详情
     */
    onViewNodeDetail() {
      const nodeId = this.data.selectedNode.id;
      this.triggerEvent('nodeDetail', { nodeId });
      this.onNodeDetailClose();
    },
    
    /**
     * 设为中心节点
     */
    onSetAsCenter() {
      const nodeId = this.data.selectedNode.id;
      this.triggerEvent('centerChange', { centerNodeId: nodeId });
      this.onNodeDetailClose();
    },
    
    /**
     * 确认关系
     */
    onConfirmLink() {
      const relationshipId = this.data.selectedLink.relationshipId;
      this.triggerEvent('confirmRelationship', { relationshipId });
      this.onLinkDetailClose();
    },
    
    /**
     * 忽略关系
     */
    onIgnoreLink() {
      const relationshipId = this.data.selectedLink.relationshipId;
      this.triggerEvent('ignoreRelationship', { relationshipId });
      this.onLinkDetailClose();
    },
    
    /**
     * 获取连接颜色
     */
    getLinkColor(type) {
      return GraphDataProcessor.getLinkColor(type);
    },
    
    /**
     * 获取关系类型名称
     */
    getRelationshipTypeName(type) {
      const typeNames = {
        'colleague': '同事',
        'friend': '朋友',
        'family': '家人',
        'partner': '合作伙伴',
        'client': '客户',
        'supplier': '供应商',
        'alumni': '校友',
        'neighbor': '邻居',
        'same_location': '同地区',
        'competitor': '竞争对手',
        'investor': '投资人'
      };
      
      return typeNames[type] || type;
    },
    
    /**
     * 获取关系强度名称
     */
    getRelationshipStrengthName(strength) {
      const strengthNames = {
        'strong': '强关系',
        'medium': '中等关系',
        'weak': '弱关系'
      };
      
      return strengthNames[strength] || strength;
    },
    
    /**
     * 获取连接源节点名称
     */
    getLinkSourceName(link) {
      const sourceNode = this.data.graphData.nodes.find(n => n.id === link.source);
      return sourceNode ? sourceNode.name : '未知';
    },
    
    /**
     * 获取连接目标节点名称
     */
    getLinkTargetName(link) {
      const targetNode = this.data.graphData.nodes.find(n => n.id === link.target);
      return targetNode ? targetNode.name : '未知';
    },
    
    /**
     * 格式化置信度
     */
    formatConfidence(confidence) {
      return (confidence * 100).toFixed(1);
    },
    
    /**
     * 格式化最小置信度
     */
    formatMinConfidence(minConfidence) {
      return (minConfidence * 100).toFixed(0);
    }
  }
});