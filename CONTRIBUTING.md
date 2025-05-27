# 贡献指南 🤝

感谢您对期货持仓分析系统的关注！我们欢迎各种形式的贡献。

## 🚀 如何贡献

### 报告问题
如果您发现了bug或有功能建议，请：
1. 检查[Issues](https://github.com/your-username/futures-position-analysis/issues)中是否已有相关问题
2. 如果没有，请创建新的Issue，详细描述问题或建议

### 提交代码
1. **Fork项目**
   ```bash
   git clone https://github.com/your-username/futures-position-analysis.git
   cd futures-position-analysis
   ```

2. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **进行开发**
   - 遵循代码规范
   - 添加必要的测试
   - 更新相关文档

4. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   ```

5. **推送分支**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **创建Pull Request**
   - 详细描述您的更改
   - 关联相关的Issue
   - 等待代码审查

## 📝 代码规范

### Python代码规范
- 遵循[PEP 8](https://www.python.org/dev/peps/pep-0008/)编码规范
- 使用有意义的变量和函数名
- 添加适当的注释和文档字符串
- 保持函数简洁，单一职责

### 提交信息规范
使用[约定式提交](https://www.conventionalcommits.org/zh-hans/)格式：
- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建过程或辅助工具的变动

### 示例
```
feat: 添加期限结构分析功能

- 新增期限结构分析模块
- 支持Back和Contango结构识别
- 添加可视化图表展示
- 更新用户界面

Closes #123
```

## 🧪 测试

在提交代码前，请确保：
1. 代码能够正常运行
2. 没有明显的性能问题
3. 新功能有适当的错误处理
4. 更新了相关文档

### 本地测试
```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python start_app.py

# 测试主要功能
# 1. 数据获取
# 2. 策略分析
# 3. 图表生成
# 4. 数据导出
```

## 📚 开发环境设置

### 推荐工具
- **IDE**: VS Code, PyCharm
- **Python版本**: 3.8+
- **虚拟环境**: venv或conda
- **代码格式化**: black, autopep8
- **代码检查**: flake8, pylint

### 环境配置
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装开发依赖
pip install -r requirements.txt
pip install black flake8 pytest

# 代码格式化
black .

# 代码检查
flake8 .
```

## 🎯 优先级任务

我们特别欢迎以下方面的贡献：

### 高优先级
- 🐛 Bug修复
- 📈 性能优化
- 🔒 安全性改进
- 📱 移动端适配

### 中优先级
- ✨ 新策略算法
- 📊 数据可视化改进
- 🌐 国际化支持
- 📝 文档完善

### 低优先级
- 🎨 UI/UX改进
- 🧪 单元测试
- 📦 打包优化
- 🔧 开发工具改进

## 📋 Issue模板

### Bug报告
```markdown
**问题描述**
简要描述遇到的问题

**复现步骤**
1. 进入...
2. 点击...
3. 看到错误...

**预期行为**
描述您期望发生的情况

**实际行为**
描述实际发生的情况

**环境信息**
- 操作系统: [例如 Windows 10]
- Python版本: [例如 3.9.0]
- 浏览器: [例如 Chrome 95.0]

**截图**
如果适用，添加截图来帮助解释问题

**附加信息**
添加任何其他相关信息
```

### 功能请求
```markdown
**功能描述**
简要描述您希望添加的功能

**使用场景**
描述这个功能的使用场景和价值

**解决方案**
描述您认为可行的解决方案

**替代方案**
描述您考虑过的其他解决方案

**附加信息**
添加任何其他相关信息
```

## 🏆 贡献者

感谢所有为项目做出贡献的开发者！

<!-- 这里会自动生成贡献者列表 -->

## 📞 联系我们

如果您有任何问题或建议，可以通过以下方式联系我们：
- 创建[Issue](https://github.com/your-username/futures-position-analysis/issues)
- 发送邮件至：your-email@example.com
- 加入我们的讨论群：[群号或链接]

---

再次感谢您的贡献！🎉 