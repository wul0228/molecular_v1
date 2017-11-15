#!/usr/bin/env python
# --coding:utf-8--
# date:20171023
# author:wuling
# emai:ling.wu@myhealthgene.com

'''
this model setted  to download, extract and update chebi data automatically
'''
import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *

version = '1.0'

model_name = psplit(os.path.abspath(__file__))[1]

# buid directory to store raw an extracted data
(chebi_model,chebi_raw,chebi_store,chebi_db) = buildSubDir('chebi')

# main code
def downloadData( redownload = False ):
    '''
    this function is to download the raw data from ChEBI FTP WebSite
    paras:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    '''
    if  not redownload:

        # check  to see if there have been an edition

        (choice,existChEBIFile) = lookforExisted(chebi_raw,'ChEBI')

        if choice != 'y':
            return

    if redownload or not existChEBIFile or  choice == 'y':

        ftp = connectFTP(**chebi_ftp_infos)

        mt = ftp.sendcmd('MDTM ChEBI_complete.sdf.gz').replace(' ','',1)

        # initialiaze log file
        if not pexists(pjoin(chebi_model,'chebi.log')):

            initLogFile('chebi',model_name,chebi_model,mt)

        savefilename = 'ChEBI_complete_{}_{}.sdf.gz'.format(mt,today)

        save_file_path = ftpDownload(ftp,chebi_compound_filename,savefilename,chebi_raw,chebi_compound_filepath)

        ftp.quit() 

        print  'dataload completed !'

        return save_file_path

def extractData(filepath = None, latest = False):

    '''
    this function is set to extract the infos in chebi download file  and save as a json file
    paras:
    filepath -- if filepath afforded, file handling at once
    latest-- if no filepath , default False ,extract data directely from latest edition in /dataraw/chebi/
            --  if set to True, download data in real-time before extract
    '''
    if filepath:
        try:
            store_file_path = standarData(filepath)

        except Exception,e:
            print e
    else:
        # check  to see if there have been an edition
        existChEBIFile = filter(lambda x:x.startswith('ChEBI'),listdir(chebi_raw))

        # if  latest or not exists, download befor next step
        if latest or not existChEBIFile:
            
            print 'there not exists raw data of chebi , before the next step , we must downlaod previously'

            filepath = downloadData()
        
        else:
            # chose a old edition to continue

            edition = choseExisted(existChEBIFile)

            if edition == 'q':
                
                return

            filepath = pjoin(chebi_raw,existChEBIFile[edition])

            store_file_path = standarData(filepath)

    return store_file_path

def standarData(filepath):
    '''
    this function is to transfer sdf file to json and add a field STANDAR_SMILES
    '''
    # pre-deal  the file after get the filepath
    filename = psplit(filepath)[1].strip()

    if  filename.endswith('gz'):

        gunzip = 'gunzip {}'.format(filepath)
        
        os.popen(gunzip)
        
        filepath = filepath.rsplit('.',1)[0].strip()

    # start to extract data
    file = open(filepath).read().strip().split('$$$$')

    gzip = 'gzip {}'.format(filepath)

    os.popen(gzip)

    mols = list()

    for block in file:

        mol = dict()

        items = block.split('> <')[1:]

        for it in items:

            #change the space in key to '_'
            key = it.split('>',1)[0].strip().replace(' ','_')

            value = it.split('>',1)[1].strip()

            # value contains \n .transfer to list, if ':' also fund  transfer to dict
            if value.count('\n'):

                value =[i.strip() for i in  value.split('\n') if i]

                if key !=  "IUPAC_Names" and all([x.count(':') for x in value]):

                    value_dict = dict()

                    for j in value:

                        j_key = j.split(':',1)[0].strip()

                        j_value = j.split(':',1)[1].strip()

                        value_dict[j_key] = j_value

                        value = value_dict
                        
            mol[key] = value

        # add Standard SMILES 
        standard_smiles = neutrCharge(mol.get("SMILES"))
        mol['Standard_SMILES'] = standard_smiles

        mols.append(mol)

    store_file_name = filename.split('.')[0] + '.json'

    store_file_path = pjoin(chebi_store,store_file_name)
   
    with open(store_file_path, 'w') as wf:
        json.dump(mols,wf,indent=2)

    print  'dataextract completed !'
    
    return store_file_path


def insertData(store_file_path):
    '''
    this function is set to inser extracted data to mongdb database
    pares:
    store_file_path -- a json file's path,stored the chebi data
    '''
    try:

        store_file_name = psplit(store_file_path)[1].strip()

        mols = json.load(open(store_file_path))

        mt = store_file_name.split('ChEBI_complete_')[1].strip().split('_',1)[0].strip()

        date = store_file_name.split('.json')[0].strip().rsplit('_',1)[1].strip()

        collection_name  ='ChEBI_' + mt + '_'  +date

        #  insert data to mongodb

        conn = MongoClient('127.0.0.1',27017)

        db = conn.ChEBI
       
        collection = db.collection_name
        
        for mol in mols:
            mol['CREATED_TIME'] = datetime.now()
        
        collection.insert(mols)

        db.collection_name.rename(collection_name )

        print 'insertData completed !'

    except Exception,e:
        print e

    
def updateData(insert=True):

    # method 1
    ftp = connectFTP(**chebi_ftp_infos)

    latest_edition = ftp.sendcmd('MDTM ChEBI_complete.sdf.gz').strip().replace(' ','')

    ftp.quit()
    
    chebi_log = json.load(open(pjoin(chebi_model,'chebi.log')))

    last_record = chebi_log[-1]

    if latest_edition != last_record[0]:

        print 'new edition found !'
        
        choseDown(choice = 'download')

        chebi_log .append((latest_edition,today,os.path.abspath(__file__)))

        with open(pjoin(chebi_model,'chebi.log'),'w') as wf:

            json.dump(chebi_log,wf,indent=2)
        
        print  'dataupdate completed !'

    else:

        print 'remote latest edition is %s ' % latest_edition 

        print 'local is the latest edition!'

    #method 2 
    # url = 'ftp://ftp.ebi.ac.uk/pub/databases/chebi/SDF/'
    # browser = webdriver.Chrome()
    # browser.get(url)
    # date = browser.find_element_by_xpath('//*[@id="tbody"]/tr[2]/td[3]').text
    # date = date.split(' ')[0]
    # browser.close()
    # compare the latest edition with log record
    
def selectData():
    '''
    this function is set to select data from mongodb
    '''
    conn = MongoClient('127.0.0.1',27017)

    db = conn.ChEBI

    colnamehead = 'ChEBI'

    querykey = 'Standard_SMILES'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

def choseDown(choice = 'update',insert=True):
    
    if choice == 'update':

        updateData()

    elif choice == 'download':

        save_file_path = downloadData(redownload=True )

        store_file_path  = extractData(save_file_path)

        if insert:

            insertData(store_file_path)

    elif choice == 'select':

        selectData()
        
    else:
        pass

def main():

    tips = '''
    Download : 1
    Update : 2
    Select : 3
    '''
    index = raw_input(tips)

    chose = {'1':'download','2':'update','3':'select'}

    choseDown(choice =chose[index])

if __name__ =='__main__':

    main()
