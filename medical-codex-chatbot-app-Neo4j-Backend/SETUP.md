# SETUP (WSL + Neo4j + Python venv)

This guide sets up **Neo4j Community** inside **WSL2 (Ubuntu)**, exposes the Neo4j Browser to your Windows browser, and installs Python deps in a virtual environment using your `requirements.txt`.

> All commands run **inside WSL** unless explicitly noted. Tested on Ubuntu 22.04+.

---

## 1) Prereqs

* Windows 10/11 with **WSL2** and an Ubuntu distro installed.
* Verify tools in WSL:

  ```bash
  python3 --version
  pip3 --version
  ```

---

## 2) Install Neo4j (inside WSL)

Add Neo4j’s APT repo and install the server (Java is included):

```bash
# Add key & repo
sudo mkdir -p /usr/share/keyrings
curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key \
  | sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg

echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable latest" \
  | sudo tee /etc/apt/sources.list.d/neo4j.list

sudo apt update
sudo apt install -y neo4j
```

Set the initial password (first time only):

```bash
# default user is 'neo4j'
sudo neo4j-admin dbms set-initial-password "password"   # change later!
```

Start and enable the service:

```bash
sudo systemctl enable --now neo4j
sudo systemctl status neo4j --no-pager
```

---

## 3) Make the web UI reachable from Windows

Edit the Neo4j config:

```bash
sudo vim /etc/neo4j/neo4j.conf
```

Ensure these lines exist **once each** (no duplicates):

```
server.default_listen_address=0.0.0.0
server.http.listen_address=:7474
server.bolt.listen_address=:7687
server.http.enabled=true
```

Restart Neo4j:

```bash
sudo systemctl restart neo4j
```

Open the Browser in Windows: **[http://localhost:7474/](http://localhost:7474/)**

Use these connection details in the UI:

* **Connect URL**: `bolt://localhost:7687`
* **User**: `neo4j`
* **Password**: `password`  *(change later)*

> If `localhost` doesn’t work, find your WSL IP:
>
> ```bash
> ip -4 addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'
> ```
>
> then open `http://<that-ip>:7474/` in Windows.

---

## 4) Sanity checks (inside WSL)

```bash
# Should return "ok"
cypher-shell -u neo4j -p password 'RETURN 1 AS ok;'

# Verify listening ports
ss -lntp | grep -E '(:7474|:7687)'

# Logs if something fails
sudo journalctl -u neo4j -f
sudo tail -n 200 /var/log/neo4j/debug.log
```

---

## 5) Start / Stop / Restart Neo4j (inside WSL)

```bash
sudo systemctl start neo4j
sudo systemctl stop neo4j
sudo systemctl restart neo4j
sudo systemctl status neo4j --no-pager
```

---

## 6) Python virtualenv + requirements

Your Python code and `requirements.txt` live in **`backend/data-import/`**.

From the repo root (inside WSL):

```bash
cd backend/data-import

# Create & activate venv
python3 -m venv .venv
source .venv/bin/activate

# (optional) upgrade pip
pip install --upgrade pip

# Install project deps
pip install -r requirements.txt
```

When you’re done working:

```bash
deactivate
```

> There’s an example script at **`backend/data-import/neo4j_demo.py`** you can run after activating the venv.

---

## 7) Viewing the database on your host browser

After running `neo4j console` on your host machine you can execute the scripts in WSL and then view the resulting graph database on your host machine like so:

```bash
hostname -I | awk '{print $1}'
neo4j://<WSL_IP>:7687
```

---

## 8) Issues/FAQ I ran into

* **Browser won’t load at `http://localhost:7474`**

  * Ensure the service is running: `sudo systemctl status neo4j`.

* **Python “Connection refused”**

  * Neo4j isn’t running or port differs. Verify with:

    ```bash
    cypher-shell -u neo4j -p password 'RETURN 1;'
    ss -lntp | grep -E '(:7474|:7687)'
    ```

* **Change/reset the password**

  * While DB is running:

    ```bash
    cypher-shell -u neo4j -p current 'ALTER CURRENT USER SET PASSWORD FROM "current" TO "newpass"'
    ```
  * Before first start / while stopped:

    ```bash
    sudo neo4j-admin dbms set-initial-password "newpass"
    ```
