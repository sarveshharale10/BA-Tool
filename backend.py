from pymongo import MongoClient
from flask import Flask,jsonify, render_template, request, redirect
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
db.alerts.aggregate({
"$lookup":{
     from: 'transactions',
     localField: 'tx_hash',
     foreignField: 'tx_hash',
     as: 'details'
}
});
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


@app.route("/transaction",methods=['GET','POST'])
def get_transaction():
	if request.method == 'GET':
		return render_template('search.html')
	tx_hash = request.values['tx_hash']
	cluster = request.values["cluster"]

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

	if(cluster == "true"):
		return convert_result_to_cluster("",responses)
	else:
		return convert_result_to_json("",responses)
	

@app.route("/address",methods=['GET','POST'])
def get_address():
	if request.method == 'GET':
		return render_template('search.html')
	address = request.values['address']
	cluster = request.values["cluster"]

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

	if(cluster == "true"):
		return convert_result_to_cluster(address,responses)
	else:
		return convert_result_to_json(address,responses)


@app.route("/track",methods=['GET','POST'])
def track():
	if request.method == 'GET':
		return render_template('track.html')
	address = request.values['address']
	hop_count = request.values['hop_count']
	cluster = request.values["cluster"]

	db = app.config["db"]
	transactions = db["transactions"]

	tracker = Tracker(transactions)

	result = tracker.track(address,int(hop_count))
	
	responses = []
	for key,value in result.items():
		r = transactions.find({"tx_hash":{"$in":list(value)}})
		for row in r:
			response = {}
			response["tx_hash"] = row["tx_hash"]
			response["timestamp"] = row["timestamp"]
			response["inputs"] = row["inputs"]
			response["outputs"] = row["outputs"]
			response["depth"] = key
			responses.append(response)

	if(cluster == "true"):
		return convert_result_to_cluster(address,responses)
	else:
		return convert_result_to_json(address,responses)

@app.route("/trace", methods=['GET','POST'])
def trace():
	if request.method == 'GET':
		return render_template('trace.html')
	address = request.values['address']
	hop_count = request.values['hop_count']
	cluster = request.values["cluster"]

	db = app.config["db"]
	transactions = db["transactions"]

	tracer = Tracer(transactions)

	result = tracer.trace(address,int(hop_count))
	
	responses = []
	for key,value in result.items():
		r = transactions.find({"tx_hash":{"$in":list(value)}})
		for row in r:
			response = {}
			response["tx_hash"] = row["tx_hash"]
			response["timestamp"] = row["timestamp"]
			response["inputs"] = row["inputs"]
			response["outputs"] = row["outputs"]
			response["depth"] = key
			responses.append(response)

	if(cluster == "true"):
		return convert_result_to_cluster(address,responses)
	else:
		return convert_result_to_json(address,responses)

@app.route("/", methods=['GET'])
def home():
	return redirect("/home")

@app.route("/home", methods=['GET','POST'])
def dashboard():
	return render_template("index.html")

@app.route("/search", methods=['GET'])
def search():
	return render_template("search.html")

@app.route("/alerts", methods=['GET','POST'])
def alert():
	return render_template("alerts.html")

@app.route("/alert_dummy",methods=['GET'])
def alert_dummy():
	db = app.config["db"]
	collection = db["alerts"]

	result = collection.find()
	tx_hashes = []
	for row in result:
		tx_hashes.append(row["tx_hash"])

	result = db.transactions.find({"tx_hash":{"$in":tx_hashes}},{"_id":0,"tx_hash":1}).sort("timestamp",-1)
	return result

@app.route("/monitors_dummy",methods=['GET',"POST","PUT","DELETE"])
def monitors():
	db = app.config["db"]
	collection = db["monitors"]

	if(request.method == "GET"):
		result = collection.find()
		responses = []
		for row in result:
			response = {}
			response["type"] = row["type"]
			response["value"] = row["value"]
			response["count"] = len(row["alerts"])
			responses.append(response)
		return jsonify(responses=responses)

	elif(request.method == "PUT"):
		monitor_type = request.values["type"]
		value = request.values["value"]
		doc_id = f"{monitor_type}-{value}"
		doc = {
			"_id":doc_id,
			"type":monitor_type,
			"value":value
		}
		collection.insert(doc)
		return jsonify(success=True)

	elif(request.method == "POST"):
		doc_id = request.values["id"]
		tx_hash = request.values["tx_hash"]
		collection = db["alerts"]

		collection.insert({"monitor_id":doc_id,"tx_hash":tx_hash})
		return jsonify(success=True)

	elif(request.method == "DELETE"):
		collection.remove({"_id":request.values["id"]})
		return jsonify(success=True)

	return jsonify(success=False)

@app.route("/monitors", methods=['GET','POST'])
def monitor():
	return render_template("monitors.html")


@app.after_request
def add_header(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r

if __name__ == '__main__':
    app.run(debug=True)