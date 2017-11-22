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

        db = conn.mymol
       
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

    db = conn.mymol

    colnamehead = 'ChEBI'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class dbMap(object):
    '''
    this class is to build a mapping relation between key field in database
    '''
    def __init__(self,store_file_path):

        self.filepath = store_file_path

        self.jsonfile = json.load(open(self.filepath))

        self.mapdir = pjoin(chebi_map,psplit(store_file_path)[1].strip().split('.json')[0].strip())

        createDir(self.mapdir)

    def mapInit2SecondID(self):

        init_id = dict()

        for block in self.jsonfile:

            chebi_id = block.get("ChEBI&ID")
            
            chebi_second_id =block.get("Secondary&ChEBI&ID")

            if not chebi_second_id:

                continue

            chebi_second_id = strAndList([chebi_second_id])

            if chebi_id not in init_id:

                init_id[chebi_id] = list()

            init_id[chebi_id] += chebi_second_id

        with open(pjoin(self.mapdir,'init2secondid.json'),'w') as wf:

            json.dump(init_id,wf,indent=2)

        print 'init have 2 or more second id :', len(init_id)

        print 'mapInit2SecondID  completed ! '

        return init_id

    def mapName2ID(self):

        name_id = dict()

        id_name = dict()

        for block in self.jsonfile:

            chebi_id = block.get("ChEBI&ID")
            
            chebi_name = block.get("ChEBI&Name")

            iupac_name = block.get('IUPAC&Names')

            brand_name = block.get('BRAND&Names')

            synonyms = block.get('Synonyms')

            names = strAndList([chebi_name,iupac_name,brand_name,synonyms])

            for name in names:
                if name not in name_id:
                    name_id[name] = list()
                name_id[name].append(chebi_id)
        
        with open(pjoin(self.mapdir,'name2id.json'),'w') as wf:
            json.dump(name_id,wf,indent=2)

        print 'name have ids:', len(name_id)

        print 'mapName2ID completed ! '

        return name_id

    def mapID2Name(self,name_id):

        id_name = value2key(name_id)

        with open(pjoin(self.mapdir,'id2name.json'),'w') as wf:

            json.dump(id_name,wf,indent=2)

        print 'id have name', len(id_name)

        print 'mapID2Name completed ! '

        return id_name

    def mapCas2ID(self):

        # a chebi id  coresponding to multi cas
        cas_id = dict()

        for block in self.jsonfile:

            chebi_id = block.get("ChEBI&ID")
            
            cas = block.get("CAS&Registry&Numbers")

            if not cas:

                continue

            cass = strAndList([cas])

            for cas in cass:

                if cas not in cas_id:

                    cas_id[cas] = list()

                cas_id[cas].append(chebi_id)

        with open(pjoin(self.mapdir,'cas2id.json'),'w') as wf:

            json.dump(cas_id,wf,indent=2)

        print 'cas have id:', len(cas_id)

        print 'mapCas2ID  completed ! '

        return cas_id

    def mapID2Cas(self,cas_id):

        id_cas = value2key(cas_id)

        with open(pjoin(self.mapdir, 'id2cas.json'),'w') as wf:

            json.dump(id_cas,wf,indent=2)

        print 'id have cas :', len(id_cas)

        print 'mapID2cases completed ! '

        return id_cas


    def mapName2Cas(self,name_id,id_cas):
        
        name_cas = dict()

        for name,ids in name_id.items():

            for _id in ids:

                cases = id_cas.get(_id)

                if not cases:

                    continue

                if name not in name_cas:

                    name_cas[name] = list()

                name_cas[name] += cases

            if name_cas.get(name):

                name_cas[name] = list(set(name_cas[name]))
        
        with open(pjoin(self.mapdir,'name2cas.json'),'w') as wf:

            json.dump(name_cas,wf,indent=2)

        print 'name have cas :', len(name_cas)

        print 'mapName2Cas completed ! '

        return name_cas

    def mapCas2Name(self,name_cas):

        cas_name = value2key(name_cas)

        with open(pjoin(self.mapdir,'cas2name.json'),'w') as wf:

            json.dump(cas_name,wf,indent=2)

        print 'cas have name: ', len(cas_name)

        print 'mapCas2Names completed ! '

        return cas_name

    def mapStandSmi2ID(self):

        # a chebi id  coresponding to multi cas

        standSmi_id = dict()

        for block in self.jsonfile:

            chebi_id = block.get("ChEBI&ID")
            
            standSmi = block.get("Standard_SMILES")

            if not standSmi:

                continue

            standSmis = strAndList([standSmi])

            for standSmi in standSmis:
                if standSmi not in standSmi_id:
                    standSmi_id[standSmi] = list()
                standSmi_id[standSmi].append(chebi_id)

        with open(pjoin(self.mapdir,'standsmi2id.json'),'w') as wf:
            json.dump(standSmi_id,wf,indent=2)

        print 'standsmi have id :', len(standSmi_id)

        print 'mapStandSmi2ID  completed ! '

        return standSmi_id

    def mapping(self):
        
         self.mapInit2SecondID()

         name_id = self.mapName2ID()

         id_name = self.mapID2Name(name_id)

         cas_id = self.mapCas2ID()

         id_cas = self.mapID2Cas(cas_id)

         name_cas = self.mapName2Cas(name_id,id_cas)

         cas_name= self.mapCas2Name(name_cas)

         self.mapStandSmi2ID()

def main():

    modelhelp = model_help.replace('*'*6,sys.argv[0]).replace('&'*6,'ChEBI').replace('#'*6,'chebi')

    funcs = (downloadData,extractData,standarData,insertData,updateData,selectData,dbMap,chebi_store)

    getOpts(modelhelp,funcs=funcs)
        
if __name__ == '__main__':
    
    main()
