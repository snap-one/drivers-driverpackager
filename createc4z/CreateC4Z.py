"""
    File is: CreateC4Z.py
    Copyright 2021 Wirepath Home Systems LLC. All Rights Reserved.

"""

import argparse
import sys
import os
import datetime
import shutil
from distutils import dir_util
import zipfile
from M2Crypto import BIO, Rand, SMIME, X509

from xml.dom import minidom
import xml.etree.ElementTree as ET

PUBLIC_KEY = '''-----BEGIN CERTIFICATE-----
MIIEUTCCAzmgAwIBAgIJAK1MSC7OcXXEMA0GCSqGSIb3DQEBBQUAMIG+MQswCQYD
VQQGEwJVUzENMAsGA1UECAwEVXRhaDEPMA0GA1UEBwwGRHJhcGVyMR0wGwYDVQQK
DBRDb250cm9sNCBDb3Jwb3JhdGlvbjEiMCAGA1UECwwZRHJpdmVyV29ya3MgRW5j
cnlwdGlvbiBWMjEiMCAGA1UEAwwZRHJpdmVyV29ya3MgRW5jcnlwdGlvbiBWMjEo
MCYGCSqGSIb3DQEJARYZY2VydC1zdXBwb3J0QGNvbnRyb2w0LmNvbTAeFw0xMzA5
MTcxOTUwMTlaFw0zMzA5MTIxOTUwMTlaMIG+MQswCQYDVQQGEwJVUzENMAsGA1UE
CAwEVXRhaDEPMA0GA1UEBwwGRHJhcGVyMR0wGwYDVQQKDBRDb250cm9sNCBDb3Jw
b3JhdGlvbjEiMCAGA1UECwwZRHJpdmVyV29ya3MgRW5jcnlwdGlvbiBWMjEiMCAG
A1UEAwwZRHJpdmVyV29ya3MgRW5jcnlwdGlvbiBWMjEoMCYGCSqGSIb3DQEJARYZ
Y2VydC1zdXBwb3J0QGNvbnRyb2w0LmNvbTCCASIwDQYJKoZIhvcNAQEBBQADggEP
ADCCAQoCggEBANpapgg8oU3FIhzDYEVM14lPKVbsuqm/+9CJKYSPVPjEvdm17IMI
O4axqFDj1BH8qdbSwhPugC+j0q5O2jlfA19u5aL2vHpr04MSZF0OHWYN20g+pWXe
gaq3LQsjBLiQPQKewS5v5Ff4GydJD63rJz8pO18ztYlPYNrABOBcEM7MiVvzJK6e
NMTOOEZqf2FIjtXQhyclkzcBz7j/TC2jqvYa96DmfpYoPAajf+ypzxezSZ6G4GRa
6jlNtBg40QjHtHxWa3PsZ86PiLMnZ2z4SryMpcecm7Jj/iA9Hh76wLglv4TtjXxk
gtqkv7RzOHlmOeB4nH8lsqTyRBmnn39fDuMCAwEAAaNQME4wHQYDVR0OBBYEFHCV
PSWmatjY5ixd4azS6+GxDIpwMB8GA1UdIwQYMBaAFHCVPSWmatjY5ixd4azS6+Gx
DIpwMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQEFBQADggEBAHl58yYI7IMWkkxI
vu5kff/MKTSt4SXN365o3opc8FBuo/d3v2IKkIlo8BWbuCp4MwqV8L/0UYupFs49
RI5N0ETTapdg1uoVUd8NGHx7FgZ5MU9+caMEI8PoaRcFPdrxL1S7nOyl0ceFWwIz
1V2Hc9hZQEcv586El+/xXq/jd/oydN+j+knaL/dwvcK88TvQjl3AS974QuedvGIh
pq8tXfMiu1iPpc29tOMgfJzO0V6T92Fn5XbAY4u5p9Rvs/h8x7Ono++zRh66JOXQ
T++pYjmRUr+BSgZfoZzvs9mdMqtFpeWIx6nW4vXjDwAILVP3Bgh9MwrEzJtIQ/qy
Zwi18AY=
-----END CERTIFICATE-----'''


class CreateC4Z():
    def __init__(self, args):
        self.__ProjectFileName = args.proj
        self.__TargDriverName = ""
        self.__SrcDir = args.srcdir
        self.__DstDir = args.dstdir
        self.__Encrypt = args.encrypt
        self.__Develop = args.develop
        self.__LuaRefMap = {}
        

    def DoC4ZCreation(self):
        self.GetProjectInfo()
        self.TweakFiles()

        if(self.__Encrypt):
            self.CreateEncryptedC4Z()
        else:
            self.CreateC4Z()

        self.CleanupTempFiles()
        return(0)
        


    def GetProjectInfo(self):
        ProjFile = os.path.join(self.__SrcDir, self.__ProjectFileName + ".c4zproj")
        ProjTree = ET.parse(ProjFile)
        ProjRoot = ProjTree.getroot()
        self.__TargDriverName = ProjRoot.attrib['name'] + ".c4z"
        print ("TargName is: {}".format(self.__TargDriverName))
        ItemsElem = ProjRoot.find("Items")
        for CurItem in ItemsElem:
            if(CurItem.attrib['type'] == 'dir'):
                self.__LuaRefMap[CurItem.attrib['c4zDir']] = CurItem.attrib['name']


    def TweakFiles(self):
        if(self.__Develop):
            # Put AllowExecute and Development flag in driver.lua
            OrgLuaFile = os.path.join(self.__SrcDir, "driver.lua")
            TmpLuaFile = os.path.join(self.__SrcDir, "driver.lua.tmp")
            shutil.copyfile(OrgLuaFile, TmpLuaFile)
            with open(OrgLuaFile, "a") as DriverLuaFile:
                DriverLuaFile.write((
                                        "\n"
                                        "C4:AllowExecute(true)\n"
                                        "gIsDevelopmentVersionOfDriver = true\n"
                                        "\n"
                                   ))
                DriverLuaFile.close()

        if(self.__Encrypt):
            # shim the 'encryption = "2"' attribute into the script tag
            OrgXMLFile = os.path.join(self.__SrcDir, "driver.xml")
            TmpXMLFile = os.path.join(self.__SrcDir, "driver.xml.tmp")
            shutil.copyfile(OrgXMLFile, TmpXMLFile)
            DriverXMLTree = ET.parse(OrgXMLFile)
            DriverXMLRoot = DriverXMLTree.getroot()
            ScriptElem = DriverXMLRoot.find('config').find('script')
            ScriptElem.set("encryption", "2")
            AllXMLstr = minidom.parseString(ET.tostring(DriverXMLRoot)).toxml()
            with open(OrgXMLFile, "w") as DriverXMLFile:
                DriverXMLFile.write(AllXMLstr.split(">",1)[1])
                DriverXMLFile.close()



    def CreateC4Z(self):
        RequiredFileSet = ExtractAllRequired(self.__LuaRefMap)

        DriverC4ZName = os.path.join(self.__DstDir, self.__TargDriverName)
        try:
            with zipfile.ZipFile(DriverC4ZName, 'w', compression=zipfile.ZIP_DEFLATED) as zip:
                for CurFile in RequiredFileSet:
                    #print("CreateC4Z  fileName is: {}".format(CurFile))
                    zip.write(CurFile['SrcFile'], arcname=CurFile['DstFile'])

                self.AddCommonC4ZFiles(zip)

        except zipfile.BadZipfile as ex:
            if os.path.exists(DriverC4ZName):
                os.remove(DriverC4ZName)
            print("Error building {}  ...exception: {}".format(DriverC4ZName, ex.message))

        except OSError as ex:
            print ("Error building {}  ...exception: {}".format(DriverC4ZName, ex.strerror))


    def CreateEncryptedC4Z(self):
        def DoSquish():
            def AddSquishModule(ModInfo):
                BracketIt = (ModInfo['LuaRef'] != 'driver') # a bit of a kludge so that driver.lua doesn't get bracketed

                if BracketIt:
                    SqFile.write("package.preload['{}'] = (function (...)\n".format(ModInfo['LuaRef']))

                with open(ModInfo['SrcFile'], "r") as LuaFile:
                    SqFile.write(LuaFile.read())
        
                if BracketIt:
                    SqFile.write("\nend)\n")


            AllFilesInfo = ExtractAllRequired(self.__LuaRefMap)
        
            SqFile = open(SquishedFileName, "w+")
            for CurMod in AllFilesInfo:
                AddSquishModule(CurMod)

            SqFile.close()

        def EncryptSquishedFile():
            with open(SquishedFileName, 'rb') as InFile:
                str = InFile.read()
                buf = BIO.MemoryBuffer(str)
            
                smime = SMIME.SMIME()
                x509 = X509.load_cert_string(PUBLIC_KEY)
                x509_stack = X509.X509_Stack()
                x509_stack.push(x509)
                smime.set_x509_stack(x509_stack)
                smime.set_cipher(SMIME.Cipher('aes_256_cbc'))

                pkcs7 = smime.encrypt(buf, flags=SMIME.PKCS7_BINARY)
                outbuf = BIO.MemoryBuffer()
                pkcs7.write_der(outbuf)
            
                with open(EncryptedFileName, 'wb') as outfile:
                    outfile.write(outbuf.read())

        SquishedFileName = "driver.lua.squished"
        EncryptedFileName = "driver.lua.encrypted"

        DoSquish()
        EncryptSquishedFile()
        
        DriverC4ZName = os.path.join(self.__DstDir, self.__TargDriverName)
        try:
            with zipfile.ZipFile(DriverC4ZName, 'w', compression=zipfile.ZIP_DEFLATED) as zip:
                zip.write(EncryptedFileName)

                self.AddCommonC4ZFiles(zip)

        except zipfile.BadZipfile as ex:
            if os.path.exists(DriverC4ZName):
                os.remove(DriverC4ZName)
            print("Error building {}  ...exception: {}".format(DriverC4ZName, ex.message))

        except OSError as ex:
            print ("Error building {}  ...exception: {}".format(DriverC4ZName, ex.strerror))


    def AddCommonC4ZFiles(self, zip):
        zip.write("driver.xml")
    
        for root, dirs, files in os.walk("www"):
            root = os.path.normpath(root)
            
            # Ignore hidden files and directories
            files = [f for f in files if not f[0] == '.']
            dirs[:] = [d for d in dirs if not d[0] == '.']

            for fileName in files:
                zip.write(os.path.join(root, fileName))
    
    

    def CleanupTempFiles(self):
        # restore files that may have been tweaked
        if(os.path.exists(os.path.join(self.__SrcDir, "driver.lua.tmp"))):
            shutil.copyfile(os.path.join(self.__SrcDir, "driver.lua.tmp"), os.path.join(self.__SrcDir, "driver.lua"))
            os.remove(os.path.join(self.__SrcDir, "driver.lua.tmp"))

        if(os.path.exists(os.path.join(self.__SrcDir, "driver.xml.tmp"))):
            shutil.copyfile(os.path.join(self.__SrcDir, "driver.xml.tmp"), os.path.join(self.__SrcDir, "driver.xml"))
            os.remove(os.path.join(self.__SrcDir, "driver.xml.tmp"))


#=================================================================

def ExtractAllRequired(LuaRefFileMap):
    class LuaFile:
        def __init__(self, RefName, DirRefMap):
            self.__RefName = RefName
            self.__DstFileName = self.__RefName.replace('.', '/') + ".lua"
            if(RefName.find('.') >= 0):
                DirName, FileName = RefName.split('.')
                self.__SrcFileName = DirRefMap[DirName] + '/' + FileName + '.lua'
            else:
                self.__SrcFileName = RefName + '.lua'
                
            #print("Extract Ref: {}  Src: {}  Dst: {}".format(self.__RefName, self.__SrcFileName, self.__DstFileName))
            

        def TraverseRequiredFiles(self, MasterFileList, MasterFileSet, DirRefMap):
            if self.__DstFileName not in MasterFileSet:
                MasterFileSet.add(self.__DstFileName)
                LuaSourceFile = open(self.__SrcFileName, "r")
                FileContent = LuaSourceFile.readlines()

                for Curline in FileContent:
                    if(Curline[:7] == 'require'):       # only check at the beginning of the line so requires inside functions aren't snagged.
                        reqStr, subFileStr = Curline.split(' ', 1)
                        QuoteChar = subFileStr[:1]
                        CloseQuoteLoc = subFileStr[1:].find(QuoteChar) + 1
                        subFileStr = subFileStr[1:CloseQuoteLoc]

                        reqFile = LuaFile(subFileStr, DirRefMap)
                        reqFile.TraverseRequiredFiles(MasterFileList, MasterFileSet, DirRefMap)

                LuaSourceFile.close()
                MasterFileList.append({ 'LuaRef':self.__RefName, 'SrcFile': self.__SrcFileName, 'DstFile': self.__DstFileName})

    #---------------------

    AllFilesList = []
    AllFilesSet = set()     # use for quick duplicate check
    
    rootLua = LuaFile("driver", LuaRefFileMap)     # Start with driver.lua
    rootLua.TraverseRequiredFiles(AllFilesList, AllFilesSet, LuaRefFileMap)

    return AllFilesList

#=================================================================


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("proj",
                        help = "name of project file.",
                        nargs = '?')
    parser.add_argument("srcdir",
                        help = "Directory where c4z source files are located.")
    parser.add_argument("dstdir",
                        help = "Directory where c4z files are placed.")
    parser.add_argument("-e", "--encrypt", action="store_true",
                        help = "Encrypt the driver.")
    parser.add_argument("-d", "--develop", action="store_true",
                        help = "Development version of the driver.")

    args = parser.parse_args()
    return CreateC4Z(args)



if __name__ == '__main__':
    C4ZConjure = main()
    sys.exit(C4ZConjure.DoC4ZCreation())


