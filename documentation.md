docker desktop is used for monitoring the immages and container and their logs can also be seen from there.

dbeaver is used to monitor the databases -
cred for same -
host = localhost
port = 5432
database = unigpu_db
username = unigpu
password = [unigpu_secret]


frontend login cred - 
username - testclient
password - pass123

username - testprovider
password - pass123

username - testadmin
password - pass123


backend server commands -

command to build app using docker - 
$env:PATH += ";C:\Program Files\Docker\Docker\resources\bin"; docker compose down; docker compose up --build -d

command to build app up using docker - 
$env:PATH += ";C:\Program Files\Docker\Docker\resources\bin"; docker compose down; docker compose up

command to app down using docker - 
docker compose down
