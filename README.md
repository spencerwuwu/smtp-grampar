# GramPar's fork of SMTP Garden

(to be completed)

## Install
Build the required docker images
```bash
docker compose build soil
docker compose build echo <servers to test>
```
List of supported MTA / MUA:
- postfix
- msmtp 
- exim 
- opensmtpd 
- nullmailer 
- aiosmtpd 
- james-maildir

For the python interface
```bash
pip install -r requirements-dev.txt
```

## Execute queries
Edit the `servers` to send queries to in **run_echo_query.py** (at the bottom).
Then
```bash
./run_echo_query.py <testcase>
```
Example queries can be found in *testcases/*
