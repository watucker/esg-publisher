from esgcet.pub_client import publisherClient
import sys, json, requests
from datetime import datetime
from pathlib import Path

class ESGPubUpdate:
    ''' Handles setting latest=false for previously published versions, includes finding those in the index
    '''


    def __init__(self, index_node, cert_fn, silent=False, verbose=False):    
        """
            index_node (string):  The node to search for the update 
            cert_fn (string):  Filename for certicate to use to push updates to the API
            silent (bool):  suppress INFO messages
            verbose (bool):  extended output, useful for debugging
        """
        self.index_node = index_node 
        self.cert_fn = cert_fn
        self.silent = silent
        self.verbose = verbose
        self.pubCli = publisherClient(self.cert_fn, self.index_node, verbose=self.verbose, silent=self.silent)

        self.SEARCH_TEMPLATE = 'http://{}/esg-search/search/?latest=true&distrib=false&format=application%2Fsolr%2Bjson&data_node={}&master_id={}&fields=version,id'


    def gen_hide_xml(self, id, type):
        ''' Generate the xml to hide the previous version

            id - the full dataset identifier
            type - which core to target: "files" or datasets"
        '''

        dateFormat = "%Y-%m-%dT%H:%M:%SZ"
        now = datetime.utcnow()
        ts = now.strftime(dateFormat)
        idfield = "id"
        if type == "files":
            idfield = "dataset_id"
        txt = f"""<updates core="{type}" action="set">
            <update>
              <query>{idfield}={id}</query>
              <field name="latest">
                 <value>false</value>
              </field>
              <field name="_timestamp">
                 <value>{ts}</value>
              </field>
            </update>
            </updates>
            \n"""

        return txt


    def update_core(self, dsetid, type):
        """ For a specific core, generate the xml and run the update.

            id - the full dataset identifier
            type - which core to target: "files" or datasets"
        """
        update_rec = self.gen_hide_xml(dsetid, type)
        if self.verbose:
            print(update_rec)
        self.pubCli.update(update_rec)

    def do_update(self, input_rec):
        """ Check a record in the index and peform the updates

            input_rec - a json record to be published containing a "master_id" and "data_node" fields with 
                        a new version
        """
    # The dataset record either first or last in the input file
        dset_idx = -1
        if not input_rec[dset_idx]['type'] == 'Dataset':
            dset_idx = 0

        if not input_rec[dset_idx]['type'] == 'Dataset':
            print("Error: could not find the Dataset record.  Malformed input, exiting!", file=sys.stderr)
            exit(1)

        mst = input_rec[dset_idx]['master_id']
        dnode = input_rec[dset_idx]['data_node']

        # query for
        url = self.SEARCH_TEMPLATE.format(index_node, dnode, mst)

        if self.verbose:
            print(f"Search Url: '{url}'")
        resp = requests.get(url)

        if self.verbose:
            print(resp.text)
        if not resp.status_code == 200:
            print(f'Error: received {resp.status_code} from index server.', file=sys.stderr)
            exit(1)

        res = json.loads(resp.text)

        if res['response']['numFound'] > 0:
            docs = res['response']["docs"]
            dsetid = docs[0]['id']

            self.update_core(dsetid,"datasets")
            self.update_core(dsetid, "files")
            if not self.silent:
                print(f'INFO: Found previous version, updating the record: {dsetid}')

        else:
            if not self.silent:
                version = input_rec['version']
                print(f'INFO: First dataset version for {mst}: v{version}.)')
