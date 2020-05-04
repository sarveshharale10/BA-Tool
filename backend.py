from pymongo import MongoClient
from flask import Flask,jsonify, render_template, request, redirect,json
from api import api
from api.routes import get_monitors,get_alerts
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
app.register_blueprint(api)


@app.route("/transaction",methods=['GET'])
def transaction():
	return render_template('search.html')

@app.route("/address",methods=['GET'])
def address():
	return render_template('search.html')

@app.route("/track",methods=['GET'])
def track():
	return render_template('track.html')

@app.route("/trace", methods=['GET'])
def trace():
	return render_template('trace.html')

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
	db = app.config["db"]
	responses = get_alerts(db)
	return render_template("alerts.html",responses=responses)


@app.route("/monitors", methods=['GET'])
def monitors():
	db = app.config["db"]
	responses = get_monitors(db)
	return render_template("monitors.html",responses=responses)

@app.after_request
def add_header(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r

if __name__ == '__main__':
    app.run(debug=True)