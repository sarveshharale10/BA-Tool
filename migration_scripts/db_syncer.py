from pymongo import MongoClient
from blockchain_parser.blockchain import Blockchain
import pandas as pd
import time
import os
import requests
from datetime import datetime
from urllib.request import urlopen
import ssl
from web3 import Web3
from concurrent.futures import ProcessPoolExecutor

class DBSyncer():
	def sync_db(self):
		pass

	def check_for_alerts(self,tx,db):
		tx_volume = 0

		addresses = set()
		for inp in tx["inputs"]:
			addresses.add(inp["address"])

		for output in tx["outputs"]:
			addresses.add(output["address"])
			tx_volume += output["amount"]


		monitors = db.monitors.find()
		for monitor in monitors:
			if((monitor["type"] == "address" and monitor["value"] in addresses) or (monitor["type"] == "amount" and tx_volume >= float(monitor["value"]))):
				db.monitors.update({"_id":monitor["_id"]},{"$push":{"alerts":{"tx_hash":tx["tx_hash"],"timestamp":datetime.now()}}})

	def update_statistics(self,tx,db):
		for output in tx["outputs"]:
			try:
				current_value = db.top_receivers.find_one({"_id":output["address"]},{"_id":0,"value":1})["value"]
				new_value = current_value + output["amount"]
				db.top_receivers.update({"_id":output["address"]},{"$set":{"value":new_value}})
			except:
				new_value = output["amount"]
				db.top_receivers.insert({"_id":output["address"],"value":new_value})

			try:
				current_value = db.top_holders.find_one({"_id":output["address"]},{"_id":0,"value":1})["value"]
				new_value = current_value + output["amount"]
				db.top_holders.update({"_id":output["address"]},{"$set":{"value":new_value}})
			except:
				new_value = output["amount"]
				db.top_holders.insert({"_id":output["address"],"value":new_value})

		for output in tx["inputs"]:
			try:
				current_value = db.top_senders.find_one({"_id":output["address"]},{"_id":0,"value":1})["value"]
				new_value = current_value + output["amount"]
				db.top_senders.update({"_id":output["address"]},{"$set":{"value":new_value}})
			except:
				new_value = output["amount"]
				db.top_senders.insert({"_id":output["address"],"value":new_value})

			try:
				current_value = db.top_holders.find_one({"_id":output["address"]},{"_id":0,"value":1})["value"]
				new_value = current_value - output["amount"]
				db.top_holders.update({"_id":output["address"]},{"$set":{"value":new_value}})
			except:
				new_value = -output["amount"]
				db.top_holders.insert({"_id":output["address"],"value":new_value})

	def update_last_block(self,last_block,db):
		db.config.update({},{"$set":{"last_block":last_block}})
			

class BtcDBSyncer(DBSyncer):
	db_name = "ba"

	def sync_db(self):
		db = MongoClient("mongodb://localhost:27017")[self.db_name]

		utxo = db["utxo"]
		transactions = db["transactions"]

		try:
			config = db["config"]
			last_block = config.find_one({"_id":0,"last_block":1})["last_block"]
		except:
			last_block = -1
		next_block = last_block + 1
		blocks_path = '/home/shared/bitcoin/blocks'
		index_path = ""

		blockchain = Blockchain(os.path.expanduser(blocks_path))
		for block in blockchain.get_ordered_blocks(index_path,start=next_block):
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
						documents.append(document)
					except Exception as e:
						f = open('logs', 'a')
						f.write(e)
						f.write("TX HASH" + str(tx_hash)+ '\n')
						f.close()
					utxo.insert_one(document)

			timestamp = block.header.timestamp

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

				transactions.insert_one(document)
				self.check_for_alerts(document,db)
				self.update_statistics(document,db)

			self.update_last_block(block.height,db)

class EthDBSyncer(DBSyncer):
	db_name = "ethereum"

	def sync_db(self):
		db = MongoClient("mongodb://localhost:27017")[self.db_name]
		transactions = db["transactions"]

		geth_ipc_path = "/media/sarvesh/HD-B1/sarvesh/BlockchainAnalysis/ethereum/geth.ipc"
		w3 = Web3(Web3.IPCProvider(geth_ipc_path))

		try:
			last_block = int(db.config.find_one({},{"_id":0,"last_block":1})["last_block"])
		except Exception as e:
			print(e)
			last_block = -1

		next_block = last_block + 1
		last_block = w3.eth.blockNumber
		for i in range(next_block,last_block):
			try:
				block = w3.eth.getBlock(i)
				print(f"block {i} found",end="\r")
				timestamp = block.timestamp
				txhashes = block.transactions
				for txhash in txhashes:
					transaction = dict(w3.eth.getTransaction(txhash.hex()))
					tx_from = transaction["from"].lower()
					tx_to = transaction["to"].lower()

					if(len(tx_from) != 42 or len(tx_to) != 42 or len(transaction["input"]) != 2):
						continue

					doc = {}
					doc["timestamp"] = timestamp
					doc["tx_hash"] = transaction["hash"].hex()
					total = (transaction["value"] + transaction["gas"] * transaction["gasPrice"]) / (10 ** 18)
					doc["inputs"] = [{"address":tx_from,"amount":total}]
					doc["outputs"] = [{"address":tx_to,"amount":transaction["value"] / (10 ** 18)}]
					transactions.insert_one(doc)
					self.check_for_alerts(doc,db)
					self.update_statistics(doc,db)

				self.update_last_block(i,db)
				i += 1
			except Exception as e:
				print(e)

class VjCoinDbSyncer(DBSyncer):		

	def process_dfs(self,dfs):
		block_list = []
		transaction_list = []
		for df in dfs[::2]:
			block_list.append(df.T.values[0])
		for df in dfs[1::2]:
			transaction_list.append(df.T.values[0])
		return block_list,transaction_list

	def process_transaction_dfs(self,dfs):
		receivers_list = []
		transaction_list = []
		transaction_list.append(dfs[0].T.values[0])
		receivers_list.append([dfs[1].index[0],dfs[1].Address.values[0]])
		return transaction_list,receivers_list

	def get_entire_chain(self):
		dfs0 = pd.read_html('https://explore.vjti-bct.in/explorer', header=None, index_col=0)
		blocks,transactions = self.process_dfs(dfs0)

		for i in range(1,72):
				if i % 4 == 0:
						time.sleep(1)
				print(i)
				url = 'https://explore.vjti-bct.in/explorer?prev={}'.format(i)
				dfs = pd.read_html(url, header=None, index_col=0)
				temp_blocks,temp_transactions = self.process_dfs(dfs)
				blocks = blocks + temp_blocks
				transactions = transactions + temp_transactions

		df_blocks = pd.DataFrame(blocks)
		df_transactions = pd.DataFrame(transactions)
		df_blocks.columns = dfs0[0].index
		df_blocks['tx_hash']  = df_blocks.Transactions.str.split(' ',expand=True)[2]
		df_blocks.drop_duplicates(keep="first")
		#print(df_blocks.columns)
		transactions = []
		receivers = []
		for index, row in df_blocks.iterrows():
				if index % 4 == 0:
						time.sleep(1)
				print(index)
				url = 'https://explore.vjti-bct.in/transaction/{}/{}'.format(row['Block Hash'],row['tx_hash'])
				dfs = pd.read_html(url, header=None, index_col=0)
				temp_transactions, temp_receivers = self.process_transaction_dfs(dfs)
				receivers = receivers + temp_receivers
				transactions = transactions + temp_transactions

		df_receivers = pd.DataFrame(receivers)
		df_transactions = pd.DataFrame(transactions)
		#print(df_blocks.columns)
		df_transactions.columns = ['Transaction Hash','Block Hash','Timestamp','Sender Address','Message','Receivers']
		df_transactions = pd.merge(df_transactions,df_blocks[['Block Hash', 'Block Number']],on='Block Hash')
		df_transactions['Receivers'] = df_receivers[1]
		df_transactions['Amount'] = df_receivers[0]
		df_transactions['Timestamp'] = df_transactions['Timestamp'].str.split('(',expand=True)[1].str.split(')',expand=True)[0]

		self.insert_df_mongo(df_transactions)
		df_transactions.to_csv('vjchain.csv')

	def insert_df_mongo(self,df,block_height):
		client = MongoClient("mongodb://localhost:27017")
		ba = client["vjcoin"]
		transactions = ba["transactions"]

		for index, row in df.iterrows():
			tx = {}
			if (int(row['Block Number']) >= block_height):
				tx["block_height"] = int(row['Block Number'])
				tx["tx_hash"] = row['Transaction Hash']
				tx["timestamp"] = int(row['Timestamp'])
				tx["outputs"] = list()
				tx["inputs"] = list()
				record = {}
				record["address"] = row['Receivers']
				record["amount"] = row['Amount']
				tx["outputs"].append(record)
				record = {}
				record["address"] = row['Sender Address']
				record["amount"] = row['Amount']
				tx["inputs"].append(record)
				transactions.insert_one(tx)

				self.check_for_alerts(tx,ba)
				self.update_statistics(tx,ba)

	def get_response(self,url):
		i = 1
		context = ssl._create_unverified_context()
		myURL = urlopen(url, context=context)
		# html = response.read()
		# return html

		while(myURL.status != 200):
			try:
				myURL = urlopen(url, context=context)
			except:
				time.sleep(10)
				
			# response = requests.get(url)
			i += 1
			if i % 4 == 0:
				time.sleep(1)
		return myURL.read()

	def sync_db(self):
		client = MongoClient("mongodb://localhost:27017")
		ba = client["vjcoin"]
		transactions = ba["transactions"]
		try:
			block_height = transactions.find().sort("block_height",-1).limit(1)[0]["block_height"]
			#print (block_height)
		except:
			block_height = -1
		block_height += 1
		response = self.get_response('https://explore.vjti-bct.in/info')
		chain_height = int(response.decode().split('<br>')[0].split(':')[-1])
		if (block_height < chain_height):
			remaining_blocks = chain_height - block_height
			num_iterations = int (remaining_blocks / 8)
			remaining_blocks -= num_iterations*8
			if remaining_blocks > 0:
				num_iterations += 1
			response = self.get_response('https://explore.vjti-bct.in/explorer')
			dfs0 = pd.read_html(response, header=None, index_col=0)
			blocks,transactions = self.process_dfs(dfs0)
			time.sleep(1)
			for i in range(1,num_iterations):
					if i % 4 == 0:
							time.sleep(1)
					#print(i)
					url = 'https://explore.vjti-bct.in/explorer?prev={}'.format(i)
					response = self.get_response(url)
					dfs = pd.read_html(response, header=None, index_col=0)
					temp_blocks,temp_transactions = self.process_dfs(dfs)
					blocks = blocks + temp_blocks
					transactions = transactions + temp_transactions

			df_blocks = pd.DataFrame(blocks)
			df_transactions = pd.DataFrame(transactions)
			df_blocks.columns = dfs0[0].index
			df_blocks['tx_hash']  = df_blocks.Transactions.str.split(' ',expand=True)[2]
			df_blocks.drop_duplicates(keep="first")
			#print(df_blocks.columns)
			transactions = []
			receivers = []
			for index, row in df_blocks.iterrows():
					if index % 4 == 0:
							time.sleep(1)
					print(index)
					url = 'https://explore.vjti-bct.in/transaction/{}/{}'.format(row['Block Hash'],row['tx_hash'])
					response = self.get_response(url)
					dfs = pd.read_html(response, header=None, index_col=0)
					temp_transactions, temp_receivers = self.process_transaction_dfs(dfs)
					receivers = receivers + temp_receivers
					transactions = transactions + temp_transactions

			df_receivers = pd.DataFrame(receivers)
			df_transactions = pd.DataFrame(transactions)
			#print(df_blocks.columns)
			df_transactions.columns = ['Transaction Hash','Block Hash','Timestamp','Sender Address','Message','Receivers']
			df_transactions = pd.merge(df_transactions,df_blocks[['Block Hash', 'Block Number']],on='Block Hash')
			df_transactions['Receivers'] = df_receivers[1]
			df_transactions['Amount'] = df_receivers[0]
			df_transactions['Timestamp'] = df_transactions['Timestamp'].str.split('(',expand=True)[1].str.split(')',expand=True)[0]

			self.insert_df_mongo(df_transactions,block_height)

executor = ProcessPoolExecutor(max_workers = 3)

if(__name__ == "__main__"):
	syncer = VjCoinDbSyncer()
	executor.submit(syncer.sync_db)
	syncer = EthDBSyncer()
	executor.submit(syncer.sync_db)
	executor.shutdown(wait=True)
	time.sleep(180 * 60)