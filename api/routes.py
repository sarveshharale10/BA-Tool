from . import api
from .utils import *
from flask import request,current_app
from .track_trace import *
from datetime import datetime

def get_monitors(db):
	result = db.monitors.find()
	responses = []
	for row in result:
		response = {}
		response["id"] = row["_id"]
		response["type"] = row["type"]
		response["value"] = row["value"]
		response["count"] = len(row["alerts"])
		responses.append(response)
	return responses

def get_alerts(db):
	collection = db["monitors"]

	result = collection.find()
	responses = []
	for row in result:
		for alert in row["alerts"]:
			responses.append({"type":row["type"],"value":row["value"],"tx_hash":alert})

	return responses

@api.route("/transaction",methods=['POST'])
def get_transaction():
	tx_hash = request.values['tx_hash']
	cluster = request.values["cluster"]

	db = current_app.config["db"]
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
		graph = convert_result_to_cluster("",responses)
	else:
		graph = convert_result_to_json("",responses)
	return jsonify(graph)

@api.route("/address",methods=['POST'])
def address():
	address = request.values['address']
	cluster = request.values["cluster"]

	db = current_app.config["db"]
	node_limit = current_app.config["limit"]
	transactions = db["transactions"]

	date_set = False
	try:
		datetime_start = datetime.strptime(request.values["start"],"%d-%m-%Y")
		datetime_end = datetime.strptime(request.values["end"],"%d-%m-%Y")
		date_set = True
	except:
		pass

	if(date_set):
		result = db.transactions.find({
						"$and":[
							{"$and":[{
								"timestamp":{"$gte":datetime_start},
							},
							{
								"timestamp":{"$lte":datetime_end},
							}
							]},
							{"$or":[{
								"outputs":{"$elemMatch":{"address":address}}
							},
							{
								"inputs":{"$elemMatch":{"address":address}}
							}]}
						]
					}).limit(node_limit)
	else:
		result = transactions.find({"$or":[{"outputs":{"$elemMatch":{"address":address}}},{"inputs":{"$elemMatch":{"address":address}}}]}).limit(node_limit)
	responses = []
	total_count = result.count()
	for row in result:
		response = {}
		response["tx_hash"] = row["tx_hash"]
		response["timestamp"] = row["timestamp"]
		response["inputs"] = row["inputs"]
		response["outputs"] = row["outputs"]
		responses.append(response)

	if(cluster == "true"):
		graph = convert_result_to_cluster(address,responses)
	else:
		graph = convert_result_to_json(address,responses)

	graph["actual_tx_count"] = total_count
	graph["received_tx_count"] = len([1 for x in graph["nodes"] if x["labels"][0] == "Transaction"])

	return jsonify(graph)

@api.route("/track",methods=['POST'])
@api.route("/trace",methods=['POST'])
def track_trace():
	
	address = request.values['address']
	hop_count = request.values['hop_count']
	cluster = request.values["cluster"]

	db = current_app.config["db"]
	transactions = db["transactions"]

	operation = request.path.split("/")[-1]
	if(operation == "track"):
		finder = Tracker(transactions)
	elif(operation == "trace"):
		finder = Tracer(transactions)

	result = finder.find(address,int(hop_count))

	date_set = False
	try:
		datetime_start = datetime.strptime(request.values["start"],"%d-%m-%Y")
		datetime_end = datetime.strptime(request.values["end"],"%d-%m-%Y")
		date_set = True
	except Exception as e:
		pass
		
	responses = []
	node_limit = int(current_app.config["limit"] / int(hop_count))
	total_count = 0
	for key,value in result.items():
		total_count += len(value)
		if(date_set):
			r = db.transactions.find({
						"$and":[{
							"tx_hash":{"$in":list(value)}
							},
							{
								"timestamp":{"$gte":datetime_start},
							},
							{
								"timestamp":{"$lte":datetime_end},
							}
						]
					}).limit(node_limit)
		else:
			r = transactions.find({"tx_hash":{"$in":list(value)}}).limit(node_limit)
		
		for row in r:
			response = {}
			response["tx_hash"] = row["tx_hash"]
			response["timestamp"] = row["timestamp"]
			response["inputs"] = row["inputs"]
			response["outputs"] = row["outputs"]
			response["depth"] = key
			responses.append(response)

	if(cluster == "true"):
		graph = convert_result_to_cluster(address,responses)
	else:
		graph = convert_result_to_json(address,responses)

	graph["actual_tx_count"] = total_count
	graph["received_tx_count"] = len([1 for x in graph["nodes"] if x["labels"][0] == "Transaction"])
	return jsonify(graph)

@api.route("/monitors",methods=['GET',"POST","DELETE"])
def monitors():
	db = current_app.config["db"]
	collection = db["monitors"]

	if(request.method == "GET"):
		return jsonify(responses=get_monitors(collection))

	elif(request.method == "POST"):
		monitor_type = request.values["type"]
		value = request.values["value"]
		doc_id = f"{monitor_type}-{value}"
		doc = {
			"_id":doc_id,
			"type":monitor_type,
			"value":value,
			"alerts":[]
		}
		collection.insert(doc)
		return jsonify(success=True)

	elif(request.method == "DELETE"):
		collection.remove({"_id":request.values["id"]})
		return jsonify(success=True)

	return jsonify(success=False)

@api.route("/alert_dummy",methods=['GET'])
def alert_dummy():

	if(request.method == "POST"):
		doc_id = request.values["id"]
		tx_hash = request.values["tx_hash"]

		collection.update({"_id":doc_id},{"$push":{"alerts":tx_hash}})
		return jsonify(success=True)

	return tx_hashes

@api.route("/top_holders",methods=['GET'])
def top_holders():
	db = current_app.config["db"]
	collection = db["top_holders"]
	result = collection.find().sort("value",-1).limit(10);
	responses = []
	for index,row in enumerate(result):
		response = {}
		response["rank"] = index + 1
		response["address"] = row["_id"]
		response["amount"] = row["value"]
		responses.append(response)
	return responses

@api.route("/top_receivers",methods=['GET'])
def top_receivers():
	db = current_app.config["db"]
	collection = db["top_receivers"]
	result = collection.find().sort("value",-1).limit(10);
	responses = []
	for index,row in enumerate(result):
		response = {}
		response["rank"] = index + 1
		response["address"] = row["_id"]
		response["amount"] = row["value"]
		responses.append(response)
	return responses

@api.route("/top_senders",methods=['GET'])
def top_senders():
	db = current_app.config["db"]
	collection = db["top_senders"]
	result = collection.find().sort("value",-1).limit(10);
	responses = []
	for index,row in enumerate(result):
		response = {}
		response["rank"] = index + 1
		response["address"] = row["_id"]
		response["amount"] = row["value"]
		responses.append(response)
	return responses

