# CreateC4Z

Usage:

CreateC4Z c4zprojfile srcdir dstdir [-d] [-e]

Required arguments:

c4zprojfile: filename of the c4zproj file

srcdir: Directory where c4z source files are located

dstdir: Directory where the generated c4z file will be placed

Optional arguments:

-d, --develop: designates this build as a development build.

-e, --encrypt: designates that the driver should be squished and encrypted.

c4zprojfile is the name of the project file (without the extension) The script will pull the target driver name from there and will use it to find directories that might be in different locations than in the final driver. The individual file names listed do not matter and the ‘squishLua’ and ‘manualsquish’ are ignored.

scrdir is the location of at least the driver.xml and driver.lua files. All other relative directory locations are keyed from there.

dstdir is the location where the generated c4z driver file will end up.

-d is an optional parameter. If it is present, then the script will make and use a temporary copy of driver.lua and the lines

C4:AllowExecute(true)

gIsDevelopmentVersionOfDriver = true

will be added. This will allow us to use the Lua window in Composer even if the file is encrypted and will cause the LogDev statements to be functional.

-e is an optional parameter. If it is present, then that designates that all the source files should be pulled into one file and that that file should be encrypted. This will also cause the script to make a temporary copy of driver.xml and insert

encryption=”2” as an attribute to the ‘script’ tag in the ‘config’ section.

----

I have tried to boil this program down. It doesn’t have a lot of bells and whistles, but it handles the common cases by itself. Its secret weapon is its ability to traverse the list of required files in the proper order starting from driver.lua. This list is used to pull only the needed files from the template directories and will have them in the right order if they should be pulled into a single file to be encrypted.

The program does make some assumptions. It is hard-coded to include driver.xml, driver.lua, and all files and directories in the www directory that are not hidden. It assumes that driver.lua exists and that it is the root starting file for the Lua program.

For a non-encrypted driver, CreateC4Z will pull in source files from directories specified in the c4zproj file and place them in the c4z (zip) file in the directory structure that makes sense to the Lua interpreter.

This program does not use the ‘squish’ utility. I looked at squish and it can do a lot of things to make files smaller and more obfuscated. However, we were only using it as a utility to pull all the source files into a single file. Even then we had to do work to create a correct squishy file that would list the files in their proper order. I decided that it would be more efficient for the script to just create the driver.lua.squished file by itself.

The program will only make the squished file if the -e flag is set. It seems to me that the only real reason to squish the source code is that it can all be encrypted. So, the -e flag has two effects. It will pull all of the source files into one file and then encrypt it to driver.lua.encrypted. It will also open the driver.xml file and insert ‘encryption=”2”’ in as attribute of the ‘script’ tag in the ‘config’ section. I feel that encrypting or not encrypting should be a build time decision, not a property of the driver itself. This has been a problem because Composer and Director would get that information by looking at that attribute. So, now it can be added at build time and not worried about otherwise.

I also feel that specifying a driver as a development version should be a build time decision too. However, I think it is also good luck to have the development version to be as close to the release version as possible. So, the -d option will add two lines into the driver.lua file.

One line is ‘C4:AllowExecute(true)’. This will allow us to use the Lua window in composer even if the driver has been encrypted. If the driver was not encrypted, the line will still be added, but will have no effect.

The other line is ‘gIsDevelopmentVersionOfDriver = true’. I added a LogDev option into our logging template code. It is similar to LogInfo, LogTrace, etc., but will only print if that variable is set to true. I use this for printing things like user codes that are helpful during development but should not be exposed in the release version of a driver.

encrypt_c4z.py was written as a stand-alone script and called from driverpackager. I just stole its code and put it into a routine in CreateC4Z. It will only act on driver.lua.squished to create driver.lua.encrypted. I have only executed this under Python2.7. I’m not sure what it will do in Python3.6.