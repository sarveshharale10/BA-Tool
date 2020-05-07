from pymongo import MongoClient
from blockchain_parser.blockchain import Blockchain

db = MongoClient("mongodb://localhost:27017")["ba"]

config = db["config"]

utxo = db["utxo"]
transactions = db["transactions"]

#get last block height
last_block = config.find({"name":"bitcoin"},{"_id":0,"last_block":1})

blocks_path = '/home/shared/bitcoin/blocks'
index_path = ""

blockchain = Blockchain(os.path.expanduser(blocks_path))
for block in blockchain.get_ordered_blocks(index_path,start=last_block + 1):
	for tx in block.transactions:
		tx_hash = tx.hash
		documents = []
		for index,output in enumerate(tx.outputs):
			try:
				document = {
					"tx_hash":tx_hash,
					"index":index,
					"address":output.addresses[0].address,
					"amount":output.value / 100000000
				}
				documents.append(document)
			except Exception as e:
				f = open('logs', 'a')
				f.write(e)
				f.write("TX HASH" + str(tx_hash)+ '\n')
				f.close()
		utxo.insert_many(documents)

for block in blockchain.get_ordered_blocks(index_path,start=last_block + 1):
	timestamp = block.header.timestamp

	documents = []
	for transaction in block.transactions:
		tx_hash = transaction.hash
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

		documents.append(tx)
	transactions.insert_many(documents)

