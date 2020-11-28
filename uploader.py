from vendor.skydb import skydb
from vendor.passphrase.passphrase import Passphrase
from multiprocessing.dummy import Pool
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


# Accepts filename of the locator output ("trp-locator.txt"), returns dict
def restore_from_file(filename):
    with open(filename) as f:
        return json.load(f)

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


def update_registry(argtuple):
    index_name = argtuple[0]
    skylink = argtuple[1]
    linenumber = argtuple[2]
    pk = argtuple[3]
    sk = argtuple[4]

    revision = 0  # TODO: Allow for updates by checking latest rev number
    data_key = 'trp:' + index_name
    data_value = skylink + '#L' + str(linenumber)

    entry = skydb.RegistryEntry(pk, sk)
    try:
        entry.set_entry(data_key=data_key, data=data_value, revision=revision)
        data_value, revision = entry.get_entry(data_key=data_key)
        print_if_verbose(data_key + '\t' + data_value + '\t' + str(revision))
    except:
        print(f'Failed: {data_key}')
        raise Exception
    return (pk, data_key, data_value, revision)


if __name__ == '__main__':
    verb = sys.argv[1]
    fileparam = sys.argv[2]
    outputdir = sys.argv[3]
    try:
        credentials = sys.argv[4]
    except:
        credentials = None
    try:
        alreadydone = sys.argv[5]
    except:
        alreadydone = None
    filelocator = None
    locator = None
    VERBOSE = True

    if verb == 'create':
        filelocator = create_index(fileparam, outputdir)  # also accepts URL
        with open(os.path.join(outputdir, 'trp-filelocator.txt'), 'w') as f:
            json.dump(filelocator, f)
    elif verb == 'loadfiles':
        filelocator = restore_from_file(fileparam)
    elif verb == 'loadskylinks':
        locator = restore_from_file(fileparam)
    else:
        raise Exception('Verb not recognized. Use create, loadfiles, loadskylinks.')
    
    filename_to_skylink = {}
    if locator is None:
        locator = {}
        for index_name, pair in filelocator.items():
            filename = os.path.join(outputdir, to_filename(pair[0]))
            if filename not in filename_to_skylink:
                print_if_verbose(filename)
                filename_to_skylink[filename] = upload_to_skynet(filename)
            locator[index_name] = (filename_to_skylink[filename], pair[1], filename)

        with open(os.path.join(outputdir, 'trp-skylinks.txt'), 'w') as f:
            json.dump(locator, f)

    if credentials is None:
        seed = generate_seed()
        pk, sk = skydb.crypto.genKeyPairFromSeed(seed)
        print_if_verbose('Seed – KEEP PRIVATE\n' + seed)
        print_if_verbose('Secret Key – KEEP PRIVATE\n' + sk.hex())
        print_if_verbose('Public Key\n' + pk.hex())
        with open(os.path.join(outputdir, 'trp-keys.txt'), 'w') as f:
            json.dump({'pk': pk.hex(), 'sk': sk.hex(), 'seed': seed}, f)
    else:
        credentials = restore_from_file(credentials)
        pk = bytes.fromhex(credentials['pk'])
        sk = bytes.fromhex(credentials['sk'])


    do_not_lookup = []
    if alreadydone is not None:
        with open(alreadydone) as f:
            for line in f:
                do_not_lookup.append(line.replace('trp:', '').replace('\n', '').strip())

    with Pool(5) as pool:
        to_update = [(index_name, tup[0], tup[1], pk, sk)
                 for index_name, tup in locator.items()
                 if index_name not in do_not_lookup]
        results = pool.map(update_registry, to_update)
