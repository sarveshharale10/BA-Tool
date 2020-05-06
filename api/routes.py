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
		return convert_result_to_cluster("",responses)
	else:
		return convert_result_to_json("",responses)

@api.route("/address",methods=['POST'])
def address():
	address = request.values['address']
	cluster = request.values["cluster"]

	db = current_app.config["db"]
	transactions = db["transactions"]

	date_set = False
	try:
		datetime_start = datetime.strptime(request.values["start"],"%d %B %Y - %H:%M")
		datetime_end = datetime.strptime(request.values["end"],"%d %B %Y - %H:%M")
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
					})
	else:
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

@api.route("/track",methods=['POST'])
def track():
	address = request.values['address']
	hop_count = request.values['hop_count']
	cluster = request.values["cluster"]

	db = current_app.config["db"]
	transactions = db["transactions"]

	tracker = Tracker(transactions)

	result = tracker.track(address,int(hop_count))

	date_set = False
	try:
		datetime_start = datetime.strptime(request.values["start"],"%d %B %Y - %H:%M")
		datetime_end = datetime.strptime(request.values["end"],"%d %B %Y - %H:%M")
		date_set = True
	except:
		pass
		
	responses = []
	for key,value in result.items():
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
					})
		else:
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

@api.route("/trace", methods=['POST'])
def trace():
	address = request.values['address']
	hop_count = request.values['hop_count']
	cluster = request.values["cluster"]

	db = current_app.config["db"]
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