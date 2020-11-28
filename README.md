# Upload RDF data to Skynet and then retrieve it

The `trp-uploader` software package is a basic Python utility that lets you prepare RDF data (XML, Turtle, ntriples, JSON-LD, etc.) for upload to Skynet and subsequent retrieval of that data through simple triple pattern lookups and single-URI graph lookups.

This is very new and experimental and might be rough around the edges.

Demo video: https://siasky.net/AABEnDFEHOhug47LXgbzQXu1GsYTPKJXRum9kKMOJLH28g

## Introduction
RDF is a simple format for expressing structured data, consisting of statements with three words: a subject, a predicate, and an object. The value of each word can be a URI, a universal identifier for resources that may resolve to an online resource as well (but is not required to). For example, if you had a namespace `<http://cooldata>`, the statement "the capital of Mississippi is Jackson" could be expressed as `<http://cooldata/Mississippi> <http://cooldata/hasCapital> <http://cooldata/JacksonMissisippi> .`, with each of those URIs referring to different concepts. RDF is a standard for expressing data in graph databases, where connections are drawn between related concepts. It is an appealing format because it is simple, it is schemaless, and it facilitates interoperability between datasets through the use of common URIs and the mapping together of distinct URIs through [semantic matching](https://en.wikipedia.org/wiki/Semantic_matching).

Graph databases are known to take up large amounts of memory. Efficient querying of large datasets can require over 100 GB of RAM, and the operation of graph database servers can cost thousands of dollars per month on AWS and similar services. While graph databases give us a flexible and highly scalable option for organizing data and revealing insights from that data, the limitations of public endpoints such as the [Wikidata Query Service](https://query.wikidata.org) limits the growth of apps built on such endpoints.

Enter Skynet. [Skynet](https://siasky.net) is a decentralized content delivery network built on the [Sia](https://sia.tech) network, where individuals and organizations with spare hard drive capacity can rent that capacity out to an online network of renters. Renters select their hosts through an automated selection process and pay hosts directly through a payment token particular to that network. The result is a highly available public network that is highly resistant to downtime. Portals such as [siasky.net](https://siasky.net) facilitate public access to this network, though individuals can set up their own private portals as well.

A key feature of Skynet is a global shared state known as the Skynet Registry, which allows any user or application to register key-value pairs to the network. In the absence of a global identifier or authentication scheme is one centered on public-key cryptography, and [ed25519](https://ed25519.cr.yp.to) public-private key pairs in particular. In essence, a public key identifies a user, and a secret key allows that user to update their user-specific key-value pairs. This allows for the development of applications on the network with user accounts interchangable between apps, with data always in the user's control.

The **Triplespace** project uses Skynet Registry to store RDF triple datasets, for public or private use, transforming Skynet into an Internet-wide graph database. We can do this by changing how we think about databases. Currently, databases work by indexing the data on one system (or cluster of systems) and carrying out all the computational work while receiving requests from clients. Triplespace removes central computing servers from the equation and uses the network as a global index while relegating computational work to the client. Instead of sending a request to a database server, clients instead request the necessary datasets and then use client-side RDF libraries (available in Python, JavaScript, and more) to reconstruct graph databases for client-side SPARQL queries and the like.

The `trp-uploader` is the first phase of the project, facilitating upload and (simple) retrieval workflows. With Triplespace, a public key identifies a graph/dataset, and lookups are achieved through combining the public key with the terms of the lookup. There is no need to maintain a central index, though indices do need to be updated as new datasets are uploaded.

## Installation

1. `git clone https://github.com/harej/trp-uploader`

2. `cd trp-uploader`

3. `pip3 install rdflib rdflib-jsonld requests`

4. `cd vendor/skydb`

5. `pip3 install -r requirements.txt`

## Usage

### Command line

#### Create indexes from datasets and upload to Skynet

`python3 uploader.py (data file) (output dir for index files)`

The *data file* is an RDF file (XML, JSON-LD, NT, Turtle, etc. accepted). It will guess what file type it is based on the file extension. Gzipped files should not be used for now. You can also specify a URL to a dataset in lieu of a local file path.

The *output dir* is the directory where the intermediate index files should be saved to. Make sure to end the directory name with a slash `/` at the end.

The output of this command is a public key, secret key, and seed used to generate both. The seed and secret key should be kept secret. The public key identifies your dataset publicly. If you want others to use the dataset, you can post the public key in a conspicuous place. Include documentation about how your data is structured. If you don't want others to use it, don't tell anyone about it.

In the future, datasets can be uploaded through updates to the Skynet Registry, but for now, if you want to make changes to a dataset, you have to upload it anew.

#### Look up based on triple pattern

`python3 lookup.py triple (public key) (subject) (predicate) (object)`

The *public key* is produced during the process described above, and it is used to distinguish datasets from others. The *subject*, *predicate*, and *object* are RDF terms, including URIs such as `<https://www.wikidata.org/entity/Q55654897>`, string literals such as `"This"`, numbers, etc. For variables, use a question mark followed by text like `?this`. For command line use, wrap each term in quotation marks.

Example:

```
$ python3 lookup.py triple 062572f5766e35b556e66a2f0920a615f68e3897727cbe5d4f56bc8e7da5c545 "?subj" "<http://james/instanceOf>" "<http://james/cat>"

<http://james/daisy> <http://james/instanceOf> <http://james/cat>
```

#### Look up graph for a given term

`python lookup.py graph (public key) (term)`

Constructs a graph based on the appearance of the given term as a subject, predicate, *or* object.

Example:
````
$ python3 lookup.py graph 062572f5766e35b556e66a2f0920a615f68e3897727cbe5d4f56bc8e7da5c545 "<http://james/cat>"                                                 
<http://james/daisy> <http://james/instanceOf> <http://james/cat>
<http://james/cat> <http://james/instanceOf> <http://james/mammal>
````
