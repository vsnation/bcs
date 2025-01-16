# BEAM Funding System

A simple Flask application for managing donations.

Example
-------

[https://funding.beam.mw](funding.beam.mw)

## Installation

Good luck with trying to get this to run! Some pointers:

Make sure you have a machine with about 50GB of space.

### Install postgres
```
sudo apt install aptitude
sudo aptitude install postgresql postgresql-contrib
```
https://tecadmin.net/how-to-install-postgresql-in-ubuntu-20-04/


### Web application

Download application and configure.

```

sudo apt install libjpeg-dev libpng-dev python3 redis-server postgresql-server-dev-*
sudo apt install python3-virtualenv
sudo apt install python3-venv
git clone https://github.com/BeamMW/bcs.git
cd bcs
python3 -m venv venv
source venv/bin/activate
pip uninstall pillow
pip install wheel
pip install -r requirements.txt
CC="cc -mavx2" pip install -U --force-reinstall pillow-simd
cp settings.py_example settings.py
- change settings.py accordingly
```
eg change the psql_pass to your database password, psql_db to your database name

Run the application:

```bash
python run_dev.py
```

Beware `run_dev.py` is meant as a development server.

When running behind nginx/apache, inject `X-Forwarded-For`.

### Setting Up Admins
go into your postgres user then
```
// substitute postgres with whatever username you set up in the postgres step
sudo su - postgres
psql
```

select your database
```
\dt
\c yourdatabasename
```

find the user_id of the user you want to turn into an admin, then do:
```
SELECT * FROM users;
UPDATE users SET admin = TRUE WHERE user_id = your_number;
```
### Contributors

- [vsnation](https://github.com/vsnation)

### License

© 2022 WTFPL – Do What the Fuck You Want to Public License
