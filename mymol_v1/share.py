#!/usr/bin/env python
# --coding:utf-8--
# date:20171023
# author:wuling
# emai:ling.wu@myhealthgene.com

#+++++++++++++++++++++++++ packages ++++++++++++++++++++++++++++++++++++++#

from config import *

reload(sys)
sys.path.append('..')
sys.setdefaultencoding = ('utf-8')

#+++++++++++++++++++++++++ main code ++++++++++++++++++++++++++++++++++++++#

def createDir(dirpath):
    '''
    this function is to create directory if not exist
    '''
    if not os.path.exists(dirpath):

        os.mkdir(dirpath)

    return dirpath

def buildSubDir(name):
    '''
    this function is to build all sub-directory for specified
    '''
    _model = pjoin(mymol_path,name)

    # _load = pjoin(mymol_path,name,'dataload')

    _raw = pjoin(mymol_path,name,'dataraw')

    _store =  pjoin(mymol_path,name,'datastore')

    _db = pjoin(mymol_path,name,'database')

    for _dir in [ _model,_raw,_store,_db]:

        createDir(_dir)      

    return (_model,_raw,_store,_db)

def initLogFile(parser,modelname,storedir,mt=None,rawdir=None):

    # if parser in[ 'chebi' , 'drugbank','kegg']:
    if any([parser.startswith(start) for start in [ 'chebi' , 'drugbank','kegg'] ]):

        # create a log file (json) , to record the data edition and update date
        with open(pjoin(storedir,'{}.log'.format(parser)),'w') as wf:

            json.dump([
                ('version','update date','{}_v*'.format(parser)),
                (mt,today,modelname),],wf,indent=2)

    elif parser == 'pubchem':

        with open(pjoin(storedir,'pubchem_new.log'),'w') as wf: 

            log_dict = dict()

            for filename in listdir(rawdir):

                print filename

                name = filename.split('_213')[0].strip() + '.sdf.gz'

                mt = '213 ' + filename.split('_213')[1].strip().split('_',1)[0].strip()

                if name not in log_dict:

                 log_dict[name] = list()

                log_dict[name].append((mt,today))

            json.dump(log_dict,wf,indent=2)

def lookforExisted(datadir,dirnamehead):

        existFile = filter(lambda x:x.startswith(dirnamehead),listdir(datadir))

        tips = '''
        there have been stored  editions of  below: \n
        {} \n
        if you still want to download again? 
        chose  y/n :'''.format(existFile)
     
        choice  = str(raw_input(tips))

        if choice != 'y':
            return  (None,None)

        else:
            return (choice,existFile)

def choseExisted(existFile):

    tips =  '''
    there are {}  edition below, please chose one of them to continue ?
    {}
    input a index like 0,1,2... (input 'q' to quit):'''.format(len(existFile), \
    [ "{} {} ".format(str(index),name) for index,name in enumerate(existFile) ])

    while True:

        index = raw_input(tips)

        if str(index) == 'q':
            return 'q'
        try:
            edition = int(index)
        except  Exception,e:
            print e

        if edition in range(len(existPubChemFile)):
            return edition

        else:
            print '\n !!! index out of range.please check again \n'

def connectFTP(host,user=None,passwd=None,logdir=None):
    '''
    this function is to connect  ftp site 
    '''
    ftp = FTP(host)

    if user or passwd:

        ftp.login(user,passwd)

    else:

        ftp.login()

    ftp.cwd(logdir)

    return ftp

def  ftpDownload(ftp,filename,savefilename,rawdir,remoteabsfilepath):
    '''
    this function is to download specified file from ftp site
    '''
    bufsize=1024 

    save_file_path =pjoin(rawdir,savefilename)

    file_handle=open(save_file_path,'wb')

    ftp.retrbinary('RETR {}'.format(remoteabsfilepath) ,file_handle.write ,bufsize) 
   
    ftp.set_debuglevel(0) 

    return save_file_path


def connect2DB(server = 'mongodb',host='localhots',port=27017,dbname='ChEBI'):
    '''
    this function is set to connect  database mymol in localhost mysql server
    '''
    if server == 'mongodb':

        db = MongoClient('mongodb://{}:{}/{}'.format(host,port,dbname))

        return db

    elif server == 'mysql':

        connection = MySQLdb.connect(host=host,port=port,user='root',passwd='281625',db=dbname)

        cursor = connection.cursor()

        return cursor

    else:

        print  'no server input'

def atomPair(): 

    #构建需要replace的带电原子类型与其对应的中性原子的pair对
    patts= (
    # Imidazoles
    ('[n+;H]','n'),
    # Amines
    ('[N+;!H0]','N'),
    # Carboxylic acids and alcohols ('[$([O-]);!$([O-][#7])]','O'), # Thiols
    ('[S-;X1]','S'),
    # Sulfonamides 
    ('[$([N-;X2]S(=O)=O)]','N'), 
    # Enamines 
    ('[$([N-;X2][C,N]=C)]','N'), 
    # Tetrazoles 
    ('[n-]','[nH]'),
    # Sulfoxides 
    ('[$([S-]=O)]','S'),
    # Amides
    ('[$([N-]C=O)]','N'),
    #
    ('[O-;X1]',"O"),
    #
    ('[O+;X3]',"O"),
    #
    ('[$([O-]=C)]','O'),
    #20170308
    ('[C-;X3]','C'),
    #20170308
    # ('[Se-;H2]','Se'),
    ('[c-;X3]','c')
    )
    return [(Chem.MolFromSmarts(x),Chem.MolFromSmiles(y,False)) for x,y in patts]

def neutrCharge(smiles):
    """
    this function is to transform the charged smiles to electroneutral
    """
    try:
        mol = mfsmi(smiles)
    except:
        return smiles

    if not mol:
        return smiles
 
    atomPairs= atomPair()

    #circulate all pairs to find if there is a substructure in pre-defined pairs
    for i,(reactant, product) in enumerate( atomPairs):

        while mol.HasSubstructMatch(reactant): 

            #ReplaceSubstructures可选择Replacement = True（默认为False）一步替换所有
            rms = AllChem.ReplaceSubstructs(mol, reactant, product) 

            #rms是一个tuple,内含多个重复的mol，原因不明
            mol = rms[0] 

    # ****** C[O+](C)C
    # ****** [HH].CC1CCC2C(C(OC3C24C1CCC(O3)(O4)C)OC5C(C6CCC(C7C68C(O5)(OC(O8)(CC7)C)C)C)C)C
    try:
        return mtsmi(mol)
    except:
        print '******',smiles
        return smiles


def dataFromDB(database,colnamehead,querykey,queryvalue=None):

    '''
    this function is set to select data from mongodb
    '''
    # get all edition collection
    col_names =[col_name for col_name in  database.collection_names() if col_name.startswith(colnamehead)]

    col_names.sort(key = lambda x:x.split('_')[1].strip())
    
    print  '*'*80
    print 'existed collections','\n'

    for index,ver in enumerate(col_names):

        print  'index {}  edition {} '.format(index,ver)
        print ''

    edition = raw_input('chose edition index or enter to latest : ')

    if edition == '':
        col_name = col_names[-1]
    else:
        col_name = col_names[-1]
        # col _name = col_names[int(edition)]

    col = database.get_collection(col_name)

    print '*'*80

    smiles = ['PUBCHEM_OPENEYE_STANDARD_SMILES','Standard_SMILES']
    while True:

        queryvalue = str(raw_input('input %s  (q to quit) : ' %  querykey))
        
        if queryvalue == 'q' or queryvalue =='Q':

            break

        elif querykey in smiles:
            
            try:
                queryvalue = neutrCharge(queryvalue)

            except Exception,e:

                print e
        
        docs = col.find({querykey:queryvalue})
       
        n = 0

        if docs:

            print '\n','Result: ','\n'

            for doc in docs:
                
                for key,value in doc.items():
                    print key,':',value
                    print ''
               
                print '~'*50
               
                n += 1
            
            print 'allfind:',n
   
        else:
            print 'No record'

        print '-'*80

def deBlankDict(dic):
    '''
    this function is to 
    a. delete key from dic if val is None
    b. if val is list but only contain  a element  so list transfer to this element
    c. if val is list  and have multi elements ,first dedup ,an then  if dict included , iterate to deblank
    d. if val is dict but only have one key , so ,delete the key from parent-dict and update with sub-dict
    '''
    
    for key,val in dic.items():

        if not val:
            
            dic.pop(key)

        elif isinstance(val,list):

            if len(val) == 1:

                dic[key] =val[0]

            else:
                # dedup
                _val = list()

                for v in val:

                    if v not in _val:

                        if isinstance(v,dict):

                            v = deBlankDict(v)

                        _val.append(v)

                dic[key] = _val

        elif isinstance(val,dict):

            if len(val.keys()) ==1:

                val_key = val.keys()[0]

                val_val = val[val_key]

                dic.pop(key)

                dic[val_key] = val_val

            else:
                deBlankDict(val)

    return dic

def multiProcess(func,args,size=16):
    '''
    this function is to concurrent processing
    size -- run  processes all at once
    func --- the  function to run
    args  -- argument for function
    '''

    pool = ThreadPool(size)

    results = pool.map(func,args)

    pool.close

    pool.join

def tsv2json(rawpath,savepath):
    '''
    this function is to thansform the tsv flle to a json file
    rawpath --- the tsv file path
    savepath --- the json file path
    '''
    tsvfile = open(rawpath)
    
    n = 0

    data_list = list()
    
    for line in tsvfile:
        data = line.strip().split('\t')

        if n == 0:
            keys = data
        else:
            data_list.append(dict(zip(keys,data)))

        n += 1

    with open(savepath,'w') as wf:
        
        json.dump(data_list,wf,indent=2)

def tsv2muljson(rawpath,savedir):
    '''
    this function is to thansform the tsv flle to a json file,  apply to big file
    rawpath --- the tsv file path
    savepath --- the json file save dir
    '''
    tsvfile = open(rawpath)

    n = 0

    data_list = list()
    
    for line in tsvfile:

        data = line.strip().split('\t')

        if n == 0:
            keys = data
        else:
            data_list.append(dict(zip(keys,data)))

        if len(data_list) == 50 :

            with open(pjoin(savedir,'{}.json'.format(n)),'w') as wf:
                
                json.dump(data_list,wf,indent=2)

                # clear
                data_list = list()

        n += 1

    with open(pjoin(savedir,'{}.json'.format(n)),'w') as wf:
        
        json.dump(data_list,wf,indent=2)
        
def main():

    print neutrCharge('c1ccccc1CC([NH3+])C(=O)[O-]')

if __name__ == '__main__' :

    main()