from pymongo import MongoClient
from flask import Flask,jsonify, render_template
from track_trace import Tracker,Tracer
import string
import random

'''
var mapFunction1 = function() {
    this.inputs.forEach(function(item){ emit(item.address,item.amount); });
}

var reduceFunction1 = function(address,amounts) {
                          return Array.sum(amounts);
                      };
'''

app = Flask(__name__)
app.config["db"] = MongoClient("mongodb://localhost:27017")["ba"]

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

def convert_result_to_json(query,responses):
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

	for address in unique_addresses:
		color = "#F79767"

		if(address == query):
			color = "#ff0000"

		graph["nodes"].append({
			"id":address,
			"labels":["Address"],
			"properties":{
				"value":address
			},
			"color":color
		})
	
	return jsonify(graph)

def convert_result_to_cluster(responses):
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

	for response in responses:
		for inp in response["inputs"]:
			inp["address"] = addresses[inp["address"]]

		for out in response["outputs"]:
			out["address"] = addresses[out["address"]]

	responses,unique_clusters = combine_inputs_outputs(responses)

	return convert_result_to_json("",responses)


@app.route("/transaction/<tx_hash>",methods=['GET'])
def get_transaction(tx_hash):
	db = app.config["db"]
	transactions = db["transactions"]

	result = transactions.find({"tx_hash":tx_hash})
	responses = []
	for row in result:
		response = {}
		response["tx_hash"] = row["tx_hash"]
		response["timestamp"] = row["timestamp"]
		response["inputs"] = row["inputs"]
		response["outputs"] = row["outputs"]
		responses.append(response)

	return convert_result_to_json(responses)

	

@app.route("/address/<address>",methods=['GET'])
def get_address(address):
	db = app.config["db"]
	transactions = db["transactions"]

	result = transactions.find({"$or":[{"outputs":{"$elemMatch":{"address":address}}},{"inputs":{"$elemMatch":{"address":address}}}]});
	responses = []
	for row in result:
		response = {}
		response["tx_hash"] = row["tx_hash"]
		response["timestamp"] = row["timestamp"]
		response["inputs"] = row["inputs"]
		response["outputs"] = row["outputs"]
		responses.append(response)

	return convert_result_to_json(responses)

@app.route("/track/<address>/<hop_count>",methods=['GET'])
def track(address,hop_count):
	db = app.config["db"]
	transactions = db["transactions"]

	tracker = Tracker(transactions)

	result = tracker.track(address,int(hop_count))
	
	responses = []
	for key,value in result.items():
		for v in value:
			r = transactions.find({"tx_hash":v})
			for row in r:
				response = {}
				response["tx_hash"] = row["tx_hash"]
				response["timestamp"] = row["timestamp"]
				response["inputs"] = row["inputs"]
				response["outputs"] = row["outputs"]
				response["depth"] = key
				responses.append(response)

	return convert_result_to_json(address,responses)

@app.route("/trace/<address>/<hop_count>",methods=['GET'])
def trace(address,hop_count):
	db = app.config["db"]
	transactions = db["transactions"]

	tracer = Tracer(transactions)

	result = tracer.trace(address,int(hop_count))
	
	responses = []
	for key,value in result.items():
		for v in value:
			r = transactions.find({"tx_hash":v})
			for row in r:
				response = {}
				response["tx_hash"] = row["tx_hash"]
				response["timestamp"] = row["timestamp"]
				response["inputs"] = row["inputs"]
				response["outputs"] = row["outputs"]
				response["depth"] = key
				responses.append(response)

	return convert_result_to_json(address,responses)
@app.route("/", methods=['GET'])
def home():
	return render_template("index.html")

@app.after_request
def add_header(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r

if __name__ == '__main__':
    app.run(debug=True)


#transactions.find({$or:[{"outputs":{$elemMatch:{"address":"1FijBR5s3EU1JS3UokzTZbkAibgL4SXzxm"}}},{"inputs":{$elemMatch:{"address":"1FijBR5s3EU1JS3UokzTZbkAibgL4SXzxm"}}}]}).count();