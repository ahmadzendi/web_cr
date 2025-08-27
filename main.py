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

@app.get("/data")
def data():
    # 1. Baca filter dari last_request.json
    try:
        with open("last_request.json", "r", encoding="utf-8") as f:
            req = json.load(f)
        t_awal = req.get("start", "-")
        t_akhir = req.get("end", "-")
        usernames = [u.lower() for u in req.get("usernames", [])]
        mode = req.get("mode", "")
        kata = req.get("kata", None)
    except Exception:
        t_awal = "-"
        t_akhir = "-"
        usernames = []
        mode = ""
        kata = None

    # 2. Jika filter tidak ada, return data kosong
    if t_awal == "-" or t_akhir == "-":
        return {
            "ranking": [],
            "t_awal": "-",
            "t_akhir": "-"
        }

    # 3. Query ke database sesuai filter
    conn = get_db()
    c = conn.cursor()
    query = "SELECT username, content, timestamp_wib, level FROM chat WHERE timestamp_wib BETWEEN %s AND %s"
    params = [t_awal, t_akhir]
    if kata:
        query += " AND LOWER(content) LIKE %s"
        params.append(f"%{kata}%")
    if mode == "username" and usernames:
        query += " AND LOWER(username) = ANY(%s)"
        params.append(usernames)
    c.execute(query, params)
    rows = c.fetchall()
    c.close()
    conn.close()

    # 4. Proses hasil query untuk ranking
    user_info = {}
    for row in rows:
        uname = row[0].lower()
        content = row[1]
        t_chat = row[2]
        level = row[3]
        if uname not in user_info:
            user_info[uname] = {
                "count": 1,
                "last_content": content,
                "last_time": t_chat,
                "level": level
            }
        else:
            user_info[uname]["count"] += 1
            # Update last_content dan last_time jika waktu lebih baru
            if t_chat > user_info[uname]["last_time"]:
                user_info[uname]["last_content"] = content
                user_info[uname]["last_time"] = t_chat
                user_info[uname]["level"] = level

    # 5. Urutkan ranking
    if mode == "username" and usernames:
        # Ambil data user yang ada, lalu urutkan dari count terbanyak
        ranking = [(u, user_info[u]) if u in user_info else (u, {"count": 0, "last_content": "-", "last_time": "-", "level": 0}) for u in usernames]
        # Urutkan ranking berdasarkan count (jumlah chat) DESC
        ranking = sorted(ranking, key=lambda x: x[1]["count"], reverse=True)
    else:
        ranking = sorted(user_info.items(), key=lambda x: x[1]["count"], reverse=True)
    # 6. Format output
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
