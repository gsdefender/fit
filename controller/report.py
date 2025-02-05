#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######  
import fnmatch
import os

from xhtml2pdf import pisa
from PyPDF2 import PdfMerger
import zipfile
from common.utility import get_logo, get_version, get_language



class Report:

    def __init__(self, cases_folder_path, case_info):
        self.cases_folder_path = cases_folder_path
        self.output_front = os.path.join(self.cases_folder_path, "front_report.pdf")
        self.output_content = os.path.join(self.cases_folder_path, "content_report.pdf")
        self.output_front_result = open(self.output_front, "w+b")
        self.output_content_result = open(self.output_content, "w+b")
        self.case_info = case_info

        language = get_language()
        if language == 'Italian':
            import common.constants.controller.report as REPORT
        else:
            import common.constants.controller.report_eng as REPORT
        self.REPORT = REPORT

    def generate_pdf(self, type, ntp):

        # PREPARING DATA TO FILL THE PDF
        if type == 'web':
            try:
                with open(os.path.join(self.cases_folder_path, 'whois.txt'), "r") as f:
                    whois_text = f.read()
                    f.close()
            except:
                whois_text = 'Not produced'

        user_files = self.__hash_reader()

        acquisition_files = self._acquisition_files_names()

        zip_enum = self._zip_files_enum()

        # FILLING FRONT PAGE WITH DATA
        front_index_path = os.path.join("assets", "templates","front.html")
        front_index = open(front_index_path).read().format(
            img=get_logo(), t1=self.REPORT.T1,
            title=self.REPORT.TITLE, report=self.REPORT.REPORT, version=get_version()
        )

        # FILLING TEMPLATE WITH DATA
        if type == 'web':
            content_index_path = os.path.join("assets", "templates", "template_web.html")
            content_index = open(content_index_path).read().format(

                title=self.REPORT.TITLE,
                index=self.REPORT.INDEX,
                description=self.REPORT.DESCRIPTION, t1=self.REPORT.T1, t2=self.REPORT.T2,
                case=self.REPORT.CASEINFO, casedata=self.REPORT.CASEDATA,
                case0=self.REPORT.CASE, case1=self.REPORT.LAWYER, case2=self.REPORT.PROCEEDING,
                case3=self.REPORT.COURT, case4=self.REPORT.NUMBER, case5=self.REPORT.ACQUISITION_TYPE, case6=self.REPORT.ACQUISITION_DATE,

                data0=str(self.case_info['name'] or 'N/A'),
                data1=str(self.case_info['lawyer_name'] or 'N/A'),
                data2=str(self.case_info['proceeding_type'] or 'N/A'),
                data3=str(self.case_info['courthouse'] or 'N/A'),
                data4=str(self.case_info['proceeding_number'] or 'N/A'),
                typed=self.REPORT.TYPED, type=type,
                date=self.REPORT.DATE, ntp=ntp,
                t3=self.REPORT.T3, t3descr=self.REPORT.T3DESCR,
                whoisfile=whois_text,
                t4=self.REPORT.T4, t4descr=self.REPORT.T4DESCR,
                name=self.REPORT.NAME, descr=self.REPORT.DESCR,

                avi=acquisition_files[fnmatch.filter(acquisition_files.keys(), '*.avi')[0]], avid=self.REPORT.AVID,
                hash=acquisition_files['acquisition.hash'], hashd=self.REPORT.HASHD,
                log=acquisition_files['acquisition.log'], logd=self.REPORT.LOGD,
                pcap=acquisition_files['acquisition.pcap'], pcapd=self.REPORT.PCAPD,
                zip=acquisition_files[fnmatch.filter(acquisition_files.keys(), '*.zip')[0]], zipd=self.REPORT.ZIPD,
                whois=acquisition_files['whois.txt'], whoisd=self.REPORT.WHOISD,
                headers=acquisition_files['headers.txt'], headersd=self.REPORT.HEADERSD,
                nslookup=acquisition_files['nslookup.txt'], nslookupd=self.REPORT.PNGD,
                cer=acquisition_files['server.cer'], cerd=self.REPORT.CERD,
                sslkey=acquisition_files['sslkey.log'], sslkeyd=self.REPORT.SSLKEYD,
                traceroute=acquisition_files['traceroute.txt'], tracerouted=self.REPORT.TRACEROUTED,

                t5=self.REPORT.T5, t5descr=self.REPORT.T5DESCR, file=user_files,
                t6=self.REPORT.T6, t6descr=self.REPORT.T6DESCR, filedata=zip_enum,
                t7=self.REPORT.T7, t7descr=self.REPORT.T7DESCR,
                titlecc=self.REPORT.TITLECC, ccdescr=self.REPORT.CCDESCR,
                titleh=self.REPORT.TITLEH, hdescr=self.REPORT.HDESCR
            )
            pdf_options = {
                'page-size': 'Letter',
                'margin-top': '1in',
                'margin-right': '1in',
                'margin-bottom': '1in',
                'margin-left': '1in',
            }
            # create pdf front and content, merge them and remove merged files
            pisa.CreatePDF(front_index, dest=self.output_front_result, options=pdf_options)
            pisa.CreatePDF(content_index, dest=self.output_content_result, options=pdf_options)

        if type == 'email' or type == 'instagram' or type == 'youtube':
            content_index_path = os.path.join("assets", "templates",
                                              "template_email.html")
            content_index = open(content_index_path).read().format(

                title=self.REPORT.TITLE,
                index=self.REPORT.INDEX,
                description=self.REPORT.DESCRIPTION, t1=self.REPORT.T1, t2=self.REPORT.T2,
                case=self.REPORT.CASEINFO, casedata=self.REPORT.CASEDATA,
                case0=self.REPORT.CASE, case1=self.REPORT.LAWYER, case2=self.REPORT.PROCEEDING,
                case3=self.REPORT.COURT, case4=self.REPORT.NUMBER, case5=self.REPORT.ACQUISITION_TYPE, case6=self.REPORT.ACQUISITION_DATE,

                data0=str(self.case_info['name'] or 'N/A'),
                data1=str(self.case_info['lawyer_name'] or 'N/A'),
                data2=str(self.case_info['proceeding_type'] or 'N/A'),
                data3=str(self.case_info['courthouse'] or 'N/A'),
                data4=str(self.case_info['proceeding_number'] or 'N/A'),
                typed=self.REPORT.TYPED, type=type,
                date=self.REPORT.DATE, ntp=ntp,
                t4=self.REPORT.T4, t4descr=self.REPORT.T4DESCR,
                name=self.REPORT.NAME, descr=self.REPORT.DESCR,
                hash=acquisition_files['acquisition.hash'], hashd=self.REPORT.HASHD,
                log=acquisition_files['acquisition.log'], logd=self.REPORT.LOGD,
                zip=acquisition_files[fnmatch.filter(acquisition_files.keys(), '*.zip')[0]], zipd=self.REPORT.ZIPD,
                t5=self.REPORT.T5, t5descr=self.REPORT.T5DESCR, file=user_files,
                t6=self.REPORT.T6, t6descr=self.REPORT.T6DESCR, filedata=zip_enum,
                t7=self.REPORT.T7, t7descr=self.REPORT.T7DESCR,
                titlecc=self.REPORT.TITLECC, ccdescr=self.REPORT.CCDESCR,
                titleh=self.REPORT.TITLEH, hdescr=self.REPORT.HDESCR

            )
            # create pdf front and content, merge them and remove merged files
            pisa.CreatePDF(front_index, dest=self.output_front_result)
            pisa.CreatePDF(content_index, dest=self.output_content_result)

        merger = PdfMerger()
        merger.append(self.output_front_result)
        merger.append(self.output_content_result)

        merger.write(os.path.join(self.cases_folder_path, "acquisition_report.pdf"))
        merger.close()
        self.output_content_result.close()
        self.output_front_result.close()
        if os.path.exists(self.output_front):
            os.remove(self.output_front)
        if os.path.exists(self.output_content):
            os.remove(self.output_content)


    def _acquisition_files_names(self):
        acquisition_files = {}
        files = [f.name for f in os.scandir(self.cases_folder_path) if f.is_file()]
        for file in files:
            acquisition_files[file] = file

        if not any(value.endswith('.avi') for value in acquisition_files.values()):
            acquisition_files['acquisition.avi'] = self.REPORT.NOT_PRODUCED
        if not 'acquisition.hash' in acquisition_files.values():
            acquisition_files['acquisition.hash'] = self.REPORT.NOT_PRODUCED
        if not 'acquisition.log' in acquisition_files.values():
            acquisition_files['acquisition.log'] = self.REPORT.NOT_PRODUCED
        if not any(value.endswith('.pcap') for value in acquisition_files.values()):
            acquisition_files['acquisition.pcap'] = self.REPORT.NOT_PRODUCED
        if not any(value.endswith('.zip') for value in acquisition_files.values()):
            acquisition_files['acquisition.zip'] = self.REPORT.NOT_PRODUCED
        if not 'whois.txt' in acquisition_files.values():
            acquisition_files['whois.txt'] = self.REPORT.NOT_PRODUCED
        if not 'headers.txt' in acquisition_files.values():
            acquisition_files['headers.txt'] = self.REPORT.NOT_PRODUCED
        if not 'nslookup.txt' in acquisition_files.values():
            acquisition_files['nslookup.txt'] = self.REPORT.NOT_PRODUCED
        if not 'server.cer' in acquisition_files.values():
            acquisition_files['server.cer'] = self.REPORT.NOT_PRODUCED
        if not 'sslkey.log' in acquisition_files.values():
            acquisition_files['sslkey.log'] = self.REPORT.NOT_PRODUCED
        if not 'traceroute.txt' in acquisition_files.values():
            acquisition_files['traceroute.txt'] = self.REPORT.NOT_PRODUCED

        return acquisition_files

    def _zip_files_enum(self):
        zip_enum = ''
        zip_dir = ''
        # getting zip folder and passing file names and dimensions to the template
        for fname in os.listdir(self.cases_folder_path):
            if fname.endswith('.zip'):
                zip_dir = os.path.join(self.cases_folder_path, fname)

        zip_folder = zipfile.ZipFile(zip_dir)
        for zip_file in zip_folder.filelist:
            size = zip_file.file_size
            filename = zip_file.filename
            if filename.count(".") > 1:
                filename = filename.rsplit(".", 1)[0]
            else:
                pass
            if size > 0:
                zip_enum += '<p>' + filename + "</p>"
                zip_enum += '<p>'+self.REPORT.NOT_PRODUCED + str(size) + " bytes</p>"
                zip_enum += '<hr>'
        return zip_enum

    def __hash_reader(self):
        hash_text = ''
        with open(os.path.join(self.cases_folder_path, 'acquisition.hash'), "r", encoding='utf-8') as f:
            for line in f:
                hash_text += '<p>' + line + "</p>"
        return hash_text
