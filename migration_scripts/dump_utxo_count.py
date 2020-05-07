#dumping utxo to es
from concurrent.futures import ProcessPoolExecutor
from blockchain_parser.blockchain import Blockchain
import os
from pymongo import MongoClient
from tqdm import tqdm
from datetime import datetime

executor = ProcessPoolExecutor(max_workers = 70)

def process_block(block):
#	client = MongoClient("mongodb://localhost:27017")
#	ba = client["ba"]
#	utxo = ba["utxo"]
	utxo_count = inserted_count = skipped_count = tx_count = 0
	timestamp = block.header.timestamp
	#print(block.height)
	#block_height = block.height
	for tx in block.transactions:
		tx_count += 1
		utxos = []
		tx_hash = tx.hash
		for index,output in enumerate(tx.outputs):
			utxo_count += 1
			try:
				inserted_count += 1
				'''
				document = {
					"tx_hash":tx_hash,
					"index":index,
					"address":output.addresses[0].address,
					"amount":output.value / 100000000
				}
				utxos.append(document)
				'''
			except:
				skipped_count += 1
				pass
	itemlist = [str(timestamp), str(utxo_count), str(tx_count), str(skipped_count), str(inserted_count)]
	text = (',').join(itemlist)
#	print(text,type(text))
#	print('Processing')
#	print (timestamp,itemlist)
#	return itemlist
	with open(str(timestamp), "w") as outfile:
	    outfile.write(",".join(itemlist))



blockchain = Blockchain(os.path.expanduser('/home/shared/bitcoin/blocks'))
count = 0
encountered = False
for block in tqdm(blockchain.get_unordered_blocks()):
#	count += 1
#	if count > 20:
#		break
	executor.submit(process_block,block)
#	process_block(block)
	
