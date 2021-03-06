from . import api
from .utils import *
from flask import request,current_app,session
from .track_trace import *
from datetime import datetime
from multiprocessing import Process

def get_monitors(db):
	print(session)
	if session['logged_in']:
		result = db.monitors.find({"user_id":session['id']})
		responses = []
		for row in result:
			response = {}
			response["id"] = row["_id"]
			response["type"] = row["type"]
			response["value"] = row["value"]
			response["count"] = len(row["alerts"])
			responses.append(response)
	else:
		responses = []
	return responses

def get_alerts(db):
	responses = []

	if session['logged_in']:
		collection = db["monitors"]

		result = collection.find({'user_id':session['id']})
		for row in result:
			for alert in row["alerts"]:
				responses.append({"type":row["type"],"value":row["value"],"tx_hash":alert["tx_hash"]})

	return responses

def sync_wrapper(syncer):
	syncer.sync_db()

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
		if current_app.config["db_name"] == "vjcoin":
			print(1)
			datetime_start = datetime.strptime(request.values["start"],"%d-%m-%Y").timestamp()
			datetime_end = datetime.strptime(request.values["end"],"%d-%m-%Y").timestamp()
		else:
			datetime_start = datetime.strptime(request.values["start"],"%d-%m-%Y")
			datetime_end = datetime.strptime(request.values["end"],"%d-%m-%Y")


		date_set = True
	except:
		pass

	if(date_set  and address != ''):
		print('1')
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
	elif(date_set):
		print('2')
		result = db.transactions.find(
				
					{"$and":[{
						"timestamp":{"$gte":datetime_start},
					},
					{
						"timestamp":{"$lte":datetime_end},
					}
					]}
					
				
			).limit(node_limit)
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
		if current_app.config["db_name"] in ["vjcoin","ethereum"]:
			print(1)
			datetime_start = datetime.strptime(request.values["start"],"%d-%m-%Y").timestamp()
			datetime_end = datetime.strptime(request.values["end"],"%d-%m-%Y").timestamp()
		else:
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
		user_id = session["id"]
		doc_id = f"{monitor_type}-{value}"
		doc = {
			"_id":doc_id,
			"type":monitor_type,
			"value":value,
			"alerts":[],
			"user_id":user_id
		}
		collection.insert(doc)
		return jsonify(success=True)

	elif(request.method == "DELETE"):
		collection.remove({"_id":request.values["id"]})
		return jsonify(success=True)

	return jsonify(success=False)

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

@api.route("/refresh",methods=['POST'])
def refresh():
	db_name = current_app.config["db_name"]

	syncer = current_app.config["syncer"][db_name]
	p = Process(target=sync_wrapper,args=(syncer,))
	p.start()

	return jsonify(success=1)


