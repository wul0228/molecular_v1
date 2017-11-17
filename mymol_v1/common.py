#!/usr/bin/env python
# --coding:utf-8--
# date:20171117
# author:wuling
# emai:ling.wu@myhealthgene.com

'''this model is set to supply a external interface of some  common tools
'''

__all__ = ['tsv2json','tsv2jsons','csv2json','csv2jsons','xml2json']

import sys
sys.path.append('../..')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *

__all__ = ['tsv2json','tsv2muljson']


def sv2json(rawpath,savepath,sep):
    '''
    this function is to thansform the sv flle to a json file
    rawpath --- the sv file path
    savepath --- the json file path
    '''
    print '-'*50
    try:
        tsvfile = open(rawpath)
        
        n = 0

        data_list = list()
        
        for line in tsvfile:

            data = line.strip().split(sep)

            if n == 0:

                keys = list()
                for key in data:
                    if  key.startswith('#'):
                        key = key.replace('#','',1)
                    keys.append(key)

            else:

                data_list.append(dict(zip(keys,data)))

            n += 1

        with open(savepath,'w') as wf:
            
            json.dump(data_list,wf,indent=2)

        print 'converted ! '

    except Exception,e:
        print e

def sv2jsons(rawpath,savedir,sep):
    '''
    this function is to thansform the sv flle to a json file,  apply to big file
    rawpath --- the sv file path
    savepath --- the json file save dir
    '''
    print '-'*50
    try:
        createDir(savedir)

        tsvfile = open(rawpath)

        n = 0

        maxnum = 0

        data_list = list()
        
        for line in tsvfile:

            data = line.strip().split(sep)

            if n == 0:

                keys = list()
                for key in data:
                    if  key.startswith('#'):
                        key = key.replace('#','',1)
                    keys.append(key)

            else:
                data_list.append(dict(zip(keys,data)))

            if len(data_list) == 10000 :

                with open(pjoin(savedir,'{}_{}.json'.format(n-10000,n)),'w') as wf:
                    
                    json.dump(data_list,wf,indent=2)

                    # clear
                    data_list = list()
                    maxnum = n

            n += 1

        with open(pjoin(savedir,'{}_{}.json'.format(maxnum,n)),'w') as wf:
            
            json.dump(data_list,wf,indent=2)

        print 'converted ! '

    except Exception,e:
        print e

def tsv2json(rawpath,savepath):
    sv2json(rawpath,savepath,sep='\t')

def tsv2jsons(rawpath,savepath):
    sv2jsons(rawpath,savepath,sep='\t')

def csv2json(rawpath,savepath):
    sv2json(rawpath,savepath,sep=',')

def csv2jsons(rawpath,savepath):
    sv2jsons(rawpath,savepath,sep=',')

def xml2json(rawpath,savepath):
    '''
    this function is to transform xml file to a json file
    rawpath --- the tsv file path
    savepath --- the json file save dir
    '''
    print '-'*50
    try:
        xmlfile = open(rawpath)

        jsonfile = parse(xmlfile)

        with open(savepath,'w') as wf:

            json.dump(jsonfile,wf,indent=2)

        print 'converted ! '

    except Exception,e:

        print e

def main():

    try:

        (opts,args) = getopt.getopt(sys.argv[1:],"hi:o:f:",['--help=',"--input=","--output=","--function="])

        (_input,_output,_function) =('','','')

        for op,value in opts:

            if op in ("-h","--help"):

                print common_help
                return

            if  op in ('-i','--input='):

                _input = str(value).strip()

            elif op in ('-o','--output'):

               _output = str(value).strip()

            elif op in ('-f','--function'):

                funcs = {
                'tsv2json':tsv2json,
                'tsv2jsons':tsv2jsons,
                'csv2json':csv2json,
                'csv2jsons':csv2jsons,
                'xml2json':xml2json}

                try:
                    _function = funcs[value.strip()]
                except Exception,e:
                    print e

        if _function and _input and _output:

            _function(_input,_output)

    except getopt.GetoptError:

        sys.exit()

if __name__ == '__main__':

    main()