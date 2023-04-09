#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# MIT License
#
# Copyright (c) 2022 FIT-Project and others
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# -----
######

import logging.config
import os.path
import shutil

import numpy as np
import PIL
from PIL import Image

from scapy.all import *

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import QtWebEngineWidgets
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage

from view.web.navigationtoolbar import NavigationToolBar as NavigationToolBarView
from view.web.screenshot_select_area import SelectArea as SelectAreaView


from view.pec import Pec as PecView
from view.screenrecorder import ScreenRecorder as ScreenRecorderView
from view.packetcapture import PacketCapture as PacketCaptureView
from view.acquisitionstatus import AcquisitionStatus as AcquisitionStatusView
from view.timestamp import Timestamp as TimestampView
from view.case import Case as CaseView
from view.configuration import Configuration as ConfigurationView
from view.error import Error as ErrorView

from controller.report import Report as ReportController
from controller.web import Web as WebController

from common.error import ErrorMessage

from common.settings import DEBUG
from common.config import LogConfig
import common.utility as utility

import sslkeylog

logger_acquisition = logging.getLogger(__name__)
logger_hashreport = logging.getLogger('hashreport')
logger_whois = logging.getLogger('whois')
logger_headers = logging.getLogger('headers')
logger_nslookup = logging.getLogger('nslookup')

class WebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)

class MainWindow(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        page = WebEnginePage(self)

        self.setPage(page)

    def closeEvent(self, event):
        self.page().profile().clearHttpCache()


class Web(QtWidgets.QMainWindow):
    stop_signal = QtCore.pyqtSignal()  # make a stop signal to communicate with the workers in another threads

    def __init__(self, *args, **kwargs):
        super(Web, self).__init__(*args, **kwargs)
        self.error_msg = ErrorMessage()
        self.acquisition_directory = None
        self.screenshot_folder = None
        self.acquisition_is_started = False
        self.current_page_load_is_finished = False
        self.acquisition_status = AcquisitionStatusView(self)
        self.acquisition_status.setupUi()
        self.log_confing = LogConfig()
        self.is_enabled_screen_recorder = False
        self.is_screenrecorder_finished = False
        self.is_enabled_packet_capture = False
        self.is_packet_capture_finished = False
        self.is_stop_acquisition_finished = False
        self.is_enabled_timestamp = False
        self.case_info = None

        self.setWindowFlag(QtCore.Qt.WindowMinMaxButtonsHint, False)
        self.setObjectName('FITWeb')

    def init(self, case_info, wizard, options=None):

        self.__init__()
        self.wizard = wizard
        self.case_info = case_info

        self.screenshot_full_page = None
        if options:
            if "screenshot_full_page" in options:
                self.screenshot_full_page = options['screenshot_full_page']
        
        self.configuration_view = ConfigurationView(self)
        self.configuration_view.hide()

        self.case_view = CaseView(self.case_info, self)
        self.case_view.hide()

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)

        self.setCentralWidget(self.tabs)

        self.status = QtWidgets.QStatusBar()
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMaximumWidth(400)
        self.progress_bar.setFixedHeight(25)
        self.status.addPermanentWidget(self.progress_bar)

        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        self.setStatusBar(self.status)
        self.progress_bar.setHidden(True)

        self.navtb = NavigationToolBarView(self)
        self.addToolBar(self.navtb)


        # Uncomment to disable native menubar on Mac
        self.menuBar().setNativeMenuBar(False)

        tab_menu = self.menuBar().addMenu("&Tab")
        new_tab_action = QtWidgets.QAction(QtGui.QIcon(os.path.join('assets/images', 'ui-tab--plus.png')), "New Tab",
                                           self)
        new_tab_action.setStatusTip("Open a new tab")
        new_tab_action.triggered.connect(lambda _: self.add_new_tab())
        tab_menu.addAction(new_tab_action)

        # CONFIGURATION ACTION
        configuration_action = QtWidgets.QAction("Configuration", self)
        configuration_action.setStatusTip("Show configuration info")
        configuration_action.triggered.connect(self.configuration)
        self.menuBar().addAction(configuration_action)

        # CASE ACTION
        case_action = QtWidgets.QAction("Case", self)
        case_action.setStatusTip("Show case info")
        case_action.triggered.connect(self.case)
        self.menuBar().addAction(case_action)

        # BACK ACTION
        back_action = QtWidgets.QAction("Back to wizard", self)
        back_action.setStatusTip("Go back to the main menu")
        back_action.triggered.connect(self.__back_to_wizard)
        self.menuBar().addAction(back_action)

        self.configuration_general = self.configuration_view.get_tab_from_name("configuration_general")

        # Get network parameters for check (NTP, nslookup)
        self.configuration_network = self.configuration_general.findChild(QtWidgets.QGroupBox,
                                                                          'group_box_network_check')

        # Get timestamp parameters
        self.configuration_timestamp = self.configuration_view.get_tab_from_name("configuration_timestamp")

        self.add_new_tab(QtCore.QUrl(self.configuration_general.configuration['home_page_url']), 'Homepage')

        self.show()

        self.setWindowTitle("Freezing Internet Tool")
        self.setWindowIcon(QtGui.QIcon(os.path.join('assets/images/', 'icon.png')))

        # Enable/Disable other modules logger
        if not DEBUG:
            loggers = [logging.getLogger()]  # get the root logger
            loggers = loggers + [logging.getLogger(name) for name in logging.root.manager.loggerDict if
                                 name not in [__name__, 'hashreport']]

            self.log_confing.disable_loggers(loggers)

    def start_acquisition(self):
        # Step 1: Disable start_acquisition_action and clear current threads and acquisition information on dialog

        self.acquisition_status.clear()
        self.acquisition_status.set_title('Acquisition is started!')

        # Step 2: Create acquisiton directory
        self.acquisition_directory = self.case_view.form.controller.create_acquisition_directory(
            'web',
            self.configuration_general.configuration['cases_folder_path'],
            self.case_info['name'],
            self.tabs.currentWidget().url().toString()
        )

        if self.acquisition_directory is not None:

            self.screenshot_folder = os.path.join(self.acquisition_directory, "screenshot")
            if not os.path.isdir(self.screenshot_folder):
                os.makedirs(self.screenshot_folder)
            # show progress bar
            self.progress_bar.setHidden(False)

            self.acquisition_is_started = True

            # disable start acquisition button
            self.navtb.enable_start_acquisition_button()
            # enable screenshot buttons
            self.navtb.enable_screenshot_buttons()
            # enable stop and info acquisition button
            self.navtb.enable_stop_and_info_acquisition_button()


            self.acquisition_status.set_title('Acquisition in progress:')
            self.acquisition_status.add_task('Case Folder')
            self.acquisition_status.set_status('Case Folder', self.acquisition_directory, 'done')
            self.status.showMessage(self.acquisition_directory)
            self.progress_bar.setValue(25)

            # Step 3: Create loggin handler and start loggin information
            self.log_confing.change_filehandlers_path(self.acquisition_directory)
            logging.config.dictConfig(self.log_confing.config)
            logger_acquisition.info('Acquisition started')
            logger_acquisition.info(
                f'NTP start acquisition time: {utility.get_ntp_date_and_time(self.configuration_network.configuration["ntp_server"])}')
            self.acquisition_status.add_task('Logger')
            self.acquisition_status.set_status('Logger', 'Started', 'done')
            self.status.showMessage('Logging handler and login information have been started')
            self.progress_bar.setValue(50)

            # Step 4: Add new thread for network packet capture and start it
            self.configuration_packetcapture = self.configuration_view.get_tab_from_name("configuration_packetcapture")
            options = self.configuration_packetcapture.options
            self.is_enabled_packet_capture = options['enabled']
            if self.is_enabled_packet_capture:
                options['acquisition_directory'] = self.acquisition_directory
                self.start_packet_capture(options)
                self.acquisition_status.add_task('Network Packet Capture')
                self.acquisition_status.set_status('Network Packet Capture',
                                                   'Capture loop has been started in a new thread!', 'done')
                logger_acquisition.info('Network Packet Capture started')
                self.status.showMessage('Capture loop has been started in a new thread!')
                self.progress_bar.setValue(75)

            # Step 5: Add new thread for screen video recoder and start it
            self.configuration_screenrecorder = self.configuration_view.get_tab_from_name(
                "configuration_screenrecorder")
            options = self.configuration_screenrecorder.options
            self.is_enabled_screen_recorder = bool(options['enabled'])

            if self.is_enabled_screen_recorder:
                options['filename'] = os.path.join(self.acquisition_directory, options['filename'])
                self.start_screen_recoder(options)
                self.acquisition_status.add_task('Screen Recoder')
                self.acquisition_status.set_status('Screen Recoder', 'Recoder loop has been started in a new thread!',
                                                   'done')
                self.status.showMessage('Recoder loop has been started in a new thread!')
                self.progress_bar.setValue(100)
                logger_acquisition.info('Screen recoder started')
                logger_acquisition.info('Initial URL: ' + self.tabs.currentWidget().url().toString())
                self.acquisition_status.set_title('Acquisition started success:')

            # hidden progress bar
            self.progress_bar.setHidden(True)
            self.status.showMessage('')

    def stop_acquisition(self):

        if self.acquisition_is_started:
            self.progress_bar.setHidden(False)
            url = self.tabs.currentWidget().url().toString()

            # Step 1: Disable all actions and clear current acquisition information on dialog
            self.acquisition_is_started = False
            self.__disable_all()

            self.acquisition_status.clear()
            self.acquisition_status.set_title('Interruption of the acquisition in progress:')
            logger_acquisition.info('Acquisition stopped')
            logger_acquisition.info('End URL: ' + url)
            self.statusBar().showMessage('Message in statusbar.')

            # Stop screen recorder
            if self.is_enabled_screen_recorder:
                self.screenrecorder.stop()

            # Step 2: Get nslookup info
            logger_acquisition.info('Get NSLOOKUP info for URL: ' + url)
            logger_nslookup.info(utility.nslookup(url,
                                                  self.configuration_network.configuration["nslookup_dns_server"],
                                                  self.configuration_network.configuration["nslookup_enable_tcp"],
                                                  self.configuration_network.configuration[
                                                      "nslookup_enable_verbose_mode"]
                                                  ))

            self.status.showMessage('Get WHOIS info')
            self.progress_bar.setValue(2)

            # Step 3: Get headers info
            logger_acquisition.info('Get HEADERS info for URL: ' + url)
            logger_headers.info(utility.get_headers_information(url))

            self.status.showMessage('Get HEADERS info')
            self.progress_bar.setValue(3)

            # Step 4: Get traceroute info
            logger_acquisition.info('Get TRACEROUTE info for URL: ' + url)
            # utility.traceroute(url, os.path.join(self.acquisition_directory, 'traceroute.txt'))
            self.status.showMessage('Get TRACEROUTE info')
            self.progress_bar.setValue(8)
            ### END NETWORK CHECK ###

            ### START GET SSLKEYLOG AND SSL CERTIFICATE ###
            # Step 5: Get sslkey.log
            logger_acquisition.info('Get SSLKEYLOG')
            sslkeylog.set_keylog(os.path.join(self.acquisition_directory, 'sslkey.log'))
            self.status.showMessage('Get SSLKEYLOG')
            self.progress_bar.setValue(9)

            # Step 6: Get peer SSL certificate
            if utility.check_if_peer_certificate_exist(url):
                logger_acquisition.info('Get SSL certificate for URL:' + url)
                certificate = utility.get_peer_PEM_cert(url)
                utility.save_PEM_cert_to_CER_cert(os.path.join(self.acquisition_directory, 'server.cer'), certificate)
                self.status.showMessage('Get SSL CERTIFICATE')
                self.progress_bar.setValue(10)
            ### END GET SSLKEYLOG AND SSL CERTIFICATE ###


            # Step 7:  Save screenshot of current page
            logger_acquisition.info('Save screenshot of current page')
            self.take_full_page_screenshot(last=True)

            print("################### {} ################################".format(self.progress_bar.value()))
            self.acquisition_status.add_task('Screenshot Page')
            self.acquisition_status.set_status('ScreenShot Page', 'Screenshot of current web page is done!', 'done')

            self.status.showMessage('Save all resource of current page')
            self.progress_bar.setValue(20)

            ### START NETWORK CHECK ###
            # Step 8: Get whois info
            logger_acquisition.info('Get WHOIS info for URL: ' + url)
            logger_whois.info(utility.whois(url))
            self.status.showMessage('Get WHOIS info')
            self.progress_bar.setValue(1)

            # Step 9:  Save all resource of current page
            zip_folder = self.save_page()
            logger_acquisition.info('Save all resource of current page')
            self.acquisition_status.add_task('Save Page')
            self.acquisition_status.set_status('Save Page', zip_folder, 'done')

            try:
                # Step 10: stop packet capture
                if self.is_enabled_packet_capture:
                    self.packetcapture.stop()
            except:
                pass

            ### Waiting everything is synchronized
            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(2000, loop.quit)
            loop.exec_()

            self.status.showMessage('Calculate acquisition file hash')
            self.progress_bar.setValue(100)
            # Step 9:  Calculate acquisition hash
            logger_acquisition.info('Calculate acquisition file hash')
            files = [f.name for f in os.scandir(self.acquisition_directory) if f.is_file()]

            for file in files:
                if file != 'acquisition.hash':
                    filename = os.path.join(self.acquisition_directory, file)
                    file_stats = os.stat(filename)
                    logger_hashreport.info(file)
                    logger_hashreport.info('=========================================================')
                    logger_hashreport.info(f'Size: {file_stats.st_size}')
                    algorithm = 'md5'
                    logger_hashreport.info(f'MD5: {utility.calculate_hash(filename, algorithm)}')
                    algorithm = 'sha1'
                    logger_hashreport.info(f'SHA-1: {utility.calculate_hash(filename, algorithm)}')
                    algorithm = 'sha256'
                    logger_hashreport.info(f'SHA-256: {utility.calculate_hash(filename, algorithm)}\n')

            logger_acquisition.info('Acquisition end')

            ntp = utility.get_ntp_date_and_time(self.configuration_network.configuration["ntp_server"])
            logger_acquisition.info(f'NTP end acquisition time: {ntp}')

            logger_acquisition.info('Acquisition end')

            logger_acquisition.info('PDF generation start')
            ### generate pdf report ###
            report = ReportController(self.acquisition_directory, self.case_info)
            report.generate_pdf('web', ntp)
            logger_acquisition.info('PDF generation end')

            ### generate timestamp for the report ###
            options = self.configuration_timestamp.options
            self.is_enabled_timestamp = options['enabled']
            if self.is_enabled_timestamp:
                self.timestamp = TimestampView()
                self.timestamp.set_options(options)
                try:
                    self.timestamp.apply_timestamp(self.acquisition_directory, 'acquisition_report.pdf')
                except Exception as e:
                    error_dlg = ErrorView(QtWidgets.QMessageBox.Critical,
                                          self.error_msg.TITLES['timestamp'],
                                          self.error_msg.MESSAGES['timestamp_timeout'],
                                          "Error: %s - %s." % (e.filename, e.strerror)
                                          )

                    error_dlg.buttonClicked.connect(quit)

            self.is_stop_acquisition_finished = True
            self.__stop_acquisition_is_finished()

    def _acquisition_status(self):
        self.acquisition_status.show()

    def start_packet_capture(self, options):

        self.th_packetcapture = QtCore.QThread()

        self.packetcapture = PacketCaptureView()
        self.packetcapture.set_options(options)

        self.packetcapture.moveToThread(self.th_packetcapture)

        self.th_packetcapture.started.connect(self.packetcapture.start)
        self.packetcapture.finished.connect(self.th_packetcapture.quit)
        self.packetcapture.finished.connect(self.packetcapture.deleteLater)
        self.th_packetcapture.finished.connect(self.th_packetcapture.deleteLater)
        self.th_packetcapture.finished.connect(self._thread_packetcapture_is_finished)

        self.th_packetcapture.start()

    def _thread_packetcapture_is_finished(self):
        self.status.showMessage('Loop has been stopped and .pcap file has been saved in the case folder')
        value = self.progress_bar.value() + 30
        self.progress_bar.setValue(value)
        logger_acquisition.info('Network Packet Capture stopped')
        self.acquisition_status.add_task('Network Packet Capture')
        self.acquisition_status.set_status('Network Packet Capture',
                                           'Loop has been stopped and .pcap file has been saved in the case folder',
                                           'done')
        self.th_packetcapture.quit()
        self.th_packetcapture.wait()
        self.is_enabled_packet_capture_finished = True
        self.__stop_acquisition_is_finished()

    def start_screen_recoder(self, options):
        self.th_screenrecorder = QtCore.QThread()

        self.screenrecorder = ScreenRecorderView()
        self.screenrecorder.set_options(options)

        self.screenrecorder.moveToThread(self.th_screenrecorder)

        self.th_screenrecorder.started.connect(self.screenrecorder.start)
        self.screenrecorder.finished.connect(self.th_screenrecorder.quit)
        self.screenrecorder.finished.connect(self.screenrecorder.deleteLater)
        self.th_screenrecorder.finished.connect(self.th_screenrecorder.deleteLater)
        self.th_screenrecorder.finished.connect(self._thread_screenrecorder_is_finished)

        self.th_screenrecorder.start()

    def _thread_screenrecorder_is_finished(self):
        self.status.showMessage('Loop has been stopped and .avi file has been saved in the case folder')
        value = self.progress_bar.value() + 30
        self.progress_bar.setValue(value)
        logger_acquisition.info('Screen recoder stopped')
        self.acquisition_status.add_task('Screen Recoder')
        self.acquisition_status.set_status('Screen Recoder',
                                           'Loop has been stopped and .avi file has been saved in the case folder',
                                           'done')
        self.th_screenrecorder.quit()
        self.th_screenrecorder.wait()
        self.is_screenrecorder_finished = True
        self.__stop_acquisition_is_finished()

    def save_page(self):
        project_folder = self.acquisition_directory

        project_name = "acquisition_page"
        acquisition_page_folder = os.path.join(project_folder, project_name)
        if not os.path.isdir(acquisition_page_folder):
            os.makedirs(acquisition_page_folder)

        # call controller here
        web = WebController(self.tabs.currentWidget().url(),acquisition_page_folder)
        web.save_html()

        #self.tabs.currentWidget().page().save(file_name)

        zip_folder = shutil.make_archive(acquisition_page_folder, 'zip', acquisition_page_folder)
        try:
            shutil.rmtree(acquisition_page_folder)
        except OSError as e:
            error_dlg = ErrorView(QtWidgets.QMessageBox.Critical,
                                  self.error_msg.TITLES['save_web_page'],
                                  self.error_msg.MESSAGES['delete_project_folder'],
                                  "Error: %s - %s." % (e.filename, e.strerror)
                                  )

            error_dlg.buttonClicked.connect(quit)
            # error_dlg.exec_()

        return zip_folder

    def case(self):
        self.case_view.exec_()

    def configuration(self):
        self.configuration_view.exec_()
    
    def take_screenshot(self):
        if self.screenshot_folder is not None:
            self.__disable_all()
            filename = utility.screenshot_filename(self.screenshot_folder ,self.tabs.currentWidget().url().host())
            self.browser.grab().save(filename)
            self.__enable_all()

    
    def take_screenshot_selected_area(self):

        if self.screenshot_folder is not None:
            self.__disable_all()
            filename = utility.screenshot_filename(self.screenshot_folder ,"selected_" + self.tabs.currentWidget().url().host())
            select_area = SelectAreaView(filename, self)
            select_area.finished.connect(self.__enable_all)
            select_area.snip_area()
    
    def take_full_page_screenshot(self, last=False):
        
        if self.screenshot_folder is not None:
        
            full_page_folder = os.path.join(self.screenshot_folder + "/full_page/{}/".format(self.tabs.currentWidget().url().host()))
            if not os.path.isdir(full_page_folder):
                os.makedirs(full_page_folder)
            
            self.status.showMessage('Save screenshot of current page')
            
            if last is False:
                self.progress_bar.setHidden(False)

            self.__disable_all()
            #move page on top
            self.tabs.currentWidget().page().runJavaScript("window.scrollTo(0, 0);")
           
            next = 0
            part = 0
            step = self.browser.height()
            end = self.tabs.currentWidget().page().contentsSize().toSize().height()
            parts = end/step
            
            increment = 90/parts
            progress = 0
            if last:
                increment = 10/parts
                progress = self.progress_bar.value()

            

            images = []
            
            while next < end:
                filename = utility.screenshot_filename(full_page_folder,"part_" + str(part))
                if next == 0:
                    self.browser.grab().save(filename)
                else:
                    self.tabs.currentWidget().page().runJavaScript("window.scrollTo({}, {});".format(0, next))
                    ### Waiting everything is synchronized
                    loop = QtCore.QEventLoop()
                    QtCore.QTimer.singleShot(500, loop.quit)
                    loop.exec_()
                    self.browser.grab().save(filename)
                
                progress += increment
                self.progress_bar.setValue(progress)

                images.append(filename)
                
                part += 1
                next += step

            #combine all images part in an unique image
            imgs    = [ Image.open(i) for i in images ]
            # pick the image which is the smallest, and resize the others to match it (can be arbitrary image shape here)
            min_shape = sorted( [(np.sum(i.size), i.size ) for i in imgs])[0][1]

            # for a vertical stacking it is simple: use vstack
            imgs_comb = np.vstack([i.resize(min_shape) for i in imgs])
            imgs_comb = Image.fromarray( imgs_comb)

            whole_img_filename = utility.screenshot_filename(full_page_folder,"full_page" + "")

            if last:
                whole_img_filename = os.path.join(self.acquisition_directory, 'screenshot.png' )
            
            imgs_comb.save(whole_img_filename)
            if last:
                self.progress_bar.setValue(10 - progress)
            else:
                self.progress_bar.setValue(100 - progress)
            self.__enable_all()

            if last is False:
                self.progress_bar.setHidden(True)


    def back(self):
        if self.acquisition_is_started:
            logger_acquisition.info('User clicked the back button')
        self.tabs.currentWidget().back()

    def forward(self):
        if self.acquisition_is_started:
            logger_acquisition.info('User clicked the forward button')
        self.tabs.currentWidget().forward()

    def reload(self):
        if self.acquisition_is_started:
            logger_acquisition.info('User clicked the reload button')
        self.tabs.currentWidget().reload()

    def add_new_tab(self, qurl=None, label="Blank"):
        self.current_page_load_is_finished = False

        if qurl is None:
            qurl = QtCore.QUrl('')

        self.browser = MainWindow()
        self.browser.setUrl(qurl)
        i = self.tabs.addTab(self.browser, label)

        self.tabs.setCurrentIndex(i)

        # More difficult! We only want to update the url when it's from the
        # correct tab
        self.browser.urlChanged.connect(lambda qurl, browser=self.browser:
                                        self.__update_urlbar(qurl, browser))

        self.browser.loadProgress.connect(self.load_progress)

        self.browser.loadFinished.connect(lambda _, i=i, browser=self.browser:
                                          self.__page_on_loaded(i, browser))

        if i == 0:
            self.showMaximized()
        
    def __page_on_loaded(self, tab_index, browser):
        self.tabs.setTabText(tab_index, browser.page().title())

        self.current_page_load_is_finished = True
        self.navtb.enable_screenshot_buttons()


    def tab_open_doubleclick(self, i):
        if i == -1 and self.isEnabled():  # No tab under the click
            self.add_new_tab()

    def current_tab_changed(self, i):
        if self.tabs.currentWidget() is not None:
            qurl = self.tabs.currentWidget().url()
            self.__update_urlbar(qurl, self.tabs.currentWidget())
            self.update_title(self.tabs.currentWidget())

    def close_current_tab(self, i):
        if self.acquisition_is_started:
            logger_acquisition.info('User remove tab')
        if self.tabs.count() < 2:
            return

        self.tabs.removeTab(i)

    def update_title(self, browser):
        if browser != self.tabs.currentWidget():
            # If this signal is not from the current tab, ignore
            return

        title = self.tabs.currentWidget().page().title()
        self.setWindowTitle("%s - Freezing Internet Tool" % title)

    def navigate_home(self):
        if self.acquisition_is_started:
            logger_acquisition.info('User clicked the home button')
        self.tabs.currentWidget().setUrl(QtCore.QUrl(self.configuration_general.configuration['home_page_url']))

    def navigate_to_url(self):  # Does not receive the Url
        q = QtCore.QUrl(self.navtb.urlbar.text())
        if q.scheme() == "":
            q.setScheme("http")

        self.tabs.currentWidget().setUrl(q)

    def load_progress(self, prog):
        if self.acquisition_is_started and prog == 100:
            logger_acquisition.info('Loaded: ' + self.tabs.currentWidget().url().toString())

    def __update_urlbar(self, q, browser=None):

        self.current_page_load_is_finished = False
        self.navtb.enable_screenshot_buttons()

        if browser != self.tabs.currentWidget():
            # If this signal is not from the current tab, ignore
            return
        
        if q.scheme() == 'https':
            # Secure padlock icon
            pixmap = QtGui.QPixmap(os.path.join('assets/svg/toolbar', 'lock-close.svg'))
            self.navtb.httpsicon.setPixmap(pixmap.scaled(16, 16, QtCore.Qt.KeepAspectRatio))

        else:
            # Insecure padlock icon
            pixmap = QtGui.QPixmap(os.path.join('assets/svg/toolbar', 'lock-open.svg'))
            self.navtb.httpsicon.setPixmap(pixmap.scaled(16, 16, QtCore.Qt.KeepAspectRatio))

        self.navtb.urlbar.setText(q.toString())
        self.navtb.urlbar.setCursorPosition(0)

    def __back_to_wizard(self):
          if self.acquisition_is_started is False:
            self.deleteLater()
            self.wizard.reload_case_info()
            self.wizard.show()

    def __disable_all(self):
        self.setEnabled(False)
        self.navtb.setEnabled(False)
        self.navtb.enable_actions(enabled=False)

    
    def __enable_all(self):
        self.setEnabled(True)
        self.navtb.setEnabled(True)
        self.navtb.enable_actions(filter=self.navtb.navigation_actions)
        self.navtb.enable_screenshot_buttons()
        self.navtb.enable_start_acquisition_button()
        self.navtb.enable_stop_and_info_acquisition_button()

    
    def __stop_acquisition_is_finished(self):
        if self.is_enabled_packet_capture and self.is_enabled_screen_recorder and self.is_stop_acquisition_finished:
            self.__enable_all()
            self.pec = PecView()
            self.pec.hide()
            self.acquisition_window = self.pec
            self.acquisition_window.init(self.case_info, "Web", self.acquisition_directory)
            self.acquisition_window.show()


            # hidden progress bar
            self.progress_bar.setHidden(True)
            self.status.showMessage('')

            # delete cookies from the store and clean the cache
            cookie_store = self.tabs.currentWidget().page().profile().cookieStore()
            cookie_store.deleteAllCookies()
            self.tabs.currentWidget().page().profile().clearAllVisitedLinks()
            self.tabs.currentWidget().page().profile().clearHttpCache()


    def closeEvent(self, event):
        event.ignore()
        self.__back_to_wizard()

