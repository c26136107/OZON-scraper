# OZON商品采集系统

## 简介
基于 PySide6 + QtWebEngine（内置Chromium内核）的OZON商品信息采集工具。
通过内置浏览器直接访问OZON页面，使用JavaScript注入提取商品数据，规避反爬限制。

## 功能特性
- 🔍 关键词搜索 + 价格范围筛选
- 📦 一键采集商品数据（名称、价格、原价、评分、评论、SKU、链接）
- 📋 卡片视图 / 表格视图切换
- 💾 CSV导出（UTF-8 BOM编码，Excel可直接打开）
- 🌐 内置Chromium浏览器，无需外部浏览器
- 📝 完整操作日志记录

## 技术架构
- **UI框架**: PySide6（Qt6 Python绑定）
- **内置浏览器**: QtWebEngine（Chromium内核）
- **数据提取**: JavaScript注入（runJavaScript API）
- **反爬策略**: 真实浏览器渲染 + 俄语UA + 多选择器容错

## 快速启动

### 方式一：直接运行
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动程序
python main.py
```

### 方式二：双击启动
直接双击 `run.bat` 即可（自动检测并安装依赖）

### 方式三：打包为独立EXE（任何电脑直接使用）
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "OZON商品采集" main.py
```

## 使用说明
1. 在左侧输入关键词和价格范围
2. 点击"🚀 搜索"按钮，右侧浏览器会加载搜索结果页面
3. 等待页面完全加载后，点击"📦 采集数据"按钮
4. 采集到的商品会显示在卡片/表格中
5. 点击"💾 导出CSV"可导出数据

## OZON搜索URL格式
```
https://www.ozon.ru/highlight/ozon-global/?currency_price=最低价%3B最高价&text=关键词
```

## 注意事项
- OZON反爬较强，首次访问可能需要等待页面完全加载
- 采集数据时建议等待页面滚动加载完成后再点击采集
- 内置浏览器使用独立Profile，不会影响系统Chrome
- 如果页面结构变更，可能需要更新JS选择器