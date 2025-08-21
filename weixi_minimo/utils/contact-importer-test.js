/**
 * 联系人导入功能测试工具
 * 用于模拟和测试批量导入功能的各种场景
 */
import contactImporter from './contact-importer';

class ContactImporterTester {
  constructor() {
    this.testResults = [];
    this.mockContacts = [
      { name: '张三', phone: '13800138001' },
      { name: '李四', phone: '13800138002' },
      { name: '王五', phone: '13800138003' },
      { name: '赵六', phone: '13800138004' },
      { name: '钱七', phone: '13800138005' },
      { name: '无效联系人', phone: '' }, // 测试无效数据
      { name: '', phone: '13800138006' }, // 测试无效姓名
      { name: '重复联系人', phone: '13800138001' }, // 测试重复检测
    ];
  }

  /**
   * 运行所有测试
   */
  async runAllTests() {
    console.log('🧪 开始运行联系人导入测试...');
    
    try {
      await this.testDataValidation();
      await this.testDataSanitization();
      await this.testDuplicateDetection();
      await this.testPerformanceStats();
      await this.testBatchProcessing();
      
      this.printTestResults();
      
    } catch (error) {
      console.error('❌ 测试运行失败:', error);
    }
  }

  /**
   * 测试数据验证功能
   */
  async testDataValidation() {
    console.log('\n📋 测试数据验证功能...');
    
    const testCases = [
      { contact: { name: '张三', phone: '13800138001' }, shouldPass: true },
      { contact: { name: '', phone: '13800138001' }, shouldPass: false },
      { contact: { name: '李四', phone: '123' }, shouldPass: false },
      { contact: { name: '王五', phone: '13800138003' }, shouldPass: true },
    ];
    
    for (const testCase of testCases) {
      const validation = contactImporter.validateContactData(testCase.contact);
      const passed = validation.isValid === testCase.shouldPass;
      
      this.addTestResult('数据验证', {
        input: testCase.contact,
        expected: testCase.shouldPass,
        actual: validation.isValid,
        passed,
        errors: validation.errors
      });
      
      console.log(passed ? '✅' : '❌', `${testCase.contact.name || '空姓名'} - ${passed ? '通过' : '失败'}`);
    }
  }

  /**
   * 测试数据清理功能
   */
  async testDataSanitization() {
    console.log('\n🧹 测试数据清理功能...');
    
    const testCases = [
      { 
        input: { name: '  张三  ', phone: '138-0013-8001', company: '  ABC公司  ' },
        expected: { name: '张三', phone: '138-0013-8001', company: 'ABC公司' }
      },
      {
        input: { name: '李四' + 'x'.repeat(60), phone: '13800138002' },
        expected: { name: '李四' + 'x'.repeat(46), phone: '13800138002' } // 截断到50字符
      }
    ];
    
    for (const testCase of testCases) {
      const sanitized = contactImporter.sanitizeContactData(testCase.input);
      const passed = sanitized.name === testCase.expected.name && 
                    sanitized.phone === testCase.expected.phone;
      
      this.addTestResult('数据清理', {
        input: testCase.input,
        expected: testCase.expected,
        actual: sanitized,
        passed
      });
      
      console.log(passed ? '✅' : '❌', `数据清理 - ${passed ? '通过' : '失败'}`);
    }
  }

  /**
   * 测试重复检测功能
   */
  async testDuplicateDetection() {
    console.log('\n🔍 测试重复检测功能...');
    
    // 模拟现有联系人数据
    const mockExistingContacts = [
      { phone: '13800138001', profile_name: '张三' },
      { phone: '138-0013-8002', profile_name: '李四' }
    ];
    
    // 临时设置现有联系人数据
    const originalContacts = contactImporter.dataManager?.contacts;
    if (contactImporter.dataManager) {
      contactImporter.dataManager.contacts = mockExistingContacts;
    }
    
    const testCases = [
      { contact: { name: '张三新', phone: '13800138001' }, shouldBeDuplicate: true },
      { contact: { name: '王五', phone: '13800138005' }, shouldBeDuplicate: false },
      { contact: { name: '李四新', phone: '138 0013 8002' }, shouldBeDuplicate: true },
    ];
    
    for (const testCase of testCases) {
      const duplicateCheck = await contactImporter.checkDuplicate(testCase.contact);
      const passed = duplicateCheck.isDuplicate === testCase.shouldBeDuplicate;
      
      this.addTestResult('重复检测', {
        input: testCase.contact,
        expected: testCase.shouldBeDuplicate,
        actual: duplicateCheck.isDuplicate,
        passed
      });
      
      console.log(passed ? '✅' : '❌', `${testCase.contact.name} - ${passed ? '通过' : '失败'}`);
    }
    
    // 恢复原始数据
    if (contactImporter.dataManager && originalContacts) {
      contactImporter.dataManager.contacts = originalContacts;
    }
  }

  /**
   * 测试性能统计功能
   */
  async testPerformanceStats() {
    console.log('\n📊 测试性能统计功能...');
    
    // 模拟导入过程
    contactImporter.importStartTime = Date.now() - 5000; // 5秒前开始
    contactImporter.importEndTime = Date.now();
    contactImporter.importStats = {
      total: 10,
      success: 8,
      errors: 1,
      duplicates: 1
    };
    
    const perfStats = contactImporter.getPerformanceStats();
    
    const expectedSuccessRate = 80; // 8/10 * 100
    const passed = Math.abs(perfStats.successRate - expectedSuccessRate) < 1;
    
    this.addTestResult('性能统计', {
      expected: { successRate: expectedSuccessRate },
      actual: perfStats,
      passed
    });
    
    console.log(passed ? '✅' : '❌', `性能统计 - ${passed ? '通过' : '失败'}`);
    console.log('统计数据:', perfStats);
  }

  /**
   * 测试批量处理功能
   */
  async testBatchProcessing() {
    console.log('\n⚡ 测试批量处理功能...');
    
    const testArray = Array.from({ length: 13 }, (_, i) => ({ id: i + 1 }));
    const chunks = contactImporter.chunkArray(testArray, 5);
    
    const expectedChunks = 3; // 13个元素，每批5个，应该是3批
    const passed = chunks.length === expectedChunks && 
                   chunks[0].length === 5 && 
                   chunks[1].length === 5 && 
                   chunks[2].length === 3;
    
    this.addTestResult('批量处理', {
      input: `${testArray.length}个元素，批大小5`,
      expected: `${expectedChunks}批`,
      actual: `${chunks.length}批`,
      passed
    });
    
    console.log(passed ? '✅' : '❌', `批量分组 - ${passed ? '通过' : '失败'}`);
  }

  /**
   * 添加测试结果
   */
  addTestResult(testName, result) {
    this.testResults.push({
      testName,
      timestamp: new Date().toISOString(),
      ...result
    });
  }

  /**
   * 打印测试结果
   */
  printTestResults() {
    console.log('\n📋 测试结果汇总:');
    console.log('==================');
    
    const totalTests = this.testResults.length;
    const passedTests = this.testResults.filter(r => r.passed).length;
    const failedTests = totalTests - passedTests;
    
    console.log(`总测试数: ${totalTests}`);
    console.log(`通过: ${passedTests} ✅`);
    console.log(`失败: ${failedTests} ❌`);
    console.log(`成功率: ${((passedTests / totalTests) * 100).toFixed(1)}%`);
    
    // 显示失败的测试
    const failedResults = this.testResults.filter(r => !r.passed);
    if (failedResults.length > 0) {
      console.log('\n❌ 失败的测试:');
      failedResults.forEach(result => {
        console.log(`- ${result.testName}: ${JSON.stringify(result.input)} -> 期望: ${JSON.stringify(result.expected)}, 实际: ${JSON.stringify(result.actual)}`);
      });
    }
    
    return {
      total: totalTests,
      passed: passedTests,
      failed: failedTests,
      successRate: (passedTests / totalTests) * 100
    };
  }

  /**
   * 模拟快速批量导入流程（不实际执行）
   */
  async simulateQuickBatchImport() {
    console.log('\n🎭 模拟快速批量导入流程...');
    
    const mockProgressCallback = (progress) => {
      console.log(`进度更新: ${progress.phase} - ${JSON.stringify(progress)}`);
    };
    
    // 设置模拟模式
    const originalFunction = contactImporter.selectContactFromPhoneBook;
    let selectionCount = 0;
    
    contactImporter.selectContactFromPhoneBook = () => {
      return new Promise((resolve) => {
        selectionCount++;
        if (selectionCount <= 3) {
          resolve(this.mockContacts[selectionCount - 1]);
        } else {
          resolve(null); // 模拟用户取消
        }
      });
    };
    
    try {
      contactImporter.setProgressCallback(mockProgressCallback);
      
      // 这里不实际执行，只是演示API
      console.log('✅ 模拟导入流程设置完成');
      console.log('📝 模拟进度回调已设置');
      console.log('🎯 准备就绪，可以开始实际测试');
      
    } finally {
      // 恢复原始函数
      contactImporter.selectContactFromPhoneBook = originalFunction;
    }
  }
}

// 创建测试实例
const tester = new ContactImporterTester();

export default tester;