import string
import random
from flask import jsonify

def combine_inputs_outputs(responses):
	unique_addresses = set()

	for response in responses:

		contributions = dict()
		for inp in response["inputs"]:
			try:
				contributions[inp["address"]] += inp["amount"]
			except:
				contributions[inp["address"]] = inp["amount"]

		inputs = list()
		for (key,value) in contributions.items():
			inputs.append({"address":key,"amount":value})
			unique_addresses.add(key)
		response["inputs"] = inputs
	
		contributions = dict()
		for inp in response["outputs"]:
			try:
				contributions[inp["address"]] += inp["amount"]
			except:
				contributions[inp["address"]] = inp["amount"]

		outputs = list()
		for (key,value) in contributions.items():
			unique_addresses.add(key)
			outputs.append({"address":key,"amount":value})
		response["outputs"] = outputs

	return responses,unique_addresses

def convert_result_to_json(query,responses,clusterized = False):
	graph = {}
	graph["nodes"] = list()
	graph["relationships"] = list()

	depth_colors = {
		0:"#87faed",
		1:"#87cefa",
		2:"#8795fa"
	}

	responses,unique_addresses = combine_inputs_outputs(responses)

	for response in responses:

		color = "#57C7E3"

		if("depth" in response):
			color = depth_colors[response["depth"]]

		if(response["tx_hash"] == query):
			color = "#ff0000"

		graph["nodes"].append({
			"id":response["tx_hash"],
			"labels":["Transaction"],
			"properties":{
				"tx_hash":response["tx_hash"]
			},
			"color":color
		})

		for inp in response["inputs"]:
			graph["relationships"].append({
				"type":"INPUT",
				"startNode":inp["address"],
				"endNode":response["tx_hash"],
				"properties":{
					"amount":inp["amount"]
				}
			})

		for inp in response["outputs"]:
			graph["relationships"].append({
				"type":"OUTPUT",
				"startNode":response["tx_hash"],
				"endNode":inp["address"],
				"properties":{
					"amount":inp["amount"]
				}
			})

	label = "Cluster" if clusterized else "Address"

	for address in unique_addresses:
		color = "#F79767"

		if(address == query):
			color = "#ff0000"

		graph["nodes"].append({
			"id":address,
			"labels":[label],
			"properties":{
				"value":address
			},
			"color":color
		})
	
	return jsonify(graph)

def convert_result_to_cluster(query,responses):
	responses,unique_addresses = combine_inputs_outputs(responses)

	addresses = {}

	for response in responses:
		tag = ""
		tag_exists = False
		for inp in response["inputs"]:
			address = inp["address"]
			if(address in addresses):
				tag = addresses[address]
				tag_exists = True
				break

		if(tag_exists):
			for inp in response["inputs"]:
				address = inp["address"]
				addresses[address] = tag
		else:
			tag = ''.join(random.choices(string.ascii_uppercase + string.digits, k = 5))
			for inp in response["inputs"]:
				address = inp["address"]
				addresses[address] = tag


		for out in response["outputs"]:
			address = out["address"]
			if(address not in addresses):
				tag = ''.join(random.choices(string.ascii_uppercase + string.digits, k = 5))
				addresses[address] = tag

	try:
		tag_for_query = addresses[query]
	except:
		tag_for_query = ""

	for response in responses:
		for inp in response["inputs"]:
			inp["address"] = addresses[inp["address"]]

		for out in response["outputs"]:
			out["address"] = addresses[out["address"]]

	responses,unique_clusters = combine_inputs_outputs(responses)

	return convert_result_to_json(tag_for_query,responses,True)