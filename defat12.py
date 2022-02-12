import struct
import datetime
import zipfile

f = open('hp9133_150_data_file', 'rb')
zf = zipfile.ZipFile('image.zip', 'w')
src = f.read()
f.close()

loc_fat1 = 0xc200
loc_fat2 = 0xc200 + 0x1600
loc_root_dir = 0xc200 + 0x1600 + 0x1600

fat1 = src[loc_fat1:loc_fat1 + 0x1600]
fat2 = src[loc_fat2:loc_fat2 + 0x1600]
rootdir = src[loc_root_dir:loc_root_dir + 0x500]

# Check if FAT tables match
if (fat1 == fat2):
    print ("Both FAT tables match!")
else:
    print ("FAT tables do not match.")

# Copy FAT table into data structure that is easier to use
fat = []
for i in range(0, len(fat1)-1, 3):
    # 3 bytes in, 2 entries out
    d1 = fat1[i]
    d2 = fat1[i + 1]
    d3 = fat1[i + 2]
    byte1 = d1 | ((d2 & 0xF) << 8)
    byte2 = ((d2 >> 4) & 0xF) | (d3 << 4)
    fat.append(byte1)
    fat.append(byte2)

#print (fat)

# Returns the cluster data indicated by the cluster number passed in
def get_cluster(cluster):
    offset = 0x14e00 # c200 + 1600 + 1600 + 4000 + 2000
    size = 0x1000 # 4096 bytes per cluster
    return src[(offset + cluster * size):(offset + (cluster + 1) * size)]

# Returns all data associated with a chain of clusters
def get_chain_data(start_cluster):
    data = b''
    while True:
        #print("Getting data for cluster %i" % start_cluster)
        data += get_cluster(start_cluster)
        start_cluster = fat[start_cluster]
        if start_cluster > 0xFEF:
            break
    return data

# Turns DOS date and time into Pythonese
def decode_datetime(timeval, dateval):
    try:
        hours = (timeval >> 11) & 0x1F
        minutes = (timeval >> 5) & 0x3F
        seconds = timeval & 0x1F
        year = 1980 + ((dateval >> 9) & 0x7F)
        month = (dateval >> 5) & 0xF
        if (month == 0):
            month = 1
        day = dateval & 0x1F
        if (day == 0):
            day = 1
        return datetime.datetime(year, month, day, hours, minutes, seconds)
    except ValueError as e:
        print(year, month, day, hours, minutes, seconds)

# Turns DOS attributes into a string code
def decode_attr(attr):
    s = ''
    if attr & 0x1:
        s += 'R'
    if attr & 0x2:
        s += 'H'
    if attr & 0x4:
        s += 'S'
    if attr & 0x8:
        s += 'V'
    if attr & 0x10:
        s += 'D'
    if attr & 0x20:
        s += 'A'
    if attr & 0x40:
        s += 'd'
    return s


def do_directory(dirdata, inpath):
    for i in range(0, len(dirdata), 32):
        # uatt, fch, u1, u2, u3, u4 are not used.
        (name, ext, att, uatt, fch, u1, u2, u3, u4, modtime,\
        moddate, startcl, filesize) = struct.unpack('<8s3sBBBHHHHHHHL', dirdata[i:i+32])
        ext = ext.decode().strip()
        name = name.decode(encoding='latin-1').strip(' ')
        std_name = name
        if ext:
            std_name += '.' + ext
        mod = decode_datetime(modtime, moddate)
 #       print (std_name, decode_datetime(modtime, moddate), startcl, filesize, decode_attr(att))
        # Pretty print the file
        if (name != '.') and (name != '..') and (name != '\x00\x00\x00\x00\x00\x00\x00\x00'):
            if (att & 0x10):
                # we have directory
                print('{:8}       <DIR>             {:%m-%d-%Y %H:%M:%S}'.format(name, mod))
            else:
                print('{:8} {:3}{:20,} {:%m-%d-%Y %H:%M:%S}'.format(name, ext, filesize, mod))

            # Fetch the file's data
            if (att & 0x10):
                filesize = 4096
            filedata = get_chain_data(startcl)[:filesize]

            # Add to zipfile
            if (att & 0x10):
                # Create directory in zip
                print("Creating directory: %s" % (inpath + std_name + '\\'))
                zi = zipfile.ZipInfo(inpath + std_name + '\\')
                zi.date_time = (mod.year, mod.month, mod.day, mod.hour, mod.minute, mod.second)
                zf.writestr(zi, '')
            else:
                print("Creating file: %s, %d" % (inpath + std_name, len(filedata)))
                zi = zipfile.ZipInfo(inpath + std_name)
                zi.date_time = (mod.year, mod.month, mod.day, mod.hour, mod.minute, mod.second)
                print(zi.filename)
                zf.writestr(zi, filedata)

            # Recurse into directory
            if (att & 0x10) and (name != '.') and (name != '..'):
                print (" ***** ENTERING DIRECTORY ***** ")
                do_directory(filedata, name + '\\')
                print (" ***** GOING UP A LEVEL ***** ")

do_directory(rootdir, '')
zf.close()
