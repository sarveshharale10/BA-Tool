#dumping utxo to es
from concurrent.futures import ProcessPoolExecutor
from blockchain_parser.blockchain import Blockchain
import os
from pymongo import MongoClient
from tqdm import tqdm
from datetime import datetime
import gc

executor = ProcessPoolExecutor(max_workers = 70)

def process_block(block):
	client = MongoClient("mongodb://localhost:27017")
	ba = client["ba"]
	utxo = ba["utxo1"]

	for tx in block.transactions:
		tx_hash = tx.hash
		for index,output in enumerate(tx.outputs):
			try:
				document = {
					"tx_hash":tx_hash,
					"index":index,
					"address":output.addresses[0].address,
					"amount":output.value / 100000000
				}
				utxo.insert(document)
			except Exception as e:
				f = open('logs', 'a')
				f.write(e)
				f.write("TX HASH" + str(tx_hash)+ '\n')
				f.close()
	# Free RAM
	del block
	gc.collect()



blockchain = Blockchain(os.path.expanduser('/home/shared/bitcoin/blocks'))
count = 0
encountered = False
for block in tqdm(blockchain.get_unordered_blocks()):
	if(int(block.header.timestamp.timestamp()) < 1430832925):
		executor.submit(process_block,block)
