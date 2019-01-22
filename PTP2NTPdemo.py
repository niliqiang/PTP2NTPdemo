#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PTP to NTP Demo

import os
import socket
import threading
import time

global interruptFlag, ReferTimestamp
interruptFlag = False
ReferTimestamp = 0

socketNTP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socketNTP.bind(('0.0.0.0', 123))
print('Bind NTP on 123...')
socketPTPEvent = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socketPTPEvent.bind(('0.0.0.0', 319))
print('Bind PTP Event on 319...')
socketPTPGeneral = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socketPTPGeneral.bind(('0.0.0.0', 320))
print('Bind PTP General on 320...')

# PTP 部分处理函数
def FuncPTP():
	timestampPTP = [0]*6
	delayReqData = bytearray(44)
	while True:
		recvFollowUp = False
		recvDelayResp = False
		# 接收 PTP 数据
		print('Receiving PTP server data...')
		syncData, serverAddr = socketPTPEvent.recvfrom(44)
		print('Received from %s:%s.' % serverAddr)
		if syncData[0] == 0:
			# Received Sync packet
			timestampPTP[2] = int(time.time()*1000)
			while not recvFollowUp:
				# Receiving FollowUp packet
				followUpData = socketPTPGeneral.recv(44)
				if followUpData[0] == 0x08 and syncData[31] == followUpData[31]:
					# Received FollowUp packet
					timestampPTP[1] = ReadPTPTimestamp(followUpData, 36)
					recvFollowUp = True
					
			WritePTPHead(delayReqData)
			timestampPTP[3] = int(time.time()*1000)
			WritePTPTimestamp(delayReqData, 36, timestampPTP[3])
			socketPTPEvent.sendto(bytes(delayReqData), serverAddr)
			while not recvDelayResp:
				# Receiving DelayResp packet
				delayRespData = socketPTPGeneral.recv(54)
				if delayRespData[0] == 0x09 and delayRespData[31] == 0xAA:
					# Received DelayResp packet
					timestampPTP[4] = ReadPTPTimestamp(delayRespData, 36)
					recvDelayResp = True
			
			# 本地时钟的 offset		
			timestampPTP[0] = ((timestampPTP[2]-timestampPTP[1]) - (timestampPTP[4]-timestampPTP[3])) // 2
			timestampPTP[5] = int(time.time()*1000)
			# 时间格式转换
			referTimestamp = timestampPTP[5] - timestampPTP[0]
			now = time.asctime(time.localtime(referTimestamp/1000)) 
			# 调用系统指令更改时间
			os.system("date -s '%s'" % now)
			
			print('\n')
		
		if interruptFlag:
			break

	
# 写发送数据包包头
def WritePTPHead(bytearrData):
	bytearrData[0] = 0x81		# messageId: Delay_Req Message (0x1)
	bytearrData[1] = 0x02		# versionPTP: 2
	bytearrData[3] = 0x2C		# messageLength: 44
	bytearrData[6] = 0x06		# PTP_TWO_STEP: True; PTP_UNICAST: True
	bytearrData[29] = 0x01		# SourcePortID: 1
	bytearrData[31] = 0xAA		# sequenceId: 0xAA
	bytearrData[32] = 0x01		# control: Delay_Req Message (1)
	bytearrData[33] = 0xFF		# logMessagePeriod: 127

# 写PTP时间戳
def WritePTPTimestamp(bytearrData, offset, timestamp):
	seconds = timestamp//1000
	milliseconds = timestamp - seconds*1000
	bytearrData[offset] = (seconds >> 24) & 0xFF
	bytearrData[offset + 1] = (seconds >> 16) & 0xFF
	bytearrData[offset + 2] = (seconds >> 8) & 0xFF
	bytearrData[offset + 3] = (seconds >> 0) & 0xFF
	fraction = milliseconds * 1000000
	bytearrData[offset + 4] = (fraction >> 24) & 0xFF
	bytearrData[offset + 5] = (fraction >> 16) & 0xFF
	bytearrData[offset + 6] = (fraction >> 8) & 0xFF
	bytearrData[offset + 7] = (fraction >> 0) & 0xFF
	
# 读PTP时间戳
def ReadPTPTimestamp(byteData, offset):
	seconds = Read(byteData, offset)
	fraction = Read(byteData, offset + 4)
	return seconds*1000 + fraction//1000000
	


# NTP 部分处理函数
def FuncNTP():
	timestampNTP = [0]*6
	respData = bytearray(48)
	recvResp = False
	while True:
		#接收 NTP 数据
		print('    Receiving NTP client data...')
		clientData, clientAddr = socketNTP.recvfrom(48)
		print('    Received from %s:%s.' % clientAddr)
		if (clientData[0] & 0x03) == 0x03:
			# Received NTP client request
			timestampNTP[2] = int(time.time()*1000)
			timestampNTP[1] = ReadNTPTimestamp(clientData, 40)
			WriteNTPHead(respData)
			WriteNTPTimestamp(respData, 16, ReferTimestamp)
			WriteNTPTimestamp(respData, 24, timestampNTP[1])
			WriteNTPTimestamp(respData, 32, timestampNTP[2])
			timestampNTP[3] = int(time.time()*1000)
			WriteNTPTimestamp(respData, 40, timestampNTP[3])
			socketNTP.sendto(bytes(respData), clientAddr)
			
			print('    Client time synchronization succeed. \n')


# 写发送数据包包头
def WriteNTPHead(bytearrData):
	bytearrData[0] = 0x1C		# NTP version: 3; Mode: server(4)
	bytearrData[1] = 0x02		# primary reference: 1
	bytearrData[3] = 0xE7		# Peer Clock Precision: 0.000000 sec

# 写NTP时间戳
def WriteNTPTimestamp(bytearrData, offset, timestamp):
	seconds = timestamp//1000
	milliseconds = timestamp - seconds*1000
	seconds += 2208988800
	bytearrData[offset] = (seconds >> 24) & 0xFF
	bytearrData[offset + 1] = (seconds >> 16) & 0xFF
	bytearrData[offset + 2] = (seconds >> 8) & 0xFF
	bytearrData[offset + 3] = (seconds >> 0) & 0xFF
	fraction = milliseconds * 4294967296 // 1000
	bytearrData[offset + 4] = (fraction >> 24) & 0xFF
	bytearrData[offset + 5] = (fraction >> 16) & 0xFF
	bytearrData[offset + 6] = (fraction >> 8) & 0xFF
	bytearrData[offset + 7] = (fraction >> 0) & 0xFF
	
# 读NTP时间戳
def ReadNTPTimestamp(byteData, offset):
	seconds = Read(byteData, offset)
	fraction = Read(byteData, offset + 4)
	return (seconds-2208988800)*1000 + fraction*1000//4294967296
	
	
		
# 读取时间戳中的数据
def Read(byteData, offset):
	b0 = byteData[offset]
	b1 = byteData[offset + 1]
	b2 = byteData[offset + 2]
	b3 = byteData[offset + 3]
	return (b0 << 24) + (b1 << 16) + (b2 << 8) + b3	
		
	
		
if __name__ == '__main__':
	try:
		threadPTP = threading.Thread(target=FuncPTP)
		threadPTP.start()
		#threadPTP.join()
		
		FuncNTP()
		
		#while True:
		#	pass
		
	except KeyboardInterrupt:	#按下ctrl+C时需将socket关闭
		interruptFlag = True
		socketNTP.close()
		socketPTPEvent.close()
		socketPTPGeneral.close()
		print('\nAll socket are closed.')
		
		
