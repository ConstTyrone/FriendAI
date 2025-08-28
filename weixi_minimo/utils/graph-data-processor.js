/**
 * 关系图谱数据处理器
 * 将关系数据转换为图形可视化所需的节点和边数据
 */

class GraphDataProcessor {
  /**
   * 将关系数据转换为图谱数据
   * @param {Array} relationships - 关系数据数组
   * @param {Array} profiles - 联系人数据数组  
   * @param {Object} options - 配置选项
   * @returns {Object} 包含nodes和links的图谱数据
   */
  static processRelationshipData(relationships, profiles, options = {}) {
    const {
      centerNodeId = null,           // 中心节点ID
      maxDepth = 2,                  // 最大展示层级
      includeWeakLinks = true,       // 是否包含弱关系
      minConfidence = 0.3           // 最小置信度阈值
    } = options;
    
    // 创建节点映射
    const nodeMap = new Map();
    const linkMap = new Map();
    
    // 处理联系人节点
    profiles.forEach(profile => {
      nodeMap.set(profile.id, {
        id: profile.id,
        name: profile.profile_name || profile.name,
        type: 'contact',
        avatar: profile.avatar || '',
        company: profile.company || '未知',
        position: profile.position || '',
        tags: profile.tags || [],
        
        // 视觉属性
        size: centerNodeId === profile.id ? 'large' : 'medium',
        color: this.getNodeColor(profile),
        level: centerNodeId === profile.id ? 0 : 1,
        
        // 统计信息
        relationshipCount: 0,
        strongRelationshipCount: 0
      });
    });
    
    // 处理关系连接
    relationships.forEach(rel => {
      const confidence = rel.confidence_score || 0;
      
      // 跳过低置信度关系
      if (confidence < minConfidence) return;
      
      const sourceNode = nodeMap.get(rel.source_profile_id);
      const targetNode = nodeMap.get(rel.target_profile_id);
      
      if (!sourceNode || !targetNode) return;
      
      // 创建连接
      const linkId = `${rel.source_profile_id}-${rel.target_profile_id}`;
      const link = {
        id: linkId,
        relationshipId: rel.id,
        source: rel.source_profile_id,
        target: rel.target_profile_id,
        
        // 关系信息
        type: rel.relationship_type,
        subtype: rel.relationship_subtype || '',
        direction: rel.relationship_direction || 'bidirectional',
        confidence: confidence,
        strength: rel.relationship_strength || 'medium',
        
        // 证据信息
        evidence: rel.evidence || {},
        matchedFields: rel.evidence_fields ? rel.evidence_fields.split(',') : [],
        
        // 视觉属性
        width: this.getLinkWidth(rel.relationship_strength),
        color: this.getLinkColor(rel.relationship_type),
        style: confidence > 0.7 ? 'solid' : 'dashed',
        
        // 状态
        status: rel.status || 'discovered',
        confirmed: rel.status === 'confirmed'
      };
      
      linkMap.set(linkId, link);
      
      // 更新节点统计
      sourceNode.relationshipCount++;
      targetNode.relationshipCount++;
      
      if (confidence > 0.7) {
        sourceNode.strongRelationshipCount++;
        targetNode.strongRelationshipCount++;
      }
    });
    
    // 计算节点层级（基于中心节点的距离）
    if (centerNodeId) {
      this.calculateNodeLevels(nodeMap, linkMap, centerNodeId, maxDepth);
    }
    
    // 过滤节点和连接
    const nodes = Array.from(nodeMap.values())
      .filter(node => node.level <= maxDepth)
      .sort((a, b) => a.level - b.level || b.strongRelationshipCount - a.strongRelationshipCount);
    
    const links = Array.from(linkMap.values())
      .filter(link => {
        const sourceNode = nodeMap.get(link.source);
        const targetNode = nodeMap.get(link.target);
        return sourceNode && targetNode && 
               sourceNode.level <= maxDepth && 
               targetNode.level <= maxDepth;
      });
    
    return {
      nodes,
      links,
      stats: {
        totalNodes: nodes.length,
        totalLinks: links.length,
        confirmedLinks: links.filter(l => l.confirmed).length,
        strongLinks: links.filter(l => l.confidence > 0.7).length,
        relationshipTypes: this.getRelationshipTypeStats(links)
      }
    };
  }
  
  /**
   * 计算节点层级（BFS算法）
   */
  static calculateNodeLevels(nodeMap, linkMap, centerNodeId, maxDepth) {
    const queue = [{ nodeId: centerNodeId, level: 0 }];
    const visited = new Set([centerNodeId]);
    
    // 构建邻接表
    const adjacencyList = new Map();
    linkMap.forEach(link => {
      if (!adjacencyList.has(link.source)) adjacencyList.set(link.source, []);
      if (!adjacencyList.has(link.target)) adjacencyList.set(link.target, []);
      
      adjacencyList.get(link.source).push(link.target);
      adjacencyList.get(link.target).push(link.source);
    });
    
    while (queue.length > 0) {
      const { nodeId, level } = queue.shift();
      const node = nodeMap.get(nodeId);
      if (node) node.level = level;
      
      if (level < maxDepth) {
        const neighbors = adjacencyList.get(nodeId) || [];
        neighbors.forEach(neighborId => {
          if (!visited.has(neighborId)) {
            visited.add(neighborId);
            queue.push({ nodeId: neighborId, level: level + 1 });
          }
        });
      }
    }
  }
  
  /**
   * 获取节点颜色
   */
  static getNodeColor(profile) {
    // 基于公司或标签确定颜色
    if (profile.company && profile.company !== '未知') {
      return this.hashStringToColor(profile.company);
    }
    
    if (profile.tags && profile.tags.length > 0) {
      return this.hashStringToColor(profile.tags[0]);
    }
    
    return '#7c7c7c'; // 默认灰色
  }
  
  /**
   * 获取连接颜色
   */
  static getLinkColor(relationshipType) {
    const colorMap = {
      'colleague': '#4CAF50',      // 绿色 - 同事
      'friend': '#2196F3',         // 蓝色 - 朋友  
      'family': '#FF5722',         // 红色 - 家人
      'partner': '#FF9800',        // 橙色 - 合作伙伴
      'client': '#9C27B0',         // 紫色 - 客户
      'supplier': '#795548',       // 棕色 - 供应商
      'alumni': '#607D8B',         // 青灰色 - 校友
      'neighbor': '#FFC107',       // 黄色 - 邻居
      'same_location': '#E91E63',  // 粉色 - 同地区
      'competitor': '#F44336',     // 深红色 - 竞争对手
      'investor': '#3F51B5'        // 靛蓝色 - 投资人
    };
    
    return colorMap[relationshipType] || '#9E9E9E';
  }
  
  /**
   * 获取连接宽度
   */
  static getLinkWidth(strength) {
    const widthMap = {
      'strong': 3,
      'medium': 2, 
      'weak': 1
    };
    
    return widthMap[strength] || 2;
  }
  
  /**
   * 字符串哈希到颜色
   */
  static hashStringToColor(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    const hue = Math.abs(hash) % 360;
    return `hsl(${hue}, 65%, 55%)`;
  }
  
  /**
   * 获取关系类型统计
   */
  static getRelationshipTypeStats(links) {
    const stats = {};
    links.forEach(link => {
      const type = link.type;
      stats[type] = (stats[type] || 0) + 1;
    });
    
    return Object.entries(stats)
      .sort(([,a], [,b]) => b - a)
      .map(([type, count]) => ({ type, count }));
  }
  
  /**
   * 计算图谱布局位置
   * @param {Array} nodes - 节点数组
   * @param {Array} links - 连接数组
   * @param {Object} options - 布局选项
   * @returns {Object} 包含位置信息的节点和连接
   */
  static calculateLayout(nodes, links, options = {}) {
    const {
      width = 300,
      height = 300,
      centerX = width / 2,
      centerY = height / 2,
      layoutType = 'circle'  // circle, force, radial
    } = options;
    
    switch (layoutType) {
      case 'circle':
        return this.circleLayout(nodes, links, { width, height, centerX, centerY });
      case 'radial':
        return this.radialLayout(nodes, links, { width, height, centerX, centerY });
      case 'force':
        return this.forceLayout(nodes, links, { width, height, centerX, centerY });
      default:
        return this.circleLayout(nodes, links, { width, height, centerX, centerY });
    }
  }
  
  /**
   * 环形布局
   */
  static circleLayout(nodes, links, { width, height, centerX, centerY }) {
    const centerNode = nodes.find(n => n.level === 0);
    const otherNodes = nodes.filter(n => n.level > 0);
    
    // 中心节点
    if (centerNode) {
      centerNode.x = centerX;
      centerNode.y = centerY;
    }
    
    // 其他节点按层级环形分布
    const layers = {};
    otherNodes.forEach(node => {
      if (!layers[node.level]) layers[node.level] = [];
      layers[node.level].push(node);
    });
    
    Object.entries(layers).forEach(([level, levelNodes]) => {
      const radius = Math.min(width, height) * 0.2 * level;
      const angleStep = (2 * Math.PI) / levelNodes.length;
      
      levelNodes.forEach((node, index) => {
        const angle = angleStep * index;
        node.x = centerX + radius * Math.cos(angle);
        node.y = centerY + radius * Math.sin(angle);
      });
    });
    
    return { nodes, links };
  }
  
  /**
   * 径向布局
   */
  static radialLayout(nodes, links, { width, height, centerX, centerY }) {
    // 类似环形布局，但考虑连接密度
    return this.circleLayout(nodes, links, { width, height, centerX, centerY });
  }
  
  /**
   * 力导向布局（简化版）
   */
  static forceLayout(nodes, links, { width, height, centerX, centerY }) {
    // 初始随机位置
    nodes.forEach(node => {
      if (node.level === 0) {
        node.x = centerX;
        node.y = centerY;
      } else {
        node.x = Math.random() * width;
        node.y = Math.random() * height;
      }
    });
    
    // 简单的力导向调整（可以后续优化）
    return { nodes, links };
  }
}

export default GraphDataProcessor;