#!/usr/bin/env python
# ---coding:utf-8---
# date:20171115
# author:wuling
# emai:ling.wu@myhealthgene.com

'''
this model is set to start a new sub-model for a database like chebi
'''
import sys
sys.path.append('../..')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *
from chebi import chebi_v1  
from drugbank import drugbank_v1
from kegg import kegg_compound_v1
from pubchem import pubchem_compound_v1

version = '1.0'

model_name = psplit(os.path.abspath(__file__))[1]

current_path = psplit(os.path.abspath(__file__))[0]

models =  [name for name in listdir('./') if  not any([name.endswith(x) for x in ['.py','.pyc','.readme']])  and   name != 'map']

class manager(object):

    '''
    this class is to mange all models  under this directory 
    '''

    def __init__(self,modelname):

        self.modelname = modelname

    def helper(self):

        print  manage_help

    def importModel(self,allupdate=False):
        '''
        this function is to return a update function of all model under current directory
        modelname --- the specified model's name
        allupdate -- default False,if set to true, update all model one by one
        '''
        updates = {
        'chebi':chebi_v1.updateData,
        'kegg':kegg_compound_v1.updateData,
        'drugbank':drugbank_v1.updateData,
        'pubchem':pubchem_compound_v1.updateData,
        }

        return updates.values() if allupdate else updates.get(self.modelname)
            
    def initModel(self):
        '''
        this function is to init a new model with specified model name
        modelname --- the specified model's name
        '''
        # check to see if modelname  existed
        print '-'*50

        if self.modelname in models:

            tips = 'the model {} existed ,do  you still want to  create it ? (y/n) : '.format(self.modelname)

            choice = raw_input(tips)

            if choice == 'n':
                return
        # create major dir
        createDir(pjoin('./',self.modelname))

        # create dataload,dataraw,datastore and database  
        (_model,_raw,_store,_db,_map) = buildSubDir(self.modelname)
        createDir(pjoin(_db,'docs'))

        # create moldename_v1.py
        pyload = open(pjoin(_model,'{}_v1.py'.format(self.modelname)),'w')
        pyload.write(py_template.replace('*'*6,self.modelname).strip() + '\n')
        pyload.close()

        initload = open(pjoin(_model,'__init__.py'),'w')
        initload.close()

        introload = open(pjoin(_model,'{}.readme'.format(self.modelname)),'w')
        introload.write(model_intros.replace('*'*6,self.modelname) + '\n')
        introload.close()

        print 'model %s  created successfully !' % self.modelname

    def updateModel(self):
        '''
        this function is to update the specified mode 
        modelname ---the specified model's name,if == 'all',all model would be updated
        '''
        if self.modelname != 'all':

            if self.modelname not in models:

                print 'No model named {} '.format(self.modelname)
                sys.exit()

            else:
                try:
                    update_fun = self.importModel(allupdate=False)

                    print '-'*50
                    update_fun()

                except Exception,e:
                    print e
        else:

            update_funs =self.importModel(allupdate=True)

            for fun in update_funs:

                print '-'*50

                fun()

    def deleteModel(self):
        

        if self.modelname not in models:

            print 'No model named {} '.format(self.modelname)

            sys.exit()     

        protectmodels = ['chebi','drugbank','kegg','pubchem']

        if self.modelname in protectmodels:

            print ' this model counld not been delete'

            sys.exit()  

        else:
            command = 'rm  -r  {}'.format(self.modelname)
            os.popen(command)

class dbMap(object):

    def __init__(self):

        map_dir = dict()

        for model in models:

            model_map = pjoin(current_path,model,'datamap')

            latest_map = sorted([_dir for _dir in listdir(model_map)],key=lambda x: x.rsplit('_',1)[1].strip())[-1]

            latest_map_dir = pjoin(model_map,latest_map)

            map_dir[model] = latest_map_dir

        self.mapdirs = map_dir

    def mapAll(self):

        for convertor in ['name2id','cas2id','name2cas','cas2name','id2cas','id2name']:

            _all = dict()

            for model,mapdir in self.mapdirs.items():

                if model == 'pubchem':

                    continue

                con  = json.load(open(pjoin(mapdir,'{}.json'.format(convertor))))

                print model,len(con)

                for key,vals in con.items():

                    if key not in _all:

                        _all[key] = dict()

                    _all[key][model] = vals


            Map = pjoin(current_path,'map','{}_all_{}.json'.format(convertor,now))

            with open(Map,'w') as wf:
                json.dump(_all,wf,indent=2)

            print 'all',len(_all)

            log_path = pjoin(current_path,'map','map.log')
            
            if not pexists(log_path):

                with open(log_path,'w') as wf:

                    json.dump({},wf,indent=2)
        
            log = json.load(open(log_path))

            savekey = '{}_all'.format(convertor)

            if  savekey not in log:

                log[savekey] = list()

                log[savekey].append({now:self.mapdirs})

            else:

                if log[savekey][-1].values()[0] != self.mapdirs:

                    log[savekey].append({now:self.mapdirs})

            with open(log_path,'w') as wf:

                json.dump(log,wf,indent=2)

            # insert to mongdb

            conn = MongoClient('127.0.0.1',27017)

            db = conn.mymol_map

            col = db.collection

            _all_list = list()

            a = convertor.split('2')[0].strip()
            b = convertor.split('2')[1].strip()

            for key,val in _all.items():
                _all_list.append({a:key,b:val})

            col.insert(_all_list)

            col.rename('{}_{}'.format(savekey,now))

            print '~'*10
            print convertor,'done'
            print '-'*50

    def smi2id(self):
        pass


class query(object):

    def __init__(self,field,value,out):

        self.field = field
        self.value = value
        self.out = out

    def select(self):

        chose = {'name':'name2id','cas':'cas2id','smi':'smi2id'}

        conn = MongoClient('127.0.0.1',27017)

        map_db = conn.mymol_map

        colnamehead = chose[self.field]

        # get all filed2id map relation collection
        col_names =[col_name for col_name in  map_db.collection_names() if col_name.startswith(colnamehead)]

        # get the newest 
        col_names.sort(key = lambda x:x.rsplit('_')[1].strip())

        latest_colname= col_names[-1]

        col = map_db.get_collection(latest_colname)

        docs = col.find({self.field:self.value})

        ids = dict()

        for doc in docs:
            for db,dbids in doc['id'].items():
                if db not in dbids:
                    ids[db] = list()
                ids[db] += dbids

        mol_db = conn.mymol

        dbfileld = {'chebi':'ChEBI&ID','kegg':'kegg_id','drugbank':'drugbank-id'}

        dbcol = {'chebi':'ChEBI','kegg':'kegg_compound','drugbank':'drugbank'}
        
        result = dict()

        for db,dbids in ids.items():

            result[db] = list()

            col_names =[col_name for col_name in  mol_db.collection_names() if col_name.startswith(dbcol[db])]

            col_names.sort(key = lambda x:x.rsplit('_')[1].strip())

            latest_colname= col_names[-1]

            col = mol_db.get_collection(latest_colname)

            for i in dbids:
                key = dbfileld[db]
                mol = col.find({key:i})

                for m in mol:
                    m.pop('_id')
                    result[db].append(m)

        with open(self.out,'w') as wf:

            json.dump(result,wf,indent=4,cls=DateEncoder)
            

def main():
    
    try:

        (opts,args) = getopt.getopt(sys.argv[1:],"hmi:u:d:f:v:o:",['--help',"--map","--init=","--update=",'--delete=',"--field","--value","--output"])

        (field,val,out) = ("","","")

        for op,value in opts:

            man = manager(value)

            if op in ("-h","--help"):
                man.helper()

            elif op in ('-m','--map'):
                man = dbMap()
                man.mapAll()

            elif op in ('-i','--init'):
                man.initModel()

            elif op in ('-u','--update'):
                man.updateModel()

            elif op in ('-d','--delete'):
                man.deleteModel()

            elif op in ('-f','--field'):
                field = value
 
            elif op in ('-v','--value'):
                val = value

            elif op in ('-o','--output'):
                out = value
            if field and val and out:
                man = query(field,val,out)
                man.select()

    except getopt.GetoptError:

        sys.exit()

if __name__ == '__main__':

    main()
   
