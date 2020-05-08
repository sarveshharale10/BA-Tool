import pandas as pd
import time
import os
from pymongo import MongoClient
from tqdm import tqdm
import requests

def process_dfs(dfs):
	block_list = []
	transaction_list = []
	for df in dfs[::2]:
		block_list.append(df.T.values[0])
	for df in dfs[1::2]:
		transaction_list.append(df.T.values[0])
	return block_list,transaction_list

def process_transaction_dfs(dfs):
	receivers_list = []
	transaction_list = []
	transaction_list.append(dfs[0].T.values[0])
	receivers_list.append([dfs[1].index[0],dfs[1].Address.values[0]])
	return transaction_list,receivers_list

def get_entire_chain():
	dfs0 = pd.read_html('https://explore.vjti-bct.in/explorer', header=None, index_col=0)
	blocks,transactions = process_dfs(dfs0)

	for i in range(1,72):
			if i % 4 == 0:
					time.sleep(1)
			print(i)
			url = 'https://explore.vjti-bct.in/explorer?prev={}'.format(i)
			dfs = pd.read_html(url, header=None, index_col=0)
			temp_blocks,temp_transactions = process_dfs(dfs)
			blocks = blocks + temp_blocks
			transactions = transactions + temp_transactions

	df_blocks = pd.DataFrame(blocks)
	df_transactions = pd.DataFrame(transactions)
	df_blocks.columns = dfs0[0].index
	df_blocks['tx_hash']  = df_blocks.Transactions.str.split(' ',expand=True)[2]
	df_blocks.drop_duplicates(ignore_index= True)
	print(df_blocks.columns)
	transactions = []
	receivers = []
	for index, row in df_blocks.iterrows():
			if index % 4 == 0:
					time.sleep(1)
			print(index)
			url = 'https://explore.vjti-bct.in/transaction/{}/{}'.format(row['Block Hash'],row['tx_hash'])
			dfs = pd.read_html(url, header=None, index_col=0)
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

	insert_df_mongo(df_transactions)
	df_transactions.to_csv('vjchain.csv')

def insert_df_mongo(df,block_height):
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

def sync_chain():
	client = MongoClient("mongodb://localhost:27017")
	ba = client["vjcoin"]
	transactions = ba["transactions"]
	try:
		block_height = transactions.find().sort("block_height",-1).limit(1)[0]["block_height"]
		print (block_height)
	except:
		block_height = -1
	block_height += 1
	response = requests.get('https://explore.vjti-bct.in/info')
	chain_height = int(response.text.split('<br>')[0].split(':')[-1])
	if (block_height < chain_height):
		remaining_blocks = chain_height - block_height
		num_iterations = int (remaining_blocks / 8)
		remaining_blocks -= num_iterations*8
		if remaining_blocks > 0:
			num_iterations += 1
		dfs0 = pd.read_html('https://explore.vjti-bct.in/explorer', header=None, index_col=0)
		blocks,transactions = process_dfs(dfs0)
		time.sleep(1)
		for i in range(1,num_iterations):
				if i % 4 == 0:
						time.sleep(1)
				print(i)
				url = 'https://explore.vjti-bct.in/explorer?prev={}'.format(i)
				dfs = pd.read_html(url, header=None, index_col=0)
				temp_blocks,temp_transactions = process_dfs(dfs)
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

		insert_df_mongo(df_transactions,block_height)

if __name__ == "__main__":
	sync_chain()
	# df = pd.read_csv('vjchain.csv')
	# insert_df_mongo(df)