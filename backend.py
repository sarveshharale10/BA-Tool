from pymongo import MongoClient
from flask import Flask,jsonify, render_template, request, redirect,json
from api import api
from api.routes import get_monitors,get_alerts,top_holders,top_receivers,top_senders
'''
var mapFunction3 = function() {
    this.outputs.forEach(function(item){ emit(item.address,+item.amount); });
	this.inputs.forEach(function(item){ emit(item.address,-item.amount); });
}

var reduceFunction3 = function(address,amounts) {
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
app.config["db_name"] = "ba"
app.config["db"] = MongoClient("mongodb://localhost:27017")["vjcoin"]
app.config["limit"] = 100
app.register_blueprint(api)

@app.route("/settings",methods=['POST'])
def setting():
	# print(request.values)
	db = request.values["db"]
	limit = request.values["limit"]
	app.config["db_name"] = db
	app.config["db"] = MongoClient("mongodb://localhost:27017")[db]
	app.config["limit"] = int(limit)

	return jsonify({'success':1})

@app.route("/test",methods=['GET'])
def test():
	settings = {"db":app.config["db_name"],"limit":app.config["limit"]}
	return render_template('test.html',config=settings)

@app.route("/track",methods=['GET'])
def track():
	settings = {"db":app.config["db_name"],"limit":app.config["limit"]}
	return render_template('track.html',config=settings)

@app.route("/trace", methods=['GET'])
def trace():
	settings = {"db":app.config["db_name"],"limit":app.config["limit"]}
	return render_template('trace.html',config=settings)

@app.route("/", methods=['GET'])
def home():
	return redirect("/home")

@app.route("/home", methods=['GET','POST'])
def dashboard():
	holders = top_holders()
	receivers = top_receivers()
	senders = top_senders()
	settings = {"db":app.config["db_name"],"limit":app.config["limit"]}
	return render_template("index.html",holders=holders,senders=senders,receivers=receivers,config=settings)

@app.route("/search", methods=['GET'])
def search():
	settings = {"db":app.config["db_name"],"limit":app.config["limit"]}
	return render_template("search.html",config=settings)

@app.route("/alerts", methods=['GET','POST'])
def alert():
	settings = {"db":app.config["db_name"],"limit":app.config["limit"]}
	db = app.config["db"]
	responses = get_alerts(db)
	return render_template("alerts.html",responses=responses,config=settings)


@app.route("/monitors", methods=['GET'])
def monitors():
	settings = {"db":app.config["db_name"],"limit":app.config["limit"]}
	db = app.config["db"]
	responses = get_monitors(db)
	return render_template("monitors.html",responses=responses,config=settings)

@app.after_request
def add_header(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5000)
