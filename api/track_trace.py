import pymongo
import json

client = pymongo.MongoClient("mongodb://localhost:27017")

transactions = client["ba"]["transactions"]

class Tracker():

	def __init__(self,transactions):
		self.transactions = transactions

	def get_single_forward_transactions(self,addresses):

		result = self.transactions.find({"inputs":{"$elemMatch":{"address":{"$in":addresses}}}});

		single_hop_transactions = list()
		for item in result:
			single_hop_transactions.append(item["tx_hash"])

		return single_hop_transactions

	def track(self,address,hop_count):
		result = {}
		#returns transactions at each level
		txs = self.get_single_forward_transactions([address])
		result[0] = txs
		for count in range(hop_count - 1):
			#iterate
			output_addresses = set()
			all_outputs = self.transactions.find({"tx_hash":{"$in":list(txs)}},{"_id":0,"outputs":1})
			for record in all_outputs:
				for output in record["outputs"]:
					output_addresses.add(output["address"])

			txs = set()
			transactions_1 = self.get_single_forward_transactions(list(output_addresses))
			for transaction in transactions_1:
				txs.add(transaction)

			result[count + 1] = txs

		return result

class Tracer():

	def __init__(self,transactions):
		self.transactions = transactions

	def get_single_backward_transactions(self,addresses):

		result = self.transactions.find({"outputs":{"$elemMatch":{"address":{"$in":addresses}}}});

		single_hop_transactions = list()
		for item in result:
			single_hop_transactions.append(item["tx_hash"])

		return single_hop_transactions

	def trace(self,address,hop_count):
		result = {}
		txs = self.get_single_backward_transactions([address])
		result[0] = txs
		for count in range(hop_count - 1):
			#iterate
			input_addresses = set()
			all_inputs = self.transactions.find({"tx_hash":{"$in":list(txs)}},{"_id":0,"inputs":1})
			for record in all_inputs:
				for inp in record["inputs"]:
					input_addresses.add(inp["address"])

			txs = set()
			transactions_1 = self.get_single_backward_transactions(list(input_addresses))
			for transaction in transactions_1:
				txs.add(transaction)

			result[count + 1] = txs

		return result

tracker = Tracker(transactions)

tracer = Tracer(transactions)

#print(tracer.trace("1FijBR5s3EU1JS3UokzTZbkAibgL4SXzxm",1))
