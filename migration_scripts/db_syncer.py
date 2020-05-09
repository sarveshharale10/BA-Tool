from pymongo import MongoClient
from blockchain_parser.blockchain import Blockchain
import pandas as pd
import time
import os
import requests
from datetime import datetime
from urllib.request import urlopen


class DBSnycer():
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
				print("Got Alert")

class BtcDBSyncer(DBSnycer):

	def sync_db(self):
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

class VjCoinDbSyncer(DBSnycer):		

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
		blocks,transactions = self.self.process_dfs(dfs0)

		for i in range(1,72):
				if i % 4 == 0:
						time.sleep(1)
				print(i)
				url = 'https://explore.vjti-bct.in/explorer?prev={}'.format(i)
				dfs = pd.read_html(url, header=None, index_col=0)
				temp_blocks,temp_transactions = self.self.process_dfs(dfs)
				blocks = blocks + temp_blocks
				transactions = transactions + temp_transactions

		df_blocks = pd.DataFrame(blocks)
		df_transactions = pd.DataFrame(transactions)
		df_blocks.columns = dfs0[0].index
		df_blocks['tx_hash']  = df_blocks.Transactions.str.split(' ',expand=True)[2]
		df_blocks.drop_duplicates(keep="first")
		print(df_blocks.columns)
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
		print(df_blocks.columns)
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
	
	def get_response(self,url):
        i = 1
        success = True
        try:
                myURL = urlopen(url)
                if(myURL.getcode() == 200):
                        return myURL.read()
        except:
                print("Connection Reset")
                time.sleep(0.25)

        while(True):
                try:
                        myURL = urlopen(url)
                        if (myURL.getcode() == 200):
                                return myURL.read()
                except:
                        print("Connection Reset")
                        time.sleep(0.1)
        return myURL.read()


	def sync_db(self):
        client = MongoClient("mongodb://localhost:27017")
        ba = client["vjcoin"]
        transactions = ba["transactions"]
        try:
			block_height = transactions.find().sort("block_height",-1).limit(1)[0]["block_height"]
			print (block_height)
        except:
			block_height = -1
        block_height += 1
        print(block_height)
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
			for i in range(1,num_iterations):
				print(i)
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
			print(df_blocks.columns)
			transactions = []
			receivers = []
			for index, row in df_blocks.iterrows():
				print(index)
				url = 'https://explore.vjti-bct.in/transaction/{}/{}'.format(row['Block Hash'],row['tx_hash'])
				response = self.get_response(url)
				dfs = pd.read_html(response, header=None, index_col=0)
				temp_transactions, temp_receivers = process_transaction_dfs(dfs)
				receivers = receivers + temp_receivers
				transactions = transactions + temp_transactions

			df_receivers = pd.DataFrame(receivers)
			df_transactions = pd.DataFrame(transactions)
			print(df_blocks.columns)
			df_transactions.columns = ['Transaction Hash','Block Hash','Timestamp','Sender Address','Message','Receivers']
			df_transactions = pd.merge(df_transactions,df_blocks[['Block Hash', 'Block Number']],on='Block Hash')
			df_transactions['Receivers'] = df_receivers[1]
			df_transactions['Amount'] = df_receivers[0]
			df_transactions['Timestamp'] = df_transactions['Timestamp'].str.split('(',expand=True)[1].str.split(')',expand=True)[0]
			self.insert_df_mongo(df_transactions,block_height)
