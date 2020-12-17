import time as tm
import serial.tools.list_ports as ser_list
import serial as ser
import requests as rqst


# 调试性内容打印（防止有不合法打印）
def Debug_Print(output_string):
  try:
    print(output_string)
  except UnicodeEncodeError:
    print(repr(output_string)[1:-1])


# 查看短信是否是Unicode编码
def Data_Is_Unicode(sms_text_str):
  compare_str = "0123456789ABCDEF"
  for i in range(0, len(sms_text_str)):
    result = compare_str.find(sms_text_str[i], 0, len(compare_str))
    if result == -1:
      return False
  return True


# 找字符
def Find_Sub_String(substr, str, i):
  count = 0
  while i > 0:
    index = str.find(substr)
    if index == -1:
      return -1
    else:
      str = str[index + 1:]                                       # 第一次出现的位置截止后的字符串
      i -= 1
      count = count + index + 1                                   # 字符串位置数累加
  return count - 1


# 设备搜索
def Device_Connect():
  device_status = False
  try:
    uart = ser.Serial('/dev/ttyUSB0', 115200, timeout=600)
    uartIsOpen = uart.isOpen()                                    # Judge wheather the serial port is open
    if uartIsOpen == False:
      print("串口被占用")
    else:
      uart.write("AT\r\n".encode())                               # Send AT test instruction
      tm.sleep(0.01)                                              # Waitting for about 10ms
      uart_rx_len = uart.in_waiting                               # Read the buffer in recived buffer
      uart_rx_str = str(uart.read(uart_rx_len))
      if uart_rx_str.find("OK") != -1:                            # If the device respose character "OK"
        device_status = True
  except:
    uart = -1
  return device_status, uart


# 解析短信
def SMS_Parsing(sms_info_str):
  # 解析电话号码字符串
  phone_number_pos_start = Find_Sub_String("\"", sms_info_str, 3) + 1
  phone_number_pos_end = Find_Sub_String("\"", sms_info_str, 4)
  phone_number_str = sms_info_str[phone_number_pos_start:phone_number_pos_end]
  # 解析时间
  sms_time_index_start = Find_Sub_String("\"", sms_info_str, 7) + 1
  sms_time_index_end = Find_Sub_String("\"", sms_info_str, 8) - 3
  sms_time_str = sms_info_str[sms_time_index_start:sms_time_index_end]
  sms_time_str = sms_time_str.replace(',', ' ')
  # 解析短信内容
  sms_text_index_start = Find_Sub_String("\\r\\n", sms_info_str, 1) + 4
  sms_text_index_end = Find_Sub_String("\\r\\n", sms_info_str, 2) - 1
  sms_text_str = sms_info_str[sms_text_index_start:sms_text_index_end]
  result = Data_Is_Unicode(sms_text_str)
  if result == True:
    sms_text_str_unicode = ""
    for i in range(0, int(len(sms_text_str) / 4)):
      sms_text_str_unicode = sms_text_str_unicode + '\\u' + sms_text_str[i * 4:i * 4 + 4]
    sms_text_str_utf8 = sms_text_str_unicode.encode('utf-8').decode('unicode_escape')
    sms_text_str = sms_text_str_utf8
  return phone_number_str, sms_time_str, sms_text_str


# 读取最新短信
def SMS_Read_New(uart):
  sms_text_str = SMS_Read_Text(uart)
  sms_index = SMS_Get_Index(sms_text_str)
  if sms_index != -1:
    sms_info_str = SMS_Get_Whole_One(sms_text_str, sms_index)                                             # 截取整调信息
    phone_number_str, sms_time_str, sms_text_str = SMS_Parsing(sms_info_str)                              # 解析短信
  return phone_number_str, sms_time_str, sms_text_str


# 读取上一条信息
def SMS_Read_Last(uart, msm_index_now):
  sms_text_str = SMS_Read_Text(uart)
  sms_index = SMS_Get_Index(sms_text_str)
  if sms_index != -1:
    if msm_index_now > 1:
      msm_index_now -= 1
    else:
      msm_index_now = sms_index
    sms_info_str = SMS_Get_Whole_One(sms_text_str, msm_index_now)
    SMS_Parsing(sms_info_str)
  return msm_index_now


# 读取下一条信息
def SMS_Read_Next(uart, sms_index_now):
  sms_text_str = SMS_Read_Text(uart)
  sms_index = SMS_Get_Index(sms_text_str)
  if sms_index != -1:
    if sms_index_now < sms_index:
      sms_index_now += 1
    else:
      sms_index_now = 1
    sms_info_str = SMS_Get_Whole_One(sms_text_str, sms_index_now)
    SMS_Parsing(sms_info_str)
  return sms_index_now


# 删除所有短信
def SMS_Delect_All(uart):
  uart.write("AT+CMGD=1,4\r\n".encode())
  # Waitting for about 100ms
  tm.sleep(1)
  # Read the buffer in recived buffer
  Uart_rx_len = uart.in_waiting
  Uart_rx_str = str(uart.read(Uart_rx_len))
  # If the device respose character "OK"
  if Uart_rx_str.find('OK'):
    return True
  else:
    return False


# 读取信息
def SMS_Read_Text(uart):
  uart.write("AT+CMGF=1\r\n".encode())
  # Waitting for about 100ms
  tm.sleep(0.1)
  # Read the buffer in recived buffer
  Uart_rx_len = uart.in_waiting
  Uart_rx_str = str(uart.read(Uart_rx_len))
  if Uart_rx_str.find('OK') == -1:
    return ""
  uart.write("AT+CMGL=\"ALL\",0\r\n".encode())                # Read all sms
  Uart_rx_len = 0
  i = 0
  while i < 200:
    # Waitting for about 1s
    tm.sleep(0.1)
    if Uart_rx_len != uart.in_waiting:                        # Read the buffer in recived buffer
      Uart_rx_len = uart.in_waiting
    else:
      break
    i += 1
  Uart_rx_str = str(uart.read(Uart_rx_len))
  return Uart_rx_str


# 获取信息条数
def SMS_Get_Index(sms_str):
  sms_index_pos = sms_str.rfind("+CMGL: ", 0, len(sms_str))
  if sms_index_pos != -1:
    sms_index = int(sms_str[sms_index_pos + 7:sms_index_pos + 8])
  else:
    sms_index = -1
  return sms_index


# 获取一条信息
def SMS_Get_Whole_One(sms_str, sms_index):
  sms_one_start = Find_Sub_String("+CMGL: ", sms_str, sms_index)
  sms_one_str = sms_str[sms_one_start: len(sms_str)]
  sms_one_end = Find_Sub_String("\\r\\n", sms_one_str, 3)-2
  sms_one_str = sms_one_str[0: sms_one_end]
  return sms_one_str

# 短信更新
def SMS_Update(uart):
  uart_rx_len = uart.in_waiting                                 # Read the buffer in recived buffer
  if uart_rx_len == 0:
    sms_new = False
    return sms_new 
  uart_rx_str = str(uart.read(uart_rx_len))
  sms_index = uart_rx_str.rfind("+CMTI: \"SM\"", 0, len(uart_rx_str))
  if sms_index != -1:
    sms_new = True
    phone_number_str, sms_time_str, sms_text_str = SMS_Read_New(uart)
    sms_titile = phone_number_str
    sms_content = sms_time_str + "\r\n" + sms_text_str
    rqst.get("https://sc.ftqq.com/SCKEY.send?text={}&desp={}".format(sms_titile, sms_content))
    Debug_Print(phone_number_str)
    Debug_Print(sms_time_str)
    Debug_Print(sms_text_str)
    SMS_Delect_All(uart)
    return sms_new
  else:
    sms_new = False
    return sms_new 


if __name__ == '__main__':
  device_status = False
  while True:
    if device_status == False:
      device_status, uart = Device_Connect()
      print("设备状态：", device_status)
      tm.sleep(2)
    else:
      sms_new = SMS_Update(uart)
      print("新信息状态：", (sms_new))
      tm.sleep(5)

