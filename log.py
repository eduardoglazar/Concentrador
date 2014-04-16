#!/usr/bin/python
# -*- coding:utf-8 -*-

""" Programa para teste parser

54 41 44 30 00 1C 00 00 00 00 AA 55 00 13 28 72 60 05 0A 02  00 00 0105 0A 07 FF FF FF 05 0A 0C FF FF FF 33 63 00 
54414430001C00000000AA550013287260050A02000001050A07FFFFFF050A0CFFFFFF336300 

54 41 44 - Cabeçalho "TAD"
30 - Versao 3.0 do sistema
00 - Byte livre
1C - RSSI - Qualidade do sinal em dBm
00 00 00 00 - Bytes livres
AA 55 - Preâmbulo do pacote PIMA agrupado (Sempre 2 bytes)
00 13 28 72 60 - Serial do Medidor (Sempre 5 bytes)
05 - Tamanho do consumo ativo + escopo e índice
0A 02 - Escopo e índice do KWh
00 00 01 - Consumo do KWh
05 - Tamanho do consumo Reativo Indutivo + Escopo e índice
0A 07 - Esopo e índice do Reativo Indutivo
FF FF FF - Consumo KWh do Reativo Indutivo - FF por não ter medidor!
05 - Tamanho do consumo capacitivo + escopo e índice
0A 0C - Escopo e índice do capacitivo
FF FF FF - Consumo KWh do Capacitivo - FF por não ter medidor!
33 63 - CRC
00 - BCC (!Inativo!) """

import serial
import time
import MySQLdb

print(" ###### TAD ANALYSER V2.0 ######")
#delta=input('Entre com o delta de envio:')
#coletas=input('Entre com o número de coletas:')
#t_coleta = 255*delta*coletas					#Tempo total da coleta, em segundos

delta = 10
coletas = 30
t_coleta = 255*delta*coletas
#t_coleta = 3600

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



medidor = serial.Serial('/dev/ttyUSB0', 57600)
print("Serial medidor")
con = MySQLdb.connect(host='127.0.0.1', user='fapes', passwd='fapes',db='fapes')
c = con.cursor()
print("Banco De Dados concectado")
medidor.flushInput();

t_total = int(time.time()) + t_coleta   # Tempo inicial como parametro

while (t_total > int(time.time())):           # Enquanto o tempo de coleta n�o foi estourado
	if medidor.inWaiting()> 0:
			primeira = medidor.read(1)
			if (primeira=="T"):
				if (medidor.read(1)=="A"):
					if medidor.read(1)=="D":
						versao = bcd2int(list(hex2list(medidor.read(1))))
						byte_livre_1 = bcd2int(list(hex2list(medidor.read(1))))
						rssi = bcd2int(list(hex2list(medidor.read(1))))
						byte_livre_2 = bcd2int(list(hex2list(medidor.read(4))))
						preambulo = medidor.read(2)
						cdc = bcd2int(list(hex2list(medidor.read(5))))					
						tam_ativo = medidor.read(1)
						escopo_ativo = medidor.read(2)
						consumo_ativo = list(hex2list(medidor.read(ord(tam_ativo) - 2)))
						del consumo_ativo[len(consumo_ativo)-4]
						del consumo_ativo[len(consumo_ativo)-2]
						consumo_ativo = bcd2int(consumo_ativo)
						tam_reativo = medidor.read(1)
						escopo_reativo = medidor.read(2)
						consumo_reativo = bcd2int(list(hex2list(medidor.read(ord(tam_reativo) - 2))))
						tam_capacitivo = medidor.read(1)
						escopo_capacitivo = medidor.read(2)
						consumo_capacitivo =  bcd2int(list(hex2list(medidor.read(ord(tam_capacitivo) - 2))))
						crc = bcd2int(list(hex2list(medidor.read(2))))
						bcc = medidor.read(1)
	
						c.execute("INSERT INTO `logs` VALUES(ID,%d,%d,CURRENT_TIMESTAMP)"%(cdc,consumo_ativo))
					#	con.commit()
						
						print ( "TAD %d, leitura %d, rssi: %d - sucesso"%(cdc,consumo_ativo,rssi))						
						
						

						
			else : 
				print ("Não Identificou String")

con.commit()    #Executa o Commit 
print("Coleta Finalizada")


"""c.execute("INSERT INTO `leitura` VALUES(30,223,21,23,24,CURRENT_TIMESTAMP)")"""
"""c.execute("INSERT INTO `leitura` VALUES(ID,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)"%(2,3,4,5,6,7))"""
"""c.execute('SELECT * FROM leitura WHERE serial=%s',(3))"""
"""c.execute("UPDATE `leitura` SET  `c_ativo` = %r WHERE  `leitura`.`serial` =%r"%(consumo_reativo,cdc))"""
"""c.execute('SELECT * FROM leitura WHERE serial=%r'%(cdc))"""
	



