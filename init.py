import logging
import sys
import json
from main import CfcProdutivo
from sys import argv

def main(login:str, senha:str, web_hook:str, id=''):
    try:
        client = CfcProdutivo()
        client.login(username=login, password=senha, web_hook=web_hook)
        if id != '':
            client.buscar_id(id=id) 
        else:
            client.buscar_links() 
    except Exception as e:
        print(e)


content = sys.argv[1:]
login, senha, web_hook = content[0], content[1], content[2]
try: id = content[3]
except: id = ''
main(login=login, senha=senha, id=id, web_hook=web_hook)
