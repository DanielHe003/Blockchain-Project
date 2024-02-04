import hashlib
import json
import requests
from time import time
from urllib.parse import urlparse
from uuid import uuid4

from flask import Flask, jsonify, request

class Blockchain:
    def __init__(self):
        self.chain = []
        self.nodes = set()
        self.current_transactions = []

        # this is where the genesis block is created
        self.new_block(previous_has = '1', proof = 100)

    def registr_node(self, address):
        # adds a node to the list.
        # Param address: Address of the node, ex:'http://192.168.0.5:5000'

        url = urlparse(address)
        if url.netloc:
            self.nodes.add(url.netloc)
        #no scheme, ex: '192.168.0.5:5000'
        elif url.path: 
            self.nodes.add(url.path)
        else:
            raise ValueError('URL of the address is Incorrect.')

    def valid_chain(self, chain):
        # Determine if the Blockchain is valid.
        # Param: chain: Blockchain
        # return True if Valid, False if Not Valid.

        tail = chain[0]
        index = 1

        while index < len(chain):
            block = chain[index]
            print(f'{tail}')
            print(f'{block}')
            print("\n-------------\n")

            # Checks for validity
            last_hash = self.hash(tail)
            if block['previous_hash'] != lash_hash:
                return False
            if not self.valid_proof(tail['proof'], block['proof'], lash_hash):
                return False
            tail = block
            index += 1
            
        return True

    def resolve_conflict(self):
        # Resolves conflict by replacing chain with the longest one in the current network
        # return: True if chain was altered, False if not

        neighbors = self.nodes
        newChain = None
        maxLength = len(self.chain)

        #verification on chains
        for node in neighbors:
            response = request.get(f'http://{node}/chain')

            if response.statusCode == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > maxLength and self.valid_chain(chain):
                    maxLength = length
                    newChain = chain
        if newChain:
            self.chain = newChain
            return True
        
        return False

    def new_block(self, proof, previous_hash):
        # Creates a new block for the blockchain
        # Param: proof: proof of work algorithm
        # return: New Block

        block = {
            'proof': proof,
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
            'transactions': self.current_transactions,
        }

        self.current_transactions = []
        self.chain.append(block)
        return block

    @staticmethod
    def hash(block):
        # SHA-256 hash
        # Param block: Block

        block_string = json.dump(block, sort_keys= True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def new_transaction(self, sender, recipient, amount):
        # New transaction for the block.
        # Param: sender: Address of the Sender
        # Param: Recipient: Address of the Recipient
        # Param: Amount: Amount of currency in the transction

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        # Returns last block of the chain
        # Return: Last block

        return self.chain[-1]

    def proof_of_work(self, lash_block):
        # Proof of Work Algo
        # Param: last_block: dict, last Block
        # Return: Int
        last_proof = last_block['proof']
        last_hash = self.hash(lash_block)
        proof = 0

        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof, lash_hash):
        # Validitation off the Proof
        # Param: last_proof: Int, Prev Proof
        # Param: proof: Int, Curr Proof
        # Param: last_hash Str, Hash of Prev Block
        # Return: bool, True if Correct, else False

        guess = f'{last_proof}{proof}{lash_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()



# This was provided by a online module, concept is simple so I did not implement this part myself.
# Some parts were edited to get a better grasp on the topic.
# Credit to Daniel van Flymen
@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


#The following code was half guided. 
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return "Error: List of Nodes is not Valid", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New node(s) have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)