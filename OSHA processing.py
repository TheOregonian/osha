#!/usr/bin/env python
# coding: utf-8

import urllib2
import zipfile
import os, os.path
import pandas as pd
import datetime
import shutil
import re
import geopandas

##################################################################################
# SET THIS VARIABLE BASED ON WHETHER WE WANT THE FULL HISTORY BACK TO 1973
##################################################################################
shorthistory = True

# Basic date info
now       = datetime.datetime.now()
yesterday = now - datetime.timedelta(days = 1)
today     = now.strftime("%Y%m%d")
yesterday = yesterday.strftime("%Y%m%d")

# List of available datasets and download locations at:
# https://enforcedata.dol.gov/views/data_summary.php
base_url = "https://enfxfr.dol.gov/data_catalog/OSHA/osha_"   
filetypes      = ["accident","accident_abstract","accident_injury","inspection","violation","violation_event","violation_gen_duty_std"]
for thistype in filetypes:
    allfile = thistype + '_all.csv'
    try:
        fh = open(allfile, 'r')
        os.remove(allfile)
    except:
        print allfile + ' not present to remove'
    url = base_url + thistype + '_' + today + '.csv.zip'
    try:
        filedata = urllib2.urlopen(url)
    except:
        url = base_url + thistype + '_' + yesterday + '.csv.zip'
        try:
            filedata = urllib2.urlopen(url)
        except:
            print "Missing file at " + url
            continue
    datatowrite = filedata.read()
    with open(thistype + '_' + today + '.zip', 'wb') as f:  
        f.write(datatowrite)
    zip = zipfile.ZipFile(thistype + '_' + today + '.zip', 'r')
    zip.extractall(thistype + '_' + today)
    filecount = len(os.listdir(thistype + '_' + today))
    files = range(filecount)
    collection = pd.DataFrame()
    limits = {'inspection':4,'violation_event':9,'violation':12}
    if shorthistory:
    	limit = limits[thistype] - 1
    	# Eliminate older files in order to conserve memory
    	del files[0:limit]
    for file in files:
    	# There's only one file for accidents, so no suffix
        if thistype[0:8] == 'accident':
            ending = ""
        # Other types of files end with a number
        else:
            ending = file
        collection = collection.append(pd.read_csv(thistype + '_' + today + "/osha_" + thistype + str(ending) + ".csv",low_memory=False))
    collection.to_csv(thistype + '_all.csv')
    shutil.rmtree(thistype + '_' + today)
    os.remove(thistype + '_' + today + '.zip')
    

# Pull up our file showing the ID of the last record processed in the "latest_inspections.csv" file
# If this is a first run of the app, then no bookmark exists and we run everything.
import os
exists = os.path.isfile('bookmark')
if exists:
    bookmark = pd.read_csv("bookmark")
    appending = True
else:
    appending = False


inspections = pd.read_csv('inspection_all.csv')
# Drop all the old records that we've already processed
if appending:
    inspections = inspections[inspections.activity_nr > int(bookmark.top[0])]


# Isolate recent Oregon inspections and violations
oregon_inspections = inspections[(inspections.open_date > '2019-01-01') & (inspections.site_state == 'OR')]
oregon_inspection_IDs = oregon_inspections['activity_nr']
violations = pd.read_csv('violation_all.csv')
if appending:
    violations = violations[violations.activity_nr > int(bookmark.top[0])]
oregon_violations = pd.merge(oregon_inspection_IDs,violations,on='activity_nr')
oregon_violation_count = oregon_violations.groupby('activity_nr').count()[['citation_id']]
oregon_violation_count = oregon_violation_count.rename(columns={'citation_id':'violations'})
oregon_inspections = pd.merge(oregon_inspections,oregon_violation_count,on='activity_nr',how='left')
oregon_inspections['violations'].fillna(0, inplace=True)
oregon_inspections['violations'] = oregon_inspections['violations'].astype(int)

# Clean up genduty file, which has extensive comments on each violation
#
genduty = pd.read_csv('violation_gen_duty_std_all.csv')
# combine multiple lines of text per violation into single comment
pd.set_option('display.max_colwidth', 1000)
genduty = genduty.sort_values(by=['activity_nr','citation_id','line_nr'])
cleantext = genduty.groupby(['activity_nr','citation_id'])['line_text'].apply(lambda text: ''.join(text.to_string(index=False))).str.replace('(\\n)', '').reset_index()
# merge the single comment with single violations in Oregon
oregon_violations = pd.merge(oregon_violations,cleantext,on=['activity_nr','citation_id'],how='left')


# Create a standards column for cleaning
oregon_violations['standard_paragraph'] = oregon_violations['standard']
oregon_violations['standard_paragraph'][oregon_violations['standard_paragraph'].str.contains(r'^OAR ')] = oregon_violations['standard_paragraph'].str.replace(r'^OAR (.*?)(\(|$).*',r'\1',regex=True)

# Clean the cited standard to match our table of standards
def parse_str(match):
    firstfour = None; secondfour = None; letter = None; graphno =None ; space = None; roman = None; lastletter = None; lastnumber = None
    if len(match.groups()) == 7:
        firstfour, secondfour, letter, graphno, roman, lastletter, lastnumber = match.groups()
    if len(match.groups()) == 6:
        firstfour, secondfour, letter, graphno, roman, lastletter = match.groups()
    elif len(match.groups()) == 5:
        firstfour, secondfour, letter, graphno, roman = match.groups()
    elif len(match.groups()) == 4:
        firstfour, secondfour, letter, graphno = match.groups()
    elif len(match.groups()) == 3:
        firstfour, secondfour, letter = match.groups()
    elif len(match.groups()) == 2:
        firstfour, secondfour = match.groups()
    if secondfour:
        secondfour = secondfour.strip("0").strip()
    standard = firstfour + '.' + secondfour 
    if letter:
        letter = letter.lower().strip()
        standard = standard + '(' + letter + ')'
    if graphno:
        graphno = graphno.strip("0").strip()
        standard = standard + '(' + graphno + ')'
    if roman:
        roman = roman.lower().strip()
        standard = standard + '(' + roman + ')'
    if lastletter:
        lastletter = lastletter.strip()
        standard = standard + '(' + lastletter + ')'
    if lastnumber:
        lastnumber = lastnumber.strip("0").strip()
        standard = standard + '(' + lastnumber + ')'
    return standard
oregon_violations['standard_paragraph'][oregon_violations['standard_paragraph'].str.contains(r'^19[0-9][0-9][0-9][0-9][0-9][0-9]( |$)')] = oregon_violations['standard_paragraph'].str.replace(r'^(19[0-9][0-9])([0-9][0-9][0-9][0-9]) ([A-Z])(.*?) ([A-Za-z]{1,}) ([A-Za-z]) ([0-9]{1,})$',parse_str)
oregon_violations['standard_paragraph'][oregon_violations['standard_paragraph'].str.contains(r'^19[0-9][0-9][0-9][0-9][0-9][0-9]( |$)')] = oregon_violations['standard_paragraph'].str.replace(r'^(19[0-9][0-9])([0-9][0-9][0-9][0-9]) ([A-Z])(.*?) ([A-Za-z]{1,}) ([A-Za-z])$',parse_str)
oregon_violations['standard_paragraph'][oregon_violations['standard_paragraph'].str.contains(r'^19[0-9][0-9][0-9][0-9][0-9][0-9]( |$)')] = oregon_violations['standard_paragraph'].str.replace(r'^(19[0-9][0-9])([0-9][0-9][0-9][0-9]) ([A-Z])(.*?) ([A-Za-z]{1,})$',parse_str)
oregon_violations['standard_paragraph'][oregon_violations['standard_paragraph'].str.contains(r'^19[0-9][0-9][0-9][0-9][0-9][0-9]( |$)')] = oregon_violations['standard_paragraph'].str.replace(r'^(19[0-9][0-9])([0-9][0-9][0-9][0-9]) ([A-Z])(.*?)$',parse_str)
oregon_violations['standard_paragraph'][oregon_violations['standard_paragraph'].str.contains(r'^19[0-9][0-9][0-9][0-9][0-9][0-9]( |$)')] = oregon_violations['standard_paragraph'].str.replace(r'^(19[0-9][0-9])([0-9][0-9][0-9][0-9]) ([A-Z])$',parse_str)
oregon_violations['standard_paragraph'][oregon_violations['standard_paragraph'].str.contains(r'^19[0-9][0-9][0-9][0-9][0-9][0-9]( |$)')] = oregon_violations['standard_paragraph'].str.replace(r'^(19[0-9][0-9])([0-9][0-9][0-9][0-9])$',parse_str)
oregon_violations['standard_paragraph'][oregon_violations['standard_paragraph'].str.contains(r'^19[0-9][0-9][0-9][0-9][0-9][0-9]( |$)')] = oregon_violations['standard_paragraph'].str.replace(' ','')


# Prepare standards files to apply to Oregon
standards = pd.read_csv('standards.csv')
state = pd.read_csv('state_standards.csv')
standards = standards.append(state)

# Join Oregon violations on the lookup file for standards, state and federal
oregon_violations = pd.merge(oregon_violations,standards,on='standard_paragraph',how='left')

# Output the violations file: It's done
oregon_violations.to_csv('latest_violations.csv')

# Prepare inspections df for geocoding
oregon_inspections = oregon_inspections.fillna('-1')
counter = 0
from geopy.geocoders import Bing
bingkey = "AuNPKK6wEhtJOp2JSz1iQQwqgCptimUiyamkP18Bnz4ycjMaxcFdd1kYEqyWrdxL"

# Iterate through data, geocoding each row
for row in oregon_inspections.itertuples():
    counter+=1
    # Compile the address using available street/city/county/state fields
    address = str(int(row.site_zip))
    if not isinstance(row.site_state,float):
        address = str(row.site_state) + ',' + address
    if not isinstance(row.site_city,float):
        address = str(row.site_city) + ',' + address
    if not isinstance(row.site_address,float):
        address = str(row.site_address) + ',' + address
    # Geocode the address
    try:
        location = geopandas.tools.geocode(address,provider="Bing",api_key=bingkey)
        location['activity_nr'] = row.activity_nr
        if counter == 1:
            locations = geopandas.GeoDataFrame(location)
        else:
            locations = locations.append(location)
    except:
        continue

#Merge the geocodes with  inspection data
oregon_inspections = pd.merge(oregon_inspections,locations,on='activity_nr',how='left')

# Output to csv
oregon_inspections.to_csv('latest_inspections.csv')

# Create a text file noting record ID of where we left off with the last import of data.
biggest = oregon_inspections.activity_nr.max()
bookmark = pd.DataFrame({'top':[biggest]})
bookmark.to_csv('bookmark')




