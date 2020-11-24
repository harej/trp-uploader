from vendor.skydb import skydb
import json
import rdflib
import requests
import sys

PORTAL = 'https://siasky.net'

def process_and_print(index_json):
    g = rdflib.Graph()
    g = g.parse(data=index_json, format='json-ld')
    for subj, pred, obj in g.triples((None, None, None)):
        print(f'{subj.n3()} {pred.n3()} {obj.n3()}')

def get_registry(public_key, data_key):
    data_key = skydb.crypto.hash_data_key(data_key)
    public_key = 'ed25519:' + public_key
    data = {'publickey': public_key, 'datakey': data_key}
    return requests.get(PORTAL + '/skynet/registry', params=data).json()

def get_index(public_key, index):
    data_key = 'trp:' + index
    data = get_registry(public_key, data_key)
    data = bytes.fromhex(data['data']).decode('utf-8')
    data = data.split('#')
    skylink = data[0]
    line_number = int(data[1].replace('L', ''))
    skyfile = requests.get(f'{PORTAL}/{skylink}')
    skyfile = skyfile.text.split('\n')
    return skyfile[line_number]

def get_triple_pattern(public_key, subj, pred, obj):
    # s  p? o? --> s:{subj}
    # s? p  o? --> p:{pred}
    # s? p? o  --> o:{obj}
    # s? p  o  --> po:{pred}:{obj}
    # s  p  o? --> sp:{subj}:{pred}
    # s  p? o  --> so:{subj}:{obj}

    subj_is_known = True
    pred_is_known = True
    obj_is_known = True

    if subj[0] == '?':
        subj_is_known = False
    if pred[0] == '?':
        pred_is_known = False
    if obj[0] == '?':
        obj_is_known = False

    if not subj_is_known and not pred_is_known and not obj_is_known:
        raise Exception('Please specify at least one value')

    if subj_is_known and pred_is_known and obj_is_known:
        raise Exception('Nothing to look up')

    if subj_is_known:
        if pred_is_known:
            return get_index(public_key, f'sp:{subj}:{pred}')
        elif obj_is_known:
            return get_index(public_key, f'so:{subj}:{obj}')
        else:
            return get_index(public_key, f's:{subj}')
    elif pred_is_known:
        if obj_is_known:
            return get_index(public_key, f'po:{pred}:{obj}')
        else:
            return get_index(public_key, f'p:{pred}')
    elif obj_is_known:
        return get_index(public_key, f'o:{obj}')


def get_graph(public_key, param):
    return get_index(public_key, f'value:{param}')

if __name__ == '__main__':
    arg = sys.argv
    verb = arg[1]
    if verb == 'registry':
        print(json.dumps(get_registry(arg[2], arg[3])))
    elif verb == 'index':
        process_and_print(get_index(arg[2], arg[3]))
    elif verb == 'triple':
        process_and_print(get_triple_pattern(arg[2], arg[3], arg[4], arg[5]))
    elif verb == 'graph':
        process_and_print(get_graph(arg[2], arg[3]))
    else:
        print('Verb not recognized. Use: triple, graph, index, registry')
