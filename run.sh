# gunicorn backend:app -b localhost:5000 -w 4

sudo /usr/bin/mongod --dbpath /var/lib/mongodb --replSet "rs0" --bind_ip localhost
