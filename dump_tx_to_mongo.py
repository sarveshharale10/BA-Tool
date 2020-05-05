#dumping tx to es
from concurrent.futures import ProcessPoolExecutor
from blockchain_parser.blockchain import Blockchain
import os
from pymongo import MongoClient
from tqdm import tqdm

executor = ProcessPoolExecutor(max_workers = 40)

def process_block(block):
	client = MongoClient("mongodb://localhost:27017")
	ba = client["ba"]
	transactions = ba["transactions"]
	utxo = ba["utxo"]

	timestamp = block.header.timestamp
	documents = []
	for transaction in block.transactions:
		tx = {}
		tx_hash = transaction.hash
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
			for index,output in enumerate(transaction.outputs):
				try:
					result = utxo.find({"tx_hash":tx_hash,"index":index}).count()
					record = {}
					record["address"] = output.addresses[0].address
					record["amount"] = output.value / 100000000
					tx["outputs"].append(record)
					if(result == 0):
						utxo.insert({"tx_hash":tx_hash,"index":index,"address":record["address"],"amount":record["amount"]})
				except:
					pass

			for inp in transaction.inputs:
				try:
					result = utxo.find_one({"tx_hash":inp.transaction_hash,"index":inp.transaction_index},{"_id":0,"address":1,"amount":1})
					record = {}
					record["address"] = result["address"]
					record["amount"] = result["amount"]
					tx["inputs"].append(record)
				except:
					pass

		transactions.insert(tx)


blockchain = Blockchain(os.path.expanduser('/home/shared/bitcoin/blocks'))
count = 0
encountered = False
for block in tqdm(blockchain.get_unordered_blocks()):
	x = int(block.header.timestamp.timestamp())
#	if (x > 1430832925 and x < 1493991325)):
	if (x < 1430832925):
		executor.submit(process_block,block)
