import requests
import json
import re
import asyncio
import os
import logging
from bs4 import BeautifulSoup
from datetime import datetime


logging.basicConfig(level=logging.INFO)


class CfcProdutivo:
    def __init__(self):        
        self.session = requests.Session()
        self.URL_BASE = 'https://cfcprodutivo.com.br'
        self.URL_BUSCA = self.URL_BASE + '/framework/admin/ajax/'
        self.URL_PERFIL = self.URL_BASE + '/framework/admin/editar/alunos/'
        self.URL_TEORICA = self.URL_BASE + '/framework/admin/ver/alunos/'
        self.URL_LOGIN = self.URL_BASE + '/framework/admin/ajax/login.php'
        self.URL_FINANCEIRO = self.URL_BUSCA + 'containerTabClientesAlunosVerMovimentacoes.php'
        self.URL_EXAME = self.URL_BUSCA + 'containerTabClientesAlunosVerExamesDetalheDesenvolvimento.php'
        self.URL_PRATICA = self.URL_BUSCA + 'containerTabClientesAlunosVerAgendaPratica.php'
        self.URL_ALUNOS = self.URL_BUSCA + 'ajaxListaClientesAlunos.php'



    def login(self, username:str, password:str, web_hook:str):
        self.USERNAME = username
        self.WEB_HOOK = web_hook

        payload = {'login': username,
                    'senha': password}

        login = self.session.request('POST', self.URL_LOGIN, data=payload).json()
        if login['retorno'] == 0:
            self.error(id='', error=True, msg='Login incorreto')
            assert login['retorno'] == 1, 'Login incorreto'
        logging.info('Login Ok')
    


    def buscar_links(self):
        logging.info('Buscar links')
        ids = list()
        params = {
            'iDisplayStart': '0',
            'iDisplayLength': '1000000',
            'iSortCol_0': '1',
            'sSortDir_0': 'desc',
            }

        soaps = self.request_soap(func='buscar_links', url=self.URL_ALUNOS, params=params)
        hrefs = soaps.select('a[target*="_blank"]')
        for href in hrefs:
            if href.find('img') is None:
                continue

            link = href['href'].replace('\\', '').replace('"', '')
            id = int(re.search(r'\d+', link).group())
            ids.append(id)
        
        for id in ids:
            dados = self.extrair_dados(id=id)
            if dados is not None: 
                self.salvar(dados=dados)
                self.returnMsg(status=True, id=id, error=False, msg="id finalizado")
            else:
                logging.warning(F"Erro no id:{id}, resultado:nonetype")
        self.returnMsg(status=True, id="", error=False, msg="Work Finish")


    def buscar_id(self, id):
        dados = self.extrair_dados(id=id)
        if dados is not None: 
            self.salvar(dados=dados)
            self.returnMsg(status=True, id=id, error=False, msg="Work Finish")

        
    def extrair_perfil(self, id:str):
        infos = dict()
        response_perfil = self.session.request("GET", self.URL_PERFIL + str(id))
        soap = BeautifulSoup(response_perfil.content, 'html.parser')
          
        dados_bancarios = soap.find('textarea', {'id': 'dados_bancarios'}).text.strip()
        observaçao = soap.find('textarea', {'id': 'observacoes'}).text.strip()
        infos.update(
            {  
                'id': soap.find('input', {"name": "id"})['value'],
                'nome': soap.find('input', {"name": "nome"})['value'],
                'cpf': soap.find('input', {"name": "cpf"})['value'],
                'rg': soap.find('input', {"name": "rg"})['value'],
                'mae': soap.find('input', {"name": "mae"})['value'],
                'pai': soap.find('input', {"name": "pai"})['value'],
                'email': soap.find('input', {"name": "email"})['value'],
                'telefone': soap.find('input', {"name": "telefone"})['value'],
                'data_nascimento': soap.find('input', {"name": "data_nascimento"})['value'],
                'profissao': soap.find('input', {"name": "profissao"})['value'],
                'cep': soap.find('input', {"name": "cep"})['value'],
                'endereco': soap.find('input', {"name": "endereco"})['value'],
                'numero': soap.find('input', {"name": "numero"})['value'],
                'complemento': soap.find('input', {"name": "complemento"})['value'],
                'bairro': soap.find('input', {"name": "bairro"})['value'],
                'cidade': soap.find('input', {"name": "cidade"})['value'],
                'uf': soap.find('input', {"name": "uf"})['value'],
                "dados Bancarios": dados_bancarios,
                "observações": observaçao 
            })
        return infos


            
    def extrair_financeiro(self, id):
        financeiro = list()
        soap = self.request_soap(func='extrair_financeiro',id=id, url=self.URL_FINANCEIRO, msg=['Ainda não existem registros financeiros' ])
        
        if soap == []:
            return soap

        hrefs_financeiro = soap.findAll('tr')
        for href in hrefs_financeiro:
            dic = dict()
            parcelas_list = list()

            url = self.URL_BASE + href.td.a['href']
            soap = self.request_soap(func='extrair_financeiro', url=url, id=id)
            legenda = soap.find('p', {'class': 'f_legend'}).strong
            bancario = soap.find('div', {'class': 'span6'})

            table_parcelas = soap.find('table', {'class': 'table'}).tbody
            blocoInformacoes = soap.find('div', {'id': 'blocoInformacoes'})

            for table in blocoInformacoes.findAll('table'):
                for tr_bloco in table.tbody.findAll("tr"):
                    dic.update({tr_bloco.findAll('td')[0].text.strip(): tr_bloco.findAll('td')[1].text.strip()})
            
            dic.update({       
                    "legenda": legenda.text.strip(),
                    "total" : bancario.h3.text.split('R$')[-1].strip(),
                    "pago": bancario.findAll('span')[0].text.split('R$')[-1].strip(),
                    "pendente": bancario.findAll('span')[1].text.split('R$')[-1].strip()
            })

            for tr in table_parcelas.findAll('tr'):
                id_historico = False
                parcelas = dict()

                try:
                    if tr.get('class') or tr.get('role'):
                        tr.decompose()
                        continue
                except: continue
                tds = tr.findAll('td')

                parcelas.update({
                    "data de vencimento": tds[1].text.strip(),
                    "valor": tds[2].text.strip(),
                    "acrescimos": tds[3].text.strip(),
                    "forma de pagamento": tds[4].text.strip(),
                    "conta": tds[5].text.strip(),
                    "situacao": tds[6].text.strip(),
                    "parcela": tds[7].text.strip(),

                })
                id_historico = tds[0].select_one('a[class*="btnAbreHistoricoParcelas"]')['data-id']
                if id_historico:
                    historico = soap.find('tr', {'id': f'blocoHistoricoParcelas_{id_historico}'})

                    if historico.find('div', {"class":"blocoHistoricoParcelasConteudo"}):
                        tds_historico = historico.tbody.findAll('td')

                        informacao_registro = {
                            "data_pagamento": tds_historico[0].text.strip(),
                            "valor": tds_historico[1].text.strip(),
                            "usuario": tds_historico[2].text.strip(),
                            "operacao": tds_historico[3].text.strip(),
                            "observacao": tds_historico[4].text.strip(),
                            "ata": tds_historico[5].text.strip(),
                            "dados_anteriores": {
                                "valor": tds_historico[6].text.strip(),
                                "forma_de_pagamento": tds_historico[7].text.strip(),
                                "conta": tds_historico[8].text.strip(),
                                "vencimento": tds_historico[9].text.strip(),
                            }
                        }
                        parcelas.update({"historico": informacao_registro})
                    else: parcelas.update({"historico": ''})

                parcelas_list.append(parcelas)
            

            dic['parcelas'] = parcelas_list
            financeiro.append(dic)
        
        return financeiro

    
    def extrair_teorica(self, id):
        response_teorica = self.session.request("GET", self.URL_TEORICA + str(id) )
        soap_agenda = BeautifulSoup(response_teorica.content, 'html.parser')
        url_agenda = soap_agenda.find('div', {'id': 'tab_p_3'})['data-url']

        response_agenda = self.session.request("GET", self.URL_BASE + url_agenda )
        soap = BeautifulSoup(response_agenda.content, 'html.parser')
        dias_tabela = soap.findAll("div", {"class": "dia"})
        aulas_list = list()

        for dia in dias_tabela[1:]:
            aulas = dia.select("div[class*='ocupadoPeloAluno']")
            if aulas != []:
                for aula in aulas:
                    hora = aula.find("div", {"class": "labelHora"}).text.strip()
                    tema = aula.find("div", {"class": "tema"}).text.strip()
                    instrutor = aula.find("div", {"class": "instrutor"}).text.strip()
                    sala = aula.find("div", {"class": "sala"}).text.strip()
                    aulas_list.append({
                        'hora': hora,
                        'tema': tema, 
                        'instrutor': instrutor,
                        'sala': sala
                        })
        return aulas_list
        
        
    def extrair_praticas(self, id):
        aulas_list = list()
        soap = self.request_soap(func='extrair_praticas', id=id, url=self.URL_PRATICA, msg=['Não existem aulas agendadas'])
        if soap == []:
            return soap
        for tr in soap.select("tr[class*='blocoHistoricoAulas']"):
            tr.decompose()

        table = soap.table.tbody.findAll('tr')
        for tr in table[1:-2]:
            tds = tr.findAll('td')
            aulas_list.append({
                "aula": tds[1].text.strip(),
                "instrutor": tds[2].text.strip(),
                "veiculo": tds[3].text.strip(),
                "data e hora": tds[4].text.strip(),
                "local": tds[5].text.strip(),
                "situacao": tds[6].text.strip(),

            })
        return aulas_list

    
    def extrair_exames(self, id):
        exames = list()
        for i in range(1, 10):

            params = {
                'idAluno': id,
                'tipo': i
                }
            soap = self.request_soap(func='extrair_exames', id=id, url=self.URL_EXAME, 
                                     msg=['Não há exames', 'Faltam informações para a busca dos dados.'], params=params)
            if soap == []:
                continue
            if soap.findAll('table') == []:
                    return []
            
            tds = soap.table.tbody.findAll('td')
            data, hora = tds[0].contents[0].text.strip().split(' ')
            exames.append({
                'exame': soap.find('h4').text.strip(),
                'data': data,
                'hora': hora,
                'local': tds[0].span.text.strip(),
                'situcao': tds[1].text.strip()
            })

        return exames


    def extrair_dados(self, id):
        try:
            dados = self.extrair_perfil(id=id)
            dados['financeiro'] = self.extrair_financeiro(id=id)
            dados['teorico'] = self.extrair_teorica(id=id)   
            dados['pratico'] = self.extrair_praticas(id=id)
            dados['exames'] = self.extrair_exames(id=id) 
            return dados
        except Exception as msg:
            return self.error(id=id, error=True, msg=msg)


 ############################# UTILS ################################ 
    def request_soap(self, func:str, id=None, msg=None,  url=None, params=None):

        if params is None:
            params = {
                'idAluno': id
                }
        response = self.session.request("GET", url, params=params)
        logging.info(f'{func} GET {response.status_code} {response.url}')

        if msg != None:
            for text in msg:
                if text in response.text:
                    return []
        return BeautifulSoup(response.content, 'html.parser')


    def error(self, id:str, error:bool, msg:str):
        logging.error(f"Aconteceu erro no id: {id}")
        return self.returnMsg(status=False, id=id, error=error, msg=msg)


    def salvar(self, dados:dict):
        nome_arquivo = dados['cpf']
        newpath = "dados_salvos/" + self.USERNAME

        if os.path.exists(newpath):pass
        else: os.makedirs(newpath)
        with open(f'{newpath}/{nome_arquivo}.json', 'w') as fp:
            json.dump(dados, fp)

        logging.info(f"Salvando: dados_salvos/{nome_arquivo}.json")

    
    def web_wook(self, msg:dict):
        try:requests.request('POST', self.WEB_HOOK, json=msg, timeout=5)
        except: logging.error('Erro ao enviar o web hook a url')


    def returnMsg(self, status:bool, id:str, error=False, msg=''):
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        finally_msg = {"timestamp": dt_string, "finalizado": status, "id": id, "error": error, "msg":f"{msg}"}
        return self.web_wook(msg=finally_msg)
