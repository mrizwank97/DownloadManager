import os
import time
import argparse
import datetime
import threading
import math
from socket import *
from urlparse import urlparse

parser = argparse.ArgumentParser(description="Downloading file Through HTTP Requests")
parser.add_argument('-n','--numr',type=int,required=True,metavar="",help="Total number of simultaneous connections")
parser.add_argument('-i','--time',type=float,required=True,metavar="",help="Time interval in seconds between metric reporting")
parser.add_argument('-c','--type',required=True,metavar="",help="Type of connection: UDP or TCP")
parser.add_argument('-f','--dest',required=True,metavar="",help="Address pointing to the file location on the web")
parser.add_argument('-o','--loc',required=True,metavar="",help="Address pointing to the location where the file is downloaded")
parser.add_argument('-r','--resume',required=False,metavar="",help="Whether to resume the existing download in progress")
args = parser.parse_args()

downloaded = []
prevDownloaded = []
assignedSize = []
startingStatus = ""
endingStatus = ""
multipleStatus = ""
allowDisplay = True
UPDATE_TIME = args.time
fileSize = 0

#thread class for displaying the performance metric
class Displayer (threading.Thread):

   def __init__(self):
      threading.Thread.__init__(self)
   
   def run(self):
      while(allowDisplay):
           os.system('cls')
           print startingStatus
           print multipleStatus
           print "-------------------------------------------------------"
           down = 0
           count = 0
           Totalspeeds = 0
           totSiz = 0
           for i in range(0, len(downloaded)):
              #getting total size of files
              totSiz = totSiz + assignedSize[i]
              #getting downloaded size
              down = down + downloaded[i]
              speed = abs(((downloaded[i]-prevDownloaded[i])/UPDATE_TIME)/1000)
              Totalspeeds = Totalspeeds + speed
              count = count+1
              print "Connection ",(i+1),": ", downloaded[i]," / ",assignedSize[i],", download speed: ", speed,"KB/Sec"
              prevDownloaded[i] = downloaded[i]
   
           print "Total: ",down," / ",totSiz,", download speed: ", (Totalspeeds/count),"KB/Sec"
           print "-------------------------------------------------------"
           time.sleep(UPDATE_TIME)
           
#thread class for opening multiple connection & downloaddiing files
class myThread (threading.Thread):

   def __init__(self, sb, eb, pat, web, file,id):
      threading.Thread.__init__(self)
      self.startingByte = sb
      self.endingByte = eb
      self.path = pat
      self.thread_data = ""
      self.web = web
      self.file = file
      self.threadID = id
        
   def run(self):
      startingByte = self.startingByte
      endingByte = self.endingByte
      path = self.path
      web = self.web
      clientSocket = connection_establish(args.type,gethostbyname(web),80)
      web = self.web
      file = self.file

      if(args.loc == '.'):

         #opeing file from current directory
         if(args.resume == '1'):
            f = open(file, 'ab')

         #creating file in current directory
         else:
            f = open(file, 'wb')
            
      else:
         print args.resume

         #opeing file from user specified directory
         if(args.resume == '1'):
            f = open(args.loc+file, 'ab')

         #creating file in user specified directory
         else:
            f = open(args.loc+file, 'wb')

      #getting size of download file
      if(args.loc == '.'):
         startsFrom = startingByte+os.path.getsize(file)

      else:
         startsFrom = startingByte+os.path.getsize(args.loc+file)

      if(startsFrom >= endingByte):
         return

      mrequest = ('GET '+ path+ ' HTTP/1.1\r\nHost: {}\r\nRange: bytes='+str(startsFrom)+'-'+str(endingByte)+'\r\n\r\n').format(web)

      #checking for assigned file size of every thread
      if(args.loc == '.'):

         assignedSize[self.threadID] = (endingByte-(startingByte+os.path.getsize(file)) + 1)
      else:
         assignedSize[self.threadID] = (endingByte-(startingByte+os.path.getsize(args.loc+file)) + 1)

      #getting file from server
      clientSocket.send(mrequest)
      data = clientSocket.recv(2048)
      #trimming response header
      data = data.split("\r\n\r\n")[1]
      try:
         while(data):
          f.write(data)
          #storing the size of downloaded file
          downloaded[self.threadID] = downloaded[self.threadID]+len(data)
          data = clientSocket.recv(1024)
      except:
         print "Done"
      clientSocket.close()

def connection_establish(type,serverIP,serverPort):

    if(type.lower() == 'udp'):
        clientSocket = socket(AF_INET,SOCK_DGRAM)

    elif(type.lower() == 'tcp'):
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect((serverIP,serverPort))

    return clientSocket

if __name__ == "__main__":

    #parsing url contens
    url = urlparse(args.dest)
    file = os.path.basename(url.path)
    serverIP = gethostbyname(url.netloc)
    clientSocket = connection_establish(args.type,serverIP,80)
    sent_time = datetime.datetime.now()

    startingStatus = "Recieve Request sent to server at: "+str(sent_time)
    print startingStatus
    sent_time = time.time()
    #head request to check if server support multiple coonnections
    request1 = b'HEAD /'+url.path+' HTTP/1.1\r\nHost:'+url.netloc+' \r\n\r\n'
    #Udp is not supported
    if(args.type.lower() == 'udp'):
        clientSocket.sendto(request1, (serverIP,80))
        data, addr = clientSocket.recvfrom(1024)
        print data
        clientSocket.sendto(request, (serverIP,80))
        data, addr = clientSocket.recvfrom(1024)
        reply = data
        while(data):
            data = clientSocket.recv(1024)
            reply += data

    else:
        clientSocket.send(request1)
        data = clientSocket.recv(1024)
        supportsMulti = False
        data = data.split("\r\n")
        #getting content length from request header
        for part in data:
               if "Content-Length:" in part:
                  fileSize = int(part.split(" ")[1])
               if "Accept-Ranges:" in part:
                  if "bytes" in part.split(" ")[1]:
                     supportsMulti = True

        #checking if server supports multiple requested/ranges
        if(supportsMulti):
            multipleStatus = "Server supports range requests"
            nThreads = args.numr
            displ = Displayer()
            displ.start()
            dividedSize = int(math.ceil(fileSize/nThreads))
            mthreads = []
            downloaded = [0]*nThreads
            prevDownloaded = [0]*nThreads
            assignedSize = [0]*nThreads
            reply = ""

            #separating file sizes
            for i in range(0,nThreads-1):
                #sending separate byte ranges for every thread
                th = myThread(i*dividedSize, (i+1)*dividedSize-1,url.path,url.netloc, str(i)+file, i)
                th.start()
                time.sleep(0.5)
                mthreads.append(th)

            #sending remaing bytes in last thread
            th = myThread((nThreads-1)*dividedSize, fileSize-1,url.path,url.netloc, str(nThreads-1)+file,nThreads-1)
            th.start()
            time.sleep(0.5)
            mthreads.append(th)

            for i in range(0, nThreads):
                mthreads[i].join()
            allowDisplay = False

            if(args.loc == '.'):
               fout = open(file,'wb')

            else:
               fout = open(args.loc+file,'wb')

            for i in range(0,nThreads):
               #merging files of each thread
               if(args.loc == '.'):
                  f = open(str(i)+file,"rb")

               else:
                  f = open(args.loc+str(i)+file,"rb")
               fout.write(f.read())
               f.close()

               #removing file after merging
               if(args.loc == '.'):
                  os.remove(str(i)+file)

               else:
                  os.remove(args.loc+str(i)+file)
        else:
            #if server does not support multiple requests
            print "Server does'nt supports range requests"
            clientSocket.send(('GET '+ url.path+ ' HTTP/1.1\r\nHost: {}\r\n\r\n').format(url.netloc))
            f = open(file, 'wb')
            data = clientSocket.recv(2048)
            data = data.split("\r\n\r\n")[1]
            while(data):
              f.write(data)
              data = clientSocket.recv(1024)

    rcv_time = datetime.datetime.now()
    print "File Successfully Downloaded from server at: "+str(rcv_time)
    clientSocket.close()
