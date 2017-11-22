#!/usr/bin/env python
# ---coding:utf-8---
# date:20171024
# author:wuling
# emai:ling.wu@myhealthgene.com

'''
this model setted  to download, extract and update pubchem data automatically
'''
import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *

__all__ = ['downloadData','extractData','standarData','insertData','updateData','selectData']

version = '1.0'

model_name = psplit(os.path.abspath(__file__))[1]

# buid directory to store raw an extracted data
(pubchem_model,pubchem_raw,pubchem_store,pubchem_db,pubchem_map) = buildSubDir('pubchem')

def downloadOne(ftp,filename,rawdir):
    '''
    this function is to download  one file under  a given remote dir 
    args:
    ftp -- a ftp cursor for a specified
    filename --  the name of file need download
    rawdir -- the directory to save download file
    '''
    mt =  ftp.sendcmd('MDTM {}'.format(filename)).replace(' ','')

    savefilename = '{}_{}_{}.sdf.gz'.format(filename.split('.',1)[0].strip(),mt,today)

    remoteabsfilepath = pjoin(pubchem_compound_path,'{}'.format(filename))

    save_file_path = ftpDownload(ftp,filename,savefilename,rawdir,remoteabsfilepath)

    return (save_file_path,mt)

def  downloadData(redownload = False,rawdir=None):
    '''
    this function is to download the raw data from PubChem FTP WebSite
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    rawdir-- the directory to save download file
    '''
    if  not redownload:

        (choice,existPubChemFile) = lookforExisted(pubchem_raw,'compound')

        if choice != 'y':
            return

    if redownload or not existPubChemFile or  choice == 'y':

        rawdir = pjoin(pubchem_raw,'compound_{}'.format(now))

        createDir(rawdir)

        ftp = connectFTP(**pubchem_ftp_infos)

        # get all the sdf filenames and 
        filenames = ftp.nlst()

        filesum = len(filenames)

        num = 0

        while num < filesum:

            try:

                for name in filenames[num:]:

                    downloadOne(ftp,name,rawdir)

                    print name,'done!'

                    num += 1

            except:
                ftp = connectFTP(**pubchem_ftp_infos)
      
    ftp.quit() 

    # initialiaze log file

    if not os.path.exists(pjoin(pubchem_model,'pubchem_compound.log')):

        initLogFile('pubchem',model_name,pubchem_model,rawdir=rawdir)

    print  'datadowload completed !'

    return rawdir

def extractData(rawdir=None,latest = False):
    '''
    this function is set to extract the infos in  /dataraw/pubchem/ in a batch
    rawdir -- if rawdir afforded, file handling at once
    storedir -- the directory to store standard data ,default is none ,if rawdir afford ,generate automatically
    latest-- if no rawdir , default False ,extract data directely from latest edition in /dataraw/chebi/
            --  if set to True, download data in real-time before extract
    '''
    if rawdir:

        # keep the  rawdir 'a name as the same as  storedir
        dirname = psplit(rawdir)[1].strip()
        storedir = pjoin(pubchem_store,dirname)

        createDir(storedir)

        try:

            for filename in listdir(rawdir):

                filepath = pjoin(rawdir,filename)

                result = standarData(filepath,storedir)

                if not result:

                    downloadOne(connectFTP(**pubchem_ftp_infos),filename,rawdir)

                    standarData(filepath,storedir)

        except Exception,e:

            print e

    else:
        # check  to see if there have been an edition
        existPubChemFile = filter(lambda x:x.startswith('compound'),listdir(pubchem_raw))

        # if not exists, download befor next step
        if latest or not existPubChemFile:
        
            print 'there not exists raw data of PubChem, before the next step , we must downlaod previously'

            rawdir = downloadData(reldownload = True)

            dirname= psplit(rawdir)[1].strip()

            storedir = pjoin(pubchem_store,dirname)

            createDir(storedir)

            for filename in listdir(rawdir):

                filepath = pjoin(rawdir,filename)

                result = standarData(filepath,storedir)

                if not result:

                    downloadOne(connectFTP(**pubchem_ftp_infos),filename,rawdir)

                    standarData(filepath,storedir)

        else:
            # chose a old edition to continue

            edition = choseExisted(existPubChemFile)

            if edition == 'q':

                return

            rawdir =  pjoin(pubchem_raw,existPubChemFile[edition])

            storedir = pjoin(pubchem_store,existPubChemFile[edition])

            createDir(storedir)

            for filename in rawdir:

                filepath = pjoin(rawdir,filename)

                result = standarData(filepath,storedir)

                if not result:

                    downloadOne(connectFTP(**pubchem_ftp_infos),filename,rawdir)

                    standarData(filepath,storedir)

    print 'extractdate completed !'

    return storedir

def extractPartData(rawdir,storedir):
    '''
    this function is to extract data in rawdir but not in storedir
    args:
    rawdir -- the  directory to store raw file
    storedir -- the directory to store standard data
    '''
    existsRawFile = [name.split('.sdf.gz',1)[0].strip() for name in listdir(rawdir) if name.startswith('Compound')]

    existsStorFile = [name.split('.json',1)[0].strip() for name in listdir(storedir)]

    needExtract  = [name for name in existsRawFile if name not in existsStorFile]

    num =len(existsStorFile)

    f = open(pjoin(pubchem_model,'errorStandardFile'),'w')

    for name in needExtract:
        
        # if name = 'Compound_059475001_059500000_21320161218001048_171030103401':
        if name.startswith('Compound_059475001_059500000_21320161218001048_171030103401'):
            continue

        filepath = pjoin(rawdir,'{}.sdf.gz'.format(name))

        try:
            print   name

            result = standarData(filepath,storedir)

            if not result:

                downloadOne(connectFTP(**pubchem_ftp_infos),name,rawdir)

                standarData(filepath,storedir)

            print '*'*80

        except:
            f.write(name + '\n')
            f.flush()

        num += 1

        print '%s files deal !' % num

def  standarData(filepath,storedir):
    '''
    this function is set to extract the infos in pubchem download file  and save as a json file
    filepath -- the data file 's absolute path 
    storedir -- the directory to store standard data
    '''
    # pre-deal  the file after get the filepath

    filename = psplit(filepath)[1]

    try:

        if filename.endswith('gz'):
        
            gunzip = 'gunzip {}'.format(filepath)

            os.system(gunzip)

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
                if value and  value.count('\n'):

                    value =[i.strip() for i in  value.split('\n') if i]

                    if   all([x.count(':') for x in value]):

                        value_dict = dict()

                        for j in value:

                            j_key = j.split(':',1)[0].strip()

                            j_value = j.split(':',1)[1].strip()

                            value_dict[j_key] = j_value

                            value = value_dict
                            
                mol[key] = value

            # add Standard SMILES 
            standard_smiles = neutrCharge(mol.get("PUBCHEM_OPENEYE_CAN_SMILES"))
            
            mol['PUBCHEM_OPENEYE_STANDARD_SMILES'] = standard_smiles

            mols.append(mol)

        store_file_name = filename.split('.sdf.gz')[0] .strip().replace('-','')+ '.json'

        store_file_path = pjoin(storedir,store_file_name)

        with open(store_file_path, 'w') as wf:
            
            json.dump(mols,wf,indent=2)

        print  '{} dataextract done !'.format(filename)

        return store_file_path

    except:

        'file error,try again'
        # sometime file download not complete and raise error when gunzip file ,unexpected end of file
        # so return None to redownload this file and then standard
        return None

def insertData(storedir):
    '''
    this function is set to inser extracted data to mongdb database ,if data insert failed ,log to errorInsert.json in pubchem_model
    pares:
    storedir -- a json file's path,stored the pubchem data
    '''

    # before insert data ,create a log to mark all files in this edition 
    
    with open(pjoin(pubchem_db,'Compound_{}.files'.format(now)),'w') as wf:

        files = dict()

        for filename in listdir(storedir):

            head  = filename.split('_213')[0].strip()

            files[head] = filename

        json.dump(files,wf,indent=2)


    # connect to db to insert
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.PubChem

    collection = db.Compound
    
    collection_name  ='Compound_' + now 

    num = 0

    all_file_nums = len(listdir(storedir))

    errorInsert = list()

    while num < all_file_nums:

        for filename in listdir(storedir)[num:]:

            print filename
            
            try:

                store_file_path = pjoin(storedir,filename)
            
                mols = json.load(open(store_file_path))

                #  insert data to mongodb
                for mol in mols:

                    mol['CREATED_TIME'] = datetime.now()
               
                collection.insert_many(mols)

                print num,'%s completed ' % filename

                print '-'*50

            except Exception,e :

                errorInsert.append(filename)

            num += 1

        print 'insertData completed !'

    db.Compound.rename(collection_name )
    
    with open(pjoin(pubchem_model, 'errorInsert_{}.json'.format(now)),'w')  as wf:

        json.dump(errorInsert,wf,indent=2)
    
def updateData(insert=False):
    '''
    this function is to uppdate pubchem data  of the ftp site according to the updated date of file in pubchem.log
    args:
    insert -- default is False, process break after standard data when update
    '''
    #  get the record edition of log
    pubchem_log =json.load(open(pjoin(pubchem_model,'pubchem_compound.log')))

    ftp = connectFTP(**pubchem_ftp_infos)

    bufsize=1024 

    # get all file name 
    filenames = ftp.nlst()

    filenames.remove('README-Compound-SDF')

    #  mark the number of file
    filesum = len(filenames)

    num = 0

    # create a dir to store updated data
    updated_data_raw  = pjoin(pubchem_raw,'compound_update_{}'.format(today))
    updated_data_store  = pjoin(pubchem_store,'compound_update_{}'.format(today))

    createDir(updated_data_raw)
    createDir(updated_data_store)

    # process break after all the file's update date checked
    while num < filesum:

        try:

            for name  in filenames[num:]:

                mt = ftp.sendcmd('MDTM {}'.format(name)).strip()

                # file not  existed 
                if name not in pubchem_log:

                    pubchem_log[name] = list()

                    pubchem_log[name].append((mt,today))

                    new = True

                # file  existed but updated
                elif  mt != pubchem_log.get(name)[-1][0].strip():

                    pubchem_log[name].append((mt,today))
                   
                    new = True

                else:
                    new = False

                if new:

                    # download new edition one by one
                    downloadOne(ftp,name,updated_data_raw)

                    print num,'{} \'s new edition is {} '.format(name,mt)

                else:
                    print num, '{} is the latest !'.format(name)

                num += 1

        except Exception ,e:
            
            # print e
             # because too many people connet the site at the same time , so report the 421 error 
            # print 'closing control connection , try again !'

            #  because of  socket.error: [Errno 32] Broken pipe, so ftp connect again
            ftp = connectFTP(**pubchem_ftp_infos)

    # save the updated log file
    with open(pjoin(pubchem_model,'pubchem_compound.log'),'w') as wf:

        json.dump(pubchem_log,wf,indent=2)

    # extract updated data in batch
    if new:

        for filename in listdir(updated_data_raw):

            filepath = pjoin(updated_data_raw,filename)
            # extract new edition file one by one
            result = standarData(filepath,updated_data_store)

            # if no result ,redownload and repeat 
            if not  result:

                downloadOne(connectFTP(**pubchem_ftp_infos),filename,updated_data_raw)

                standarData(filepath,updated_data_store)

            print '{} in datastore updated !'.format(filename)
                     
    print ' pubchem updated completed !'

    if updated_data_store:

            createNewVersion(updated_data_store)

    if insert:
         insertUpdatedData(latest_file)

    return updated_data_store

def createNewVersion(updated_storedir):
    '''
    this function is to create a new .files in database/pubchem/doc/  to record the newest  version
    args:
    updated_storedir -- the directory  store  updated data
    '''
        # before insert, generate the contained files in new edition
    update_file_heads = dict()

    for filename in listdir(updated_storedir):

        head = filename.split('_213')[0].strip()

        update_file_heads[head] = filename

        # get the latest .files file that contain the latest files name in mongodb 
    filenames = [name for name in listdir(pubchem_db) if name.endswith('.files')]

    latest = sorted(filenames,key=lambda x:x.split('Compound_')[1].strip())[-1]
        
    latest_file = json.load(open(pjoin(pubchem_db,latest)))

        # update the latest  files   with  updated  file
    for head ,name in update_file_heads.items():

        latest_file[head] = name

    with open(pjoin(pubchem_db,'Compound_{}.files').format(datetime.now().strftime('%y%m%d')),'w') as wf:

        json.dump(latest_file,wf,indent=2)

    return latest_file

def insertUpdatedData(latest_file): 
    '''
    this function is to generate a  new collection in mongodb PubChem  with updated date and the old
    args:
    latest_file -- the file record the latest file names in newest version
    '''
    # update mongodb ,create new edition
    
    # connect to db to insert
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mymol

    collection = db.Compound

    collection_name  ='pubchem_compound_' + now 

        # all file name in new vrsion
    insertFiles = latest_file.values()

    pubchem_storedirs =[dir_name for dir_name in listdir(pubchem_store) if dir_name.startswith('compound')]

    num = 0

    # circulate to insert all files in insertFiles
    for _dir  in pubchem_storedirs:

        dir_path = pjoin(pubchem_store,_dir)

        for filename in listdir(dir_path):

            if filename in insertFiles:

                fllepath = pjoin(dir_path,filename)

                mols = json.load(open(fllepath))

                #  insert data to mongodb
                for mol in mols:

                    mol['CREATED_TIME'] = datetime.now()

                collection.insert_many(mols)
                
                num += 1

                print num,filename,'done'

    db.Compound.rename(collection_name)

    print 'compound\'new edition created in mongodb '


def selectData(querykey = 'PUBCHEM_OPENEYE_STANDARD_SMILES',queryvalue='O'):
    '''
    this function is set to select data from mongodb
    args:
    querykey -- a specified field in database
    queryvalue -- a specified value for a specified field in database
    '''
    conn = MongoClient('127.0.0.1', 27017 )

    db = conn.mymol

    colnamehead = 'pubchem_compound_'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)

class dbMap(object):
    '''
    this class is to build a mapping relation between key field in database
    '''
    def __init__(self,latestfilepath):

        latest_file = json.load(open(latestfilepath))

        insertFiles = latest_file.values()

        compound_storedirs =[dir_name for dir_name in listdir(pubchem_store) if dir_name.startswith('compound')]

        filepaths  =   list()

        for _dir  in compound_storedirs:

            dir_path = pjoin(pubchem_store,_dir)

            for filename in listdir(dir_path):

                if filename in insertFiles:

                    filepath = pjoin(dir_path,filename)

                    filepaths.append(filepath)

        self.filepaths = filepaths

        self.mapdir = pjoin(pubchem_map,psplit(latestfilepath)[1].strip().split('.files')[0].strip())

        createDir(self.mapdir)

    def mapName2ID(self):

        name_id = dict()

        for index,filepath in enumerate(self.filepaths):

            print index,psplit(filepath)[1].strip()

            blocks = json.load(open(filepath))

            for block in blocks:

                compound_id = block.get("PUBCHEM_COMPOUND_CID")
                
                iupac = block.get("PUBCHEM_IUPAC_NAME")

                iupac_open = block.get("PUBCHEM_IUPAC_OPENEYE_NAME")

                iupac_trad = block.get("PUBCHEM_IUPAC_TRADITIONAL_NAME")

                iupac_cas = block.get("PUBCHEM_IUPAC_CAS_NAME")

                iupac_sys = block.get("PUBCHEM_IUPAC_SYSTEMATIC_NAME")

                names = [iupac,iupac_open,iupac_trad,iupac_cas,iupac_sys]

                for name in names:

                    if name not in name_id:

                        name_id[name] = list()

                    name_id[name].append(compound_id)

        with open(pjoin(self.mapdir,'name2id.json'),'w') as wf:

            json.dump(name_id,wf,indent=2)

        print 'name have id :', len(name_id)

        print 'mapName2ID completed ! '

        return name_id

    def mapID2Name(self,name_id):

        id_name = value2key(name_id)

        with open(pjoin(self.mapdir,'id2name.json'),'w') as wf:

            json.dump(id_name,wf,indent=2)

        print 'id have name', len(id_name)

        print 'mapID2Names completed ! '

        return id_name

    def mapStandSmi2ID(self):

        standSmi_id = dict()

        for filepath in self.filepaths:

            blocks = json.load(open(filepath))

            for block in blocks:

                compound_id = block.get("PUBCHEM_COMPOUND_CID")
                
                standSmi = block.get("PUBCHEM_OPENEYE_STANDARD_SMILES")

                if standSmi:

                    if standSmi not in standSmi_id:

                        standSmi_id[standSmi] = list()

                    standSmi_id[standSmi].append(compound_id)

        with open(pjoin(self.mapdir,'standsmi2ids.json'),'w') as wf:

            json.dump(standSmi_id,wf,indent=2)

        print 'standSmi:', len(standSmi_id)

        print 'mapStandSmi2ID completed ! '

        return standSmi_id

    def mapping(self):

         name_id = self.mapName2ID()

         id_name= self.mapID2Name(name_id)

         self.mapStandSmi2ID()

def main():

    modelhelp = model_help.replace('*'*6,sys.argv[0]).replace('&'*6,'PubChem compound').replace('#'*6,'pubchem compound')
   
    funcs = (downloadData,extractData,standarData,insertData,updateData,selectData,dbMap,pubchem_store)

    getOpts(modelhelp,funcs=funcs)
    
if __name__ == '__main__':

    main()
    # latestfilepath = '/home/user/project/molecular_v1/mymol_v1/pubchem/database/Compound_171117.files'
    # pubchemmap = dbMap(latestfilepath)
    # pubchemmap.mapping()


