import sys
import os
from datetime import datetime
import logging

from PyQt5.QtCore import QThread, pyqtSignal, Qt 
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtGui import QIcon

from py_rc.RelicKeeperUI import Ui_MainWindow
from py_rc.PageController import PageController
from py_rc.AdvancedMessageWindow import AdvancedMessageWindow
from py_rc.ocr import ocr_img, find_yuanshen_window

# 配置日志
logging.basicConfig(filename='relicsLog.txt', level=logging.INFO,
                    format='[%(asctime)s] - %(funcName)s - 【%(levelname)s】 - %(message)s')
logger = logging.getLogger(__name__)

class OCRThread(QThread):
    update_text_signal = pyqtSignal(list)

    def __init__(self, genshin_window, logger):
        super().__init__()
        
        self.is_paused = False
        self.genshin_window = genshin_window
        self.logger = logger

        from py_rc.RapidOCR_api import OcrAPI
        #############################更改相对路径
        self.testImgPath = "D:\\原神\\刷本记录\\Python实现\\cangbaimao.png"
        #############################更改相对路径
        ocrPath = ".\\RapidOCR-json_v0.2.0\\RapidOCR-json.exe"
        #############################更改相对路径
        if not os.path.exists(ocrPath):
            #print(f"未在以下路径找到引擎！\n{ocrPath}")
            ocr_msg_window = AdvancedMessageWindow()
            ocr_msg_window.show_message_box('warning', '错误', '未在以下路径找到引擎！\n' + ocrPath)
            self.logger.error("未在以下路径找到引擎！--- " + ocrPath)
            sys.exit()
        self.ocr = OcrAPI(ocrPath)
    def run(self):
        self.logger.info("开始OCR识别...")
        while True:
            if not self.is_paused:
                    print("OCR线程开始工作...")
                    
                    text_list = ocr_img(self.genshin_window, self.ocr, self.logger)
                    if text_list is not None:
                        #print(text_list)
                        del text_list[4]
                        self.logger.info("OCR识别成功，开始处理结果...")
                        self.update_text_signal.emit(text_list)
                
            self.sleep(1)
    def pause(self):
        self.is_paused = True
        self.logger.info("暂停OCR识别...")

    def resume(self):
        self.is_paused = False
        self.logger.info("重新开始OCR识别...")

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        logger.info("窗口初始化开始...")
        self.page = []
        self.page_controller = PageController(self.page)
        self.scrolling = False  # 避免重复发送滚动事件
        self.ocr_thread = None
        self.last_recorded_date = None  # 记录当天记录的日期

        self.file_path = "圣遗物刷本记录.txt"
        self.genshin_window = find_yuanshen_window()
        self.initUI()
        logger.info("窗口初始化结束...")

    def initUI(self):
        self.setupUi(self)   # 调用Qt Designer生成的UI文件-
        self.setWindowIcon(QIcon('ObsidianCodex_128.ico'))
        
        # 启动窗口位于右边，避免截图截到窗口
        desktop = QApplication.desktop()
        self.move(desktop.width() - self.width() - 100, (desktop.height() - self.height()) // 2)

        self.pushButton_start.clicked.connect(self.button_start_click)
        self.pushButton_left.clicked.connect(self.button_left_click)
        self.pushButton_right.clicked.connect(self.button_right_click)
        self.pushButton_open.clicked.connect(self.pushButton_open_click)
        self.pushButton_clear.clicked.connect(self.pushButton_clear_click)

    def wheelEvent(self, event):
        # 避免重复触发事件
        if self.scrolling:
            self.process_wheel_event(event)
            
    def process_wheel_event(self, event):
        try:
            if event.angleDelta().y() > 0:
                self.page_controller.previous_page()
            else:
                self.page_controller.next_page()
            self.update_text()
        except Exception as e:
            print(f"处理鼠标滚轮事件时发生错误: {e}")
            logger.error(f"处理鼠标滚轮事件时发生错误: {e}")

    # 将筛选结果写入txt文件
    def file_to_txt(self, file_path, result, current_date=None):
        with open(file_path, "a") as file:
            if current_date is not None:
                file.write(f"日期: {current_date}\n")
            for line in result:
                file.write(line + " ")
            file.write("\n")
        # 关闭文件
        

    def button_start_click(self):
        """
        控制OCR线程的启动、暂停和恢复。
        
        当按钮被点击时，根据当前线程状态进行相应的操作：
        - 如果线程不存在或未运行，创建并启动线程，将按钮文本设置为“暂停”。
        - 如果线程已启动但处于暂停状态，恢复线程运行，将按钮文本设置为“暂停”。
        - 如果线程正在运行，暂停线程，将按钮文本设置为“开始”。
        """
        try:
                
            if self.genshin_window is not None:
                # 检查时间线程是否不存在或未运行
                if self.ocr_thread is None or not self.ocr_thread.isRunning():
                    # 创建一个新的时间线程实例
                    self.ocr_thread = OCRThread(self.genshin_window, logger)
                    # 连接线程的update_text_signal信号到self的on_update_text方法，以便线程可以更新UI
                    self.ocr_thread.update_text_signal.connect(self.on_update_text)
                    # 启动线程
                    self.ocr_thread.start()
                    # 将按钮文本设置为“暂停”，以便用户可以暂停运行中的线程
                    self.pushButton_start.setText("暂停")
                # 如果时间线程已启动但目前处于暂停状态
                elif self.ocr_thread.is_paused:
                    # 恢复线程运行
                    self.ocr_thread.resume()
                    # 将按钮文本重新设置为“暂停”
                    self.pushButton_start.setText("暂停")
                else:
                    # 如果线程正在运行，暂停它
                    self.ocr_thread.pause()
                    # 将按钮文本设置为“开始”，以便用户可以重新开始线程
                    self.pushButton_start.setText("开始")
        except Exception as e:
            print(f"处理按钮点击事件时发生错误: {e}")
            logger.error(f"处理按钮点击事件时发生错误: {e}")

    def button_left_click(self):
        self.page_controller.previous_page()
        self.update_text()
    def button_right_click(self):
        self.page_controller.next_page()
        self.update_text()

    def on_update_text(self, list_text):
        # 当前日期
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        if list_text is not None:           # 防止空内容
            self.scrolling = True           # 避免重复发送滚动事件.这里解除限制
            if list_text not in self.page:  # 防止重复添加
                self.page.append(list_text)
                
                if self.last_recorded_date != current_date:
                    self.last_recorded_date = current_date
                    self.file_to_txt(self.file_path, list_text, current_date)
                else:
                    self.file_to_txt(self.file_path, list_text)

            self.page_controller.current_page = len(self.page) - 1
            self.update_text()
    def update_text(self):
        results = self.page_controller.get_current_text()
        # 清空原有的文本
        if results is not None:
            self.textEdit.clear()
            for result in results:
                self.textEdit.append(result)
            self.label.setText(f"第 {self.page_controller.current_page+1} 页") 

    def pushButton_open_click(self):
        import subprocess
        try:
            if not os.path.exists(self.file_path):  # 如果文件不存在，则创建一个空的文件
                with open(self.file_path, 'w') as f:
                    pass
            # 使用 subprocess 打开记事本，不显示 CMD 窗口
            subprocess.Popen(['notepad.exe', self.file_path], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            print(f"出现错误: {e}")
            logger.error(f"出现错误: {e}")

    def pushButton_clear_click(self, file_path):

        import re
        try:
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            print(f"文件大小: {file_size} 字节")
            
            if file_size != 0:
                # 读取txt文件的内容每一行的内容生成字典类型 x1{位置：内容}
                x1 = {}
                with open(file_path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                    
                    for i, line in enumerate(lines):
                        x1[i] = line.strip()
                
                # 复制x2 = x1
                x2 = x1.copy()
                # 对x2进行去除空格星号等操作保存为x3
                x3 = {k: re.sub(r'[^\w\s%+.]|\+(?!\d)|(?<=\+)(?=\D)', '', v.replace(' ', '')) for k, v in x2.items()}
                
                # 对x3去除相同的值，返回去除掉的值的位置
                removed_values = []
                seen_values = set()
                for k, v in list(x3.items()):
                    if v in seen_values:
                        removed_values.append(k)
                        del x3[k]
                    else:
                        seen_values.add(v)
                
                # 根据x3去除掉的值的位置，在x1中去除这些位置的值
                for position in removed_values:
                    x1.pop(position, None)

                # 把x1重新写入txt文件
                with open(file_path, 'w', encoding='utf-8') as file:
                    for value in x1.values():
                        file.write(value + '\n')

                print("重复行已经从文件中删除")
                logger.info("重复行已经从文件中删除")
        
        except FileNotFoundError:
            print(f"文件未找到: {file_path}")
            logger.error(f"文件未找到: {file_path}")
        except IOError as e:
            print(f"输入输出错误: {e}")
            logger.error(f"输入输出错误: {e}")
        except Exception as e:
            print(f"处理文件时发生错误: {e}")
            logger.error(f"处理文件时发生错误: {e}")
            

if __name__ == '__main__':
    # 设置高DPI缩放因子舍入策略为传递模式，这影响如何处理DPI缩放计算中的小数部分
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # 启用高DPI缩放，使得应用程序能够更好地在高DPI显示器上显示
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    # 启用高DPI图标缩放，提升高DPI显示器上图标的显示质量
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())