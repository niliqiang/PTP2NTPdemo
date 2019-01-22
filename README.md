# PTP2NTPdemo
A PTP to NTP demo on Linux  
  
  
**使用方法：**  

（1）作为 PTP 主钟的 PC 机上运行 PTPD 程序，使用单播模式，如：~$ sudo ptpd -u 10.28.194.34 -C -i ens33 -M    

（2）作为网关的 PC 机上运行此程序，如：~$ sudo python3 PTP2NTPdemo.py    

（3）作为用时终端的设备运行 NTP 客户端的程序，服务器地址输入网关的IP地址（如：10.28.194.34）    
