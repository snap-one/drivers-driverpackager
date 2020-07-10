"""
Copyright 2018 Control4 Corporation.  All Rights Reserved.
"""

#! /usr/bin/env python3

import sys
import os
import xml.etree.ElementTree as ET
from M2Crypto import BIO, Rand, SMIME, X509

def get_devicedata(filename):
    with open(filename, "rb") as file:
        try:
            filestr = file.read()
            devicedata = ET.fromstring(filestr)
        except Exception as ex:
            print ('Invalid XML - %s.' % ex)
            return None

    if devicedata is None or not devicedata.tag == "devicedata":
        print ('devicedata missing')
        return None

    return devicedata

def get_encrypt_filename(filename):
    devicedata = get_devicedata(filename)
    node = devicedata.find('config/script[@encryption="2"]')
    if node is None:
        return None
    return node.attrib['file']

def encrypt(filename, outfilename):
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

    with open(filename, 'rb') as file:
        str = file.read()
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

        with open(outfilename, 'wb') as outfile:
            outfile.write(outbuf.read())

if __name__ == '__main__':
    if len(sys.argv) > 2:
        sys.exit(0 if encrypt(sys.argv[1], sys.argv[2]) else -1)
    else:
        print ('No input or output file specified')
        sys.exit(-1)

