#!/usr/bin/env python
# --coding:utf-8--
# date:20171107
# author:wuling
# emai:ling.wu@myhealthgene.com

#+++++++++++++++++++++++++ packages ++++++++++++++++++++++++++++++++++++++#
import os , sys, getopt, tsv, json, time, rdkit, MySQLdb
from template import *
from ftplib import FTP
from rdkit import Chem
from rdkit.Chem import AllChem
from lxml import etree as et
from xmltodict import parse
from datetime import datetime
from selenium import webdriver
from pymongo import MongoClient
from multiprocessing.dummy import Pool as ThreadPool

#+++++++++++++++++++++++++ simplify  method+++++++++++++++++++++++++++++++++#
listdir = os.listdir

pjoin = os.path.join

psplit = os.path.split

pexists = os.path.exists

mfmf = Chem.MolFromMolFile

mfsmi = Chem.MolFromSmiles

mtsmi = Chem.MolToSmiles

mfsma = Chem.MolFromSmarts

mtsma = Chem.MolToSmarts

 #++++++++++++++++++++++++universal consttant +++++++++++++++++++++++++++++++++#

mymol_path =psplit(os.path.abspath(__file__))[0]

now  = datetime.now().strftime('%y%m%d')

today = datetime.now().strftime('%y%m%d%H%M%S')

#~~~~~~~~~~~~~~~~~~~PubChem~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
pubchem_ftp_infos = {
    'host' : 'ftp.ncbi.nlm.nih.gov' ,
    'user':'anonymous',
    'passwd' : '',
    'logdir' : '/pubchem/Compound/CURRENT-Full/SDF/'
    }

pubchem_compound_path = '/pubchem/Compound/CURRENT-Full/SDF/'

#~~~~~~~~~~~~~~~~~~~CheEBI~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
chebi_ftp_infos = {
    'host' : 'ftp.ebi.ac.uk',
    'user':  '',
    'passwd': '',
    'logdir':  '/pub/databases/chebi/SDF/'
    }

chebi_compound_path = '/pub/databases/chebi/SDF/'

chebi_compound_filename =  'ChEBI_complete.sdf.gz'

chebi_compound_filepath =  '/pub/databases/chebi/SDF/ChEBI_complete.sdf.gz'

#~~~~~~~~~~~~~~~~~~~DrugBank~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

drugbank_homepage = 'https://www.drugbank.ca'

drugbank_start_url = 'https://www.drugbank.ca/releases/latest'

drugbank_log_user = 'myhealthgene@163.com'

drugbank_log_passwd = 'myhealthgene@408'

#~~~~~~~~~~~~~~~~~~~KEGG~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
kegg_dbget_url = 'http://www.kegg.jp/dbget-bin/www_bfind?compound'

#++++++++++++++++++++++++init file and directory ++++++++++++++++++++++++++++++++++#



