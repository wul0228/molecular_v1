#!/usr/bin/env python
# --coding:utf-8--
# date:20171115
# author:wuling
# emai:ling.wu@myhealthgene.com

'''
this model is to create template for py file
'''

helpdoc = '''
Usage: python manage.py  [OPTION]...[MODELNAME]...

Manage model and sub-model 

-h, --help     give this help
-i, --init     init a new model and create sub-model
-u, --update   update a model in current directory,if name=all,update all
-d, --delete   delete the specified model
'''

pytemplate = '''
#!/usr/bin/env python
# --coding:utf-8--
# date: 
# author:
# emai:

#this model set  to

import sys
sys.path.append('../..')
sys.setdefaultencoding = ('utf-8')
from share import *
from config import *  

version  == 1.0

def downloadData():
    return

def  extractData():
    return

def standarData():
    return

def insertData():
    return

def updateData():
    return

def selectData():
    return

def main():
    return

if __name__ == '__main__':
    main()
'''

_all_ = [helpdoc,pytemplate]
