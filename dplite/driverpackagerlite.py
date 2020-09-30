"""
Copyright 2019 Control4 Corporation.  All Rights Reserved.

A slimmed-down version of driverpackager.

This will not work with DriverEditor.  Only run it from a command prompt or a batch file.

This will not work with c4i files.
This requires that a .c4proj file is present.

This assumes that the main xml file is named driver.xml.
This assumes that the root Lua file is driver.lua.
This assumes that the documentation and icon files are in a www directory.


This will decide whether to squish the code according to the 'squishLua' attribute in the .c4proj file.
If the .c4proj file says to squish, but you would rather keep the directory structure visible, the -nsq option will force no squishing.

If the driver is designated to be encrypted, but not squished, then only driver.lua will be encrypted.

If the driver is designated to be encyrpted and squished, all the files will be pulled in to one file which will be encrypted.

If the driver is to be squished, this will call createsquishy.

"""

#!/usr/bin/python

import argparse
import sys
import os
import datetime
import xml.etree.ElementTree as ElementTree

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

import zipfile
import shutil
import subprocess
import tempfile
import codecs
import csv
import glob
import encrypt_c4z
import createsquishy as csq


class DriverPackagerLite(object):
    def __init__(self, args):
        self.verbose = args.verbose
        self.srcdir = args.srcdir
        self.dstdir = args.dstdir
        self.manifest = args.manifest
        self.doEncrypt = False
        self.doSquish = False

        if hasattr(args, 'allowexecute'):
            self.allowExecute = args.allowexecute
        else:
            self.allowExecute = False

        if hasattr(args, 'nosquish'):
            self.blockSquish = args.nosquish
        else:
            self.blockSquish = False

        if not os.path.isdir(self.dstdir):
            os.makedirs(self.dstdir)

    def Squish(self, root):
        self.Log("Squishing Lua source...")
        oldPath = os.environ['PATH']
        myenv = os.environ.copy()
        cwd = os.getcwd()
        print ('Saved Directory: %s' % cwd)

        os.chdir(root)
        print ('Current Directory: %s' % os.getcwd())

        cmdLine = ['luajit']

        # When running as an exe
        if getattr(sys, 'frozen', False):
            cmdLine.append(os.path.join(os.path.dirname(
                os.path.realpath(sys.executable)), "squish"))
            os.environ['PATH'] = os.path.dirname(
                os.path.realpath(sys.executable)) + ";" + oldPath
        else:
            cmdLine.append(os.path.join(os.path.dirname(
                os.path.realpath(__file__)), "squish"))
            os.environ['PATH'] = os.path.dirname(os.path.realpath(
                os.path.realpath(__file__))) + os.pathsep + oldPath

        # cmdLine.append('-q')
        cmdLine.append('--no-minify')

        cmdLine.append(root)

        try:
            print ('Root Directory: %s' % root)
            print ('CommandLine: %s' % ' '.join(cmdLine))
            subprocess.check_call(cmdLine, stderr=subprocess.STDOUT)
        except OSError as ex:
            raise Exception(
                "DriverPackagerLite: Error squishing lua %s" % (ex))
        except subprocess.CalledProcessError as ex:
            raise Exception(
                "DriverPackagerLite: Lua squish failed: %s while processing %s" % (ex, root))
        finally:
            pass
            os.environ["PATH"] = oldPath
            os.chdir(cwd)

    # create a c4z file with all the Lua files pulled into a single file

    def createSquishedC4z(self, c4z, dir, squishedFileName, encryptIt):
        csq.createsq(self.manifest)
        self.Squish(dir)

        try:
            with zipfile.ZipFile(c4z, 'w', compression=zipfile.ZIP_DEFLATED) as zip:
                # add in driver.xml
                zip.write("driver.xml")

                # add in all the stuff in the www directory and its sub-directories
                self.compressDirsLists(
                    ".", [{'c4zDir': "www", 'recurse': "true", 'name': "www"}], zip)

                if encryptIt:
                    # encrypt the squished file and then include it.
                    self.Log("Encrypting %s..." % (squishedFileName))
                    encrypt_c4z.encrypt(
                        squishedFileName, "driver.lua.encrypted")

                    zip.write("driver.lua.encrypted")
                else:
                    # rename the squished file to Driver.lua and include it
                    if os.path.exists(os.path.join(dir, "driver.lua")):
                        os.remove(os.path.join(dir, "driver.lua"))

                    shutil.copyfile(squishedFileName,
                                    os.path.join(dir, "driver.lua"))
                    zip.write("driver.lua")

        except zipfile.BadZipfile as ex:
            if os.path.exists(c4z):
                os.remove(c4z)
            self.Log("Error building %s  ...exception: %s" % (c4z, ex.message))
            return False
        except OSError as ex:
            self.Log("Error building %s  ...exception: %s" %
                     (c4z, ex.strerror))
            return False

        return True

    # create a c4z file with the internal directory structure

    def createC4z(self, c4z, srcDir, dirsList, filesList, encryptIt):
        try:
            with zipfile.ZipFile(c4z, 'w', compression=zipfile.ZIP_DEFLATED) as zip:
                # add in directories
                self.compressDirsLists(srcDir, dirsList, zip)

                # not squished, but have the encryption flag set.  Encrypt the root file.
                if encryptIt:
                    encrypt_c4z.encrypt("driver.lua", "driver.lua.encrypted")

                    for curFileInfo in filesList:
                        if curFileInfo['name'] == "driver.lua":
                            curFileInfo['name'] = "driver.lua.encrypted"
                            break

                # add in files
                self.compressFileList(".", srcDir, filesList, zip)

        except zipfile.BadZipfile as ex:
            if os.path.exists(c4z):
                os.remove(c4z)
            print ("Error building %s  ...exception: %s" % c4z, ex.message)
            return False
        except OSError as ex:
            print ("Error building %s  ...exception: %s" % c4z, ex.strerror)
            return False

        return True

    # a directory and its sub-directories into the zip file

    def compressDirsLists(self, dirIn, dirsIn, zip):
        # Add directories
        for dir in dirsIn:
            dirPath = os.path.join(dirIn, dir["name"])
            dirPath = os.path.normpath(dirPath)
            for root, dirs, files in os.walk(dirPath):
                root = os.path.normpath(root)
                # Ignore hidden files and directories
                files = [f for f in files if not f[0] == '.']
                dirs[:] = [d for d in dirs if not d[0] == '.']

                # get c4zDir for this directory
                dirName = os.path.normpath(dir["name"])
                indexRelPath = dirName.rfind("..")
                if indexRelPath >= 0:
                    dirName = dirName[indexRelPath+2:]
                indexRoot = root.rfind(dirName) + len(dirName)
                c4zDir = dir["c4zDir"]
                if len(c4zDir) == 0:
                    c4zDir = dir["name"]
                rootLen = len(root)
                if indexRoot < rootLen:
                    c4zDir = c4zDir + root[indexRoot:]

                # Replace file entries with structure value entries
                for i, f in enumerate(files):
                    del files[i]
                    files.insert(i, {'c4zDir': c4zDir, 'name': f})

                self.compressFileList(dirIn, root, files, zip)
                if dir["recurse"] == str('false').lower():
                    break

        return True

    # add the list of files into the zip file
    def compressFileList(self, dir, root, files, zip):
        tRoot = root = os.path.normpath(root)
        for file in files:
            tRoot, dName = os.path.split(root)

            filePath = os.path.join(
                file["c4zDir"], os.path.basename(file["name"]))
            arcPath = os.path.join(".", filePath)
            path, fName = os.path.split(file["name"])

            newPath = os.path.join(root, file["name"])
            sourcepath = os.path.normpath(newPath)
            zip.write(sourcepath, arcname=arcPath)

        return True

    def GetSquishyOutputFile(self, srcDir):
        lines = []
        outputFile = "driver.lua.squished"      # default value
        if os.path.isfile(srcDir + os.path.sep + "squishy"):
            with open(srcDir + os.path.sep + "squishy") as squishyFile:
                squishyContent = squishyFile.readlines()
            squishyFile.close()

            for line in squishyContent:
                if line.startswith("Output") and line is not None:
                    lines.append(line.split(' '))

            for s in lines:
                path = s[1].replace('Output "', '').replace(
                    '"', '').replace("\n", '')
                outputFile = path

        return str(outputFile).rstrip('\r')

    def GetStartLuaFilename(self, filename):
        c4zStartFile = None
        try:
            xmlTree = ElementTree.parse(filename)
            xmlRoot = xmlTree.getroot()
        except ElementTree.ParseError as ex:
            raise Exception(
                "DriverPackagerLite: Invalid XML (%s): %s" % (filename, ex))
        else:
            script = xmlRoot.findall('./config/script')
            for s in script:
                if self.doSquish:
                    c4zStartFile = self.GetSquishyOutputFile(self.srcdir)
                else:
                    c4zStartFile = s.attrib.get('file')

        return c4zStartFile

    def CleanupTmpFile(self, root):
        try:
            if os.path.exists(os.path.join(root, "driver.lua.tmp")):
                shutil.copyfile(os.path.join(root, "driver.lua.tmp"),
                                os.path.join(root, "driver.lua"))
                os.remove(os.path.join(root, "driver.lua.tmp"))
        except Exception as e:
            self.Log("Unable to remove driver.lua.tmp file or file does not exist")

    def ParseXml(self, xmlRoot, root, count, errCount):
        c4zName = ''
        c4zDriverXmlFound = False
        c4zStartFile = ''
        c4zDirs = []
        c4zFiles = []

        if xmlRoot.tag != 'Driver':
            raise Exception(
                "DriverPackagerLite: Invalid XML: Missing tag 'Driver'")

        driverType = xmlRoot.attrib.get('type')
        if driverType == None:
            raise Exception(
                "DriverPackagerLite: Invalid XML: Missing tag 'type'")

        driverName = xmlRoot.attrib.get('name')
        if driverName == None:
            raise Exception(
                "DriverPackagerLite: Invalid XML: Missing tag 'name'")

        squishFlag = xmlRoot.attrib.get('squishLua')
        if((squishFlag != None) and (not self.blockSquish)):
            self.doSquish = (squishFlag.lower() == 'true')

        c4zName = '.'.join((driverName, driverType))

        shutil.copyfile(os.path.join(root, "driver.lua"),
                        os.path.join(root, "driver.lua.tmp"))

        prepackageCmds = xmlRoot.find('PrepackageCommands')
        if prepackageCmds != None:
            for prepackageCmd in prepackageCmds:
                print ("%s %s" % (prepackageCmd.tag, prepackageCmd.text))
                if prepackageCmd.tag != 'PrepackageCommand':
                    self.Log("Invalid XML: Found tag '%s', should be 'PrepackageCommand'" % (
                        prepackageCmd.tag))
                    continue

                # execute the command
                osCommand = prepackageCmd.text.replace("\\", os.path.sep)
                osCommand = osCommand.replace("/", os.path.sep)
                if (os.system(osCommand) != 0):
                    print ("Failed to execute prepackage command.")

        items = xmlRoot.find('Items')
        if items == None:
            raise Exception(
                "DriverPackagerLite: Invalid XML: Missing tag 'Items'")

        if self.allowExecute:
            # Add C4:AllowExecute(true) to file
            print ("C4:AllowExecute(true) being added to file")
            with open(os.path.join(root, "driver.lua"), "a") as myfile:
                myfile.write("\nC4:AllowExecute(true)\n")
                myfile.write("\ngIsDevelopmentVersionOfDriver = true\n")

        for item in items:
            if item.tag != 'Item':
                self.Log("Invalid XML: Found tag '%s', should be 'Item'" %
                         (item.tag))
                continue

            # Mandatory item attributes
            itemType = item.attrib.get('type')
            if itemType == None:
                self.CleanupTmpFile(root)
                raise Exception(
                    "DriverPackagerLite: Invalid XML: Missing tag 'Item' subtag 'type'")

            itemName = item.attrib.get('name')
            if itemName == None:
                self.CleanupTmpFile(root)
                raise Exception(
                    "DriverPackagerLite: Invalid XML: Missing tag 'Item' subtag 'name'")

            # If optional item attribute 'exclude' is True, skip it
            exclude = True if item.attrib.get(
                'exclude') == str('true').lower() else False
            if exclude:
                continue

            if itemType == 'dir':
                # Verify directory Item exists
                if not os.path.exists(os.path.join(root, itemName)):
                    self.CleanupTmpFile(root)
                    raise Exception(
                        "DriverPackagerLite: Error, manifest 'dir' Item '%s' does not exist." % (itemName))

                recurse = True if item.attrib.get(
                    'recurse') == str('true').lower() else False
                c4zDir = item.attrib.get('c4zDir') if item.attrib.get(
                    'c4zDir') != None else ''
                c4zDirs.append(
                    {'c4zDir': c4zDir, 'recurse': recurse, 'name': itemName})

            elif itemType == 'file':
                if c4zStartFile:
                    fn, ext = os.path.splitext(itemName)
                    if ext == '.encrypted':
                        itemName = fn

                # Verify file Item exists
                if not os.path.exists(os.path.join(root, itemName)):
                    self.CleanupTmpFile(root)
                    raise Exception(
                        "DriverPackagerLite: Error, manifest 'file' Item '%s' does not exist in '%s'." % (itemName, root))

                # Get the script section from driver.xml
                if itemName == 'driver.xml':
                    c4zDriverXmlFound = True
                    c4zStartFile = self.GetStartLuaFilename(
                        os.path.join(root, itemName))

                    # Read driver.xml  We need to check for the encryption flag.
                    xmlTree = ElementTree.parse(os.path.join(root, itemName))
                    xmlRootDriver = xmlTree.getroot()

                    script = xmlRootDriver.findall('./config/script')
                    for s in script:
                        c4zScriptEncryption = s.attrib.get('encryption')
                        if c4zScriptEncryption == '2':
                            self.doEncrypt = True

                c4zDir = item.attrib.get('c4zDir') if item.attrib.get(
                    'c4zDir') != None else ''
                c4zFiles.append({'c4zDir': c4zDir, 'name': itemName})

        if not c4zDriverXmlFound:
            raise Exception(
                "DriverPackagerLite: Error, manifest 'file' Item 'driver.xml' was not found.")

        if self.doSquish:
            self.createSquishedC4z(os.path.join(
                self.dstdir, c4zName), root, c4zStartFile, self.doEncrypt)
        else:
            self.createC4z(os.path.join(self.dstdir, c4zName),
                           root, c4zDirs, c4zFiles, self.doEncrypt)

        self.CleanupTmpFile(root)

        postpackageCmds = xmlRoot.find('PostpackageCommands')
        if postpackageCmds != None:
            for postpackageCmd in postpackageCmds:
                print ("%s %s" % postpackageCmd.tag, postpackageCmd.text)
                if postpackageCmd.tag != 'PostpackageCommand':
                    self.Log(
                        "Invalid XML: Found tag '%s', should be 'PostpackageCommand'" % (item.tag))
                    continue

                # execute the command
                osCommand = postpackageCmd.text.replace("\\", os.path.sep)
                osCommand = osCommand.replace("/", os.path.sep)
                if (os.system(osCommand.text) != 0):
                    print ("Failed to execute postpackage command.")

        return True

    def CreateFromManifest(self, manifestPath):
        retcode = 0
        try:
            xmlTree = ElementTree.parse(manifestPath)
            xmlRoot = xmlTree.getroot()
        except IOError as ex:
            self.Log(ex)
            retcode = ex.errno
        except ElementTree.ParseError as ex:
            self.Log("DriverPackagerLite: Invalid XML (%s): %s" %
                     (manifestPath, ex))
            retcode = ex.code
        else:
            try:
                self.ParseXml(xmlRoot, self.srcdir, 0, 0)
            except Exception as ex:
                self.Log(ex)
                retcode = 255

        return retcode

    def DriverPackagerLite(self):
        retcode = 0
        if self.manifest != None:
            self.Log("Building driver from manifest %s..." % (self.manifest))
            retcode = self.CreateFromManifest(
                os.path.join(self.srcdir, self.manifest))
        else:
            self.Log("No manifest file")

        return retcode

    def Log(self, line):
        if self.verbose:
            print("{}: {}".format(
                datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S"), line))
            sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose.")
    parser.add_argument("srcdir",
                        help="Directory where c4z source files are located.")
    parser.add_argument("dstdir",
                        help="Directory where c4z files are placed.")
    parser.add_argument("manifest",
                        help="Filename of manifest xml file.",
                        nargs='?')
    parser.add_argument("-ae", "--allowexecute", action="store_true",
                        help="[optional] Allow Execute in Lua Command window.")
    parser.add_argument("-nsq", "--nosquish", action="store_true",
                        help="[optional] Block squishing.")
    args = parser.parse_args()

    return DriverPackagerLite(args)


if __name__ == "__main__":
    dp = main()
    sys.exit(dp.DriverPackagerLite())
