import sys
#import math
import serial
import time
#import pdb
import select
import struct
import termstatus

def find_prologix():
    """
    Searches the ports for prologix devices to connect to.
    
    Return
    ======
    List of prologix ports available, list(serial.tools.list_ports_common.ListPortInfo)
    """
    from serial.tools import list_ports

    prologix = [p for p in list_ports.comports() if 'prologix' in p.description.lower()]

    if len(prologix) == 0: raise Exception("Can't find a Prologix")
    
    return prologix


class usbGPIB:
    def __init__(self, device, gpibAddr, baud=9600, timeout=0.5, 
                 eot=b'\004', debug=0, auto=False, log=False, tSleep=0.1):

        #End of Transmission character
        self.eot = eot
        # EOT character number in the ASCII table
        self.eotNum   = struct.unpack('B',eot)[0]
        self.debug    = debug
        self.auto     = auto
        self.tSleep   = tSleep
        self.log      = log
        self.gpibAddr = gpibAddr
        self.device   = device

        #Connect to the GPIB-USB converter
        self.ser = serial.Serial(device, baud, timeout=timeout)

        self.refresh()
        
    def refresh(self):
        """
        Sets up the GPIB connection
        """
        self.command("++addr "+str(self.gpibAddr)+"\n", sleep=0.1)
        self.command("++eos 3\n", sleep=0.1)
        self.command("++mode 1\n", sleep=0.1)
        
        if self.auto:
            self.command("++auto 1\n", sleep=0.1)
        else:
            self.command("++auto 0\n", sleep=0.1)
            
        self.command("++ifc\n",0.1)
        self.command("++read_tmo_ms 3000\n",0.1)
        self.command("++eot_char "+str(self.eotNum)+"\n",0.1)
        self.command("++eot_enable 1\n",0.1)
        
    def getData(self, buf, sleep=None):
        if sleep is None: sleep = self.tSleep + 0.1

        data=b""
        dlen=0
        if self.debug == True:
            progressInfo = termstatus.statusTxt("0 bytes received")
            
        while 1: # Repeat reading data until eot is found
            while 1:  # Read some data
                readSock, writeSock, errSock = select.select([self.ser],[],[],3)
                if len(readSock) == 1:
                    data1 = readSock[0].read(buf)
                    if self.debug == True:
                        dlen=dlen+len(data1)
                        progressInfo.update(str(dlen)+' bytes received')
                    break
                
            if data1.endswith(self.eot): #if eot is found at the end
                data = data + data1[:-1] #remove eot
                break
            else:
                data = data + data1
                time.sleep(sleep)

        if self.debug == True:
            progressInfo.end()
        return data
            
    def query(self, string, buf=100, sleep=None):
        """Send a query to the device and return the result."""
        if sleep is None: sleep=self.tSleep
        if self.log: print(sys.stderr, "?? %s" % string)
        
        cmd = string.encode() + b'\n'
        
        self.ser.write(cmd)
        
        if not self.auto:
            self.ser.write("++read eoi\n".encode()) #Change to listening mode
            
        self.ser.flush()
        time.sleep(sleep)
            
        ret = self.getData(buf)
        
        if self.log: print(sys.stderr, "== %s" % ret.strip())
            
        return ret

    def srq(self):
        """Poll the device's SRQ"""
        self.command("++srq")
        
        while True:  # Read some data
            readSock, writeSock, errSock = select.select([self.ser],[],[],3)
            if len(readSock) == 1:
                data = readSock[0].read(100)
                break

        return data[:-2]
    
    def command(self, string, sleep=None):
        """Send a command to the device."""
        if sleep is None: sleep = self.tSleep
        if self.log: print(sys.stderr, ">> %s" % string)
        
        cmd = string.encode() + b'\n'
        self.ser.write(cmd)
        self.ser.flush()
        time.sleep(sleep)

    def spoll(self):
        """Perform a serial polling and return the result."""
        self.command("++spoll")
        while 1:  # Read some data
            readSock, writeSock, errSock = select.select([self.ser],[],[],3)
            if len(readSock) == 1:
                data = readSock[0].read(100)
                break

        return data[:-2]
    
    def close(self):
        self.ser.close()
        
    def setDebugMode(self, debugFlag):
        if debugFlag:
            self.debug=1
        else:
            self.debug=0