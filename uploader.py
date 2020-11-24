from vendor.skydb import skydb
from vendor.passphrase.passphrase import Passphrase
from pprint import pprint
import json
import os
import rdflib
import requests
import sys

VERBOSE = False
PORTAL = 'https://siasky.net'

def print_if_verbose(content):
    if VERBOSE == True:
        print(content)


def bytes_of_string(s):
    return len(s.encode('utf-8'))


def to_filename(i):
    return f'trp-{str(i).zfill(15)}.txt'


def generate_seed():
    passphrase = Passphrase('internal')
    passphrase.amount_w = 18
    passphrase.amount_n = 0
    return ' '.join(passphrase.generate())


# Accepts filename, returns skylink
def upload_to_skynet(file):
    r = requests.post(
            PORTAL + '/skynet/skyfile/trp-index.jsonl',
            files={'file': open(file, 'rb')})
    response = r.json()
    try:
        skylink = response['skylink']
    except KeyError:
        pprint(response)
        raise Exception

    print_if_verbose(skylink)
    return skylink


# Accepts filename as input, returns list of files generated
def create_index(filename, outputdir):
    outputdir = os.path.dirname(outputdir)
    graph = rdflib.Graph()
    graph.parse(filename, format=rdflib.util.guess_format(filename))
    subgraphs = {}

    for subj, prop, obj in graph.triples((None, None, None)):
        indices = [f'value:{subj.n3()}',
                   f'value:{prop.n3()}',
                   f'value:{obj.n3()}',
                   f's:{subj.n3()}',
                   f'p:{prop.n3()}',
                   f'o:{obj.n3()}',
                   f'sp:{subj.n3()}:{prop.n3()}',
                   f'po:{prop.n3()}:{obj.n3()}',
                   f'so:{subj.n3()}:{obj.n3()}']

        for index in indices:
            if index not in subgraphs:
                subgraphs[index] = rdflib.Graph()
            subgraphs[index].add((subj, prop, obj))

    manifest = [[]]
    index_name_to_file_and_line = {}  # (filenumber, linenumber)
    bytes_counter = 0
    limit = 3900000
    for subgraph_name, subgraph in subgraphs.items():
        ser = subgraph.serialize(format='json-ld')
        ser = json.loads(ser.decode('utf-8'))
        ser = json.dumps(ser, indent=None, separators=(',', ':'))
        ser_bytes = bytes_of_string(ser)
        manifest[len(manifest)-1].append(ser)
        index_name_to_file_and_line[subgraph_name] = (
            len(manifest)-1,
            len(manifest[len(manifest)-1])-1
        )
        print_if_verbose(
            str(len(manifest)-1) +
            '\t' +
            str(len(manifest[len(manifest)-1])-1) +
            '\t' +
            subgraph_name
        )
        bytes_counter += ser_bytes
        filecounter = len(manifest)-1
        if bytes_counter >= limit:
            content = '\n'.join(manifest[filecounter])
            openfile = os.path.join(outputdir, to_filename(filecounter))
            with open(openfile, 'w') as f:
                f.write(content)
            manifest.append([])
            bytes_counter = 0

    # The remainder
    if bytes_counter > 0:
        filecounter = len(manifest)-1
        content = '\n'.join(manifest[filecounter])
        openfile = os.path.join(outputdir, to_filename(filecounter))
        with open(openfile, 'w') as f:
            f.write(content)

    return index_name_to_file_and_line


def update_registry(index_name, skylink, linenumber, pk, sk):
    revision = 0  # TODO: Allow for updates by checking latest rev number
    data_key = 'trp:' + index_name
    data_value = skylink + '#L' + str(linenumber)

    entry = skydb.RegistryEntry(pk, sk)
    entry.set_entry(data_key=data_key, data=data_value, revision=revision)
    
    data_value, revision = entry.get_entry(data_key=data_key)
    print_if_verbose(data_key + '\t' + data_value + '\t' + str(revision))
    return (pk, data_key, data_value, revision)


if __name__ == '__main__':
    VERBOSE = True
    filelocator = create_index(sys.argv[1], sys.argv[2])
    locator = {}
    filename_to_skylink = {}
    
    for index_name, pair in filelocator.items():
        filename = os.path.join(sys.argv[2], to_filename(pair[0]))
        if filename not in filename_to_skylink:
            print_if_verbose(filename)
            filename_to_skylink[filename] = upload_to_skynet(filename)
        locator[index_name] = (filename_to_skylink[filename], pair[1])

    seed = generate_seed()
    pk, sk = skydb.crypto.genKeyPairFromSeed(seed)
    print_if_verbose('Seed – KEEP PRIVATE\n' + seed)
    print_if_verbose('Secret Key – KEEP PRIVATE\n' + sk.hex())
    print_if_verbose('Public Key\n' + pk.hex())

    for index_name, pair in locator.items():
        returntuple = update_registry(index_name, pair[0], pair[1], pk, sk)
