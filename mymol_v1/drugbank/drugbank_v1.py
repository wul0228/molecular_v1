#!/usr/bin/env python
# ---coding:utf-8---
# date:20171102
# author:wuling
# emai:ling.wu@myhealthgene.com

'''
this model setted  to download, extract and update drugbank data automatically
'''
import sys
reload(sys)
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
import copy
import requests
from config import *
from share import *
from bs4 import BeautifulSoup as bs

__all__ = ['downloadData','extractData','standarData','insertData','updateData','selectData']

version = '1.0'

model_name = psplit(os.path.abspath(__file__))[1]

# buid directory to store raw an extracted data
(drugbank_model,drugbank_raw,drugbank_store,drugbank_db,drugbank_map) = buildSubDir('drugbank')

# main code
def getWebPage():
    '''
    this function is to get the download web page of drugbank by python crawler
    '''
    # get responce from drug bank
    web = requests.get(drugbank_start_url)

    # parser html with lxml
    soup = bs(web.text,'lxml')

    # get  content with link
    all_a = soup.select('#full > table > tbody > tr > td > a')

    for a in all_a:

        # get  the download href
        if a.get_text().strip() == 'Download':

            download_url = drugbank_homepage + a.attrs.get('href')

            releases = download_url.split('/releases/')[1].strip().split('/',1)[0].strip()

    return (download_url,releases)

def downloadData(redownload=False):
    '''
    this function is to connect drugbanek web  site and log in to download zip file
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        # check  to see if there have been an edition

        (choice,existDrugBankFile) = lookforExisted(drugbank_raw,'drugbank')

        if choice != 'y':
            return

    #because the data keep update ,so the url would change frequently, but the website frame remain, 
    #so we get download url with web crawler
    if redownload or not existDrugBankFile or  choice == 'y':

        (download_url,releases) = getWebPage()

        command = 'wget    -P {}  --http-user={}  --http-password={}  {}'.format(drugbank_raw,drugbank_log_user,drugbank_log_passwd,download_url)

        os.popen(command)

        # rename
        save_file_name = 'drugbank_{}_{}.xml.zip'.format(releases,today)

        old_file_path = pjoin(drugbank_raw,'all-full-database')

        new_file_path =  pjoin(drugbank_raw,save_file_name)

        os.rename(old_file_path,new_file_path)

        # # initialiaze log file
        if not os.path.exists(pjoin(drugbank_model,'drugbank.log')):

            initLogFile('drugbank',model_name,drugbank_model,mt=releases)

        return  new_file_path

def extractData(new_file_path):
    '''
    this function is to extract drug data from xml.zip  raw file
    args:
    new_file_path -- the renamed xml file absolute path 
    '''
    filename = psplit(new_file_path)[1].strip().split('.xml.zip')[0].strip()
    # gunzip file
    # filedir = new_file_path.split('.zip')[0].strip()

    unzip = 'unzip {} -d {}'.format(new_file_path,drugbank_raw)

    os.popen(unzip)

    # raname

    filepath = pjoin(drugbank_raw,'{}.xml'.format(filename))

    command = 'mv  {}/"full database.xml"  {}'.format(drugbank_raw,filepath)

    os.popen(command)
   
    # parse tree
    tree = parse(open(filepath))

    # the only key in tree dict is drugbank
    db = tree["drugbank"]

    version = db["@version"]

    exported = db["@exported-on"]

    drugs = db['drug']

    drug_store = pjoin(drugbank_store,filename)

    createDir(drug_store)

    n = 0

    for drug in drugs:

        stand_drug = standarData(drug)

        with open(pjoin(drug_store,'drug_{}.json'.format(str(n))),'w') as wf:

            json.dump(stand_drug,wf,indent=2)

        n += 1
        print n 

    return drug_store

def standarData(drug):
    '''
    this funcition is to standard a dict  obeject  to delet some keys that's value is none recursive
    args:
    drug -- a dict object from xmltodict result of drugbank.xml file
    '''

    equal = False

    start = drug

    while not equal :

        a = deBlankDict(start)

        b = deBlankDict(a)

        if b == a:
            equal = True 
            end = b
        else:
            start = b

    return end

def insertData(storedir):
    '''
    this function is to insert extracted data to mongodb database
    args:
    storedir ~ a json file's path dir ,stored the drugbank data
    '''

    conn = MongoClient('127.0.0.1',27017)

    db = conn.DrugBank

    collection_name = psplit(storedir)[1].strip().replace('-','')

    collection = db.collection_name
    
    for filename in listdir(storedir):

        filepath = pjoin(storedir,filename)

        drug = json.load(open(filepath))

        drug['CREATED_TIME'] = datetime.now()

        collection.insert(drug)

    db.collection_name.rename(collection_name )

    print 'insertData completed !'

def updateData(insert=True):
    '''
    this function is to check the edition existed and update or not
    args:
    insert -- default is Ture, after standar data ,insert to mongodb, if set to false, process break when standarData completed
    '''
    drugbank_log = json.load(open(pjoin(drugbank_model,'drugbank.log')))
    
    latest_edition =drugbank_log [-1][0].strip()

    (download_url,releases) = getWebPage()

    if releases != latest_edition:

        save = downloadData(redownload=True)

        store  = extractData(save)

        if insert:
        
            insertData(store)

        drugbank_log .append((releases,today,os.path.abspath(__file__)))

        with open(pjoin(drugbank_model,'drugbank.log'),'w') as wf:
            json.dump(drugbank_log,wf,indent=2)
        
        print  'dataupdate completed !'

    else:

        print 'remote latest edition is %s ' % latest_edition 

        print 'local is the latest edition!'
        
def selectData(querykey = 'name',queryvalue='Lepirudin'):
    '''
    this function is set to select data from mongodb
    args:
    querykey --  the filed name 
    queryvalue -- the field value
    '''
    conn = MongoClient('127.0.0.1',27017)

    db = conn.DrugBank

    colnamehead = 'drugbank'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

def main():

    modelhelp = model_help.replace('*'*6,sys.argv[0]).replace('&'*6,'DrugBank').replace('#'*6,'drugbank')

    funcs = (downloadData,extractData,standarData,insertData,updateData,selectData)

    getOpts(modelhelp,funcs=funcs)

if __name__ == '__main__':
    main()
