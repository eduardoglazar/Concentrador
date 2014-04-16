#!/usr/bin/python
# -*- coding:utf-8 -*-

""" Programa para teste parser

54 41 44 30 00 1C 00 00 00 00 AA 55 00 13 28 72 60 05 0A 02  00 00 0105 0A 07 FF FF FF 05 0A 0C FF FF FF 33 63 00 
54414430001C00000000AA550013287260050A02000001050A07FFFFFF050A0CFFFFFF336300 

54 41 44 - CabeÃ§alho "TAD"
30 - Versao 3.0 do sistema
00 - Byte livre
1C - RSSI - Qualidade do sinal em dBm
00 00 00 00 - Bytes livres
AA 55 - PreÃ¢mbulo do pacote PIMA agrupado (Sempre 2 bytes)
00 13 28 72 60 - Serial do Medidor (Sempre 5 bytes)
05 - Tamanho do consumo ativo + escopo e Ã­ndice
0A 02 - Escopo e Ã­ndice do KWh
00 00 01 - Consumo do KWh
05 - Tamanho do consumo Reativo Indutivo + Escopo e Ã­ndice
0A 07 - Esopo e Ã­ndice do Reativo Indutivo
FF FF FF - Consumo KWh do Reativo Indutivo - FF por nÃ£o ter medidor!
05 - Tamanho do consumo capacitivo + escopo e Ã­ndice
0A 0C - Escopo e Ã­ndice do capacitivo
FF FF FF - Consumo KWh do Capacitivo - FF por nÃ£o ter medidor!
33 63 - CRC
00 - BCC (!Inativo!) """

import serial
import time
import MySQLdb
import crcmod	#Biblioteca necessário para o cálculo do CRC16
import binascii #Biblioteca necessario para conversao de HEX 2 ASCII


crc16 = crcmod.predefined.mkCrcFun('crc-16')		#Definicao da funcao para calculo do CRC16

print(" ###### TAD ANALYSER V2.0 ######")
#delta=input('Entre com o delta de envio:')
#coletas=input('Entre com o nÃºmero de coletas:')
#t_coleta = 255*delta*coletas					#Tempo total da coleta, em segundos

delta = 10
coletas = 2
t_coleta = 255*delta*coletas

def bcd2int(my_list):  # Don't use `list` as variable name
    product = 0
    i=0
    tam = len(my_list)
    for item in my_list:
        product += item * (pow(10,tam - i))
        i+=1
    return product/10

def hex2list(chars):
    for char in chars:
        char = ord(char)
        for val in ((char >> 4) , char & 0xF):
            if val == 0xF:
                return
            yield val



medidor = serial.Serial('/dev/ttyUSB0', 115200)
print("Serial medidor")
con = MySQLdb.connect(host='localhost', user='analisador', passwd='analisador',db='log')
c = con.cursor()
print("Banco De Dados concectado")
medidor.flushInput();
medidor.write("ATTAD_REQ0\r\n");	#Solicita para recebimento

t_total = int(time.time()) + t_coleta   
t_inicial5 = int(time.time())		# Tempo inicial como parametro 5min
t_inicial2 = int(time.time())		# Tempo inicial como parametro para 2min
treshold_2min = 99999				# Garante tratar primeiro a rotina de 5min
treshold_5min = 300					# Trata primeiro a rotina de 5min
while (1):           # Loop infinito
	if int(time.time()) > t_inicial5 + treshold_5min:
		treshold_5min = 99999				#Garante que a próxima rotina será 2min
		t_inicial2 = int(time.time())		#Armazena o tempo inicial para dormir
		treshold_2min = 120					#Estoura a rotina de 2min após 120s
		medidor.write("ATTAD_WAK\r\n")		#Acorda o TAD
		time.sleep(1)						#Delay para enviar o próximo comando
		medidor.flushInput();
		time.sleep(1)
		medidor.write("ATTAD_REQ0\r\n")		#Solicita para recebimento
		
		print ("Enviando REQ0")
		
	if int(time.time()) > t_inicial2 + treshold_2min:
		con.commit()						#Commita os dados para o banco de dados
		t_inicial5 = int(time.time())		#Armazena o tempo para acordar
		treshold_2min = 99999				#Garante que a próxima rotina será 5min
		treshold_5min = 300					#Estoura a rotina de 5min após 300s
		medidor.write("ATTAD_SLP\r\n")		#Manda o coordenador dormir
		time.sleep(1)						#Delay de 1 segundo
		medidor.flushInput();				#Limpa o buffer
		time.sleep(1)
		#medidor.flushInput();
		print ("Enviando SLP para coordenador")
	
	if medidor.inWaiting()> 0:
			primeira = medidor.read(1)
			if (primeira=="T"):
				if (medidor.read(1)=="A"):
					if medidor.read(1)=="D":
						if medidor.read(1) == "_":
							continue
						#versao = bcd2int(list(hex2list(medidor.read(1))))			#Lê a versão do TAD
						byte_livre_1 = bcd2int(list(hex2list(medidor.read(1))))		#Lê o Byte Livre
						tamanho_pima = ord(medidor.read(1))							#Lê o tamanho do pacote PIMA
						byte_livre_2 = bcd2int(list(hex2list(medidor.read(1))))		#Lê o byte livre
						rssi = bcd2int(list(hex2list(medidor.read(1))))				#Lê o RSSI
						dados_1 = medidor.read(2)									#Dados desnecessários
						pacotao = medidor.read(55)									#Armazena os dados a serem tratados
						tratado = "".join("%02x" % ord(c) for c in pacotao)			#Trata os dados e armazena todos juntos
						cdc = tratado[4:14]											#Armazena o CDC
						consumo_ativo = tratado[20:30]
						consumo_reativo = tratado[36:46]
						consumo_capacitivo = tratado[52:62]
						consumo_hponta = tratado[68:78]
						consumo_hfponta = tratado[84:94]
						consumo_reservado = tratado[100:110]
						crc_msb = hex(ord(medidor.read(1)))[2:]							#Lê o CRC MSB
						crc_lsb = hex(ord(medidor.read(1)))[2:]							#Lê o CRC LSB
						if crc_lsb != '0':
							aux_crc = [crc_lsb,crc_msb]										#Cria o array com o MSB e LSB do CRC já invertidos
						elif crc_lsb == '0':
							aux_crc = [crc_msb]
						crc_lido = ''.join(aux_crc)										#
						
						
						
					#	cdc = bcd2int(list(hex2list(medidor.read(5))))				#Lê o CDC do medidor				
					#	tam_ativo = medidor.read(1)									#Lê o tamanho da leitura
					#	escopo_ativo = medidor.read(2)								#Lê o escopo da leitura
					#	consumo_ativo = bcd2int(list(hex2list(medidor.read(ord(tam_ativo) - 2))))	#Lê o consumo ativo
					#	tam_reativo = medidor.read(1)								#Lê o tamanho da leitura
					#	escopo_reativo = medidor.read(2)							#Lê o escopo da leitura
					#	consumo_reativo = bcd2int(list(hex2list(medidor.read(ord(tam_reativo) - 2)))) #Lê o consumo reativo
					#	tam_capacitivo = medidor.read(1)							#Lê o tamanho do capacitivo
					#	escopo_capacitivo = medidor.read(2)							#Lê o escopo do capacitivo
					#	consumo_capacitivo =  bcd2int(list(hex2list(medidor.read(ord(tam_capacitivo) - 2)))) #Lê o consumo capacitivo
					#	tam_hponta = medidor.read(1)							#Lê o tamanho do horário de ponta
					#	escopo_hponta = medidor.read(2)							#Lê o escopo do horário de ponta
					#	consumo_hponta =  bcd2int(list(hex2list(medidor.read(ord(tam_hponta) - 2)))) #Lê o consumo do horário de ponta
					#	tam_hfponta = medidor.read(1)							#Lê o tamanho do horário de fora deponta
					#	escopo_hfponta = medidor.read(2)							#Lê o escopo do horário de fora de ponta
					#	consumo_hfponta =  bcd2int(list(hex2list(medidor.read(ord(tam_hfponta) - 2)))) #Lê o consumo do horário fora de ponta
					#	tam_reservado = medidor.read(1)							#Lê o tamanho do horário reservado
					#	escopo_reservado = medidor.read(2)							#Lê o escopo do horário reservado
					#	consumo_reservado =  bcd2int(list(hex2list(medidor.read(ord(tam_reservado) - 2)))) #Lê o consumo do horário reservado
					#	crc_msb = hex(ord(medidor.read(1)))[2:]								#Lê o CRC MSB
					#	crc_lsb = hex(ord(medidor.read(1)))[2:]								#Lê o CRC LSB
					#	aux_crc = [crc_lsb,crc_msb]										#Cria o array com o MSB e LSB do CRC já invertidos
					#	crc_lido = ''.join(aux_crc)										#
					#	#bcc = medidor.read(1)
						
						#Tratamento do CRC
						crc_aux = hex(crc16(binascii.a2b_hex(tratado)))[2:]
						
						if (crc_aux[2:3] == '0') and (crc_aux[0:1] != '0'):
							crc_msb = crc_aux[0:2]
							crc_lsb = crc_aux[3:4]
							aux_crc = [crc_msb,crc_lsb]	
							crc_calculado = ''.join(aux_crc)
						elif (crc_aux[0:1] == '0') and (crc_aux[2:3] != '0'):
							crc_msb = crc_aux[1:2]
							crc_lsb = crc_aux[2:4]
							aux_crc = [crc_msb,crc_lsb]	
							crc_calculado = ''.join(aux_crc)
						elif (crc_aux[0:1] == '0') and (crc_aux[2:3] == '0'):
							crc_msb = crc_aux[1:2]
							crc_lsb = crc_aux[3:4]
							aux_crc = [crc_msb,crc_lsb]	
							crc_calculado = ''.join(aux_crc)
						else:
							crc_calculado = crc_aux
												
						if tamanho_pima == 27:				#Se for tabela vazia força a entrada dos seguintes parâmetros
							print ("Tabela vazia")
							#medidor.flushInput();
							consumo_ativo = 'ffff'
							consumo_reativo = 'ffff'
							consumo_capacitivo = 'ffff'
							consumo_hponta = 'ffff'
							consumo_hfponta = 'ffff'
							consumo_reservado = 'ffff'
							c.execute ("INSERT INTO coletor (ID, CDC, ATIVO, REATIVO, CAPACITIVO, PONTA, HFPONTA, HRESERVADO, TIME) 				VALUES(ID,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)",(cdc,consumo_ativo,consumo_reativo,consumo_capacitivo,consumo_hponta,consumo_hfponta,consumo_reservado))
							#c.execute("INSERT INTO `coletor` VALUES(ID,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)"%(cdc,consumo_ativo,consumo_reativo,consumo_capacitivo,consumo_hponta,consumo_hfponta,consumo_reservado))
						if crc_calculado == crc_lido:
							c.execute ("INSERT INTO coletor (ID, CDC, ATIVO, REATIVO, CAPACITIVO, PONTA, HFPONTA, HRESERVADO, TIME) VALUES(ID,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)",(cdc,consumo_ativo,consumo_reativo,consumo_capacitivo,consumo_hponta,consumo_hfponta,consumo_reservado))
							#c.execute("INSERT INTO `coletor` VALUES(ID,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)"%(cdc,consumo_ativo,consumo_reativo,consumo_capacitivo,consumo_hponta,consumo_hfponta,consumo_reservado))
							#c.execute ("INSERT INTO crc (ID, PACOTE, CALCULADO, RECEBIDO, HORA) VALUES(ID,%s,%s,%s,CURRENT_TIMESTAMP)",(tratado,crc_calculado,crc_lido))
							#con.commit()
							print ( "TAD %s, leitura %s, rssi: %s - sucesso"%(cdc,consumo_ativo,rssi))
						else:
							print ("CRC nao conferiu, CRC LIDO:")
							print(crc_lido)
							print("CRC CALCULADO:")
							print(crc_calculado)
							print("Pacote a ser calculado")
							print(tratado)
							print("----------------------")
							c.execute ("INSERT INTO crc (ID, PACOTE, CALCULADO, RECEBIDO, HORA) VALUES(ID,%s,%s,%s,CURRENT_TIMESTAMP)",(tratado,crc_calculado,crc_lido))
						
						

						
			else : 
				print ("Nao Identificou String")

#con.commit()    #Executa o Commit 
print("Coleta Finalizada")


"""c.execute("INSERT INTO `leitura` VALUES(30,223,21,23,24,CURRENT_TIMESTAMP)")"""
"""c.execute("INSERT INTO `leitura` VALUES(ID,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)"%(2,3,4,5,6,7))"""
"""c.execute('SELECT * FROM leitura WHERE serial=%s',(3))"""
"""c.execute("UPDATE `leitura` SET  `c_ativo` = %r WHERE  `leitura`.`serial` =%r"%(consumo_reativo,cdc))"""
"""c.execute('SELECT * FROM leitura WHERE serial=%r'%(cdc))"""
	




