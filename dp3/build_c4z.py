#!/usr/bin/env python3

"""
Copyright 2020 Wirepath Home Systems, LLC. All Rights Reserved.
"""

import argparse
import sys
import os
import shutil
import fnmatch
import zipfile
import tempfile
import logging
import codecs
import datetime
import encrypt_c4z

squishLua_ = True
c4i_ = False


def GetSquishySource(srcDir):
    squishyLines = []
    srcToRemove = []
    if os.path.isfile(srcDir + os.path.sep + "squishy"):
        with open(srcDir + os.path.sep + "squishy") as squishyFile:
            squishyContent = squishyFile.readlines()
        squishyFile.close()

        for line in squishyContent:
            if line is not None and line.startswith("Module"):
                squishyLines.append(line.split(' '))

        for s in squishyLines:
            if s is not None and len(s) == 3:
                # If the 3rd column in the squishy file contains data, use that.
                path = s[2].replace('Module "', '').replace(
                    '"', '').replace("\n", '')
                srcToRemove.append(os.path.basename(path))
            elif s is not None and len(s) == 2:
                # If the 3rd column in the squishy file contains no data, then use the 2nd column.
                path = s[1].replace('Module "', '').replace('"', '').replace(
                    "\n", '').replace(".", os.path.sep) + ".lua"
                srcToRemove.append(os.path.basename(path))

    return srcToRemove


def GetSquishyOutputFile(srcDir):
    lines = []
    outputFile = None
    if os.path.isfile(srcDir + os.path.sep + "squishy"):
        with open(srcDir + os.path.sep + "squishy") as squishyFile:
            squishyContent = squishyFile.readlines()
        squishyFile.close()

        for line in squishyContent:
            if line is not None and line.startswith("Output") :
                lines.append(line.split(' '))

        for s in lines:
            path = s[1].replace('Output "', '').replace(
                '"', '').replace("\n", '')
            outputFile = path

    return str(outputFile).rstrip('\r')


def GetSquishyInputFile(srcDir):
    lines = []
    inputFile = None
    if os.path.isfile(srcDir + os.path.sep + "squishy"):
        with open(srcDir + os.path.sep + "squishy") as squishyFile:
            squishyContent = squishyFile.readlines()
        squishyFile.close()

        for line in squishyContent:
            if line is not None and line.startswith("Main"):
                lines.append(line.split(' '))

        for s in lines:
            path = s[1].replace('Main "', '').replace(
                '"', '').replace("\n", '')
            inputFile = path

    return str(inputFile).rstrip('\r')


def setSquishLua(squishLua):
    global squishLua_
    squishLua_ = squishLua
    return squishLua_


def setC4i(c4i):
    global c4i_
    c4i_ = c4i
    return c4i_


def compressLists(c4z, dirIn, dirsIn, filesIn, encryptedLua=None, xmlByteOverride=None):
    try:
        with zipfile.ZipFile(c4z, 'w', compression=zipfile.ZIP_DEFLATED) as zip:
            if xmlByteOverride:
                zip.writestr("driver.xml", xmlByteOverride)

            # Add files
            compressFileList(c4z, dirIn, dirIn, filesIn, zip, encryptedLua)

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
                    fileList = []
                    for i, f in enumerate(files):
                        if squishLua_ == False:
                            fileList.insert(i, {'c4zDir': c4zDir, 'name': f})
                        else:
                            if f not in GetSquishySource(dirIn):
                                fileList.insert(i, {'c4zDir': c4zDir, 'name': f})


                    compressFileList(c4z, dirIn, root, fileList,
                                     zip, encryptedLua)
                    if dir["recurse"] == str('false').lower():
                        break

    except zipfile.BadZipfile as ex:
        if os.path.exists(c4z):
            os.remove(c4z)
        print("Error building", c4z, "... exception: BadZipfile")
        return False
    except OSError as ex:
        print("Error building", c4z, "... exception:", ex.strerror)
        return False

    return True


def compressFileList(c4z, dir, root, files, zip, encryptedLua):
    tempDir = None
    try:
        squishedLua = None
        tempDir = tempfile.mkdtemp()
        tRoot = root = os.path.normpath(root)
        for file in files:
            if file["c4zDir"] and dir != root:
                tRoot, dName = os.path.split(root)
            filePath = os.path.join(
                file["c4zDir"], os.path.basename(file["name"]))
            arcPath = os.path.join(".", filePath)
            path, fName = os.path.split(file["name"])
            if encryptedLua is not None and os.path.normpath(arcPath) == os.path.normpath(encryptedLua):
                path, fName = os.path.split(file["name"])
                tempFile = os.path.join(tempDir, fName)
                Log("Encrypting %s..." % (os.path.basename(tempFile)))
                encrypt_c4z.encrypt(os.path.join(root, fName), tempFile)
                zip.write(tempFile, arcname=arcPath + '.encrypted')

                if squishLua_ is False and fName != encryptedLua:
                    zip.write(os.path.join(root, fName), arcname=arcPath)
            elif encryptedLua is not None and squishLua_:
                newPath = os.path.join(root, file["name"])
                sourcepath = os.path.normpath(newPath)
                path, fName = os.path.split(file["name"])
                inputFile = GetSquishyInputFile(root)

                if fName not in GetSquishySource(root) and fName != "squishy" and fName != inputFile:
                    zip.write(sourcepath, arcname=arcPath)
                if fName == inputFile:
                    tempFile = os.path.join(tempDir, fName)

                    # If a driver type of .c4i is detected, pass.  If c4z, go ahead and encrypt.
                    if c4i_:
                        pass
                    else:
                        Log("Encrypting %s..." % (os.path.basename(tempFile)))
                        encrypt_c4z.encrypt(os.path.join(
                            root, GetSquishyOutputFile(root)), tempFile)
                        zip.write(tempFile, arcname=arcPath + '.encrypted')

            elif encryptedLua is not None and squishLua_ is False and fName != encryptedLua:
                newPath = os.path.join(root, file["name"])
                sourcepath = os.path.normpath(newPath)
                zip.write(sourcepath, arcname=arcPath)
            elif encryptedLua is None and squishLua_:
                path, fName = os.path.split(file["name"])
                inputFile = GetSquishyInputFile(root)
                luaPath = ""
                if fName not in GetSquishySource(root) and fName != "squishy" and fName != inputFile:
                    newPath = os.path.join(root, file["name"])
                    sourcepath = os.path.normpath(newPath)
                    zip.write(sourcepath, arcname=arcPath)
                if fName == inputFile:
                    fName = GetSquishyOutputFile(root)
                    zip.write(os.path.join(root, fName), arcname=arcPath)

                    # If a c4i type driver is detected, read the contents of the squished lua file.
                    if c4i_:
                        with open(root + os.path.sep + fName) as lua:
                            squishedLua = lua.readlines()
                            lua.close()

                            # Clean up any temporary directories that start with "Squished_Lua_"
                            directories = next(
                                os.walk(tempfile.gettempdir()))[1]
                            for d in directories:
                                if str(d).startswith("Squished_Lua_"):
                                    shutil.rmtree(
                                        tempfile.gettempdir() + os.path.sep + d)

                            # Create a new temporary directory to store the Squished Lua.
                            luaPath = tempfile.mkdtemp("", "Squished_Lua_")

                            # Write the contents of the squishedLua variable to file.
                            f = codecs.open(os.path.join(
                                luaPath, "driver.lua.squished"), 'w', encoding='utf-8')
                            f.writelines(squishedLua)
                            f.close()

                if fName == 'driver.xml':
                    # if a c4i type driver is detected, read the contents of the driver.xml.
                    if c4i_:
                        with open(root + os.path.sep + fName) as driver:
                            driverXML = driver.readlines()
                            driver.close()

                            # Now write the file the same temporary directory that was created above (Squished_Lua_)
                            f = open(luaPath + os.path.sep + "driver.xml", "w")
                            f.writelines(driverXML)
                            f.close()

            else:
                newPath = os.path.join(root, file["name"])
                sourcepath = os.path.normpath(newPath)
                zip.write(sourcepath, arcname=arcPath)

        return squishedLua

    except ModuleNotFoundError as err:
        Log("Error: %s" % err)
        if err.name == 'M2Crypto':
            Log("M2Crypto is required to encrypt the driver (https://gitlab.com/m2crypto/m2crypto).")
        raise

    finally:
        if tempDir:
            shutil.rmtree(tempDir)


def compress(c4z, dir, encryptedLua=None, xmlByteOverride=None):
    tempDir = None

    try:
        with zipfile.ZipFile(c4z, 'w', compression=zipfile.ZIP_DEFLATED) as zip:
            for root, dirs, files in os.walk(dir):
                # Ignore hidden files and directories
                files = [f for f in files if not f[0] == '.']
                dirs[:] = [d for d in dirs if not d[0] == '.']
                for f in files:
                    # Ingore build.py file
                    if f == "build.py":
                        continue

                    arcpath = os.path.join(os.path.relpath(root, dir), f)

                    if f == "driver.xml" and xmlByteOverride:
                        zip.writestr("driver.xml", xmlByteOverride)
                        continue

                    if encryptedLua is not None and os.path.normpath(arcpath) == os.path.normpath(encryptedLua):
                        tempDir = tempfile.mkdtemp()
                        tempFile = os.path.join(tempDir, f)
                        Log("Encrypting %s..." % (os.path.basename(tempFile)))
                        encrypt_c4z.encrypt(os.path.join(root, f), tempFile)
                        if squishLua_:
                            newFile = tempDir + os.path.sep + \
                                GetSquishyInputFile(root)
                            oldFile = tempFile
                            os.rename(oldFile, newFile)
                            arcpath = os.path.join(os.path.relpath(
                                root, dir), GetSquishyInputFile(root))
                            zip.write(newFile, arcname=arcpath + '.encrypted')
                        if squishLua_ is False:
                            zip.write(tempFile, arcname=arcpath + '.encrypted')
                    elif squishLua_ and encryptedLua is None:
                        inputFile = GetSquishyInputFile(dir)
                        outputFile = GetSquishyOutputFile(dir)
                        if f not in GetSquishySource(dir) and f != "squishy" and f != outputFile and f != inputFile:
                            zip.write(os.path.join(root, f), arcname=arcpath)
                        if f == inputFile:
                            f = GetSquishyOutputFile(root)
                            zip.write(os.path.join(root, f), arcname=arcpath)
                    elif squishLua_ and encryptedLua is not None:
                        inputFile = GetSquishyInputFile(dir)
                        outputFile = GetSquishyOutputFile(dir)
                        if f not in GetSquishySource(dir) and f != "squishy" and f != outputFile and f != inputFile:
                            zip.write(os.path.join(root, f), arcname=arcpath)
                    else:
                        zip.write(os.path.join(root, f), arcname=arcpath)

    except zipfile.BadZipfile as ex:
        if os.path.exists(c4z):
            os.remove(c4z)
        print("Error building", c4z, "... exception: BadZipfile")
        return False
    except OSError as ex:
        print("Error building", c4z, "... exception:", ex.strerror)
        return False
    finally:
        if tempDir:
            shutil.rmtree(tempDir)

    return True


def extract(c4z, dir):
    try:
        with zipfile.ZipFile(c4z) as zip:
            zip.extractall(dir)
    except:
        if os.path.exists(dir):
            shutil.rmtree(dir, ignore_errors=True)
        return False

    return True


def Log(line):
    print("{}: {}".format(datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S"), line))
    sys.stdout.flush()


def package(inargs):
    parser = argparse.ArgumentParser(
        description="Handles creation and extraction of C4Z drivers")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Enables verbose output")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-x', '--extract', action='store_true',
                       help="Extracts rather than compresses the C4Z")
    group.add_argument('-c', '--compress', action='store_true',
                       help="Compresses the C4Z (default)")
    parser.add_argument('c4z', help="path to the C4Z file")
    parser.add_argument('dir', help="path to the C4Z contents directory")
    args = parser.parse_args(inargs)

    if args.extract:
        return 0 if extract(args.c4z, args.dir) else -1
    else:
        driverXml = os.path.join(args.dir, "driver.xml")
        driverLua = encrypt_c4z.get_encrypt_filename(
            driverXml)  # may be None if no encryption specified
        if compress(args.c4z, args.dir, driverLua):
            return 0

    return -1


if __name__ == '__main__':
    sys.exit(package(sys.argv[1:]))
