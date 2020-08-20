"""
File is: createsquishy.py
Copyright 2019 Control4 Corporation.  All Rights Reserved.
"""

#! /usr/bin/env python

import sys
import os
import xml.etree.ElementTree as ElementTree


class LuaFile:
    def __init__(self, refName, dirRefs, fileRefs, moduleList):
        self._refName = refName
        self._dirRefs = dirRefs
        self._fileRefs = fileRefs
        self._moduleList = moduleList
        self._alreadyIncluded = False

        rootLen = self._refName.find('.')
        if(rootLen >= 0):
            rootRef = self._refName[:rootLen]
            fileSubPath = self._refName[rootLen+1:].replace('.', '/')

            rootLoc = ''
            for CurDirInfo in self._dirRefs:
                if(rootRef == CurDirInfo['dstLoc']):
                    rootLoc = CurDirInfo['srcLoc']
                    break

            if(rootLoc == ''):
                raise Exception(
                    "LuaFile src directory not found (%s)" % (refName))

            self._fileName = rootLoc + '/' + fileSubPath + '.lua'

        else:
            self._fileName = refName + '.lua'

        for checkRef in self._moduleList:
            if(self._refName == checkRef['Ref']):
                self._alreadyIncluded = True
                break

        pass        # so I can put a breakpoint here

    def IsAlreadyIncluded(self):
        return self._alreadyIncluded

    def TraverseRequiredFiles(self):
        MySourceFile = open(self._fileName, "r")
        FileContent = MySourceFile.readlines()
        InsideComment = False
        for Curline in FileContent:
            # if(Curline.find('--[[')):
            #    InsideComment = True

            if(not InsideComment):
                # only check at the beginning of the line so requires inside functions aren't snagged.
                if(Curline[:7] == 'require'):
                    reqStr, subFileStr = Curline.split(' ', 1)
                    QuoteChar = subFileStr[:1]
                    CloseQuoteLoc = subFileStr[1:].find(QuoteChar) + 1
                    subFileStr = subFileStr[1:CloseQuoteLoc]
                    #print("%s traverse requires: %s" % (self._refName, subFileStr))

                    reqFile = LuaFile(subFileStr, self._dirRefs,
                                      self._fileRefs, self._moduleList)
                    if(not reqFile.IsAlreadyIncluded()):
                        reqFile.TraverseRequiredFiles()
            else:
                pass
                # if(Curline.find(']]')):
                #    InsideComment = False

        MySourceFile.close()

        self._moduleList.append(
            {'Ref': self._refName, 'FileLoc': self._fileName})


def extractFromProjFile(projFile, dirRefs, fileRefs):
    retcode = 0
    try:
        xmlTree = ElementTree.parse(projFile)
        xmlRoot = xmlTree.getroot()
    except IOError as ex:
        print("IOError: %s" % ex)
        retcode = ex.errno
    except ElementTree.ParseError as ex:
        print("CreateSquishy: Invalid XML (%s): %s" % (projFile, ex))
        retcode = ex.code
    else:
        try:
            if xmlRoot.tag != 'Driver':
                raise Exception(
                    "CreateSquishy: Invalid XML: Missing tag 'Driver'")

            items = xmlRoot.find('Items')
            if items == None:
                raise Exception(
                    "CreateSquishy: Invalid XML: Missing tag 'Items'")

            for item in items:
                if item.tag != 'Item':
                    print("Invalid XML: Found tag '%s', should be 'Item'" %
                          (item.tag))
                    continue

                # Mandatory item attributes
                itemType = item.attrib.get('type')
                if itemType == None:
                    raise Exception(
                        "CreateSquishy: Invalid XML: Missing tag 'Item' subtag 'type'")

                itemName = item.attrib.get('name')
                if itemName == None:
                    raise Exception(
                        "CreateSquishy: Invalid XML: Missing tag 'Item' subtag 'name'")

                # If optional item attribute 'exclude' is True, skip it
                exclude = True if item.attrib.get(
                    'exclude') == str('true').lower() else False
                if exclude:
                    continue

                if itemType == 'dir':
                    # Verify directory Item exists
                    if not os.path.exists(itemName):
                        raise Exception(
                            "CreateSquishy: Error, manifest 'dir' Item '%s' does not exist." % (itemName))

                    c4zDir = item.attrib.get('c4zDir') if item.attrib.get(
                        'c4zDir') != None else ''
                    dirRefs.append({'dstLoc': c4zDir, 'srcLoc': itemName})

                elif itemType == 'file':
                    # Verify file Item exists
                    if not os.path.exists(itemName):
                        raise Exception(
                            "CreateSquishy: Error, manifest 'file' Item '%s' does not exist in '%s'." % (itemName))

                    fn, ext = os.path.splitext(itemName)
                    if(ext == '.lua'):
                        fileRefs.append(fn)

        except Exception as ex:
            print("extractFromProjFile exception: %s" % ex)
            retcode = 255

    return retcode


def writeSquishyFile(ModList):
    SquishyFileName = "squishy"
    squishyFile = open(SquishyFileName, "w+")

    squishyFile.write('Main "driver.lua"\n\n')

    for CurMod in ModList:
        squishyFile.write('Module "%s"\t"%s"\n' %
                          (CurMod['Ref'], CurMod['FileLoc']))

    squishyFile.write('\nOutput "driver.lua.squished"\n')
    squishyFile.close()


def createsq(inProjFile):
    AllDirs = []
    AllFiles = []
    ModulesList = []

    print("Create squishy file from proj file: %s" % (inProjFile))
    extractFromProjFile(inProjFile, AllDirs, AllFiles)

    # print('Directories:')
    # for dirEntry in AllDirs:
    #    print("%s -> %s" % (dirEntry["dstLoc"], dirEntry["srcLoc"]))

    # print('Files:')
    # for fileEntry in AllFiles:
    #    print("%s" % fileEntry)

    rootLua = LuaFile("driver", AllDirs, AllFiles, ModulesList)
    rootLua.TraverseRequiredFiles()

    writeSquishyFile(ModulesList)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        sys.exit(0 if createsq(sys.argv[1]) else -1)
    else:
        print ('No manifest file specified')
        sys.exit(-1)
