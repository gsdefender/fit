#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######  
import os

from xhtml2pdf import pisa
from PyPDF2 import PdfMerger

from common.utility import get_logo, get_version, get_language


class VerifyPDFTimestamp:
    def __init__(self, cases_folder_path, case_info, ntp):
        self.cases_folder_path = cases_folder_path
        self.output_front = os.path.join(self.cases_folder_path, "front_report.pdf")
        self.output_content = os.path.join(self.cases_folder_path, "content_report.pdf")
        self.output_front_result = open(self.output_front, "w+b")
        self.output_content_result = open(self.output_content, "w+b")
        self.case_info = case_info
        self.ntp = ntp

        language = get_language()
        if language == 'Italian':
            import common.constants.controller.report as REPORT
        else:
            import common.constants.controller.report_eng as REPORT
        self.REPORT = REPORT

    def generate_pdf(self, result, info_file_path):

        # PREPARING DATA TO FILL THE PDF
        with open(info_file_path, "r") as f:
            info_file = f.read()
        # FILLING FRONT PAGE WITH DATA
        front_html = os.path.join('assets/templates/front.html')
        front_index = open(front_html).read().format(
            img=get_logo(), t1=self.REPORT.T1,
            title=self.REPORT.TITLE, report=self.REPORT.REPORT, version=get_version()
        )

        if result:
            t3descr = self.REPORT.VERIFI_OK
        else:
            t3descr = self.REPORT.VERIFI_KO

        content_html = os.path.join('assets/templates/template_verification.html')
        content_index = open(content_html).read().format(

            title=self.REPORT.TITLE,
            index=self.REPORT.INDEX,
            description=self.REPORT.DESCRIPTION, t1=self.REPORT.T1, t2=self.REPORT.T2,
            case=self.REPORT.CASEINFO, casedata=self.REPORT.CASEDATA,
            case0=self.REPORT.CASE, case1=self.REPORT.LAWYER, case2=self.REPORT.PROCEEDING,
            case3=self.REPORT.COURT, case4=self.REPORT.NUMBER, case5=self.REPORT.ACQUISITION_TYPE, case6=self.REPORT.ACQUISITION_DATE,
            t3=self.REPORT.VERIFICATION, t3descr=t3descr,
            info_file=info_file,

            data0=str(self.case_info['name'] or 'N/A'),
            data1=str(self.case_info['lawyer_name'] or 'N/A'),
            data2=str(self.case_info['proceeding_type'] or 'N/A'),
            data3=str(self.case_info['courthouse'] or 'N/A'),
            data4=str(self.case_info['proceeding_number'] or 'N/A'),
            typed=self.REPORT.TYPED, type=self.REPORT.VERIFICATION,
            date=self.REPORT.DATE, ntp=self.ntp,

        )
        # create pdf front and content, merge them and remove merged files
        pisa.CreatePDF(front_index, dest=self.output_front_result)
        pisa.CreatePDF(content_index, dest=self.output_content_result)
        merger = PdfMerger()
        merger.append(self.output_front_result)
        merger.append(self.output_content_result)

        report_html = os.path.join(self.cases_folder_path, "report_timestamp_verification.pdf")
        merger.write(report_html)
        merger.close()

        self.output_content_result.close()
        self.output_front_result.close()
        if os.path.exists(self.output_front):
            os.remove(self.output_front)
        if os.path.exists(self.output_content):
            os.remove(self.output_content)
        if os.path.exists(info_file_path):
            os.remove(info_file_path)