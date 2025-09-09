import os
import json
import psycopg2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

PGHOST = os.environ.get("PGHOST", "")
PGPORT = os.environ.get("PGPORT", "")
PGUSER = os.environ.get("PGUSER", "")
PGPASSWORD = os.environ.get("PGPASSWORD", "")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "")

conn = psycopg2.connect(
    dbname=POSTGRES_DB,
    user=PGUSER,
    password=PGPASSWORD,
    host=PGHOST,
    port=PGPORT
)
c = conn.cursor()

@app.get("/", response_class=HTMLResponse)
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ranking Chat Indodax</title>
        <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css"/>
        <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 30px; }
            table.dataTable thead th { font-weight: bold; }
            .btn-history { display:inline-block; margin-bottom:20px; padding:8px 16px; background:#00abff; color:#fff; border:none; border-radius:4px; text-decoration:none;}
            .btn-history:hover { background:#0056b3; }
            .level-0 { color: #000000 !important; }
            .level-1 { color: #CD7F32 !important; }
            .level-2 { color: #FFA500 !important; }
            .level-3 { color: #0000FF !important; }
            .level-4 { color: #00FF00 !important; }
            .level-5 { color: #FF00FF !important; }
            th, td {
                vertical-align: top;
            }
            th:nth-child(1), td:nth-child(1) { width: 10px; min-width: 10px; max-width: 20px; white-space: nowrap; }
            th:nth-child(2), td:nth-child(2) { width: 120px; min-width: 90px; max-width: 150px; white-space: nowrap; }
            th:nth-child(3), td:nth-child(3) { width: 10px; min-width: 10px; max-width: 35px; white-space: nowrap; }
            th:nth-child(4), td:nth-child(4) { width: auto; word-break: break-word; white-space: pre-line; }
            th:nth-child(5), td:nth-child(5) { width: 130px; min-width: 110px; max-width: 150px; white-space: nowrap; }
        </style>
    </head>
    <body>
    <h2>Top Chatroom Indodax</h2>
    <a href="https://cr-indodax.up.railway.app/" class="btn-history">Chat Terkini</a>
    <table id="ranking" class="display" style="width:100%">
        <thead>
        <tr>
            <th>No</th>
            <th>Username</th>
            <th>Total</th>
            <th>Terakhir Chat</th>
            <th>Waktu Chat</th>
        </tr>
        </thead>
        <tbody>
        </tbody>
    </table>
    <p id="periode"></p>
    <script>
        var table = $('#ranking').DataTable({
            "order": [[2, "desc"]],
            "paging": false,
            "info": false,
            "searching": true,
            "language": {
            "emptyTable": "Tidak ada DATA"
            }
        });

        function loadData() {
            $.getJSON("/data", function(data) {
                table.clear();
                if (data.ranking.length === 0) {
                    $("#periode").html("<b>Tidak ada DATA</b>");
                    table.draw();
                    return;
                }
                for (var i = 0; i < data.ranking.length; i++) {
                    var row = data.ranking[i];
                    table.row.add([
                        i+1,
                        `<span class="level-${row.level}">${row.username}</span>`,
                        row.count,
                        `<span class="level-${row.level}">${row.last_content}</span>`,
                        row.last_time
                    ]);
                }
                table.draw();
                $("#periode").html("Periode: <b>" + data.t_awal + "</b> s/d <b>" + data.t_akhir + "</b>");
            });
        }

        loadData();
        setInterval(loadData, 1000); // refresh setiap 1 detik
    </script>
    </body>
    </html>
    """
    return html

def get_db():
    return psycopg2.connect(
        dbname=POSTGRES_DB,
        user=PGUSER,
        password=PGPASSWORD,
        host=PGHOST,
        port=PGPORT
    )

def get_request():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT data FROM request ORDER BY updated_at DESC LIMIT 1")
    row = c.fetchone()
    c.close()
    conn.close()
    if row:
        return row[0]
    return None

@app.get("/data")
def data():
    req = get_request()
    if not req:
        return {"ranking": [], "t_awal": "-", "t_akhir": "-"}
    t_awal = req.get("start", "-")
    t_akhir = req.get("end", "-")
    usernames = [u.lower() for u in req.get("usernames", [])]
    usernames_filter = [u.lower() for u in req.get("usernames", [])]
    mode = req.get("mode", "")
    kata = req.get("kata", None)
    level = req.get("level", None)

    conn = get_db()
    c = conn.cursor()
    query = "SELECT username, content, timestamp_wib, level FROM chat WHERE timestamp_wib >= %s AND timestamp_wib <= %s"
    params = [t_awal, t_akhir]
    if kata:
        query += " AND LOWER(content) LIKE %s"
        params.append(f"%{kata}%")
    if mode == "username" and usernames:
        query += " AND LOWER(username) = ANY(%s)"
        params.append(usernames)
    if mode == "level" and level is not None:
        query += " AND level = %s"
        params.append(level)
    c.execute(query, params)
    rows = c.fetchall()
    c.close()
    conn.close()

    username_map = {}
    user_info = {}
    for row in rows:
        uname = row[0]
        uname_lower = uname.lower()
        content = row[1]
        t_chat = row[2]
        level = row[3]
        if uname_lower not in user_info:
            user_info[uname_lower] = {
                "username": uname,
                "count": 1,
                "last_content": content,
                "last_time": t_chat,
                "level": level
            }
        else:
            user_info[uname_lower]["count"] += 1
            if t_chat > user_info[uname_lower]["last_time"]:
                user_info[uname_lower]["last_content"] = content
                user_info[uname_lower]["last_time"] = t_chat
                user_info[uname_lower]["level"] = level

    if mode == "username" and usernames:
        ranking = []
        for u in usernames_filter:
            if u in user_info:
                ranking.append((user_info[u]["username"], user_info[u]))
            else:
                ranking.append((u, {"username": u, "count": 0, "last_content": "-", "last_time": "-", "level": 0}))
        ranking = sorted(ranking, key=lambda x: x[1]["count"], reverse=True)
    else:
        ranking = sorted([(info["username"], info) for info in user_info.values()], key=lambda x: x[1]["count"], reverse=True)

    data = []
    for user, info in ranking:
        data.append({
            "username": user,
            "count": info["count"],
            "last_content": info["last_content"],
            "last_time": info["last_time"],
            "level": info.get("level", 0)
        })
    return {
        "ranking": data,
        "t_awal": t_awal,
        "t_akhir": t_akhir
    }
