from pymongo import MongoClient
from datetime import datetime

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
		if((monitor["type"] == "address" and addresses.contains(monitor["value"])) or (monitor["type"] == "amount" and tx_volume >= monitor["value"])):
			db.monitors.update({"_id":monitor["id"]},{"$push":{"alerts":{"tx_hash":new_tx["tx_hash"],"timestamp":datetime.now()}}})

	