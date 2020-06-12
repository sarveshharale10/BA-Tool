from concurrent.futures import ProcessPoolExecutor
from web3 import Web3
from tqdm import tqdm
from pymongo import MongoClient
import sys

geth_ipc_path = "/media/sarvesh/HD-B1/sarvesh/BlockchainAnalysis/ethereum/geth.ipc"
w3 = Web3(Web3.IPCProvider(geth_ipc_path))

executor = ProcessPoolExecutor(max_workers = int(sys.argv[1]))

conn = MongoClient("mongodb://localhost:27017")["ethereum"]["transactions"]

def process_transaction(transaction,timestamp):
	tx_from = transaction["from"].lower()
	tx_to = transaction["to"].lower()

	if(len(tx_from) != 42 or len(tx_to) != 42 or len(transaction["input"]) != 2):
		return

	doc = {}
	doc["timestamp"] = timestamp
	doc["tx_hash"] = transaction["hash"].hex()
	total = (transaction["value"] + transaction["gas"] * transaction["gasPrice"]) / (10 ** 18)
	doc["inputs"] = [{"address":tx_from,"amount":total}]
	doc["outputs"] = [{"address":tx_to,"amount":transaction["value"] / (10 ** 18)}]
	conn.insert_one(doc)

try:
	latest_timestamp = conn.find({},{"_id":0,"timestamp":1}).sort("timestamp",-1).limit(1)[0]["timestamp"]
	conn.remove({"timestamp":latest_timestamp})
except Exception as e:
	latest_timestamp = 0

i = 0
while(True):
	try:
		block = w3.eth.getBlock(i)
		print(f"block {i} found",end="\r")
		timestamp = block.timestamp
		if(timestamp >= latest_timestamp):
			txhashes = block.transactions
			for txhash in txhashes:
				transaction = dict(w3.eth.getTransaction(txhash.hex()))
				executor.submit(process_transaction,transaction,timestamp)

		i += 1
	except Exception as e:
		raise e
		continue