#!/usr/bin/env python3

"""
Copyright 2020 Wirepath Home Systems, LLC. All Rights Reserved.
"""

import argparse
import sys
import os
import datetime
from io import BytesIO
from lxml import etree

import zipfile
import shutil
import subprocess
import tempfile
import codecs
import csv
import glob

import build_c4z as c4z
global squishLua
global c4i


class DriverPackager(object):
    def __init__(self, args):
        self.verbose = args.verbose
        self.srcdir = args.srcdir
        self.dstdir = args.dstdir
        self.manifest = args.manifest
        self.unzip = args.unzip
        self.bytes_io = BytesIO()
        if hasattr(args, 'allowexecute'):
            self.allowExecute = args.allowexecute
        else:
            self.allowExecute = False
        if hasattr(args, 'update_modified'):
            self.update_modified = args.update_modified
        else:
            self.update_modified = False
        if hasattr(args, 'driver_version'):
            if args.driver_version:
                self.driver_version = args.driver_version[0]
            else:
                self.Log("Version argument not found, skipping version update.")
                self.driver_version = False
        else:
            self.driver_version = False

        if not os.path.isdir(self.dstdir):
            os.makedirs(self.dstdir)

    def Squish(self, root):
        self.Log("Squishing Lua source...")
        oldPath = os.environ['PATH']
        myenv = os.environ.copy()
        cwd = os.getcwd()
        print('Saved Directory: '+cwd)

        os.chdir(root)
        print('Current Directory: '+os.getcwd())

        cmdLine = ['luajit']

        # When running as an exe
        if getattr(sys, 'frozen', False):
            cmdLine.append(os.path.join(os.path.dirname(os.path.realpath(sys.executable)), "squish"))
            os.environ['PATH'] = os.path.dirname(os.path.realpath(sys.executable)) + ";" + oldPath
        else:
            cmdLine.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "squish"))
            os.environ['PATH'] = os.path.dirname(os.path.realpath(os.path.realpath(__file__))) + os.pathsep + oldPath

        if self.verbose:
            cmdLine.append('--vv')

        cmdLine.append(root)

        try:
            print('Root Directory: '+root)
            print('CommandLine: ')
            print(' '.join(cmdLine))
            subprocess.check_call(cmdLine, stderr=subprocess.STDOUT)
        except OSError as ex:
            raise Exception("DriverPackager: Error squishing lua %s" % (ex))
        except subprocess.CalledProcessError as ex:
            raise Exception(
                "DriverPackager: Lua squish failed: %s while processing %s" % (ex, root))
        finally:
            pass
            os.environ["PATH"] = oldPath
            os.chdir(cwd)

    def CreateFromManifest(self, manifestPath):
        retcode = 0
        try:
            xmlTree = etree.parse(manifestPath)
            xmlRoot = xmlTree.getroot()
        except IOError as ex:
            self.Log(ex)
            retcode = ex.errno
        except etree.ParseError as ex:
            self.Log("DriverPackager: Invalid XML (%s): %s" %
                     (manifestPath, ex))
            retcode = ex.code
        else:
            try:
                self.ParseXml(xmlRoot, self.srcdir, 0, 0)
            except Exception as ex:
                self.Log(ex)
                retcode = 255

        return retcode

    def GetEncryptFilename(self, filename):
        c4zScriptFile = None
        try:
            xmlTree = etree.parse(filename)
            xmlRoot = xmlTree.getroot()
        except etree.ParseError as ex:
            raise Exception(
                "DriverPackager: Invalid XML (%s): %s" % (filename, ex))
        else:
            script = xmlRoot.findall('./config/script')
            for s in script:
                c4zScriptEncryption = s.attrib.get('encryption')
                if c4zScriptEncryption == '2':
                    # Only use the newer encryption
                    if c4z.squishLua_:
                        c4zScriptFile = c4z.GetSquishyOutputFile(self.srcdir)
                    else:
                        c4zScriptFile = s.attrib.get('file')

        return c4zScriptFile

    def CleanupTmpFile(self, root):
        if self.allowExecute:
            try:
                if os.path.exists(os.path.join(root, "driver.lua.tmp")):
                    shutil.copyfile(os.path.join(
                        root, "driver.lua.tmp"), os.path.join(root, "driver.lua"))
                    os.remove(os.path.join(root, "driver.lua.tmp"))
            except Exception as ex:
                self.Log(
                    "Unable to remove driver.lua.tmp file or file does not exist")

    def ParseXml(self, xmlRoot, root, count, errCount):
        c4zName = ''
        c4zDriverXmlFound = False
        c4zScriptFile = ''
        c4zDirs = []
        c4zFiles = []

        if xmlRoot.tag != 'Driver':
            raise Exception(
                "DriverPackager: Invalid XML: Missing tag 'Driver'")

        driverType = xmlRoot.attrib.get('type')
        if driverType == None:
            raise Exception("DriverPackager: Invalid XML: Missing tag 'type'")

        driverName = xmlRoot.attrib.get('name')
        if driverName == None:
            raise Exception("DriverPackager: Invalid XML: Missing tag 'name'")

        # Optional tags
        squishLua = True if xmlRoot.attrib.get(
            'squishLua') == 'true' else False
        c4z.setSquishLua(squishLua)

        # If 'c4i' is detected in the manifest, set variable to true.
        c4i = True if xmlRoot.attrib.get('type') == 'c4i' else False
        if c4i:
            self.bytes_io = None
        c4z.setC4i(c4i)

        c4zName = '.'.join((driverName, driverType))

        prepackageCmds = xmlRoot.find('PrepackageCommands')
        if prepackageCmds != None:
            for prepackageCmd in prepackageCmds:
                print(prepackageCmd.tag, prepackageCmd.text)
                if prepackageCmd.tag != 'PrepackageCommand':
                    self.Log("Invalid XML: Found tag '%s', should be 'PrepackageCommand'" % (
                        prepackageCmd.tag))
                    continue

                # execute the command
                osCommand = prepackageCmd.text.replace("\\", os.path.sep)
                osCommand = osCommand.replace("/", os.path.sep)
                if (os.system(osCommand) != 0):
                    raise Exception("Failed to execute prepackage command.")

        items = xmlRoot.find('Items')
        if items == None:
            raise Exception("DriverPackager: Invalid XML: Missing tag 'Items'")

        if self.allowExecute:
            # Add C4:AllowExecute(true) to file
            print("C4:AllowExecute(true) being added to file")
            shutil.copyfile(os.path.join(root, "driver.lua"),
                            os.path.join(root, "driver.lua.tmp"))
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
                    "DriverPackager: Invalid XML: Missing tag 'Item' subtag 'type'")

            itemName = item.attrib.get('name')
            if itemType == None:
                self.CleanupTmpFile(root)
                raise Exception(
                    "DriverPackager: Invalid XML: Missing tag 'Item' subtag 'name'")

            # If optional item attribute 'exclude' is True, skip it
            exclude = True if item.attrib.get(
                'exclude') == str('true').lower() else False
            if exclude == True:
                continue

            if itemType == 'dir':
                # Verify directory Item exists
                if not os.path.exists(os.path.join(root, itemName)):
                    self.CleanupTmpFile(root)
                    raise Exception(
                        "DriverPackager: Error, manifest 'dir' Item '%s' does not exist." % (itemName))

                recurse = True if item.attrib.get(
                    'recurse') == str('true').lower() else False
                c4zDir = item.attrib.get('c4zDir') if item.attrib.get(
                    'c4zDir') != None else ''
                c4zDirs.append(
                    {'c4zDir': c4zDir, 'recurse': recurse, 'name': itemName})

            elif itemType == 'file':
                if c4zScriptFile:
                    fn, ext = os.path.splitext(itemName)
                    if ext == '.encrypted':
                        itemName = fn

                # Verify file Item exists
                if not os.path.exists(os.path.join(root, itemName)):
                    self.CleanupTmpFile(root)
                    raise Exception(
                        "DriverPackager: Error, manifest 'file' Item '%s' does not exist in '%s'." % (itemName, root))

                # Get the script section from driver.xml
                if itemName == 'driver.xml':
                    c4zDriverXmlFound = True

                    c4zScriptFile = self.GetEncryptFilename(
                        os.path.join(root, itemName))

                    # Read the driver.xml to determine if the 'textfile' attribute exists.
                    xmlTree = etree.parse(os.path.join(root, itemName))
                    xmlRootDriver = xmlTree.getroot()

                    documentation = xmlRootDriver.findall(
                        './config/documentation')

                    if len(documentation) < 1:
                        # Couldn't find the documentation attribute so there is nothing to do.  Moving on...
                        pass
                    else:
                        if 'textfile' in xmlRootDriver.find('./config/documentation').attrib:
                            textfile = xmlRootDriver.find(
                                './config/documentation').attrib['textfile']

                            if 'file' in xmlRootDriver.find('./config/documentation').attrib:
                                docFile = xmlRootDriver.find(
                                    './config/documentation').attrib['file']
                            else:
                                docFile = None

                            # If the 'textfile' attribute exists, create a backup of the driver.xml (driver.xml.bak) because modifications will need to be made.
                            shutil.copy(os.path.join(root, itemName),
                                        os.path.join(root, itemName + '.bak'))

                            # Read the contents of the filename referenced in the above 'textfile' attribute and write it to the inner-text of the <documentation> element.
                            try:
                                codecs.open(os.path.join(root, textfile), 'r')
                            except Exception as ex:
                                self.Log("Unable to find the file " + "'" + textfile + "'" +
                                         " referenced in the 'textfile' attribute of the '<documentation>' element in your driver.xml")
                            finally:
                                textfileContents = codecs.open(
                                    os.path.join(root, textfile), 'r')
                                data = textfileContents.readlines()
                                textfileContents.close()

                            # Delete the 'textfile' attribute from the '<documentation>' element.
                            document = etree.parse(
                                os.path.join(root, itemName))
                            parent = document.find('config')
                            child = etree.SubElement(parent, 'documentation')

                            # Remove the documentation element.  It will be recreated below.
                            xmlTree = etree.parse(
                                os.path.join(root, itemName))
                            xmlRootDriver = xmlTree.getroot()
                            docElement = xmlRootDriver.findall(
                                './config/documentation')
                            documentation = xmlRootDriver.findall(
                                './config/documentation')

                            # Remove the 'documentation' tag from the driver.
                            if documentation is None:
                                pass
                            else:
                                config = xmlRootDriver.find('config')
                                for doc in config.findall('documentation'):
                                    config.remove(doc)

                            xmlTree.write(os.path.join(root, itemName))

                            # Read the driver.xml again.
                            document = etree.parse(
                                os.path.join(root, itemName))
                            parent = document.find('config')
                            child = etree.SubElement(parent, 'documentation')

                            # Add the contents of the 'textfile' to the innertext of the '<documentation>' element in the driver.xml.
                            child.text = ''.join(data)

                            if driverType == "c4z":
                                if docFile is not None:
                                    child.set('file', docFile)

                            # Write the changes to the document.
                            document.write(os.path.join(
                                root, itemName), pretty_print=True)

                        else:
                            # Couldn't find the textfile attribute so there is nothing to do.  Carry on...
                            pass

                    # If the manifest and driver.xml agree, squish Lua source.
                    if squishLua:
                        self.Squish(root)

                    if c4i and not squishLua:
                        self.CleanupTmpFile(root)
                        raise Exception(
                            "You are attempting to build a driver of type 'c4i', but 'squishLua' is set to false in the project file/manifest.  This needs to be set to true.")

                c4zDir = item.attrib.get('c4zDir') if item.attrib.get(
                    'c4zDir') != None else ''
                if itemName == "driver.xml" and not c4i:
                    pass
                else:
                    c4zFiles.append({'c4zDir': c4zDir, 'name': itemName})

        if not c4zDriverXmlFound:
            raise Exception(
                "DriverPackager: Error, manifest 'file' Item 'driver.xml' was not found.")

        # Update driver.xml
        self.UpdateDriverXml(os.path.join(root, "driver.xml"))

        if not c4z.compressLists(os.path.join(self.dstdir, c4zName), root, c4zDirs, c4zFiles, c4zScriptFile, xmlByteOverride=self.bytes_io.getvalue()):
            raise Exception("DriverPackager: Building %s failed." % (c4zName))

        self.CleanupTmpFile(root)

        if driverType == "c4i":
            # Remove the .c4i that was generated as it is a zipped up .c4i and replace it with the following:
            os.remove(os.path.join(self.dstdir, c4zName))

            # Now find the temporary directory containing the needed driver.xml and driver.lua.squished.
            sourcePath = None
            directories = next(os.walk(tempfile.gettempdir()))[1]
            for d in directories:
                if str(d).startswith("Squished_Lua_"):
                    sourcePath = os.path.join(tempfile.gettempdir(), d)

            # If sourcePath is none then the temp directory was not created because encryption was detected in the driver.xml (see build_c4z.py)
            if sourcePath is None:
                raise Exception("Encryption was detected in the driver.xml.  When building drivers of type 'c4i', encryption must be disabled.  Please remove the attribute and value of encryption='2' from the <script> element in the driver.xml")

            # Update driver.xml
            self.UpdateDriverXml(os.path.join(self.srcdir, "driver.xml"))

            # Read the driver.xml under the sourcePath and check to see it has a <script> section.
            xmlTree = etree.parse(
                os.path.join(self.srcdir, "driver.xml"))
            xmlRootDriver = xmlTree.getroot()
            script = xmlRootDriver.findall('./config/script')

            if script is None:
                pass
            else:
                config = xmlRootDriver.find('config')
                for script in config.findall('script'):
                    config.remove(script)

            xmlTree.write(os.path.join(sourcePath, "driver2.xml"))

            # Read the driver.lua.squished file to get the contents into a variable.
            lua = codecs.open(os.path.join(
                self.srcdir, "driver.lua.squished"), 'r', encoding='utf-8')
            data = lua.readlines()
            lua.close()

            # Now add the squished lua to the <script> section of the driver, wrapped in <CDATA> tags
            document = etree.parse(os.path.join(sourcePath, "driver2.xml"))
            parent = document.find('config')
            child = etree.SubElement(parent, 'script')
            child.text = etree.CDATA(''.join(data))

            # Write out the final document (c4i)
            document.write(os.path.join(
                self.dstdir, c4zName), pretty_print=True)

        else:
            if self.unzip:
                driverName = os.path.join(self.dstdir, c4zName)
                extractPath = os.path.splitext(driverName)[0]

                if os.path.exists(extractPath):
                    shutil.rmtree(extractPath)
                with zipfile.ZipFile(driverName, "r") as z:
                    z.extractall(extractPath)

        postpackageCmds = xmlRoot.find('PostpackageCommands')
        if postpackageCmds != None:
            for postpackageCmd in postpackageCmds:
                print(postpackageCmd.tag, postpackageCmd.text)
                if postpackageCmd.tag != 'PostpackageCommand':
                    self.Log(
                        "Invalid XML: Found tag '%s', should be 'PostpackageCommand'" % (item.tag))
                    continue

                # execute the command
                osCommand = postpackageCmd.text.replace("\\", os.path.sep)
                osCommand = osCommand.replace("/", os.path.sep)
                if (os.system(osCommand) != 0):
                    print("Failed to execute postpackage command.")

        return squishLua, c4i

    def UpdateDriverXml(self, driverXmlPath):
        try:
            xmlTree = etree.parse(driverXmlPath)
            xmlRoot = xmlTree.getroot()

            if self.update_modified:
                dateModified = xmlRoot.find("modified")
                if dateModified is None:
                    raise Exception("<modified> tag not found")

                timestamp = datetime.datetime.now()
                timestamp = timestamp.strftime("%m/%d/%Y %I:%M %p")
                dateModified.text = timestamp
                self.Log("Build timestamp %s" % (timestamp))

            if self.driver_version:
                driverVersion = xmlRoot.find("version")
                if driverVersion is None:
                    raise Exception("<version> tag not found")
                oldVersion = driverVersion.text
                if oldVersion is None:
                    raise Exception("empty <version> tag")
                driverVersion.text = self.driver_version

            xmlTree.write(self.bytes_io, encoding='UTF-8', xml_declaration=False)
        except Exception as ex:
            self.Log(ex)
            raise Exception("Unable to update driver.xml")

    def DriverPackager(self):
        retcode = 0
        if self.manifest != None:
            self.Log("Building driver from manifest %s..." % (self.manifest))
            retcode = self.CreateFromManifest(
                os.path.join(self.srcdir, self.manifest))
        else:
            # Look the src directory for a manifest (.c4zproj).
            manifestPath = None
            for filename in os.listdir(self.srcdir):
                fn, ext = os.path.splitext(filename)
                if ext == ".c4zproj":
                    pPath, pDir = os.path.split(self.srcdir)

                    # If manifest name is equal to the parent directory, set the manifest path.
                    if pDir == fn:
                        manifestPath = os.path.join(self.srcdir, filename)
                        break

            # If a manifest was found, build c4z from manifest.
            if manifestPath:
                self.Log("Building driver from manifest %s..." % (filename))
                retcode = self.CreateFromManifest(manifestPath)

            # Otherwise, build c4z from all files in source directory, giving it the name of the source directory.
            else:
                if os.path.isfile(self.srcdir + os.path.sep + "squishy"):
                    squishLua = True
                else:
                    squishLua = False
                c4z.setSquishLua(squishLua)

                self.Log("Building driver from directory %s..." %
                         (os.path.abspath(self.srcdir)))
                c4zName = os.path.split(os.path.abspath(self.srcdir))[
                    1] + ".c4z"
                c4zScriptFile = self.GetEncryptFilename(
                    os.path.join(self.srcdir, "driver.xml"))
                if squishLua:
                    self.Squish(self.srcdir)

                if c4zScriptFile is not None:
                    c4z.compress(os.path.join(self.dstdir, c4zName),
                                 self.srcdir, c4zScriptFile, xmlByteOverride=self.bytes_io.getvalue())
                else:
                    c4z.compress(os.path.join(self.dstdir, c4zName), self.srcdir, None, xmlByteOverride=self.bytes_io.getvalue())

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
                        help="[optional] Filename of manifest xml file.",
                        nargs='?')
    parser.add_argument("-u", "--unzip", action="store_true",
                        help="[optional] Unzip the c4z in the target location.")
    parser.add_argument("-ae", "--allowexecute", action="store_true",
                        help="[optional] Allow Execute in Lua Command window.")
    parser.add_argument("--update-modified", action="store_true",
                        help="[optional] Update driver modified date.")
    parser.add_argument("--driver-version", nargs=1,
                        help="[optional] Update driver version to next argument.")
    args = parser.parse_args()

    return DriverPackager(args)


if __name__ == "__main__":
    dp = main()
    sys.exit(dp.DriverPackager())
