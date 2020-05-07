from pymongo import MongoClient

db = MongoClient("mongodb://localhost:27017")["ba"]

change_stream = db.transactions.watch([{
    '$match': {
        'operationType': "insert"
    }
}])

for change in change_stream:
	new_tx = change["fullDocument"]
	tx_volume = 0

	addresses = set()
	for inp in new_tx["inputs"]:
		addresses.add(inp["address"])

	for output in new_tx["outputs"]:
		addresses.add(output["address"])
		tx_volume += output["amount"]

	monitors = db.monitors.find()
	for monitor in monitors:
		if(monitor["type"] == "address" and addresses.contains(monitor["value"])):
			#add alert
		elif(monitor["type"] == "amount" and tx_volume >= monitor["value"]):
			#add alert
	