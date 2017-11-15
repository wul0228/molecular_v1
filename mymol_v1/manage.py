#!/usr/bin/env python
# --coding:utf-8--
# date:20171115
# author:wuling
# emai:ling.wu@myhealthgene.com

'''
this model is set to start a new sub-model for a database like chebi
'''
import sys
sys.path.append('../..')
sys.setdefaultencoding = ('utf-8')
import getopt
from share import *
from config import *
from template import pytemplate,helpdoc
from chebi import chebi_v1
from kegg import kegg_compound_v1
from drugbank import drugbank_v1
from pubchem import pubchem_v1

version = '1.0'

model_name = psplit(os.path.abspath(__file__))[1]

def importModel(modelname,allupdate=False):
    '''
    this function is to return a update function of all model under current directory
    modelname --- the specified model's name
    allupdate -- default False,if set to true, update all model one by one
    '''
    updates = {
    'chebi':chebi_v1.updateData,
    'kegg':kegg_compound_v1.updateData,
    'drugbank':drugbank_v1.updateData,
    'pubchem':pubchem_v1.updateData,
    }

    return updates.values() if allupdate else updates.get(modelname)
        
def initModel(modelname):
    '''
    this function is to init a new model with specified model name
    modelname --- the specified model's name
    '''
    # create major dir
    createDir(pjoin('./',modelname))

    # create dataload,dataraw,datastore and database  
    (_model,_raw,_store,_db) = buildSubDir(modelname)

    # create moldename_v1.py
    pyload = open(pjoin(_model,'{}_v1.py'.format(modelname)),'w')
    pyload.write(pytemplate + '\n')
    pyload.close()

    initload = open(pjoin(_model,'__init__.py'),'w')
    initload.close()

    # create docs under dataload and database
    for _dir in [_model,_db]:
        createDir(pjoin(_dir,'docs'))

    print 'model %s  created successfully !' % modelname

def updateModel(modelname):
    '''
    this function is to update the specified mode 
    modelname ---the specified model's name,if == 'all',all model would be updated
    '''

    models = [name for name in listdir('./') if  not (name.endswith('.py') or name.endswith('.pyc'))]

    if modelname != 'all':

        if modelname not in models:

            print 'No model named {} '.format(modelname)
            sys.exit()

        else:
            try:
                update_fun = importModel(modelname)

                print '-'*50

                update_fun()

            except Exception,e:
                print e
    else:

        update_funs = importModel(modelname,allupdate=True)

        for fun in update_funs:

            print '-'*50

            fun()

def deleteModel(modelname):
    
    models =  [name for name in listdir('./') if  not (name.endswith('.py') or name.endswith('.pyc'))]

    if modelname not in models:

        print 'No model named {} '.format(modelname)

        sys.exit()     

    protectmodels = ['chebi','drugbank','kegg','pubchem']

    if modelname in protectmodels:

        print ' this model counld not been delete'

        sys.exit()  

    else:
        # os.remove(pjoin('./',modelname))
        command = 'rm  -r  {}'.format(modelname)
        os.popen(command)

def main():
    
    try:

        (opts,args) = getopt.getopt(sys.argv[1:],"hi:u:d:",['--help=',"init=","--update=",'--delete='])

        for op,value in opts:

            if op in ("-h","--help"):
                print helpdoc

            elif op in ('-i','--init'):
                initModel(value)

            elif op in ('-u','--update'):
                updateModel(value)

            elif op in ('-d','--delete'):
                deleteModel(value)

    except getopt.GetoptError:

        sys.exit()

if __name__ == '__main__':

    main()