#dumping utxo to es
from concurrent.futures import ProcessPoolExecutor
from blockchain_parser.blockchain import Blockchain
import os
from pymongo import MongoClient

executor = ProcessPoolExecutor(max_workers = 4)

def process_block(block):
	client = MongoClient("mongodb://localhost:27017")
	ba = client["ba"]
	utxo = ba["utxo"]

	timestamp = block.header.timestamp
	for tx in block.transactions:
		utxos = []
		tx_hash = tx.hash
		for index,output in enumerate(tx.outputs):
			document = {
				"tx_hash":tx_hash,
				"index":index,
				"address":output.addresses[0].address,
				"amount":output.value / 100000000
			}
			utxos.append(document)
		utxo.insert_many(utxos)


blockchain = Blockchain(os.path.expanduser('~/.bitcoin/blocks'))
count = 0
for block in blockchain.get_unordered_blocks():
	executor.submit(process_block,block)
	print(count,end="\r")
	count += 1