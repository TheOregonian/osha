# OSHA data import and processing

This repository consists of two main scripts for downloading, parsing and geocoding CSV files on inspection, violation and accident records from OSHA's website. For a full list of files, click 'Enforcement data' on this page: https://enforcedata.dol.gov/views/data_catalogs.php. The data goes back as far as 1973. OSHA updates its public files daily.

The specific implementation is for isolating records in Oregon, which is among those states that have written their own workplace standards that go over and above federal OSHA standards. You can easily adapt the code for other states that only follow federal standards.

## Installation

These scripts are built in Python 2.7. After pulling the repository into a directory called ```osha```, you should create a virtual environment in which to run everything.

``` 
virtualenv ENV
pip install -r requirements.txt
```
You will also need a Bing API key available here: https://www.bingmapsportal.com/

After creating a key, you will store it in the ```osha``` directory. The file should follow the following format:

```
service,key
bing,YOURKEYHERE
```
You can add other keys and access them by name by invoking the ```get_apikey()``` function defined in ```standards.py```.

## standards.py

The ```standards.py``` file is a scraper that compiles a list of numbered OSHA rules that the agency cites when issuing violations that arise from an inspection. The results are dumped in a file called ```standards.csv``` that includes the title and content of each rule. Find the federal standards being scraped here:
https://www.osha.gov/laws-regs/regulations/standardnumber/

In addition, the scraper pulls Oregon-specific workplace rules into a file called ```state_standards.csv```. The web pages being scraped are here:
https://osha.oregon.gov/rules/Pages/default.aspx

## processing.py

This script downloads all files available on the OSHA enforcement site, unzips them, concatenates them and saves them as big csvs. 

The most interesting element of all these data is the one that tells us what a company did wrong. The column is called "standard" in the OSHA violations file. It is an alphanumeric code corresponding to the rule number in the Code of Federal Regulation or, in the case of Oregon, the Oregon Administrative Rules.

The ```processing.py``` script cleans up and standardizes this alphanumeric code, then joins it to the ```standards.csv``` and ```state_standards.csv``` files to provide a human-readable description of the rule being violated.

Finally, the script takes the address of the workplace inspected and geocodes it.

The script is set to isolate only Oregon inspections, based on the state field shown in the inspections file. It also isolates inspections conducted since January 1 of the current year.

We have also created a system for isolating only records that you have not downloaded before. A file called ```bookmark``` is created at the end of each download session, recording the highest unique ID (activity_nr) last imported from the inspections file. If running in 'append' mode, only the recent records will be stored. Otherwise, all records from January 1 will be stored.

