import os
import re
import sys
import zipfile
import rarfile
import pymupdf
import math

if sys.platform == "win32":
    import ctypes

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QScrollArea,
    QMessageBox, QComboBox, QProgressBar, QTabBar, QStackedWidget,
    QMenu, QToolButton
)
from PyQt6.QtGui import QPixmap, QImage, QIntValidator, QPainter, QColor, QPen, QIcon, QPainterPath
from PyQt6.QtCore import Qt, QSettings, QPoint, QTimer, QSize, QPointF
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


def configure_dwm_fullscreen(hwnd, is_fullscreen: bool):
    if sys.platform != "win32":
        return
    try:
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        corner_pref = ctypes.c_int(1 if is_fullscreen else 2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(corner_pref),
            ctypes.sizeof(corner_pref)
        )

        DWMWA_BORDER_COLOR = 34
        border_color = ctypes.c_uint(0x00000000 if is_fullscreen else 0xFFFFFFFF)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_BORDER_COLOR,
            ctypes.byref(border_color),
            ctypes.sizeof(border_color)
        )
    except Exception:
        pass


def setup_rar_tool():
    app_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
    candidates = [
        os.path.join(app_dir, "UnRAR.exe"),
        os.path.join(app_dir, "7z.exe"),
        os.path.join(os.path.dirname(__file__), "UnRAR.exe"),
        os.path.join(os.path.dirname(__file__), "7z.exe"),
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        r"C:\Program Files\WinRAR\UnRAR.exe",
        r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
    ]
    for path in candidates:
        if os.path.isfile(path):
            if path.lower().endswith("7z.exe"):
                rarfile.UNRAR_TOOL = path
                rarfile.ALT_TOOL = path
            else:
                rarfile.UNRAR_TOOL = path
            return path
    return None

CONFIGURED_RAR_TOOL = setup_rar_tool()
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}


def natural_key(text):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]


def draw_x_pixmap(color_hex: str, size: int = 24, stroke: float = 2.1) -> QPixmap:
    """Draws a crisp X pixmap with padding."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color_hex), stroke, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    
    pad = 5
    painter.drawLine(pad, pad, size - pad, size - pad)
    painter.drawLine(size - pad, pad, pad, size - pad)
    painter.end()
    return pm


def draw_sun_pixmap(color_hex: str, size: int = 24) -> QPixmap:
    """Draws a vector sun icon with rays."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color_hex), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)

    cx, cy = size / 2.0, size / 2.0
    r_body = 4.2
    painter.drawEllipse(QPointF(cx, cy), r_body, r_body)

    ray_inner = 6.2
    ray_outer = 8.6
    for i in range(8):
        angle = i * (2 * math.pi / 8)
        x1 = cx + ray_inner * math.cos(angle)
        y1 = cy + ray_inner * math.sin(angle)
        x2 = cx + ray_outer * math.cos(angle)
        y2 = cy + ray_outer * math.sin(angle)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    painter.end()
    return pm


def draw_moon_pixmap(color_hex: str, size: int = 24) -> QPixmap:
    """Draws a vector crescent moon icon."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color_hex))

    outer = QPainterPath()
    outer.addEllipse(3.5, 3.5, 17.0, 17.0)

    inner = QPainterPath()
    inner.addEllipse(7.5, 1.5, 15.0, 15.0)

    crescent = outer.subtracted(inner)
    painter.drawPath(crescent)
    painter.end()
    return pm


def create_tab_close_icon(normal_color: str, hover_color: str = "#6565a4") -> QIcon:
    icon = QIcon()
    pm_normal = draw_x_pixmap(normal_color)
    pm_hover = draw_x_pixmap(hover_color)
    
    icon.addPixmap(pm_normal, QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(pm_hover, QIcon.Mode.Active, QIcon.State.Off)
    icon.addPixmap(pm_hover, QIcon.Mode.Normal, QIcon.State.On)
    return icon


class ComicScrollArea(QScrollArea):
    def __init__(self, doc_widget):
        super().__init__()
        self.doc_widget = doc_widget
        self.is_panning = False
        self.last_mouse_pos = QPoint()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.doc_widget.window.zoom_in()
            elif delta < 0:
                self.doc_widget.window.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and (
            self.doc_widget.zoom_factor > 1.05 or self.doc_widget.fit_mode == ComicReader.FIT_WIDTH
        ):
            self.is_panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_panning:
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doc_widget.window.toggle_fullscreen()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class DocumentTabWidget(QWidget):
    def __init__(self, file_path, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.file_path = os.path.normpath(file_path)

        self.chapters = []
        self.current_chapter_idx = -1
        self.current_page_idx = -1
        self.active_pixmaps = []

        self.zoom_factor = 1.0
        self.fit_mode = ComicReader.FIT_HEIGHT

        self.current_archive_path = None
        self.active_archive = None
        self.active_pdf = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll_area = ComicScrollArea(self)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.content_container)

        layout.addWidget(self.scroll_area)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.window.reading_mode != ComicReader.MODE_CONTINUOUS and self.active_pixmaps:
            self.render_current_views()

    def _on_scroll_changed(self, value):
        if self.window.reading_mode == ComicReader.MODE_CONTINUOUS and self.window.current_tab() == self:
            self.window.update_progress()

    def load_document(self, target_ch=0, target_pg=0):
        self.close_handles()
        ext = os.path.splitext(self.file_path)[1].lower().replace('.', '')

        if ext in ('cbz', 'cbr'):
            self.chapters = self._parse_archive_chapters(self.file_path, ext)
        elif ext in ('pdf', 'epub'):
            try:
                doc = pymupdf.open(self.file_path)
                page_count = len(doc)
                doc.close()
                self.chapters = [{
                    'title': os.path.basename(self.file_path),
                    'type': ext,
                    'path': self.file_path,
                    'pages': list(range(page_count))
                }]
            except Exception as e:
                QMessageBox.warning(self, f"Error Loading {ext.upper()}", str(e))
                return False

        if self.chapters:
            ch_to_load = min(max(0, target_ch), len(self.chapters) - 1)
            self.load_chapter(ch_to_load, start_page=target_pg)
            return True
        else:
            self.display_message("No readable pages found in file.")
            return False

    def _parse_archive_chapters(self, archive_path, ext):
        if ext == 'cbr' and not CONFIGURED_RAR_TOOL:
            QMessageBox.critical(
                self, "Missing RAR Tool",
                "To open .cbr files, install 7-Zip or WinRAR, or place UnRAR.exe next to the application."
            )
            return []

        try:
            if ext == 'cbz':
                with zipfile.ZipFile(archive_path, 'r') as z:
                    names = [n for n in z.namelist() if os.path.splitext(n)[1].lower() in IMAGE_EXTS]
            else:
                with rarfile.RarFile(archive_path, 'r') as r:
                    names = [n for n in r.namelist() if os.path.splitext(n)[1].lower() in IMAGE_EXTS]
        except Exception as e:
            QMessageBox.warning(self, "Error Reading Archive", f"Could not read {archive_path}:\n{e}")
            return []

        if not names:
            return []

        folder_groups = {}
        for name in names:
            clean_name = name.replace('\\', '/')
            folder_part = os.path.dirname(clean_name)
            ch_name = folder_part if folder_part else "Root"
            folder_groups.setdefault(ch_name, []).append(name)

        base_filename = os.path.basename(archive_path)
        parsed = []
        for folder_name in sorted(folder_groups.keys(), key=natural_key):
            pages = sorted(folder_groups[folder_name], key=natural_key)
            title = folder_name if folder_name != "Root" else base_filename
            parsed.append({
                'title': title,
                'type': ext,
                'path': archive_path,
                'pages': pages
            })
        return parsed

    def load_chapter(self, index, start_page=0):
        if not (0 <= index < len(self.chapters)):
            return

        self.current_chapter_idx = index
        chapter = self.chapters[index]

        if chapter['path'] != self.current_archive_path:
            self.close_handles()
            self.current_archive_path = chapter['path']
            try:
                if chapter['type'] == 'cbz':
                    self.active_archive = zipfile.ZipFile(chapter['path'], 'r')
                elif chapter['type'] == 'cbr':
                    self.active_archive = rarfile.RarFile(chapter['path'], 'r')
                elif chapter['type'] in ('pdf', 'epub'):
                    self.active_pdf = pymupdf.open(chapter['path'])
            except Exception as e:
                QMessageBox.warning(self, "Error Opening File", str(e))
                return

        if chapter['pages']:
            target_pg = min(max(0, start_page), len(chapter['pages']) - 1)
            self.load_page(target_pg)
        else:
            self.active_pixmaps = []
            self.display_message("No readable pages in this chapter.")

        if self.window.current_tab() == self:
            self.window.sync_ui_with_tab()

    def _get_page_pixmap(self, index):
        chapter = self.chapters[self.current_chapter_idx]
        page_ref = chapter['pages'][index]

        try:
            if chapter['type'] in ('cbz', 'cbr'):
                data = self.active_archive.read(page_ref)
                px = QPixmap()
                px.loadFromData(data)
                return px
            elif chapter['type'] in ('pdf', 'epub'):
                page = self.active_pdf[page_ref]
                mat = pymupdf.Matrix(2.5, 2.5)
                rendered = page.get_pixmap(matrix=mat)
                img_fmt = QImage.Format.Format_RGBA8888 if rendered.alpha else QImage.Format.Format_RGB888
                qimg = QImage(rendered.samples, rendered.width, rendered.height, rendered.stride, img_fmt)
                return QPixmap.fromImage(qimg)
        except Exception:
            return None

    def load_page(self, index):
        chapter = self.chapters[self.current_chapter_idx]
        if not (0 <= index < len(chapter['pages'])):
            return

        self.current_page_idx = index
        self.clear_content_layout()

        if self.window.reading_mode == ComicReader.MODE_CONTINUOUS:
            viewport_w = self.scroll_area.viewport().width()
            viewport_h = self.scroll_area.viewport().height()

            if viewport_h <= 50 and self.window:
                viewport_h = max(100, self.window.height() - 130)
            if viewport_w <= 50 and self.window:
                viewport_w = max(100, self.window.width() - 40)

            viewport_w = max(100, viewport_w)
            viewport_h = max(100, viewport_h)
            dpr = self.devicePixelRatioF()

            for i in range(len(chapter['pages'])):
                px = self._get_page_pixmap(i)
                if px and not px.isNull():
                    if self.fit_mode == ComicReader.FIT_HEIGHT:
                        target_h = int(viewport_h * dpr * self.zoom_factor)
                        scaled = px.scaledToHeight(target_h, Qt.TransformationMode.SmoothTransformation)
                    else:
                        target_w = int(viewport_w * dpr * self.zoom_factor)
                        scaled = px.scaledToWidth(target_w, Qt.TransformationMode.SmoothTransformation)

                    scaled.setDevicePixelRatio(dpr)
                    lbl = QLabel()
                    lbl.setPixmap(scaled)
                    lbl.setFixedSize(int(scaled.width() / dpr), int(scaled.height() / dpr))
                    self.content_layout.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignHCenter)

            self.scroll_area.verticalScrollBar().setValue(0)
        else:
            pages_to_load = []
            if self.window.reading_mode == ComicReader.MODE_DOUBLE_COVER:
                if index == 0:
                    pages_to_load = [0]
                else:
                    pair_idx = index if index % 2 != 0 else index - 1
                    pages_to_load = [pair_idx]
                    if pair_idx + 1 < len(chapter['pages']):
                        pages_to_load.append(pair_idx + 1)
            elif self.window.reading_mode == ComicReader.MODE_DOUBLE_NO_COVER:
                pair_idx = index if index % 2 == 0 else index - 1
                pages_to_load = [pair_idx]
                if pair_idx + 1 < len(chapter['pages']):
                    pages_to_load.append(pair_idx + 1)
            else:
                pages_to_load = [index]

            if self.window.reading_direction == ComicReader.DIR_RTL and len(pages_to_load) == 2:
                pages_to_load.reverse()

            self.active_pixmaps = [self._get_page_pixmap(p) for p in pages_to_load if self._get_page_pixmap(p)]
            self.render_current_views()

        if self.window.current_tab() == self:
            self.window.update_page_display()
            self.window.update_progress()

    def render_current_views(self):
        if not self.active_pixmaps:
            self.clear_content_layout()
            return

        # Suppress painting updates to prevent flicker during container teardown & rebuild
        self.setUpdatesEnabled(False)
        try:
            self.clear_content_layout()

            dpr = self.devicePixelRatioF()
            viewport = self.scroll_area.viewport()
            
            base_h = viewport.height()
            if base_h <= 50:
                base_h = self.scroll_area.height()
            if base_h <= 50 and self.window:
                bars_height = 0
                if self.window.tab_bar.isVisible():
                    bars_height += self.window.tab_bar.height()
                if self.window.top_bar_widget.isVisible():
                    bars_height += self.window.top_bar_widget.height()
                if self.window.bottom_bar_widget.isVisible():
                    bars_height += self.window.bottom_bar_widget.height()
                if bars_height == 0:
                    bars_height = 130
                base_h = max(200, self.window.height() - bars_height)
            if base_h <= 50:
                base_h = 800

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(0)
            row_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            for px in self.active_pixmaps:
                if not px or px.isNull():
                    continue

                target_h = int(base_h * dpr * self.zoom_factor)
                scaled = px.scaledToHeight(target_h, Qt.TransformationMode.SmoothTransformation)
                scaled.setDevicePixelRatio(dpr)
                lbl = QLabel()
                lbl.setPixmap(scaled)
                lbl.setFixedSize(int(scaled.width() / dpr), int(scaled.height() / dpr))
                row_layout.addWidget(lbl)

            self.content_layout.addWidget(row_widget, alignment=Qt.AlignmentFlag.AlignCenter)

            h_bar = self.scroll_area.horizontalScrollBar()
            v_bar = self.scroll_area.verticalScrollBar()
            if self.zoom_factor <= 1.0:
                v_bar.setValue(0)
            else:
                v_bar.setValue((v_bar.maximum() - v_bar.minimum()) // 2)
            h_bar.setValue((h_bar.maximum() - h_bar.minimum()) // 2)
        finally:
            self.setUpdatesEnabled(True)

    def display_message(self, text):
        self.clear_content_layout()
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(lbl)

    def clear_content_layout(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                sub_layout = item.layout()
                while sub_layout.count():
                    sub_item = sub_layout.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

    def close_handles(self):
        if self.active_archive:
            self.active_archive.close()
            self.active_archive = None
        if self.active_pdf:
            self.active_pdf.close()
            self.active_pdf = None
        self.current_archive_path = None


class ComicReader(QMainWindow):
    MODE_SINGLE = "Single Page"
    MODE_DOUBLE_NO_COVER = "Double (No Cover)"
    MODE_DOUBLE_COVER = "Double (Cover)"
    MODE_CONTINUOUS = "Continuous"

    DIR_LTR = "LTR (Western)"
    DIR_RTL = "RTL (Manga)"

    FIT_HEIGHT = "height"
    FIT_WIDTH = "width"

    SCOPE_CHAPTER = "In Chapter"
    SCOPE_MANGA = "In Manga"

    MAX_RECENT_FILES = 10

    def __init__(self, initial_file=None):
        super().__init__()
        self.setWindowTitle("Comic Reader")
        self.resize(1150, 900)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.initial_file = os.path.abspath(initial_file) if initial_file and os.path.isfile(initial_file) else None

        self.settings = QSettings("ComicApp", "ComicReader")
        self.dark_mode = self.settings.value("dark_mode", True, type=bool)
        self.reading_mode = self.settings.value("reading_mode", self.MODE_SINGLE, type=str)
        self.reading_direction = self.settings.value("reading_direction", self.DIR_LTR, type=str)
        self.page_scope = self.settings.value("page_scope", self.SCOPE_CHAPTER, type=str)

        raw_recents = self.settings.value("recent_files", [], type=list)
        self.recent_files = [f for f in raw_recents if isinstance(f, str) and os.path.isfile(f)]

        self.was_maximized_before_fs = False
        self.local_server = None

        self._init_ui()
        self._apply_theme()
        self.sync_ui_with_tab()

        # Restore past session first, then load the launch file at the rightmost tab
        QTimer.singleShot(0, self._handle_startup_tabs)

    def setup_single_instance_server(self, server_name: str):
        self.local_server = QLocalServer(self)
        QLocalServer.removeServer(server_name)
        self.local_server.listen(server_name)
        self.local_server.newConnection.connect(self._handle_new_instance_connection)

    def _handle_new_instance_connection(self):
        client_socket = self.local_server.nextPendingConnection()
        if not client_socket:
            return

        def read_data():
            raw_bytes = client_socket.readAll().data()
            file_path = raw_bytes.decode("utf-8").strip()
            if file_path and os.path.isfile(file_path):
                self.open_single_file(file_path)

            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            self.show()
            self.raise_()
            self.activateWindow()

        client_socket.readyRead.connect(read_data)

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Tab Bar
        self.tab_bar = QTabBar()
        self.tab_bar.setTabsClosable(False)
        self.tab_bar.setMovable(True)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setElideMode(Qt.TextElideMode.ElideRight)
        self.tab_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_bar.customContextMenuRequested.connect(self._show_tab_context_menu)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tab_bar)

        # 2. Top Bar
        self.top_bar_widget = QWidget()
        top_bar = QHBoxLayout(self.top_bar_widget)
        top_bar.setContentsMargins(10, 6, 10, 6)

        self.btn_open_file = QPushButton("Open File")
        self.btn_open_file.clicked.connect(self.browse_file)
        top_bar.addWidget(self.btn_open_file)

        self.recent_combo = QComboBox()
        self.recent_combo.setFixedWidth(300)
        self.recent_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._populate_recent_dropdown()
        self.recent_combo.activated.connect(self._on_recent_selected)
        top_bar.addWidget(self.recent_combo)

        self.btn_theme = QPushButton()
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.setIconSize(QSize(18, 18))
        self.btn_theme.clicked.connect(self.toggle_theme)
        top_bar.addWidget(self.btn_theme)

        self.btn_fullscreen = QPushButton("⛶ Fullscreen")
        self.btn_fullscreen.setToolTip("Toggle Fullscreen (F11 or F, Esc to exit)")
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        top_bar.addWidget(self.btn_fullscreen)

        top_bar.addSpacing(10)

        top_bar.addWidget(QLabel("Direction:"))
        self.dir_combo = QComboBox()
        self.dir_combo.addItems([self.DIR_LTR, self.DIR_RTL])
        self.dir_combo.setCurrentText(self.reading_direction)
        self.dir_combo.currentTextChanged.connect(self._on_direction_changed)
        top_bar.addWidget(self.dir_combo)

        top_bar.addSpacing(10)

        top_bar.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            self.MODE_SINGLE,
            self.MODE_DOUBLE_NO_COVER,
            self.MODE_DOUBLE_COVER,
            self.MODE_CONTINUOUS
        ])
        self.mode_combo.setCurrentText(self.reading_mode)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        top_bar.addWidget(self.mode_combo)

        top_bar.addStretch()

        self.btn_prev_ch = QPushButton("◀ Prev")
        self.btn_prev_ch.clicked.connect(self.prev_chapter)
        top_bar.addWidget(self.btn_prev_ch)

        self.chapter_combo = QComboBox()
        self.chapter_combo.setMinimumWidth(220)
        self.chapter_combo.currentIndexChanged.connect(self._on_chapter_selected)
        top_bar.addWidget(self.chapter_combo)

        self.btn_next_ch = QPushButton("Next ▶")
        self.btn_next_ch.clicked.connect(self.next_chapter)
        top_bar.addWidget(self.btn_next_ch)

        main_layout.addWidget(self.top_bar_widget)

        # 3. Stacked Viewport Area
        self.stack_widget = QStackedWidget()
        main_layout.addWidget(self.stack_widget)

        # 4. Bottom Bar
        self.bottom_bar_widget = QWidget()
        bottom_bar = QHBoxLayout(self.bottom_bar_widget)
        bottom_bar.setContentsMargins(10, 6, 10, 6)

        left_group = QHBoxLayout()
        left_group.addWidget(QLabel("Zoom:"))
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedWidth(30)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        left_group.addWidget(self.btn_zoom_out)

        self.lbl_zoom = QLineEdit("100%")
        self.lbl_zoom.setFixedWidth(52)
        self.lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_zoom.setValidator(QIntValidator(20, 800))
        self.lbl_zoom.returnPressed.connect(self._on_zoom_entered)
        self.lbl_zoom.editingFinished.connect(self._on_zoom_entered)
        left_group.addWidget(self.lbl_zoom)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedWidth(30)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        left_group.addWidget(self.btn_zoom_in)

        self.btn_zoom_reset = QPushButton("Reset")
        self.btn_zoom_reset.clicked.connect(self.zoom_reset)
        left_group.addWidget(self.btn_zoom_reset)

        left_group.addSpacing(6)

        self.btn_fit_height = QPushButton("Fit H")
        self.btn_fit_height.clicked.connect(self.set_fit_height)
        left_group.addWidget(self.btn_fit_height)

        self.btn_fit_width = QPushButton("Fit W")
        self.btn_fit_width.clicked.connect(self.set_fit_width)
        left_group.addWidget(self.btn_fit_width)

        bottom_bar.addLayout(left_group)
        bottom_bar.addStretch(1)

        self.center_page_group = QWidget()
        center_layout = QHBoxLayout(self.center_page_group)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(4)

        self.btn_prev_pg = QPushButton("◀ Prev Page")
        self.btn_prev_pg.clicked.connect(self.prev_page)
        center_layout.addWidget(self.btn_prev_pg)

        lbl_page = QLabel("Page:")
        lbl_page.setContentsMargins(6, 0, 2, 0)
        center_layout.addWidget(lbl_page)

        self.page_input = QLineEdit()
        self.page_input.setFixedWidth(56)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.setValidator(QIntValidator(1, 99999))
        self.page_input.returnPressed.connect(self.jump_to_page)
        center_layout.addWidget(self.page_input)

        self.lbl_page_total = QLabel("/ 0")
        self.lbl_page_total.setContentsMargins(4, 0, 6, 0)
        center_layout.addWidget(self.lbl_page_total)

        self.btn_next_pg = QPushButton("Next Page ▶")
        self.btn_next_pg.clicked.connect(self.next_page)
        center_layout.addWidget(self.btn_next_pg)

        bottom_bar.addWidget(self.center_page_group)
        bottom_bar.addStretch(1)

        right_group = QHBoxLayout()
        right_group.setSpacing(8)

        self.scope_combo = QComboBox()
        self.scope_combo.addItems([self.SCOPE_CHAPTER, self.SCOPE_MANGA])
        self.scope_combo.setCurrentText(self.page_scope)
        self.scope_combo.currentTextChanged.connect(self._on_scope_changed)
        right_group.addWidget(self.scope_combo)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_group.addWidget(self.progress_bar)

        bottom_bar.addLayout(right_group)
        main_layout.addWidget(self.bottom_bar_widget)

        for w in [self.btn_open_file, self.recent_combo, self.btn_theme, self.btn_fullscreen,
                  self.dir_combo, self.mode_combo, self.scope_combo, self.btn_prev_ch, 
                  self.btn_next_ch, self.btn_prev_pg, self.btn_next_pg, self.chapter_combo,
                  self.btn_zoom_out, self.btn_zoom_in, self.btn_zoom_reset,
                  self.btn_fit_height, self.btn_fit_width]:
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def current_tab(self) -> DocumentTabWidget:
        widget = self.stack_widget.currentWidget()
        return widget if isinstance(widget, DocumentTabWidget) else None

    def _show_tab_context_menu(self, pos: QPoint):
        tab_idx = self.tab_bar.tabAt(pos)
        total_tabs = self.tab_bar.count()
        if total_tabs == 0:
            return

        menu = QMenu(self)
        
        act_close = None
        if tab_idx != -1:
            act_close = menu.addAction("Close Tab")

        act_close_others = menu.addAction("Close Other Tabs")
        act_close_left = menu.addAction("Close Tabs to the Left")
        act_close_right = menu.addAction("Close Tabs to the Right")
        menu.addSeparator()
        act_close_all = menu.addAction("Close All Tabs")

        if tab_idx == -1:
            act_close_others.setEnabled(False)
            act_close_left.setEnabled(False)
            act_close_right.setEnabled(False)
        else:
            act_close_others.setEnabled(total_tabs > 1)
            act_close_left.setEnabled(tab_idx > 0)
            act_close_right.setEnabled(tab_idx < total_tabs - 1)

        action = menu.exec(self.tab_bar.mapToGlobal(pos))
        if not action:
            return

        if act_close and action == act_close:
            self.close_tab(tab_idx)
        elif action == act_close_others:
            self.close_other_tabs(tab_idx)
        elif action == act_close_left:
            self.close_tabs_left(tab_idx)
        elif action == act_close_right:
            self.close_tabs_right(tab_idx)
        elif action == act_close_all:
            self.close_all_tabs()

    def close_all_tabs(self):
        while self.tab_bar.count() > 0:
            self.close_tab(0)

    def close_other_tabs(self, keep_idx: int):
        for idx in range(self.tab_bar.count() - 1, keep_idx, -1):
            self.close_tab(idx)
        for idx in range(keep_idx - 1, -1, -1):
            self.close_tab(idx)

    def close_tabs_left(self, target_idx: int):
        for idx in range(target_idx - 1, -1, -1):
            self.close_tab(idx)

    def close_tabs_right(self, target_idx: int):
        for idx in range(self.tab_bar.count() - 1, target_idx, -1):
            self.close_tab(idx)

    def _setup_tab_close_button(self, idx: int):
        btn = QToolButton(self.tab_bar)
        btn.setObjectName("TabCloseButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(26, 26)
        btn.setIconSize(QSize(22, 22))
        btn.setAutoRaise(True)
        btn.clicked.connect(lambda _, b=btn: self._on_tab_close_clicked(b))
        self.tab_bar.setTabButton(idx, QTabBar.ButtonPosition.RightSide, btn)

    def _on_tab_close_clicked(self, button: QWidget):
        for i in range(self.tab_bar.count()):
            if self.tab_bar.tabButton(i, QTabBar.ButtonPosition.RightSide) == button:
                self.close_tab(i)
                break

    def _update_tab_close_icons(self):
        curr_idx = self.tab_bar.currentIndex()
        color_active = "#ffffff" if self.dark_mode else "#18181c"
        color_inactive = "#868e96" if self.dark_mode else "#adb5bd"
        hover_color = "#566c81"

        icon_active = create_tab_close_icon(color_active, hover_color)
        icon_inactive = create_tab_close_icon(color_inactive, hover_color)

        for i in range(self.tab_bar.count()):
            btn = self.tab_bar.tabButton(i, QTabBar.ButtonPosition.RightSide)
            if not isinstance(btn, QToolButton):
                self._setup_tab_close_button(i)
                btn = self.tab_bar.tabButton(i, QTabBar.ButtonPosition.RightSide)

            if isinstance(btn, QToolButton):
                btn.setIcon(icon_active if i == curr_idx else icon_inactive)

    def _on_tab_changed(self, index):
        if 0 <= index < self.stack_widget.count():
            # Freeze widget painting updates during tab transition
            self.stack_widget.setUpdatesEnabled(False)
            self.stack_widget.setCurrentIndex(index)
            self.stack_widget.setUpdatesEnabled(True)

            tab = self.current_tab()
            if tab and self.reading_mode != self.MODE_CONTINUOUS:
                # Render only when views haven't been constructed yet
                if not tab.content_layout.count() and tab.active_pixmaps:
                    tab.render_current_views()

        self._update_tab_close_icons()
        self.sync_ui_with_tab()
        self.setFocus()

    def sync_ui_with_tab(self):
        tab = self.current_tab()
        has_tab = tab is not None

        is_continuous = (self.reading_mode == self.MODE_CONTINUOUS)
        self.btn_fit_height.setEnabled(has_tab and is_continuous)
        self.btn_fit_width.setEnabled(has_tab and is_continuous)
        self.center_page_group.setVisible(not is_continuous)
        if not self.isFullScreen():
            self.bottom_bar_widget.setVisible(not is_continuous)

        self.chapter_combo.blockSignals(True)
        self.chapter_combo.clear()

        if not has_tab:
            self.page_input.setText("0")
            self.lbl_page_total.setText("/ 0")
            self.progress_bar.setValue(0)
            self.lbl_zoom.setText("100%")
            self.chapter_combo.blockSignals(False)
            return

        for idx, ch in enumerate(tab.chapters):
            self.chapter_combo.addItem(f"{idx + 1}. {ch['title']}")
        if 0 <= tab.current_chapter_idx < len(tab.chapters):
            self.chapter_combo.setCurrentIndex(tab.current_chapter_idx)
        self.chapter_combo.blockSignals(False)

        self.lbl_zoom.setText(f"{int(round(tab.zoom_factor * 100))}%")
        self.update_page_display()
        self.update_progress()

    def close_tab(self, index):
        if not (0 <= index < self.tab_bar.count()):
            return

        # Suppress intermediate signals so switching happens cleanly once
        self.tab_bar.blockSignals(True)
        try:
            widget = self.stack_widget.widget(index)
            if isinstance(widget, DocumentTabWidget):
                widget.close_handles()
                self.stack_widget.removeWidget(widget)
                widget.deleteLater()
            self.tab_bar.removeTab(index)
        finally:
            self.tab_bar.blockSignals(False)

        new_idx = self.tab_bar.currentIndex()
        self._on_tab_changed(new_idx)

    def _populate_recent_dropdown(self):
        self.recent_combo.blockSignals(True)
        self.recent_combo.clear()
        self.recent_combo.addItem("Recent Files...")
        for path in self.recent_files:
            file_name = os.path.basename(path)
            self.recent_combo.addItem(file_name, path)
            self.recent_combo.setItemData(self.recent_combo.count() - 1, path, Qt.ItemDataRole.ToolTipRole)
        self.recent_combo.setCurrentIndex(0)
        self.recent_combo.blockSignals(False)

    def _add_recent_file(self, file_path):
        normalized_path = os.path.normpath(file_path)
        if normalized_path in self.recent_files:
            self.recent_files.remove(normalized_path)
        self.recent_files.insert(0, normalized_path)
        self.recent_files = self.recent_files[:self.MAX_RECENT_FILES]
        self.settings.setValue("recent_files", self.recent_files)
        self._populate_recent_dropdown()

    def _on_recent_selected(self, index):
        if index <= 0:
            return
        selected_path = self.recent_combo.itemData(index)
        self.recent_combo.setCurrentIndex(0)
        if selected_path and os.path.isfile(selected_path):
            self.open_single_file(selected_path)
        else:
            QMessageBox.warning(self, "File Not Found", f"Cannot find file:\n{selected_path}")
            if selected_path in self.recent_files:
                self.recent_files.remove(selected_path)
                self.settings.setValue("recent_files", self.recent_files)
                self._populate_recent_dropdown()
        self.setFocus()

    def _apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #121214; color: #f0f0f0; }
                #top_bar_widget, #bottom_bar_widget { background-color: #1a1a1f; border-bottom: 1px solid #282830; }
                QPushButton { background-color: #2a2a35; color: #f0f0f0; border: 1px solid #3c3c4a; padding: 5px 12px; border-radius: 4px; }
                QPushButton:hover { background-color: #383848; }
                QPushButton:disabled { background-color: #1a1a20; color: #5a5a6a; border: 1px solid #282832; }
                QComboBox { background-color: #2a2a35; color: #f0f0f0; border: 1px solid #3c3c4a; padding: 4px 8px; border-radius: 4px; }
                QComboBox QAbstractItemView { background-color: #2a2a35; color: #f0f0f0; selection-background-color: #4a4a60; }
                QLineEdit { background-color: #24242e; color: #fff; border: 1px solid #3c3c4a; padding: 4px; border-radius: 4px; }
                
                QMenu {
                    background-color: #1a1a1f;
                    color: #f0f0f0;
                    border: 1px solid #3c3c4a;
                    padding: 4px;
                    border-radius: 4px;
                }
                QMenu::item {
                    padding: 6px 22px;
                    border-radius: 3px;
                }
                QMenu::item:selected {
                    background-color: #383848;
                    color: #ffffff;
                }
                QMenu::item:disabled {
                    color: #5a5a6a;
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #282830;
                    margin: 4px 6px;
                }

                QTabBar {
                    background: #0e0e10;
                    border-bottom: 1px solid #282830;
                }
                QTabBar::tab {
                    background: #18181c;
                    color: #9e9ea8;
                    border: 1px solid #282830;
                    border-bottom: none;
                    padding: 2px 10px 2px 10px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    min-width: 165px;
                    max-width: 165px;
                }
                QTabBar::tab:selected {
                    background: #2a2a35;
                    color: #ffffff;
                    border-color: #3c3c4a;
                }
                QTabBar::tab:hover:!selected {
                    background: #22222a;
                    color: #d0d0d0;
                }

                QToolButton#TabCloseButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 4px;
                    margin-left: 6px;
                    margin-right: 8px;
                }
                QToolButton#TabCloseButton:hover {
                    background-color: transparent;
                }

                QScrollArea { border: none; background-color: #121214; }
                QScrollBar:vertical {
                    background-color: #121214;
                    width: 12px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background-color: #636375;
                    min-height: 25px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #8a8a9e;
                }
                QScrollBar:horizontal {
                    background-color: #121214;
                    height: 12px;
                    margin: 0px;
                }
                QScrollBar::handle:horizontal {
                    background-color: #636375;
                    min-width: 25px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: #8a8a9e;
                }
                QScrollBar::add-line, QScrollBar::sub-line,
                QScrollBar::add-page, QScrollBar::sub-page {
                    background: none;
                    border: none;
                    height: 0px;
                    width: 0px;
                }
                QScrollBar::corner {
                    background-color: #121214;
                }

                QLabel { color: #d0d0d0; }
                QProgressBar { border: 1px solid #3c3c4a; border-radius: 4px; text-align: center; color: #f0f0f0; background-color: #1a1a20; font-size: 11px; }
                QProgressBar::chunk { background-color: #4f5d75; border-radius: 3px; }
            """)
            self.btn_theme.setIcon(QIcon(draw_sun_pixmap("#f0f0f0")))
            self.btn_theme.setText(" Light")
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #ffffff; color: #212529; }
                #top_bar_widget, #bottom_bar_widget { background-color: #f1f3f5; border-bottom: 1px solid #dee2e6; }
                QPushButton { background-color: #e9ecef; color: #212529; border: 1px solid #ced4da; padding: 5px 12px; border-radius: 4px; }
                QPushButton:hover { background-color: #dee2e6; }
                QPushButton:disabled { background-color: #f8f9fa; color: #adb5bd; border: 1px solid #e9ecef; }
                QComboBox { background-color: #ffffff; color: #212529; border: 1px solid #ced4da; padding: 4px 8px; border-radius: 4px; }
                QComboBox QAbstractItemView { background-color: #ffffff; color: #212529; selection-background-color: #e2e6ea; }
                QLineEdit { background-color: #ffffff; color: #000; border: 1px solid #ced4da; padding: 4px; border-radius: 4px; }
                
                QMenu {
                    background-color: #ffffff;
                    color: #212529;
                    border: 1px solid #ced4da;
                    padding: 4px;
                    border-radius: 4px;
                }
                QMenu::item {
                    padding: 6px 22px;
                    border-radius: 3px;
                }
                QMenu::item:selected {
                    background-color: #e9ecef;
                    color: #000000;
                }
                QMenu::item:disabled {
                    color: #adb5bd;
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #dee2e6;
                    margin: 4px 6px;
                }

                QTabBar {
                    background: #e9ecef;
                    border-bottom: 1px solid #dee2e6;
                }
                QTabBar::tab {
                    background: #f8f9fa;
                    color: #495057;
                    border: 1px solid #dee2e6;
                    border-bottom: none;
                    padding: 2px 10px 2px 10px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    min-width: 165px;
                    max-width: 165px;
                }
                QTabBar::tab:selected {
                    background: #ffffff;
                    color: #212529;
                    border-color: #ced4da;
                }
                QTabBar::tab:hover:!selected {
                    background: #f1f3f5;
                }

                QToolButton#TabCloseButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 4px;
                    margin-left: 6px;
                    margin-right: 8px;
                }
                QToolButton#TabCloseButton:hover {
                    background-color: transparent;
                }

                QScrollArea { border: none; background-color: #ffffff; }
                QScrollBar:vertical {
                    background-color: #ffffff;
                    width: 12px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background-color: #757582;
                    min-height: 25px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #4d4d58;
                }
                QScrollBar:horizontal {
                    background-color: #ffffff;
                    height: 12px;
                    margin: 0px;
                }
                QScrollBar::handle:horizontal {
                    background-color: #757582;
                    min-width: 25px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: #4d4d58;
                }
                QScrollBar::add-line, QScrollBar::sub-line,
                QScrollBar::add-page, QScrollBar::sub-page {
                    background: none;
                    border: none;
                    height: 0px;
                    width: 0px;
                }
                QScrollBar::corner {
                    background-color: #ffffff;
                }

                QLabel { color: #212529; }
                QProgressBar { border: 1px solid #ced4da; border-radius: 4px; text-align: center; color: #212529; background-color: #e9ecef; font-size: 11px; }
                QProgressBar::chunk { background-color: #4a90e2; border-radius: 3px; }
            """)
            self.btn_theme.setIcon(QIcon(draw_moon_pixmap("#212529")))
            self.btn_theme.setText(" Dark")

        self._update_tab_close_icons()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self._apply_theme()
        self.settings.setValue("dark_mode", self.dark_mode)
        self.setFocus()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            if self.was_maximized_before_fs:
                self.showMaximized()
            else:
                self.showNormal()

            configure_dwm_fullscreen(int(self.winId()), is_fullscreen=False)
            self.tab_bar.show()
            self.top_bar_widget.show()
            if self.reading_mode != self.MODE_CONTINUOUS:
                self.bottom_bar_widget.show()
            self.btn_fullscreen.setText("⛶ Fullscreen")
        else:
            self.was_maximized_before_fs = self.isMaximized()
            self.tab_bar.hide()
            self.top_bar_widget.hide()
            self.bottom_bar_widget.hide()
            self.showFullScreen()
            configure_dwm_fullscreen(int(self.winId()), is_fullscreen=True)
            self.btn_fullscreen.setText("Exit Fullscreen")
        self.setFocus()

    def _on_direction_changed(self, direction):
        self.reading_direction = direction
        self.settings.setValue("reading_direction", direction)
        tab = self.current_tab()
        if tab and tab.chapters and 0 <= tab.current_chapter_idx < len(tab.chapters):
            tab.load_page(tab.current_page_idx)
        self.setFocus()

    def _on_mode_changed(self, mode):
        self.reading_mode = mode
        self.settings.setValue("reading_mode", mode)
        tab = self.current_tab()
        if tab:
            tab.zoom_factor = 1.0
            tab.fit_mode = self.FIT_HEIGHT
            if tab.chapters and 0 <= tab.current_chapter_idx < len(tab.chapters):
                tab.load_page(tab.current_page_idx)
        self.sync_ui_with_tab()
        self.setFocus()

    def _on_scope_changed(self, scope):
        self.page_scope = scope
        self.settings.setValue("page_scope", scope)
        self.update_page_display()
        self.update_progress()
        self.setFocus()

    def _get_total_manga_pages(self):
        tab = self.current_tab()
        return sum(len(ch['pages']) for ch in tab.chapters) if tab else 0

    def _get_pages_before_chapter(self, ch_idx):
        tab = self.current_tab()
        return sum(len(tab.chapters[i]['pages']) for i in range(ch_idx)) if tab else 0

    def update_page_display(self):
        tab = self.current_tab()
        if not tab or not tab.chapters or not (0 <= tab.current_chapter_idx < len(tab.chapters)):
            self.page_input.setText("0")
            self.lbl_page_total.setText("/ 0")
            return

        curr_ch_pages = len(tab.chapters[tab.current_chapter_idx]['pages'])
        if curr_ch_pages == 0:
            self.page_input.setText("0")
            self.lbl_page_total.setText("/ 0")
            return

        offset = self._get_pages_before_chapter(tab.current_chapter_idx) if self.page_scope == self.SCOPE_MANGA else 0
        total = self._get_total_manga_pages() if self.page_scope == self.SCOPE_MANGA else curr_ch_pages
        self.lbl_page_total.setText(f"/ {total}")

        idx = tab.current_page_idx
        if self.reading_mode == self.MODE_CONTINUOUS:
            self.page_input.setText(str(idx + 1 + offset))
        elif self.reading_mode == self.MODE_DOUBLE_COVER:
            if idx == 0:
                self.page_input.setText(str(1 + offset))
            else:
                p = idx if idx % 2 != 0 else idx - 1
                if p + 1 < curr_ch_pages:
                    self.page_input.setText(f"{p + 1 + offset}-{p + 2 + offset}")
                else:
                    self.page_input.setText(str(p + 1 + offset))
        elif self.reading_mode == self.MODE_DOUBLE_NO_COVER:
            p = idx if idx % 2 == 0 else idx - 1
            if p + 1 < curr_ch_pages:
                self.page_input.setText(f"{p + 1 + offset}-{p + 2 + offset}")
            else:
                self.page_input.setText(str(p + 1 + offset))
        else:
            self.page_input.setText(str(idx + 1 + offset))

    def update_progress(self):
        tab = self.current_tab()
        if not tab or not tab.chapters or not (0 <= tab.current_chapter_idx < len(tab.chapters)):
            self.progress_bar.setValue(0)
            return

        curr_ch_pages = len(tab.chapters[tab.current_chapter_idx]['pages'])
        total_manga_pages = self._get_total_manga_pages()

        if self.page_scope == self.SCOPE_MANGA:
            if total_manga_pages <= 0:
                self.progress_bar.setValue(0)
                return
            offset = self._get_pages_before_chapter(tab.current_chapter_idx)
            if self.reading_mode == self.MODE_CONTINUOUS:
                vbar = tab.scroll_area.verticalScrollBar()
                max_val = vbar.maximum()
                val = vbar.value()
                frac = (val / max_val) if max_val > 0 else 1.0
                current_global = offset + (frac * curr_ch_pages)
                pct = int((current_global / total_manga_pages) * 100)
            else:
                current_global = offset + (tab.current_page_idx + 1)
                pct = int((current_global / total_manga_pages) * 100)
            self.progress_bar.setValue(min(100, max(0, pct)))
        else:
            if curr_ch_pages <= 0:
                self.progress_bar.setValue(0)
                return
            if self.reading_mode == self.MODE_CONTINUOUS:
                vbar = tab.scroll_area.verticalScrollBar()
                max_val = vbar.maximum()
                val = vbar.value()
                pct = int((val / max_val) * 100) if max_val > 0 else 100
            else:
                pct = int(((tab.current_page_idx + 1) / curr_ch_pages) * 100)
            self.progress_bar.setValue(min(100, max(0, pct)))

    def zoom_in(self):
        tab = self.current_tab()
        if tab and tab.zoom_factor < 8.0:
            tab.zoom_factor = round(min(8.0, tab.zoom_factor * 1.35), 2)
            self.lbl_zoom.setText(f"{int(round(tab.zoom_factor * 100))}%")
            self._apply_zoom()

    def zoom_out(self):
        tab = self.current_tab()
        if tab and tab.zoom_factor > 0.2:
            tab.zoom_factor = round(max(0.2, tab.zoom_factor / 1.35), 2)
            self.lbl_zoom.setText(f"{int(round(tab.zoom_factor * 100))}%")
            self._apply_zoom()

    def zoom_reset(self):
        tab = self.current_tab()
        if tab:
            tab.zoom_factor = 1.0
            tab.fit_mode = self.FIT_HEIGHT
            self.lbl_zoom.setText(f"{int(round(tab.zoom_factor * 100))}%")
            self._apply_zoom()

    def set_fit_height(self):
        if self.reading_mode != self.MODE_CONTINUOUS:
            return
        tab = self.current_tab()
        if tab:
            tab.fit_mode = self.FIT_HEIGHT
            tab.zoom_factor = 1.0
            self.lbl_zoom.setText(f"{int(round(tab.zoom_factor * 100))}%")
            tab.load_page(tab.current_page_idx)
            self.setFocus()

    def set_fit_width(self):
        if self.reading_mode != self.MODE_CONTINUOUS:
            return
        tab = self.current_tab()
        if tab:
            tab.fit_mode = self.FIT_WIDTH
            tab.zoom_factor = 1.0
            self.lbl_zoom.setText(f"{int(round(tab.zoom_factor * 100))}%")
            tab.load_page(tab.current_page_idx)
            self.setFocus()

    def _on_zoom_entered(self):
        tab = self.current_tab()
        if not tab:
            return
        raw_text = self.lbl_zoom.text().replace("%", "").strip()
        if raw_text.isdigit():
            percent = int(raw_text)
            percent = max(20, min(800, percent))
            tab.zoom_factor = round(percent / 100.0, 2)
            self.lbl_zoom.setText(f"{int(round(tab.zoom_factor * 100))}%")
            self._apply_zoom()
        else:
            self.lbl_zoom.setText(f"{int(round(tab.zoom_factor * 100))}%")
        self.setFocus()

    def _apply_zoom(self):
        tab = self.current_tab()
        if not tab:
            return
        if self.reading_mode == self.MODE_CONTINUOUS:
            tab.load_page(tab.current_page_idx)
        else:
            tab.render_current_views()

    def _on_chapter_selected(self, index):
        tab = self.current_tab()
        if tab and 0 <= index < len(tab.chapters) and index != tab.current_chapter_idx:
            tab.load_chapter(index)
            self.setFocus()

    def browse_file(self):
        start_file = self.settings.value("last_file_path", "")
        start_dir = os.path.dirname(start_file) if start_file else ""

        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Comic / Book Files", start_dir, "Supported Files (*.cbz *.cbr *.pdf *.epub)"
        )
        if not file_paths:
            return

        self.settings.setValue("last_file_path", file_paths[-1])
        for path in file_paths:
            self.open_single_file(path)

    def open_single_file(self, file_path, target_ch=0, target_pg=0):
        if not os.path.isfile(file_path):
            return

        normalized_path = os.path.normpath(file_path)

        for idx in range(self.stack_widget.count()):
            widget = self.stack_widget.widget(idx)
            if isinstance(widget, DocumentTabWidget) and widget.file_path == normalized_path:
                self.tab_bar.setCurrentIndex(idx)
                if target_ch != widget.current_chapter_idx or target_pg != widget.current_page_idx:
                    widget.load_chapter(target_ch, start_page=target_pg)
                return

        new_tab = DocumentTabWidget(normalized_path, self)
        if new_tab.load_document(target_ch=target_ch, target_pg=target_pg):
            title = os.path.basename(normalized_path)
            idx = self.tab_bar.addTab(title)
            self.tab_bar.setTabToolTip(idx, normalized_path)
            self.stack_widget.addWidget(new_tab)
            self._setup_tab_close_button(idx)
            self.tab_bar.setCurrentIndex(idx)
            self._update_tab_close_icons()
            self._add_recent_file(normalized_path)
            self.sync_ui_with_tab()
            QTimer.singleShot(0, new_tab.render_current_views)

        self.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        tab = self.current_tab()
        if tab and self.reading_mode != self.MODE_CONTINUOUS:
            tab.render_current_views()

    def prev_page(self):
        if self.reading_mode == self.MODE_CONTINUOUS:
            return
        tab = self.current_tab()
        if not tab or not tab.chapters:
            return

        step = 2 if "Double" in self.reading_mode else 1
        if self.reading_mode == self.MODE_DOUBLE_COVER and tab.current_page_idx in (1, 2):
            step = 1

        if tab.current_page_idx > 0:
            tab.load_page(max(0, tab.current_page_idx - step))
        elif tab.current_chapter_idx > 0:
            tab.load_chapter(tab.current_chapter_idx - 1)
            last_idx = len(tab.chapters[tab.current_chapter_idx]['pages']) - 1
            tab.load_page(last_idx)
        self.setFocus()

    def next_page(self):
        if self.reading_mode == self.MODE_CONTINUOUS:
            return
        tab = self.current_tab()
        if not tab or not tab.chapters:
            return

        step = 2 if "Double" in self.reading_mode else 1
        if self.reading_mode == self.MODE_DOUBLE_COVER and tab.current_page_idx == 0:
            step = 1

        curr_pages = tab.chapters[tab.current_chapter_idx]['pages']
        if tab.current_page_idx + step < len(curr_pages):
            tab.load_page(tab.current_page_idx + step)
        elif tab.current_chapter_idx < len(tab.chapters) - 1:
            tab.load_chapter(tab.current_chapter_idx + 1)
        self.setFocus()

    def prev_chapter(self):
        tab = self.current_tab()
        if tab and tab.current_chapter_idx > 0:
            tab.load_chapter(tab.current_chapter_idx - 1)
        self.setFocus()

    def next_chapter(self):
        tab = self.current_tab()
        if tab and tab.current_chapter_idx < len(tab.chapters) - 1:
            tab.load_chapter(tab.current_chapter_idx + 1)
        self.setFocus()

    def jump_to_page(self):
        tab = self.current_tab()
        if not tab or not tab.chapters:
            return

        text = self.page_input.text().strip()
        if not text.isdigit():
            self.update_page_display()
            self.setFocus()
            return

        target_num = int(text)
        if self.page_scope == self.SCOPE_MANGA:
            total_manga = self._get_total_manga_pages()
            if 1 <= target_num <= total_manga:
                accum = 0
                for ch_i, ch in enumerate(tab.chapters):
                    ch_len = len(ch['pages'])
                    if accum + ch_len >= target_num:
                        pg_in_ch = target_num - accum - 1
                        if ch_i != tab.current_chapter_idx:
                            tab.load_chapter(ch_i, start_page=pg_in_ch)
                        else:
                            tab.load_page(pg_in_ch)
                        break
                    accum += ch_len
            else:
                self.update_page_display()
        else:
            curr_pages = tab.chapters[tab.current_chapter_idx]['pages']
            target_idx = target_num - 1
            if 0 <= target_idx < len(curr_pages):
                tab.load_page(target_idx)
            else:
                self.update_page_display()

        self.setFocus()

    def keyPressEvent(self, event):
        if self.page_input.hasFocus() or self.lbl_zoom.hasFocus():
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()
        tab = self.current_tab()

        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_W:
                curr_idx = self.tab_bar.currentIndex()
                if curr_idx != -1:
                    self.close_tab(curr_idx)
                event.accept()
                return
            elif key == Qt.Key.Key_Tab:
                count = self.tab_bar.count()
                if count > 1:
                    self.tab_bar.setCurrentIndex((self.tab_bar.currentIndex() + 1) % count)
                event.accept()
                return
            elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.zoom_in()
                event.accept()
                return
            elif key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
                self.zoom_out()
                event.accept()
                return
            elif key == Qt.Key.Key_0:
                self.zoom_reset()
                event.accept()
                return

        if (modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)) == (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        ) and key == Qt.Key.Key_Backtab:
            count = self.tab_bar.count()
            if count > 1:
                self.tab_bar.setCurrentIndex((self.tab_bar.currentIndex() - 1) % count)
            event.accept()
            return

        if key in (Qt.Key.Key_F11, Qt.Key.Key_F):
            self.toggle_fullscreen()
            event.accept()
            return

        if key == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.toggle_fullscreen()
                event.accept()
                return

        if not tab:
            super().keyPressEvent(event)
            return

        v_bar = tab.scroll_area.verticalScrollBar()

        if self.reading_mode == self.MODE_CONTINUOUS:
            scroll_step = 300
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Right, Qt.Key.Key_Space):
                v_bar.setValue(v_bar.value() + scroll_step)
                event.accept()
            elif key in (Qt.Key.Key_Up, Qt.Key.Key_Left):
                v_bar.setValue(v_bar.value() - scroll_step)
                event.accept()
            elif key == Qt.Key.Key_PageDown:
                v_bar.setValue(v_bar.value() + tab.scroll_area.viewport().height())
                event.accept()
            elif key == Qt.Key.Key_PageUp:
                v_bar.setValue(v_bar.value() - tab.scroll_area.viewport().height())
                event.accept()
            else:
                super().keyPressEvent(event)
            return

        if self.reading_direction == self.DIR_RTL:
            forward_keys = (Qt.Key.Key_Left, Qt.Key.Key_Down, Qt.Key.Key_Space, Qt.Key.Key_PageDown, Qt.Key.Key_A)
            backward_keys = (Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Backspace, Qt.Key.Key_PageUp, Qt.Key.Key_D)
        else:
            forward_keys = (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_Space, Qt.Key.Key_PageDown, Qt.Key.Key_D)
            backward_keys = (Qt.Key.Key_Left, Qt.Key.Key_Up, Qt.Key.Key_Backspace, Qt.Key.Key_PageUp, Qt.Key.Key_A)

        if key in forward_keys:
            self.next_page()
            event.accept()
        elif key in backward_keys:
            self.prev_page()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _handle_startup_tabs(self):
        geom = self.settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)

        saved_tabs = self.settings.value("session_tabs", [], type=list)
        active_tab_idx = self.settings.value("session_active_tab", 0, type=int)

        # 1. Restore previous tabs from session first
        if isinstance(saved_tabs, list) and saved_tabs:
            for item in saved_tabs:
                if isinstance(item, dict):
                    path = item.get("path")
                    ch = item.get("chapter", 0)
                    pg = item.get("page", 0)
                    if path and os.path.isfile(path):
                        self.open_single_file(path, target_ch=ch, target_pg=pg)

            if 0 <= active_tab_idx < self.tab_bar.count():
                self.tab_bar.setCurrentIndex(active_tab_idx)
                self._update_tab_close_icons()

        # 2. If an initial file was double-clicked, open it at the end and activate it
        if self.initial_file:
            self.open_single_file(self.initial_file)
            target_idx = -1
            for idx in range(self.stack_widget.count()):
                w = self.stack_widget.widget(idx)
                if isinstance(w, DocumentTabWidget) and w.file_path == os.path.normpath(self.initial_file):
                    target_idx = idx
                    break
            if target_idx != -1:
                self.tab_bar.setCurrentIndex(target_idx)

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())

        session_tabs = []
        for idx in range(self.stack_widget.count()):
            widget = self.stack_widget.widget(idx)
            if isinstance(widget, DocumentTabWidget):
                session_tabs.append({
                    "path": widget.file_path,
                    "chapter": widget.current_chapter_idx,
                    "page": widget.current_page_idx,
                })
                widget.close_handles()

        self.settings.setValue("session_tabs", session_tabs)
        self.settings.setValue("session_active_tab", self.tab_bar.currentIndex())

        if self.local_server:
            self.local_server.close()

        event.accept()


if __name__ == "__main__":
    SERVER_NAME = "ComicReader_SingleInstance_IPC_Socket"

    # Set distinct AppUserModelID so Windows 11 binds taskbar items to app.ico
    if sys.platform == "win32":
        myappid = "trietc.comicreader.app.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    # 1. Attempt to connect to an existing running instance
    client_socket = QLocalSocket()
    client_socket.connectToServer(SERVER_NAME)

    if client_socket.waitForConnected(500):
        # Already running: pass file path argument and exit
        if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
            file_path = os.path.abspath(sys.argv[1])
            client_socket.write(file_path.encode("utf-8"))
            client_socket.waitForBytesWritten(1000)
        client_socket.disconnectFromServer()
        sys.exit(0)

    # 2. Main instance: configure application icon
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    app_icon_path = os.path.join(base_path, "icons", "app.ico")
    if os.path.isfile(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))

    # Pass command-line file to constructor for managed startup sequence
    launch_file = sys.argv[1] if (len(sys.argv) > 1 and os.path.isfile(sys.argv[1])) else None

    reader = ComicReader(initial_file=launch_file)
    reader.setup_single_instance_server(SERVER_NAME)

    reader.show()
    sys.exit(app.exec())