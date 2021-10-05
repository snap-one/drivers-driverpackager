# Driver Packager


## Versions
* **dp**: Driver Packager for Python 2
* **dp3**: Driver Packager for Python 3
* **dplite**: Driver Packager Lite for Python 2
* **dplite3**: Driver Packager Lite for Python 3

It is recommended that new Driver Packager users use dp3.

_**ONLY dp3 IS GUARANTEED TO BE MAINTAINED AND UPDATED IN THE FUTURE.**_

The rest of this README is specific to Driver Packager 3, although much of it may also apply to other versions.


## Requirements

Driver Packager requires:
* A working installation of Python 3 (https://www.python.org/downloads/)
* M2Crypto installed for your Python installation _(if encrypting your driver)_ (https://gitlab.com/m2crypto/m2crypto)
* Lua installed _(if squishing your driver)_ (https://www.lua.org/download.html)


## Using Driver Packager to build a .c4z

> usage: driverpackager.py [-h] [-v] [-u] [-ae] srcdir dstdir [manifest]
>
> * required arguments:
>   * **srcdir**: Directory where c4z source files are located
>   * **dstdir**: Directory where c4z files are placed
>   * **manifest**: [optional] Filename of manifest xml file
>
> * optional arguments:
>   * **-h, --help**: show help message and exit
>   * **-v, --verbose**: Enable verbose
>   * **-u, --unzip**: Unzip the c4z in the target location
>   * **-ae, --allowexecute**: Allow Execute in Lua Command window even for encrypted driver (adds C4:AllowExecute(true) to Lua source)
>   * **--update-modified**: Updates `modified` tag in the output driver.xml to the current time
>   * **--driver-version DRIVER_VERSION**: Set driver version (`version` XML tag) to the specified value. Overrides version from the input driver.xml.

## Using Driver Packager in Github Actions

This repository can also be used to build your c4z projects as a GitHub Action.
You'll need to use another action or script to push the file output where it needs to go next.

```yaml
uses: control4/drivers-driverpackager@v1
with:
  # Directory (relative to the root of your Git repo) that contains the .c4zproj to build
  projectDir: ''
  # Filename for the c4z project to build
  c4zproj: ''
  # Directory (relative to projectDir) to output the built c4z file to
  # Defaults to the parent directory ('./../')
  outputDir: ''

```

## Manifest File format

The manifest.xml file is an XML file, with the following format:

```
<Driver type="c4z" name="c4z_base_filename" squishLua="false">
  <Items>
    <Item type="file" name="driver.xml" />
    <Item type="file" name="driver.lua" />
    <Item type="file" c4zDir="www" name="www/documentation.rtf" />
    <Item type="file" name="id_ds2.gif" />
  </Items>
</Driver>
```

Notes:

* c4z_base_filename within the Driver tag should be replaced with the output .c4z name.
* Items with a 'c4zDir' attribute will get added to the .c4z in the specified directory.
* Items 'name' attribute is relative to the directory the manifest file is in.

## Driver Packager source files:

**driverpackager.py**:

Main Driver Packager Python script.

**build_c4z.py**:

Used by driverpackager to squish and zip the source files into the .c4z output.

>usage: build_c4z.py [-h] [-v] [-x | -c] c4z dir
>
>* Arguments:
>  * **c4z**: path to the C4Z file
>  * **dir**: path to the C4Z contents directory
>
>* Optional arguments:
>  * **-h, --help**: show help message and exit
>  * **-v, --verbose**: Enables verbose output
>  * **-x, --extract**: Extracts the C4Z
>  * **-c, --compress**: Compresses the C4Z (default)


**encrypt_c4z.py**:

Used by driverpackager to encrypt the driver.lua source file (and any squished with it) using S-MIME encryption (DriverWorks Encryption V2).

>usage: encrypt_c4z.py input_path output_path


**squish**:

Used by driverpackager to combine multiple Lua source files into a single Lua output file, which can then be encrypted.

Documentation for Squish can be found here: http://matthewwild.co.uk/projects/squish/readme.html

