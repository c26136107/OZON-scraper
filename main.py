import sys
import os
import time
import traceback
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QGroupBox, QDoubleSpinBox, QMessageBox, QFileDialog,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QObject, Slot
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PySide6.QtNetwork import QNetworkProxy


class LogSignal(QObject):
    log = Signal(str)


log_signal = LogSignal()


def log_msg(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    line = f'[{timestamp}] {msg}'
    print(line)
    try:
        log_signal.log.emit(line)
    except Exception:
        pass


def make_row(widgets_with_stretches):
    """创建一行布局，返回包含该行的QWidget"""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    for item in widgets_with_stretches:
        if item == 'stretch':
            layout.addStretch()
        elif isinstance(item, tuple):
            widget, stretch = item
            layout.addWidget(widget, stretch)
        else:
            layout.addWidget(item)
    return row


class ProductCard(QFrame):
    """商品卡片组件"""
    def __init__(self, product_data, parent=None):
        super().__init__(parent)
        self.product = product_data
        self.setFrameShape(QFrame.StyledPanel)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        name = self.product.get('name', '未知商品')
        name_label = QLabel(name)
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(60)
        name_label.setStyleSheet('font-weight: bold; font-size: 12px; color: #333;')
        layout.addWidget(name_label)

        price = self.product.get('price', '')
        price_label = QLabel(f'\U0001f4b0 {price}')
        price_label.setStyleSheet('font-size: 14px; color: #e74c3c; font-weight: bold;')
        layout.addWidget(price_label)

        old_price = self.product.get('old_price', '')
        if old_price:
            old_label = QLabel(f'\u539f\u4ef7: {old_price}')
            old_label.setStyleSheet('font-size: 11px; color: #999; text-decoration: line-through;')
            layout.addWidget(old_label)

        rating = self.product.get('rating', '')
        reviews = self.product.get('reviews', '')
        if rating or reviews:
            info_label = QLabel(f'\u2b50 {rating}  \U0001f4ac {reviews}')
            info_label.setStyleSheet('font-size: 11px; color: #666;')
            layout.addWidget(info_label)

        sku = self.product.get('sku', '')
        if sku:
            sku_label = QLabel(f'ID: {sku}')
            sku_label.setStyleSheet('font-size: 10px; color: #999;')
            layout.addWidget(sku_label)

        link_btn = QPushButton('\u67e5\u770b\u8be6\u60c5')
        link_btn.setStyleSheet('QPushButton { background: #3498db; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; } QPushButton:hover { background: #2980b9; }')
        link_btn.setCursor(Qt.PointingHandCursor)
        link_btn.clicked.connect(self.open_link)
        layout.addWidget(link_btn)

        self.setStyleSheet('QFrame { background: #f8f9fa; border: 1px solid #ddd; border-radius: 6px; }')
        self.setMinimumWidth(180)
        self.setMaximumWidth(260)
        self.setMinimumHeight(180)
        self.setMaximumHeight(230)

    def open_link(self):
        url = self.product.get('url', '')
        if url:
            main_win = self.window()
            if hasattr(main_win, 'browser_view'):
                main_win.browser_view.load(QUrl(url))
                log_msg(f'\u6253\u5f00\u5546\u54c1\u8be6\u60c5: {url}')


class OzonWebPage(QWebEnginePage):
    """自定义Web页面，处理OZON的反爬机制"""
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)

    def javaScriptConsoleMessage(self, level, message, line, source):
        msg_str = str(message)
        if any(kw in msg_str.lower() for kw in ['ozon', 'product', 'error', 'scrape']):
            log_msg(f'[Browser JS] {msg_str}')


class ScrapingThread(QThread):
    """爬取线程 - 在主线程执行JS提取商品信息"""
    products_found = Signal(list)
    scrape_progress = Signal(str)
    scrape_finished = Signal(int)

    def __init__(self, browser_view, parent=None):
        super().__init__(parent)
        self.browser_view = browser_view
        self._running = True
        self._js_result = None

    def stop(self):
        self._running = False

    def run(self):
        log_msg('\u5f00\u59cb\u87ba\u53d6\u5546\u54c1\u4fe1\u606f...')
        self.scrape_progress.emit('\u6b63\u5728\u52a0\u8f7d\u9875\u9762\uff0c\u7b49\u5f85\u5185\u5bb9\u6e32\u67d3...')
        time.sleep(3)
        if not self._running:
            return

        max_attempts = 5
        products = []
        for attempt in range(max_attempts):
            if not self._running:
                break
            log_msg(f'\u7b2c {attempt+1} \u6b21\u5c1d\u8bd5\u63d0\u53d6\u5546\u54c1\u6570\u636e...')
            self.scrape_progress.emit(f'\u7b2c {attempt+1} \u6b21\u5c1d\u8bd5\u63d0\u53d6...')
            js_code = self._get_scrape_js()
            self._js_result = None

            try:
                callback_called = [False]
                def js_callback(result):
                    self._js_result = result
                    callback_called[0] = True

                self.browser_view.page().runJavaScript(js_code, js_callback)
                time.sleep(3)

                if callback_called[0] and self._js_result and len(self._js_result) > 0:
                    products = self._js_result
                    log_msg(f'\u6210\u529f\u63d0\u53d6 {len(products)} \u4e2a\u5546\u54c1')
                    break
            except Exception as e:
                log_msg(f'JS\u6267\u884c\u9519\u8bef: {str(e)}')

            time.sleep(2)

        if products:
            self.products_found.emit(products)
        else:
            log_msg('\u672a\u80fd\u63d0\u53d6\u5230\u5546\u54c1\u6570\u636e\uff0c\u8bf7\u786e\u8ba4\u9875\u9762\u5df2\u52a0\u8f7d\u5b8c\u6210')
        self.scrape_finished.emit(len(products))

    def _get_scrape_js(self):
        return r"""
        (function() {
            var products = [];
            var selectors = [
                '[data-widget="searchResultsV2"] a[href*="/product/"]',
                '[data-widget="searchResults"] a[href*="/product/"]',
                'a[href*="/product/"][class*="b6q5"]',
                'div[class*="k7m"] a[href*="/product/"]'
            ];
            var links = [];
            selectors.forEach(function(sel) {
                var els = document.querySelectorAll(sel);
                els.forEach(function(el) { links.push(el); });
            });
            var seenUrls = {};
            var uniqueLinks = links.filter(function(l) {
                var href = l.href || l.getAttribute('href') || '';
                if (seenUrls[href]) return false;
                seenUrls[href] = true;
                return true;
            });

            for (var i = 0; i < Math.min(uniqueLinks.length, 50); i++) {
                var link = uniqueLinks[i];
                var card = link.closest('[class*="k7m"]') || link.closest('[class*="search"]') || link;
                var product = {};
                var href = link.href || link.getAttribute('href') || '';
                product.url = href.startsWith('http') ? href : 'https://www.ozon.ru' + href;

                var nameEl = card.querySelector('[class*="tsBodyL"]') || card.querySelector('span[class*="tsBody"]') || link.querySelector('[class*="tsBody"]');
                if (!nameEl) nameEl = card.querySelector('span') || card;
                if (nameEl) {
                    var txt = nameEl.innerText || nameEl.textContent || '';
                    if (txt.length > 3) product.name = txt.trim().substring(0, 200);
                }
                if (!product.name && href) {
                    var parts = href.split('/');
                    for (var p = parts.length - 1; p >= 0; p--) {
                        if (parts[p].match(/^[a-z0-9-]+$/i) && parts[p].length > 3) {
                            product.name = parts[p].replace(/-/g, ' ').replace(/\d+$/, '');
                            break;
                        }
                    }
                }

                var priceEl = card.querySelector('[class*="c1r8"]') || card.querySelector('[class*="price"] span');
                if (priceEl) {
                    var pt = priceEl.innerText || priceEl.textContent || '';
                    if (pt) product.price = pt.trim();
                }

                var ratingEl = card.querySelector('[class*="rating"]') || card.querySelector('[class*="star"]');
                if (ratingEl) {
                    var rt = ratingEl.innerText || ratingEl.textContent || '';
                    if (rt) product.rating = rt.trim();
                }

                var reviewEl = card.querySelector('[class*="review"]');
                if (reviewEl) {
                    var rv = reviewEl.innerText || reviewEl.textContent || '';
                    if (rv) product.reviews = rv.trim();
                }

                var skuMatch = product.url.match(/-(\d+)\//);
                if (skuMatch) product.sku = skuMatch[1];

                if (product.url && product.url.includes('/product/')) {
                    products.push(product);
                }
            }
            return products;
        })();
        """


class MainWindow(QMainWindow):
    def __init__(self):
        try:
            super().__init__()
            self.setWindowTitle('OZON\u5546\u54c1\u91c7\u96c6')
            self.setMinimumSize(1200, 800)
            self.resize(1400, 900)
            self.products_data = []
            self.scrape_thread = None
            self._card_widgets = []
            self.setup_ui()
            self.setup_browser()
            self.connect_signals()
            log_msg('OZON\u5546\u54c1\u91c7\u96c6\u7cfb\u7edf\u542f\u52a8\u5b8c\u6210')
        except Exception as e:
            log_msg(f'\u542f\u52a8\u9519\u8bef: {str(e)}')
            traceback.print_exc()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        content_splitter = QSplitter(Qt.Horizontal)

        # === \u5de6\u4fa7\u9762\u677f (1/3) ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(6)

        # \u641c\u7d22\u6761\u4ef6\u533a
        search_group = QGroupBox('\ud83d\udd0d \u641c\u7d22\u6761\u4ef6')
        search_group.setStyleSheet('QGroupBox { font-weight: bold; font-size: 14px; color: #2c3e50; padding-top: 20px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }')
        search_layout = QVBoxLayout(search_group)

        kw_label = QLabel('\u5173\u952e\u8bcd:')
        kw_label.setFixedWidth(60)
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText('\u8f93\u5165\u641c\u7d22\u5173\u952e\u8bcd...')
        self.keyword_input.setStyleSheet('padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;')
        search_layout.addWidget(make_row([kw_label, (self.keyword_input, 1)]))

        price_label = QLabel('\u4ef7\u683c:')
        price_label.setFixedWidth(60)
        self.price_min = QDoubleSpinBox()
        self.price_min.setRange(0, 999999)
        self.price_min.setPrefix('\u20bd ')
        self.price_min.setDecimals(0)
        self.price_min.setValue(0)
        self.price_min.setStyleSheet('padding: 4px; border: 1px solid #ddd; border-radius: 4px;')
        self.price_min.setFixedWidth(110)
        sep_label = QLabel(' \u2014 ')
        self.price_max = QDoubleSpinBox()
        self.price_max.setRange(0, 999999)
        self.price_max.setPrefix('\u20bd ')
        self.price_max.setDecimals(0)
        self.price_max.setValue(5000)
        self.price_max.setStyleSheet('padding: 4px; border: 1px solid #ddd; border-radius: 4px;')
        self.price_max.setFixedWidth(110)
        search_layout.addWidget(make_row([price_label, self.price_min, sep_label, self.price_max, 'stretch']))

        btn_row = make_row([])
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        self.search_btn = QPushButton('\ud83d\ude80 \u641c\u7d22')
        self.search_btn.setStyleSheet('QPushButton { background: #27ae60; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #219a52; } QPushButton:pressed { background: #1e8449; } QPushButton:disabled { background: #95a5a6; }')
        self.search_btn.setCursor(Qt.PointingHandCursor)

        self.scrape_btn = QPushButton('\ud83d\udce6 \u91c7\u96c6\u6570\u636e')
        self.scrape_btn.setStyleSheet('QPushButton { background: #e67e22; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #d35400; } QPushButton:pressed { background: #c0392b; } QPushButton:disabled { background: #95a5a6; }')
        self.scrape_btn.setCursor(Qt.PointingHandCursor)

        self.export_btn = QPushButton('\ud83d\udcbe \u5bfc\u51faCSV')
        self.export_btn.setStyleSheet('QPushButton { background: #3498db; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #2980b9; } QPushButton:pressed { background: #2471a3; } QPushButton:disabled { background: #95a5a6; }')
        self.export_btn.setCursor(Qt.PointingHandCursor)

        self.clear_btn = QPushButton('\ud83d\uddd1 \u6e05\u7a7a')
        self.clear_btn.setStyleSheet('QPushButton { background: #95a5a6; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #7f8c8d; } QPushButton:pressed { background: #6c7a7a; }')
        self.clear_btn.setCursor(Qt.PointingHandCursor)

        btn_layout.addWidget(self.search_btn)
        btn_layout.addWidget(self.scrape_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.clear_btn)
        search_layout.addWidget(btn_row)

        self.status_label = QLabel('\u5c31\u7eea')
        self.status_label.setStyleSheet('color: #27ae60; font-weight: bold; font-size: 12px; padding: 4px;')
        search_layout.addWidget(self.status_label)
        left_layout.addWidget(search_group, stretch=2)

        # \u5546\u54c1\u5c55\u793a\u533a
        product_group = QGroupBox('\ud83d\udccb \u5546\u54c1\u5217\u8868')
        product_group.setStyleSheet('QGroupBox { font-weight: bold; font-size: 14px; color: #2c3e50; padding-top: 20px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }')
        product_layout = QVBoxLayout(product_group)

        view_btn_row = make_row([])
        view_layout = QHBoxLayout(view_btn_row)
        view_layout.setContentsMargins(0, 0, 0, 0)
        self.card_btn = QPushButton('\u5361\u7247\u89c6\u56fe')
        self.card_btn.setStyleSheet('QPushButton { background: #3498db; color: white; border: none; padding: 4px 12px; border-radius: 3px; font-size: 11px; } QPushButton:hover { background: #2980b9; }')
        self.card_btn.setCursor(Qt.PointingHandCursor)
        self.table_btn = QPushButton('\u8868\u683c\u89c6\u56fe')
        self.table_btn.setStyleSheet('QPushButton { background: #95a5a6; color: white; border: none; padding: 4px 12px; border-radius: 3px; font-size: 11px; } QPushButton:hover { background: #7f8c8d; }')
        self.table_btn.setCursor(Qt.PointingHandCursor)
        self.count_label = QLabel('\u51710\u4ef6\u5546\u54c1')
        self.count_label.setStyleSheet('color: #666; font-size: 12px;')
        view_layout.addWidget(self.card_btn)
        view_layout.addWidget(self.table_btn)
        view_layout.addStretch()
        view_layout.addWidget(self.count_label)
        product_layout.addWidget(view_btn_row)

        self.card_scroll = QScrollArea()
        self.card_scroll.setWidgetResizable(True)
        self.card_container = QWidget()
        self.card_flow_layout = QVBoxLayout(self.card_container)
        self.card_flow_layout.setSpacing(6)
        self.card_flow_layout.setAlignment(Qt.AlignTop)
        self.card_scroll.setWidget(self.card_container)
        self.card_scroll.setStyleSheet('QScrollArea { border: 1px solid #ddd; border-radius: 4px; background: #ecf0f1; }')

        self.product_table = QTableWidget()
        self.product_table.setColumnCount(7)
        self.product_table.setHorizontalHeaderLabels(['\u5546\u54c1\u540d\u79f0', '\u4ef7\u683c', '\u539f\u4ef7', '\u8bc4\u5206', '\u8bc4\u8bba\u6570', 'SKU', '\u94fe\u63a5'])
        self.product_table.horizontalHeader().setStretchLastSection(True)
        self.product_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in [1, 2, 3, 4, 5]:
            self.product_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.product_table.setAlternatingRowColors(True)
        self.product_table.setStyleSheet('QTableWidget { border: 1px solid #ddd; border-radius: 4px; font-size: 12px; } QTableWidget::item { padding: 4px; } QHeaderView::section { background: #34495e; color: white; padding: 4px; font-weight: bold; }')
        self.product_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.product_table.setSelectionBehavior(QTableWidget.SelectRows)

        self.view_tabs = QTabWidget()
        self.view_tabs.setStyleSheet('QTabWidget::pane { border: 1px solid #ddd; border-radius: 4px; } QTabBar::tab { padding: 6px 12px; }')
        self.view_tabs.addTab(self.card_scroll, '\u5361\u7247\u89c6\u56fe')
        self.view_tabs.addTab(self.product_table, '\u8868\u683c\u89c6\u56fe')
        product_layout.addWidget(self.view_tabs)
        left_layout.addWidget(product_group, stretch=3)

        # === \u53f3\u4fa7\u6d4f\u89c8\u5668 (2/3) ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        browser_header = QLabel('\ud83c\udf10 \u5185\u7f6e\u6d4f\u89c8\u5668 \u2014 OZON')
        browser_header.setStyleSheet('background: #2c3e50; color: white; padding: 6px 10px; font-weight: bold; font-size: 13px; border-radius: 4px 4px 0 0;')
        right_layout.addWidget(browser_header)

        self.browser_view = QWebEngineView()
        self.browser_view.setMinimumHeight(400)
        right_layout.addWidget(self.browser_view)

        content_splitter.addWidget(left_panel)
        content_splitter.addWidget(right_panel)
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 2)
        content_splitter.setSizes([400, 800])

        main_layout.addWidget(content_splitter, stretch=7)

        # === \u5e95\u90e8\u65e5\u5fd7\u533a ===
        log_group = QGroupBox('\ud83d\udcd2 \u64cd\u4f5c\u65e5\u5fd7')
        log_group.setStyleSheet('QGroupBox { font-weight: bold; font-size: 12px; color: #2c3e50; padding-top: 16px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }')
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet('QTextEdit { background: #1a1a2e; color: #00ff88; font-family: Consolas, "Courier New", monospace; font-size: 11px; border: 1px solid #333; border-radius: 4px; padding: 4px; }')
        log_layout.addWidget(self.log_text)

        main_layout.addWidget(log_group, stretch=2)
        self.setStyleSheet('QMainWindow { background: #f5f6fa; }')

    def setup_browser(self):
        try:
            profile = QWebEngineProfile('ozon_scraper', self)
            profile.setHttpUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            settings = profile.settings()
            settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.AutoLoadIconsForPage, True)
            settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
            settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
            settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
            profile.setHttpAcceptLanguage('ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7')
            QNetworkProxy.setApplicationProxy(QNetworkProxy.NoProxy)
            page = OzonWebPage(profile, self.browser_view)
            self.browser_view.setPage(page)
            self.browser_view.loadFinished.connect(self._on_page_loaded)
            self.browser_view.loadProgress.connect(self._on_load_progress)
            self.browser_view.urlChanged.connect(self._on_url_changed)
            log_msg('\u5185\u7f6e\u6d4f\u89c8\u5668\u5df2\u521d\u59cb\u5316\uff0c\u52a0\u8f7dOZON\u9996\u9875')
            self.browser_view.load(QUrl('https://www.ozon.ru/highlight/ozon-global/'))
        except Exception as e:
            log_msg(f'\u6d4f\u89c8\u5668\u521d\u59cb\u5316\u5931\u8d25: {str(e)}')
            traceback.print_exc()

    def connect_signals(self):
        self.search_btn.clicked.connect(self.do_search)
        self.scrape_btn.clicked.connect(self.do_scrape)
        self.export_btn.clicked.connect(self.do_export)
        self.clear_btn.clicked.connect(self.do_clear)
        self.card_btn.clicked.connect(lambda: self.view_tabs.setCurrentIndex(0))
        self.table_btn.clicked.connect(lambda: self.view_tabs.setCurrentIndex(1))

    @Slot(str)
    def append_log(self, msg):
        try:
            color = '#00ff88'
            if any(kw in msg for kw in ['\u9519\u8bef', '\u5931\u8d25', '\u672a\u80fd']):
                color = '#ff4444'
            elif '\u6210\u529f' in msg:
                color = '#00ccff'
            elif '\u5c1d\u8bd5' in msg:
                color = '#ffaa00'
            self.log_text.append(f'<span style="color: {color}">{msg}</span>')
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_text.setTextCursor(cursor)
        except Exception:
            pass

    def do_search(self):
        keyword = self.keyword_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, '\u63d0\u793a', '\u8bf7\u8f93\u5165\u641c\u7d22\u5173\u952e\u8bcd')
            return
        price_min = int(self.price_min.value())
        price_max = int(self.price_max.value())
        if price_min > price_max:
            QMessageBox.warning(self, '\u63d0\u793a', '\u6700\u4f4e\u4ef7\u683c\u4e0d\u80fd\u5927\u4e8e\u6700\u9ad8\u4ef7\u683c')
            return
        url = f'https://www.ozon.ru/highlight/ozon-global/?currency_price={price_min}%3B{price_max}&text={keyword}'
        log_msg(f'\u641c\u7d22\u5173\u952e\u8bcd: {keyword}, \u4ef7\u683c\u8303\u56f4: \u20bd{price_min} - \u20bd{price_max}')
        log_msg(f'\u641c\u7d22URL: {url}')
        self.search_btn.setEnabled(False)
        self.scrape_btn.setEnabled(False)
        self.status_label.setText('\u23f3 \u6b63\u5728\u52a0\u8f7d\u9875\u9762...')
        self.status_label.setStyleSheet('color: #e67e22; font-weight: bold; font-size: 12px;')
        self.browser_view.load(QUrl(url))

    @Slot(int)
    def _on_load_progress(self, progress):
        self.status_label.setText(f'\u23f3 \u52a0\u8f7d\u4e2d {progress}%')
        self.status_label.setStyleSheet('color: #e67e22; font-weight: bold; font-size: 12px;')

    @Slot(QUrl)
    def _on_url_changed(self, url):
        log_msg(f'\u5bfc\u822a: {url.toString()[:80]}')

    @Slot(bool)
    def _on_page_loaded(self, ok):
        self.search_btn.setEnabled(True)
        self.scrape_btn.setEnabled(True)
        if ok:
            log_msg('\u9875\u9762\u52a0\u8f7d\u5b8c\u6210\uff0c\u53ef\u4ee5\u70b9\u51fb\u91c7\u96c6\u6570\u636e')
            self.status_label.setText('\u2705 \u9875\u9762\u5df2\u52a0\u8f7d\uff0c\u70b9\u51fb\u91c7\u96c6')
            self.status_label.setStyleSheet('color: #27ae60; font-weight: bold; font-size: 12px;')
        else:
            log_msg('\u9875\u9762\u52a0\u8f7d\u5931\u8d25')
            self.status_label.setText('\u274c \u9875\u9762\u52a0\u8f7d\u5931\u8d25')
            self.status_label.setStyleSheet('color: #e74c3c; font-weight: bold; font-size: 12px;')

    def do_scrape(self):
        if self.scrape_thread and self.scrape_thread.isRunning():
            log_msg('\u91c7\u96c6\u7ebf\u7a0b\u6b63\u5728\u8fd0\u884c\uff0c\u8bf7\u7b49\u5f85\u5b8c\u6210')
            return
        self.search_btn.setEnabled(False)
        self.scrape_btn.setEnabled(False)
        self.status_label.setText('\ud83d\udce6 \u6b63\u5728\u91c7\u96c6\u6570\u636e...')
        self.status_label.setStyleSheet('color: #e67e22; font-weight: bold; font-size: 12px;')
        log_msg('\u5f00\u59cb\u91c7\u96c6\u5546\u54c1\u6570\u636e')
        self.scrape_thread = ScrapingThread(self.browser_view)
        self.scrape_thread.products_found.connect(self.on_products_found)
        self.scrape_thread.scrape_finished.connect(self.on_scrape_finished)
        self.scrape_thread.start()

    @Slot(list)
    def on_products_found(self, products):
        try:
            self.products_data = products
            log_msg(f'\u91c7\u96c6\u5230 {len(products)} \u4ef6\u5546\u54c1')
            self.update_card_view(products)
            self.update_table_view(products)
            self.count_label.setText(f'\u5171 {len(products)} \u4ef6\u5546\u54c1')
        except Exception as e:
            log_msg(f'\u66f4\u65b0\u5546\u54c1\u89c6\u56fe\u9519\u8bef: {str(e)}')
            traceback.print_exc()

    def update_card_view(self, products):
        # \u6e05\u7406\u65e7\u5361\u7247
        while self.card_flow_layout.count():
            item = self.card_flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._card_widgets.clear()

        if not products:
            return

        cards_per_row = 3
        for i in range(0, len(products), cards_per_row):
            row_widgets = []
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            for j in range(cards_per_row):
                if i + j < len(products):
                    card = ProductCard(products[i + j])
                    row_layout.addWidget(card)
                    row_widgets.append(card)
                else:
                    row_layout.addStretch()
            self.card_flow_layout.addWidget(row)
            self._card_widgets.extend(row_widgets)

    def update_table_view(self, products):
        self.product_table.setRowCount(0)
        self.product_table.setRowCount(len(products))
        for i, prod in enumerate(products):
            self.product_table.setItem(i, 0, QTableWidgetItem(prod.get('name', '')))
            self.product_table.setItem(i, 1, QTableWidgetItem(prod.get('price', '')))
            self.product_table.setItem(i, 2, QTableWidgetItem(prod.get('old_price', '')))
            self.product_table.setItem(i, 3, QTableWidgetItem(prod.get('rating', '')))
            self.product_table.setItem(i, 4, QTableWidgetItem(prod.get('reviews', '')))
            self.product_table.setItem(i, 5, QTableWidgetItem(prod.get('sku', '')))
            self.product_table.setItem(i, 6, QTableWidgetItem(prod.get('url', '')))

    @Slot(int)
    def on_scrape_finished(self, count):
        self.search_btn.setEnabled(True)
        self.scrape_btn.setEnabled(True)
        if count > 0:
            self.status_label.setText(f'\u2705 \u91c7\u96c6\u5b8c\u6210\uff0c\u5171 {count} \u4ef6\u5546\u54c1')
            self.status_label.setStyleSheet('color: #27ae60; font-weight: bold; font-size: 12px;')
        else:
            self.status_label.setText('\u274c \u672a\u91c7\u96c6\u5230\u6570\u636e')
            self.status_label.setStyleSheet('color: #e74c3c; font-weight: bold; font-size: 12px;')

    def do_export(self):
        if not self.products_data:
            QMessageBox.warning(self, '\u63d0\u793a', '\u6ca1\u6709\u53ef\u5bfc\u51fa\u7684\u6570\u636e')
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, '\u5bfc\u51faCSV', f'ozon_products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            'CSV\u6587\u4ef6 (*.csv)'
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8-sig') as f:
                    headers = ['\u5546\u54c1\u540d\u79f0', '\u4ef7\u683c', '\u539f\u4ef7', '\u8bc4\u5206', '\u8bc4\u8bba\u6570', 'SKU', '\u94fe\u63a5']
                    f.write(','.join(headers) + '\n')
                    for prod in self.products_data:
                        row = [
                            prod.get('name', '').replace(',', ';'),
                            prod.get('price', '').replace(',', ';'),
                            prod.get('old_price', '').replace(',', ';'),
                            prod.get('rating', '').replace(',', ';'),
                            prod.get('reviews', '').replace(',', ';'),
                            prod.get('sku', ''),
                            prod.get('url', '')
                        ]
                        f.write(','.join(row) + '\n')
                log_msg(f'\u6210\u529f\u5bfc\u51fa {len(self.products_data)} \u6761\u6570\u636e\u5230: {filename}')
                QMessageBox.information(self, '\u5bfc\u51fa\u6210\u529f', f'\u5df2\u5bfc\u51fa {len(self.products_data)} \u6761\u6570\u636e\u5230:\n{filename}')
            except Exception as e:
                log_msg(f'\u5bfc\u51fa\u5931\u8d25: {str(e)}')
                QMessageBox.critical(self, '\u5bfc\u51fa\u5931\u8d25', str(e))

    def do_clear(self):
        self.products_data = []
        while self.card_flow_layout.count():
            item = self.card_flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._card_widgets.clear()
        self.product_table.setRowCount(0)
        self.count_label.setText('\u51710\u4ef6\u5546\u54c1')
        self.status_label.setText('\u5c31\u7eea')
        self.status_label.setStyleSheet('color: #27ae60; font-weight: bold; font-size: 12px;')
        log_msg('\u5df2\u6e05\u7a7a\u6240\u6709\u5546\u54c1\u6570\u636e')


def main():
    sys.excepthook = lambda t, v, tb: (
        print(f'FATAL ERROR: {v}'),
        traceback.print_tb(tb),
        input('Press Enter to exit...')
    )
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    font = QFont('\u5fae\u8f6f\u96c5\u9ed1', 10)
    app.setFont(font)
    log_signal.log.connect(lambda msg: None)  # prevent crash if no window yet
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()