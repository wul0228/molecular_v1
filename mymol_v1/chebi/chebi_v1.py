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

__all__ = ['downloadData','extractData','standarData','insertData','updateData','selectData']

version  = 1.0

model_name = psplit(os.path.abspath(__file__))[1]

(chebi_model,chebi_raw,chebi_store,chebi_db,chebi_map) = buildSubDir('chebi')

def downloadData( redownload = False ):
    '''
    this function is to download the raw data from ChEBI FTP WebSite
    args:
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
    args:
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
    args:
    filepath -- filepath of sdf file
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

    names = ["IUPAC&Names" ,'ChEBI&Name' ,'IUPAC&Names','Synonyms','Definition',"ChEBI&ID","Secondary&ChEBI&ID"]

    mols = list()

    for block in file:

        mol = dict()

        items = block.split('> <')[1:]

        for it in items:

            #change the space in key to '_'
            key = it.split('>',1)[0].strip().replace(' ','&').replace('.','*').strip()

            value = it.split('>',1)[1].strip()

            # value contains \n .transfer to list, if ':' also fund  transfer to dict
            if value.count('\n'):

                value =[i.strip() for i in  value.split('\n') if i]

                if key not in names and all([x.count(':') for x in value]):

                    value_dict = dict()

                    for j in value:

                        j_key = j.split(':',1)[0].strip().replace(' ','&').replace('.','*')

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
    args:
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
    '''
    this function is to check the edition existed and update or not
    args:
    insert -- default is Ture, after standar data ,insert to mongodb, if set to false, process break when standarData completed
    '''
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
    
def selectData(querykey = 'Standard_SMILES',queryvalue=''):
    '''
    this function is set to select data from mongodb
    args:
    querykey --  the filed name 
    queryvalue -- the field value
    '''
    conn = MongoClient('127.0.0.1',27017)

    db = conn.ChEBI

    colnamehead = 'ChEBI'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

def mapName2ID(store_file_path):

    datamap  = pjoin(chebi_model,'datamap')

    file = json.load(open(store_file_path))

    name_ids = dict()

    for block in file:

        chebi_id = block.get("ChEBI&ID")
        
        chebi_second_id =block.get("Secondary&ChEBI&ID")

        chebi_name = block.get("ChEBI&Name")

        iupac_name = block.get('IUPAC&Names')

        brand_name = block.get('BRAND&Names')

        synonyms = block.get('Synonyms')

        names = [name for name in [chebi_name,iupac_name,brand_name,synonyms] if name]

        for name in names:
            if isinstance(name,unicode):
                if name not in name_ids:
                    name_ids[name] = list()
                name_ids[name].append(chebi_id)
                name_ids[name].append(chebi_second_id)

            elif isinstance(name,list):
                for n in name:
                    if n not in name_ids:
                        name_ids[n] = list()

                    if  isinstance(chebi_id,unicode):
                        name_ids[n].append(chebi_id)  
                    elif   isinstance(chebi_id,list):
                        name_ids[n] += chebi_id
                    else:
                        if chebi_id:
                            print 'chebi_id',chebi_id

                    if   isinstance(chebi_second_id,unicode):
                        name_ids[n].append(chebi_second_id)  
                    elif  isinstance(chebi_second_id,list):
                        name_ids[n] += chebi_second_id
                    else:
                        pass
                    
            else:
                pass
    
    for name,ids in name_ids.items():
        newids = [_id for _id in ids if _id]
        name_ids[name] = newids

    savefilename = 'name2ids_{}.json'.format(store_file_path.rsplit('ChEBI_complete_')[1].split('.json')[0].strip())
    
    with open(pjoin(chebi_map,savefilename),'w') as wf:
        json.dump(name_ids,wf,indent=2)

    print len(name_ids)

    # keys = reduce(lambda x,y: set(x) |set(y) , [c.keys() for c in file])

    # nolink = [i for i in keys if not i.endswith('&Links')]

    # print keys
    # print '-'*50
    # print len(keys)

    # print nolink #BRAND_Names ChEBI_Name Synonyms IUPAC_Names
    # print '~'*50
    # print len(nolink)

def mapCas2ID(store_file_path):

    # a chebi id  coresponding to multi cas
    file = json.load(open(store_file_path))

    cas_ids = dict()

    for block in file:

        chebi_id = block.get("ChEBI&ID")
        
        chebi_second_id =block.get("Secondary&ChEBI&ID")

        cas = block.get("CAS&Registry&Numbers")

        if isinstance(cas,unicode):
            if  cas not in cas_ids:
                cas_ids[cas] = list()
            cas_ids[cas].append(chebi_id)
            cas_ids[cas].append(chebi_second_id)    

        elif isinstance(cas,list):
            for c in cas:
                if  c not in cas_ids:
                    cas_ids[c] = list()
                cas_ids[c].append(chebi_id)
                cas_ids[c].append(chebi_second_id)    

    for cas,ids in cas_ids.items():
        newids = [_id for _id in ids if _id]
        cas_ids[cas] = newids

    savefilename = 'cas2ids_{}.json'.format(store_file_path.rsplit('ChEBI_complete_')[1].split('.json')[0].strip())
    
    with open(pjoin(chebi_map,savefilename),'w') as wf:
        json.dump(cas_ids,wf,indent=2)

    print len(cas_ids)

def main():

    modelhelp = model_help.replace('*'*6,sys.argv[0]).replace('&'*6,'ChEBI').replace('#'*6,'chebi')

    funcs = (downloadData,extractData,standarData,insertData,updateData,selectData)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    
    main()
    # store_file_path = '/home/user/project/molecular_v1/mymol_v1/chebi/datastore/ChEBI_complete_21320171001032328_171031161434.json'
    # mapName2ID(store_file_path)
    # mapCas2ID(store_file_path)
    