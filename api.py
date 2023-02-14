import psutil
import subprocess
import os
import zipfile
import datetime
from flask import request, send_file
from subprocess import PIPE
from flask import Flask, request
from main import CfcProdutivo

app = Flask(__name__)

@app.route('/download-produtivo', methods=['POST'])
def download_produtivo():
    content = get_content_json(["username"])
    dir_name = "dados_salvos"
    file_name = "{}{}.zip".format(content["username"], datetime.datetime.now().strftime("%Y-%m-%d%H-%M-%S"))
    zip_path = os.path.join(dir_name, file_name)
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(dir_name):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    zipf.write(file_path)
    
    return send_file(zip_path, as_attachment=True, download_name=file_name)


@app.route('/start', methods=['POST'])
def run_crawler():
    try:
        content = get_content_json(["login", "senha", "web_hook"])
        pid = run_work(content=content)
        return {
            "sucesso" : True,
            "pid": pid,
            }

    except Exception as e: 
        print(e)
    except:
        return error() 
    
    
@app.route('/kill', methods=['DELETE'])
def remove_job():
    try:
        content = get_content_json(["pid"])
        childrens = killtree(content['pid'])
        return {
                "process": childrens,
                "method": "kill",
                "sucesso": True
                }
    except:
        return error() 
    

################### UTILS ####################### 
#### 

def run_work(content:dict):
    # from init import main
    # main(login=content['login'], senha=content['senha'], id=content['id'], web_hook=content['web_hook'])
    args = f"{content['login']} {content['senha']} {content['web_hook']}"
    process = subprocess.Popen([f"python3 init.py {args}"], shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    pid = process.pid
    return pid


def killtree(pid, including_parent=True):
    parent = psutil.Process(pid)
    childrens = list()
    try:
        for child in parent.children(recursive=True):
            childrens.append(f"child: {str(child)}")
            child.kill()

        if including_parent:
            parent.kill()
    except (psutil.NoSuchProcess):
        pass

    return childrens


def get_content_json(required_fields):
    content = request.json
    validate_content(content, required_fields)
    return content


def validate_content(content, required_fields):
    for field in required_fields:
        if field not in content:
            print(f"Requisição inválida; Campo: {field} não está no agendamento")
            raise ("Requisição inválida.")


def error(msg="Erro desconhecido ao processar requisição."):
    return {
        "sucesso" : False,
        "msg": msg
    }


def invalid_request():
    return error("Requisição inválida.")


def ok():
    return {
        "sucesso" : True
    }