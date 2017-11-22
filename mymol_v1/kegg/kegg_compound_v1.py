#!/usr/bin/env python
# ---coding:utf-8---
# date:20171109
# author:wuling
# emai:ling.wu@myhealthgene.com

'''
this model setted  to download, extract and update kegg data automatically
'''
import sys
sys.path.append('../')
sys.setdefaultencoding = ('utf-8')
import  requests 
from share import *
from config import *
from bs4 import BeautifulSoup as bs

__all__ = ['downloadData','extractData','standarData','insertData','updateData','selectData']

version = '1.0'

model_name = psplit(os.path.abspath(__file__))[1]

# buid directory to store raw an extracted data
(kegg_model,kegg_raw,kegg_store,kegg_db,kegg_map) = buildSubDir('kegg')

def parseDiv(div):
    '''
    this function is to paese a div return a dict {a.text:a.href} under the div
    args:
    div --- a element in html
    '''
    atext_href = dict([ (a.text.replace(' ','&').replace('.','*'), a['href']) for a in div.select('a') if not a.text.count('show all')])

    return atext_href  if atext_href else div.text

# main code
def getMolHtml(href,rawdir):
    '''
    this function is to get html  of a specified  molecule in kegg compound website
    args:
    href --- the link of compound in kegg website
    rawdir -- the save directory of compound html
    '''
    _id = href.rsplit('cpd:')[1].strip()

    mol_html = requests.get(href).text

    with open(pjoin(rawdir,'{}.html'.format(_id)),'w') as wf:

        wf.write(mol_html)

def parseMolHtml(htmlpath,storedir):
    '''
    this function is to parse a compound infos from kegg  Compund html
    args:
    htmlpath --- the raw html file store directory
    sroredir --- the store directore of ectracted data
    '''
    _id  = htmlpath.rsplit('/',1)[1].split('.html')[0].strip()

    mol_web = open(htmlpath).read()

    mol_soup = bs(mol_web,'lxml')

    form = mol_soup.find('form')

    table = form.select('table > tr > td > table')[0]

    trs = table.select('tr')

    mol = dict()    

    mol['kegg_id'] = _id

    n = 0

    for tr in trs:

        try:
            th = tr.select('th')[0].text.strip()
            td = tr.select('td')[0]
        except:
            pass
          
        n += 1

        if th == 'Entry':
            val = td.text.split(_id)[1].strip()

        elif th == 'Name':
            val = [ name.replace(';','') for name in  td.text.strip().split('\n') if name]

        elif th == 'Structure':

            val = dict( [ (a.select('img')[0]['name'],a['href'])  for a in td.select('a') ] )

        elif th == 'Remark':

            divs = td.select('div > div ')
            
            val = dict([( div.text.strip(),parseDiv(divs[index+1]) ) for index,div in enumerate(divs)  if index%2 == 0])

        elif th == 'Reaction':
         
            val = dict( [ (a.text,a['href'])  for a in td.select('div > a') if not a.text.count('show all')] )

        elif th ==  'Pathway':
            val = {}
            _map = td.select('table > tr ')
            
            for m in _map:

                m_id =m.select('td')[0].select('a')[0].text
                m_link =m.select('td')[0].select('a')[0]['href']
                m_name=m.select('td')[1].text

                val.update({m_id:{'href':m_link,'name':m_name}})
        elif th == 'Enzyme':

            val = dict( [(a.text.replace(' ','&').replace('.','*'),a['href'])  for a in td.select('div > a')  if not a.text.count('show all')] )

        elif th == 'Other DBs':
            
            th = th.replace(' ','_')

            divs = td.select('div > div ')
            
            val = dict([( div.text.strip(),parseDiv(divs[index+1]) ) for index,div in enumerate(divs)  if index%2 == 0])

        elif th == 'LinkDB':

            val = dict([(a.select('img')[0]['name'],a['href']) for a in td.select('a')])

        elif th == 'KCF data':

            th = th.replace(' ','_')

            val = td.select('div')[0].text

        else:
            val = td.text.strip()

        mol[th] = val


    with open(pjoin(storedir,'{}.json'.format(_id)),'w') as wf:

        json.dump(mol,wf,indent=2)

    return mol

def getMolFile(filelink,storedir):
    '''
    this function is to get the molfile string and convert to standard smiles to store
    args:
    filelink --- the href of molecule of kegg 
    storedir --- he directory to store mol json file
    '''
    # 1. get mol string 
    _id =filelink.split('compound+')[1].strip()

    print _id

    mol_web = requests.get(filelink).text

    mol_soup = bs(mol_web,'lxml')

    mol = mol_soup.select('body')[0].text.strip()

    first = mol.split(' ',1)[0].strip()

    if len(first) == 1:
        mol_str = ' \n'*3 +  '  ' + mol + '\n'
    else:
        mol_str = ' \n'*3 +  ' ' + mol + '\n'

     # 2. convert to smiles
    moldir = pjoin('./','mols')
    createDir(moldir)

    with open(pjoin(moldir,'{}.mol'.format(_id)),'w')  as wf:
        wf.write(mol_str)

     # 3. save to store dir
    mol_dict = json.load(open(pjoin(storedir,'{}.json'.format(_id))))
    
    mol_dict['Mol_String'] = mol_str

    try:
        mol_mol =mfmf(pjoin(moldir,'{}.mol'.format(_id)))

        mol_smi = mtsmi(mol_mol)

        mol_stand_smi = neutrCharge(mol_smi)

        mol_dict['Standard_Smiles'] = mol_stand_smi

    except:
        print _id,'error'
        
    with open(pjoin(storedir,'{}.json'.format(_id)),'w') as wf:
        json.dump(mol_dict,wf,indent=2)

def getLinkDB(alldblink):
    '''
    this function is to get all the db link infos of molecule in kegg
    args:
    alldblink -- the link of alldb  of mol in kegg web site
    '''
    dblink_web = requests.get(alldblink).content

    dblink_soup = bs(dblink_web,'lxml')

    all_a = dblink_soup.select('body > pre > a')

    links = dict([ (a.text,a['href'] ) for a in all_a if not a.text.startswith('All databases')  and not a.text.startswith('Download') ])

    for key,val in links.items():
        print key,val

    return links

def getVersion():
    '''
    this function is to get the lates version of kegg compound ,return latest release and entries
    '''

    dbget_page = requests.get(kegg_dbget_url)

    dbget_soup = bs(dbget_page.text,'lxml')

    divs = dbget_soup.find_all('div')

    for div in divs:

        if div.text.count('Release'):

            release = div.text.split('Release')[1].strip().split('\n',1)[0].strip().split('/')[0].strip().replace(' ','_')
            entries = div.text.split('entries')[0].strip().rsplit('\n',1)[1].strip()
            break

    return (release,entries)

def downloadData(redownload = False):
    '''
    this function is to connect kegg web  site to crawling the compound data
    args:
    redownload-- default False, check to see if exists an old edition before download
                       -- if set to true, download directly with no check
    download process
    1. get release and entries
    2. get all href of compound
    3. get compound infos one by one
    4. initialiaze log file
    '''
    if  not redownload:

     # check  to see if there have been an edition

        (choice,existKeggFile) = lookforExisted(kegg_raw,'kegg_compound')

        if choice != 'y':
            return

    if redownload or not existKeggFile or  choice == 'y':

        # 1. get  the release and entries
        (release,entries) = getVersion()

        # 2. get all href of compound
        comphref_page = 'http://www.kegg.jp/dbget-bin/www_bfind_sub?dbkey=compound&keywords=c&mode=bfind&max_hit=nolimit'
        
        comphref_page = requests.get(comphref_page)
       
        comphref_soup = bs(comphref_page.text,'lxml')

        comp_divs = comphref_soup.find_all(name='div',attrs = {'style':'width:600px'})

            # create a dict to store compound id and its href
        id_href = dict()

        for  comp in comp_divs:

            a_tag = comp.select('a')[0]

            kegg_id  = a_tag.text

            kegg_href = 'http://www.kegg.jp' + a_tag['href']

            id_href[kegg_id] = kegg_href

        # 3. get compound infos one by one
        kegg_compound_raw = pjoin(kegg_raw,'kegg_compound_{}_{}'.format(release,today))

        createDir(kegg_compound_raw)

        func = lambda x: getMolHtml(x,kegg_compound_raw)

        multiProcess(func,id_href.values(),16)

        # 4. initialiaze log file
    if not os.path.exists(pjoin(kegg_model,'kegg_compound.log')):

        initLogFile('kegg_compound',model_name,kegg_model,mt=release)

    return kegg_compound_raw

def extractData(rawdir):
    '''
    this function is to parse a compound infos from kegg  Compund html in batch
    args:
    rawdir -- the save directory of compound html
    '''
    storedir = pjoin(kegg_store,rawdir.split('kegg/dataraw/',1)[1].strip())

    createDir(storedir)

    htmlpaths = [pjoin(rawdir,filename) for filename in listdir(rawdir)]

    func = lambda x : parseMolHtml(x,storedir)

    multiProcess(func,htmlpaths,16)

    print 'extractData completed'

    standarData(storedir)
    
    return storedir

def standarData(storedir):
    '''
    this function is to get the mol struncture for every molecule and convert to standsmile to save
    args:
    storedir -- the directory to store standard file
    '''
    mol_links  = dict()

    for index,filename in enumerate(listdir(storedir)):
        
        filepath = pjoin(storedir,filename)

        mol = json.load(open(filepath))

        structure = mol.get("Structure")

        if not structure:
            continue

        mol_stru = structure.get("Mol")

        if mol_stru:
            mol_links[filename] = 'http://www.kegg.jp/'  + mol_stru

    func = lambda x : getMolFile(x,storedir)

    multiProcess(func,mol_links.values(),16)

    # command = 'rm -r ./mols'

    # os.popen(command)

    print 'standarData completed'

def insertData(storedir):
    '''
    this function is to insert extracted data to mongodb database
    args:
    storedir ~ a json file's path dir ,stored the drugbank data
    '''

    conn  = MongoClient('localhost',27017)
    
    db = conn.mymol 

    collection = db.collection

    collection_name = storedir.split('kegg/datastore/',1)[1].strip().split('/')[0].strip()

    for filename in listdir(storedir):

        filepath = pjoin(storedir,filename)

        mol = json.load(open(filepath))
        try:
            collection.insert(mol)
        except Exception,e:
            print filename
            print e

    collection.rename(collection_name)

    print 'insertData completed'

def updateData(insert=True):
    '''
    this function is to check the edition existed and update or not
    args:
    insert -- default is Ture, after standar data ,insert to mongodb, if set to false, process break when standarData completed
    '''
    kegg_compound_log =  json.load(open(pjoin(kegg_model,'kegg_compound.log')))
    
    latest_edition = kegg_compound_log[-1][0].strip()

    (release,entries) = getVersion()

    if release != latest_edition:

        save = downloadData()

        store  = extractData(save)

        standarData(store)

        if insert:
            
            insertData(store)

        kegg_compound_log .append((releases,today,os.path.abspath(__file__)))

        with open(pjoin(kegg_model,'drugbank.log'),'w') as wf:
            json.dump(kegg_compound_log,wf,indent=2)
        
        print  'dataupdate completed !'

    else:

        print 'remote latest edition is %s ' % latest_edition 

        print 'local is the latest edition!'

def selectData(querykey = 'Standard_Smiles',queryvalue='O'):
    '''
    this function is set to select data from mongodb
    args:
    querykey --  the filed name 
    queryvalue -- the field value
    '''
    conn = MongoClient('127.0.0.1',27017)

    db = conn.mymol

    colnamehead = 'kegg_compound'

    dataFromDB(db,colnamehead,querykey,queryvalue=None)


class dbMap(object):
    '''
    this class is to build a mapping relation between key field in database
    '''
    def __init__(self,storedir):

        self.storedir = storedir

        self.filepaths = [pjoin(self.storedir,filename) for filename in listdir( self.storedir)]

        self.mapdir = pjoin(kegg_map,psplit(storedir)[1])

        createDir(self.mapdir)

    def mapName2ID(self):

        name_id = dict()

        for filepath in self.filepaths:

            block = json.load(open(filepath))

            kegg_id = psplit(filepath)[1].strip().split('.json')[0].strip()
            
            kegg_name = block.get("Name")

            names = strAndList([kegg_name])

            for name in names:

                if name not in name_id:

                    name_id[name] = list()

                name_id[name].append(kegg_id)

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

    def mapCas2ID(self):

        cas_id = dict()

        for filepath in self.filepaths:

            block = json.load(open(filepath))

            kegg_id = psplit(filepath)[1].strip().split('.json')[0].strip()
            
            kegg_cas  = block.get("Other_DBs").get("CAS:")

            cass = strAndList([kegg_cas])

            for cas in cass:

                if cas not in cas_id:

                    cas_id[cas] = list()

                cas_id[cas].append(kegg_id)

        with open(pjoin(self.mapdir,'cas2id.json'),'w') as wf:

            json.dump(cas_id,wf,indent=2)

        print 'cas have id:', len(cas_id)

        print 'mapCas2ID completed ! '

        return cas_id

    def mapID2Cas(self,cas_id):

            id_cas = value2key(cas_id)

            with open(pjoin(self.mapdir, 'id2cas.json'),'w') as wf:

                json.dump(id_cas,wf,indent=2)

            print 'id have cas :', len(id_cas)

            print 'mapID2Cas completed ! '

            return id_cas

    def mapName2Cas(self,name_id,id_cas):
        
        name_cas= dict()

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

        cas_name= value2key(name_cas)

        with open(pjoin(self.mapdir,'cas2name.json'),'w') as wf:

            json.dump(cas_name,wf,indent=2)

        print 'cas have name: ', len(cas_name)

        print 'mapCas2Name completed ! '

        return cas_name

    def mapStandSmi2ID(self):

        standSmi_id = dict()

        for filepath in self.filepaths:

            block = json.load(open(filepath))

            kegg_id = psplit(filepath)[1].strip().split('.json')[0].strip()
            
            standSmi = block.get("Standard_Smiles")

            if standSmi:

                if standSmi not in standSmi_id:

                    standSmi_id[standSmi] = list()

                standSmi_id[standSmi].append(kegg_id)

        with open(pjoin(self.mapdir,'standsmi2ids.json'),'w') as wf:

            json.dump(standSmi_id,wf,indent=2)

        print 'standSmi:', len(standSmi_id)

        print 'mapStandSmi2ID completed ! '

        return standSmi_id

    def mapping(self):

         name_id = self.mapName2ID()

         id_name= self.mapID2Name(name_id)

         cas_id = self.mapCas2ID()

         id_cas= self.mapID2Cas(cas_id)

         name_cas = self.mapName2Cas(name_id,id_cas)

         cas_name = self.mapCas2Name(name_cas)

         self.mapStandSmi2ID()

def main():

    modelhelp = model_help.replace('*'*6,sys.argv[0]).replace('&'*6,'KEGG').replace('#'*6,'kegg')
   
    funcs = (downloadData,extractData,standarData,insertData,updateData,selectData,dbMap,kegg_store)

    getOpts(modelhelp,funcs=funcs)

if __name__ == '__main__':
    main()
 