#!/usr/bin/env python
# coding: utf-8

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
import time
import re
from bs4 import BeautifulSoup

from selenium.webdriver.firefox.options import Options
options = Options()
options.add_argument("--headless")

url = "https://www.osha.gov/laws-regs/regulations/standardnumber"
sections = "1904|1910|1915|1917|1918|1926|1928"

driver = webdriver.Firefox(firefox_options=options)
driver.implicitly_wait(10)
driver.get(url)
links = driver.find_elements_by_xpath("//a[@href]")
link_array = []
standard_array = []

# Compile links as strings
for link in links:
    url = str(link.get_attribute("href"))
    if re.search(sections,url):
        link_array.append(url)

# Create list of standards URLs
for link in link_array:
    print link
    try:
        driver.get(link)
        standards = driver.find_elements_by_xpath("//a[@href]")
        for standard in standards:
            url = str(standard.get_attribute("href"))
            if re.search(r'[0-9][0-9][0-9][0-9]\/[0-9][0-9][0-9][0-9]\.[0-9]',url):
                if re.search(r'App[A-Z]',url):
                    continue
                else:
                    standard_array.append(url)
    except:
        continue


from HTMLParser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

driver = webdriver.Firefox(firefox_options=options)
driver.implicitly_wait(10)
entries = []
# Cycle through standards
for standard in standard_array:
    try:
        driver.get(standard)
        soup=BeautifulSoup(driver.page_source, 'lxml')
        toplines=soup.find('ul','bulleted-list-header node-header').find_all('li')
        linelist = []
        for line in toplines:
            linestring = str(line)
            linestring = re.sub(r'<strong>.*?<\/strong>','',linestring)
            linestring = re.sub(r'\t|\n|<.*?>','',linestring)
            linelist.append(linestring)    
        paragraphs = soup.find_all('div','field--item')
        counter =0
        for paragraph in paragraphs:
            entry = {'part_number':linelist[0],'part_title':linelist[1],'subpart':linelist[2],'subpart_title':linelist[3],'standard_number':linelist[4],'standard_title':linelist[5]}
            grafstring = str(paragraph)
            grafstring = re.sub(r'\t|\n','',grafstring)
            stand_number = re.search(r'<div class\=\"paragraph paragraph\-\-type\-\-regulations\-standard\-number paragraph\-\-view-mode\-\-default\"><a href\=\"\/laws\-regs\/interlinking\/standards\/(.*?)\"',grafstring)
            if stand_number:
                stand_number = stand_number.group(1)                
            else:
                stand_number = re.search(r'<span id\=\"(.*?)\">',grafstring)
                if stand_number:
                    stand_number = stand_number.group(1)                
            stand_description = re.search(r'<strong><em>(.*?)<\/em><\/strong>',grafstring)
            if stand_description:
                stand_description = stand_description.group(1)
            else:
                stand_description = re.search(r'standard\-paragraph\-body\-p\">(.*?)<\/div>',grafstring)
                if stand_description:
                    stand_description = stand_description.group(1)
                else:
                    if stand_description:
                        stand_description = stand_description.group(1)
            stand_description = str(stand_description)
            stand_description = stand_description.strip()
            stand_description = re.sub(r' {2,}',' ',stand_description)
            if stand_number:
                entry['standard_paragraph'] = stand_number
                entry['paragraph_text'] = strip_tags(stand_description)
                entries.append(entry)
            counter+=1
        entries.append({'part_number':linelist[0],'part_title':linelist[1],'subpart':linelist[2],'subpart_title':linelist[3],'standard_number':linelist[4],'standard_title':linelist[5],'paragraph_text':linelist[5],'standard_paragraph':linelist[4]})

    except:
        continue
    
import csv
csv_columns = ['part_title', 'standard_paragraph', 'standard_number', 'subpart', 'paragraph_text', 'subpart_title', 'part_number', 'standard_title']
csv_file = "standards.csv"
try:
    with open(csv_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        for data in entries:
            writer.writerow(data)
except IOError:
    print("I/O error") 


#################################################
## Oregon standards that supersede federal OSHA
#################################################

driver = webdriver.Firefox(firefox_options=options)
driver.implicitly_wait(10)
divisions = range(1,7)
url = "https://osha.oregon.gov/rules/final/Pages/division-"
entries = []
for division in divisions:
    thisurl = url + str(division) + ".aspx"
    driver.get(thisurl)
    soup=BeautifulSoup(driver.page_source, 'lxml')
    header=soup.find('h2')
    header= strip_tags(str(header))
    sections=soup.find_all('div','anchor osha-section')
    if sections:
        for section in sections:
            sectionstring = str(section)
            sectionstring = re.sub(r'\t|\n','',sectionstring)
            section_name = re.search(r'<h4 class\=\"text-green\">(.*?)<br',sectionstring)
            if section_name:
                section_name = strip_tags(section_name.group(1))
            rows = re.findall(r'<tr>(.*?)<\/tr>',sectionstring,re.MULTILINE)
            if rows:
                for row in rows:
                    rowstring = str(row)
                    tds = re.findall(r'<td>(.*?)<\/td>',rowstring,re.MULTILINE)
                    if tds:
                        if len(tds)==2:
                            if re.search(r'^437',str(tds[0])):
                                entry={'standard_number':strip_tags(str(tds[0])),'standard_paragraph':strip_tags(str(tds[0])),'paragraph_text':strip_tags(str(tds[1])),'part_title':header,'standard_title':section_name}
                                entries.append(entry)

csv_columns = ['part_title', 'standard_paragraph', 'standard_number', 'subpart', 'paragraph_text', 'subpart_title', 'part_number', 'standard_title']
csv_file = "state_standards.csv"
try:
    with open(csv_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        for data in entries:
            writer.writerow(data)
except IOError:
    print("I/O error") 




