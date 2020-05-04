#dumping tx to es
from concurrent.futures import ProcessPoolExecutor
from blockchain_parser.blockchain import Blockchain
import os
from pymongo import MongoClient
from tqdm import tqdm

executor = ProcessPoolExecutor(max_workers = 4)

def process_block(block):
	client = MongoClient("mongodb://localhost:27017")
	ba = client["ba"]
	transactions = ba["transactions"]
	utxo = ba["utxo"]

	timestamp = block.header.timestamp
	documents = []
	for transaction in block.transactions:
		tx = {}
		tx["tx_hash"] = transaction.hash
		tx["timestamp"] = timestamp
		tx["outputs"] = list()
		tx["inputs"] = list()

		if(transaction.is_coinbase()):
			output = transaction.outputs[0]
			record = {}
			record["address"] = output.addresses[0].address
			record["amount"] = output.value / 100000000
			tx["outputs"].append(record)
		else:
			for output in transaction.outputs:
				try:
					record = {}
					record["address"] = output.addresses[0].address
					record["amount"] = output.value / 100000000
					tx["outputs"].append(record)
				except:
					pass

			for inp in transaction.inputs:
				try:
					result = utxo.find_one({"tx_hash":inp.transaction_hash,"index":inp.transaction_index})
					record = {}
					record["address"] = result["address"]
					record["amount"] = result["amount"]
					tx["inputs"].append(record)
				except:
					pass

		documents.append(tx)
	transactions.insert_many(documents)


blockchain = Blockchain(os.path.expanduser('~/.bitcoin/blocks'))
count = 0
for block in tqdm(blockchain.get_unordered_blocks()):
	count += 1
	#executor.submit(process_block,block)