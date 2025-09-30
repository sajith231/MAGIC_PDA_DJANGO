from django.urls import path
from . import views

from django.shortcuts import render

# Create your views here.
import os
import jwt
import psutil
import subprocess
import sys
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .sql_helper import get_connection, _get_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

PAIR_PASSWORD = os.getenv("PAIR_PASSWORD", "IMC-MOBILE")
JWT_SECRET    = os.getenv("JWT_SECRET")
JWT_ALGO      = os.getenv("JWT_ALGO", "HS256")

# ------------------ JWT helpers ------------------
def _extract_token(request):
    hdr = request.headers.get("Authorization", "")
    if not hdr.startswith("Bearer "):
        return None
    return hdr.split(" ", 1)[1]

def _decode(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])

def jwt_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        token = _extract_token(request)
        if not token:
            return JsonResponse({"detail": "Token missing"}, status=401)
        try:
            payload = _decode(token)
            request.userid = payload["sub"]
        except jwt.PyJWTError as e:
            return JsonResponse({"detail": "Invalid or expired token"}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped

# ------------------ endpoints ------------------
@csrf_exempt
@require_http_methods(["POST"])
def pair_check(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)

    logging.info("📱 Pair check request from: %s", data)

    if data.get("password") != PAIR_PASSWORD:
        logging.error("❌ Invalid password")
        return JsonResponse({"detail": "Invalid password"}, status=401)

    exe_name = "SyncService.exe"
    base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(base_dir, exe_name)

    if not os.path.exists(exe_path):
        logging.error("❌ SyncService.exe not found at %s", exe_path)
        return JsonResponse({"detail": "SyncService.exe not found"}, status=404)

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and "SyncService.exe" in proc.info["name"]:
                logging.info("🔄 SyncService already running (PID %s)", proc.info["pid"])
                return JsonResponse({"status": "success", "message": "SyncService already running", "pair_successful": True})
        except Exception:
            continue

    try:
        subprocess.Popen([exe_path], cwd=base_dir)
        logging.info("✅ SyncService started")
        return JsonResponse({"status": "success", "message": "SyncService launched successfully", "pair_successful": True})
    except Exception as e:
        logging.error("❌ Failed to start SyncService: %s", e)
        return JsonResponse({"detail": f"Failed to start sync service: {e}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    try:
        data = json.loads(request.body)
        userid = data["userid"]
        password = data["password"]
    except Exception:
        return JsonResponse({"detail": "userid & password required"}, status=400)

    logging.info("🔐 Login attempt for user: %s", userid)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, pass FROM acc_users WHERE id = ? AND pass = ?", (userid, password))
    row = cur.fetchone()
    cur.close(); conn.close()

    if not row:
        logging.warning("❌ Invalid credentials")
        return JsonResponse({"detail": "Invalid credentials"}, status=401)

    token = jwt.encode({"sub": userid, "exp": datetime.utcnow() + timedelta(days=7)}, JWT_SECRET, algorithm=JWT_ALGO)
    logging.info("✅ Login successful")
    return JsonResponse({"status": "success", "message": "Login successful", "user_id": row[0], "token": token})

@jwt_required
@require_http_methods(["GET"])
def verify_token(request):
    logging.info("✅ Token verified for user: %s", request.userid)
    return JsonResponse({"status": "success", "userid": request.userid})

@jwt_required
@require_http_methods(["GET"])
def data_download(request):
    logging.info("📥 Data download request")
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT code, name, place FROM acc_master WHERE super_code = 'SUNCR'")
    master_rows = cur.fetchall()
    master_data = [{"code": r[0], "name": r[1], "place": r[2]} for r in master_rows]

    cur.execute("""
        SELECT p.code, p.name, pb.barcode, pb.quantity, pb.salesprice, pb.bmrp, pb.cost
        FROM acc_product p
        LEFT JOIN acc_productbatch pb ON p.code = pb.productcode
    """)
    product_rows = cur.fetchall()
    product_data = [
        {"code": r[0], "name": r[1], "barcode": r[2], "quantity": r[3],
         "salesprice": r[4], "bmrp": r[5], "cost": r[6]} for r in product_rows
    ]
    cur.close(); conn.close()
    logging.info("✅ Downloaded %s masters, %s products", len(master_data), len(product_data))
    return JsonResponse({"status": "success", "master_data": master_data, "product_data": product_data})

# ------------------------------------------------------------------
#  NEW : helper that returns the next PK for acc_purchaseorderdetails
# ------------------------------------------------------------------
# ------------------------------------------------------------------
#  NEW : helper that returns the next PK for acc_purchaseorderdetails
# ------------------------------------------------------------------
# ------------------------------------------------------------------
#  NEW : helper that returns the next PK for acc_purchaseorderdetails
# ------------------------------------------------------------------
# ------------------------------------------------------------------
#  NEW : helper that returns the next PK for acc_purchaseorderdetails
# ------------------------------------------------------------------
# ------------------------------------------------------------------
#  FIXED helper – always returns int
# ------------------------------------------------------------------
def _next_detail_slno(cur):
    cur.execute("SELECT MAX(slno) FROM acc_purchaseorderdetails")
    row = cur.fetchone()[0]
    return int(row or 0) + 1          # ← cast to int


# ------------------------------------------------------------------
#  FINAL upload_orders – accepts flat OR array products
# ------------------------------------------------------------------
@csrf_exempt
@jwt_required
@require_http_methods(["POST"])
def upload_orders(request):
    try:
        payload = json.loads(request.body)
        orders  = payload.get("orders", [])
    except Exception:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)

    if not orders:
        return JsonResponse({"detail": "No orders supplied"}, status=400)

    logging.info("📤 Uploading %s orders", len(orders))
    logging.info("📦 Raw JSON received: %s", payload)

    conn = get_connection()
    cur  = conn.cursor()
    conn.autocommit = False

    try:
        # ---------- before counts ----------
        cur.execute("SELECT COUNT(*) FROM acc_purchaseordermaster WHERE orderdate = TODAY()")
        m_before = int(cur.fetchone()[0])
        cur.execute("""
            SELECT COUNT(*)
            FROM acc_purchaseordermaster po
            JOIN acc_purchaseorderdetails pd ON pd.masterslno = po.slno
            WHERE po.orderdate = TODAY()
        """)
        d_before = int(cur.fetchone()[0])
        logging.info("BEFORE – master today: %s  detail today: %s", m_before, d_before)

        # ---------- master seed ----------
        cur.execute("SELECT MAX(slno) FROM acc_purchaseordermaster")
        max_masterslno = int(cur.fetchone()[0] or 0)

        for idx, order in enumerate(orders, 1):
            max_masterslno += 1
            supplier  = order["supplier_code"]
            orderdate = order["order_date"]
            userid    = order.get("userid") or request.userid
            otype     = order.get("otype", "O")

            # 🔍 fix flat product → array
            products = order.get("products", [])
            if not products:                       # mobile sent flat fields
                products = [{
                    "barcode":  order["barcode"],
                    "quantity": order["quantity"],
                    "rate":     order["rate"],
                    "mrp":      order["mrp"]
                }]
                logging.info("Order #%s – wrapped flat product into array: %s", idx, products)

            # ---- header ----
            cur.execute("""
                INSERT INTO acc_purchaseordermaster
                       (slno, orderno, supplier, otype, userid, orderdate)
                VALUES (?,    ?,       ?,        ?,    ?,      ?)
            """, (max_masterslno, max_masterslno, supplier, otype, userid, orderdate))

            # 🔍 master must exist NOW
            cur.execute("SELECT COUNT(*) FROM acc_purchaseordermaster WHERE slno = ?", (max_masterslno,))
            if int(cur.fetchone()[0]) == 0:
                raise RuntimeError("Master row vanished immediately after insert!")

            # ---- details ----
            for prod in products:
                det_slno = _next_detail_slno(cur)

                qty  = float(prod["quantity"])
                rate = float(prod["rate"])
                mrp  = float(prod["mrp"])

                sql = """
                    INSERT INTO acc_purchaseorderdetails
                           (slno, masterslno, barcode, qty, rate, mrp)
                    VALUES (?,    ?,          ?,       ?,  ?,    ?)
                """
                params = (det_slno, max_masterslno, prod["barcode"], qty, rate, mrp)
                logging.info("EXEC detail sql=%s  params=%s", sql, params)
                cur.execute(sql, params)

                # 🔍 detail must exist NOW
                cur.execute("SELECT COUNT(*) FROM acc_purchaseorderdetails WHERE slno = ?", (det_slno,))
                if int(cur.fetchone()[0]) == 0:
                    raise RuntimeError(f"Detail slno {det_slno} vanished immediately after insert!")

        # ---------- after counts ----------
        cur.execute("SELECT COUNT(*) FROM acc_purchaseordermaster WHERE orderdate = TODAY()")
        m_after = int(cur.fetchone()[0])
        cur.execute("""
            SELECT COUNT(*)
            FROM acc_purchaseordermaster po
            JOIN acc_purchaseorderdetails pd ON pd.masterslno = po.slno
            WHERE po.orderdate = TODAY()
        """)
        d_after = int(cur.fetchone()[0])
        logging.info("AFTER – master today: %s  detail today: %s", m_after, d_after)

        if d_after == d_before:
            raise RuntimeError("Still zero detail rows – nothing was really inserted!")

        # ---------- commit only if everything survived ----------
        conn.commit()
        logging.info("✅ COMMITTED – master today: %s  detail today: %s", m_after, d_after)
        return JsonResponse({"status": "success", "message": "Orders uploaded successfully"})

    except Exception as exc:
        conn.rollback()
        logging.exception("❌ ROLLBACK – %s", exc)
        return JsonResponse({"detail": f"Upload failed: {exc}"}, status=500)

    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass



@require_http_methods(["GET"])
def get_status(request):
    cfg = _get_config()
    primary = cfg.get("ip", "unknown")
    all_ips = cfg.get("all_ips", [])
    return JsonResponse({
        "status": "online",
        "message": "SyncAnywhere server is running",
        "primary_ip": primary,
        "all_available_ips": all_ips,
        "connection_urls": [f"http://{ip}:8000" for ip in all_ips],
        "pair_password_hint": f"Password starts with: {PAIR_PASSWORD[:3]}...",
        "server_time": datetime.now().isoformat(),
        "instructions": {
            "mobile_setup": "Try connecting to any of the URLs listed in 'connection_urls'",
            "troubleshooting": [
                "Ensure both devices are on the same WiFi network",
                "Try each IP address if the first one doesn't work",
                "Check firewall settings on the server computer",
                "Verify port 8000 is not blocked"
            ]
        }
    })





@jwt_required
@require_http_methods(["GET"])
def get_product_details(request):
    """
    Returns combined product details from acc_product and acc_productbatch tables
    joined on code = productcode
    """
    logging.info("📦 Product details request")
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Join both tables on code = productcode
        cur.execute("""
            SELECT 
                p.code,
                p.name,
                p.catagory,
                p.product,
                p.brand,
                p.unit,
                p.taxcode,
                pb.productcode,
                pb.barcode,
                pb.quantity,
                pb.cost,
                pb.bmrp,
                pb.salesprice,
                pb.secondprice,
                pb.thirdprice,
                pb.supplier,
                pb.expirydate
            FROM acc_product p
            LEFT JOIN acc_productbatch pb ON p.code = pb.productcode
            ORDER BY p.code
        """)
        
        rows = cur.fetchall()
        
        # Format the data
        product_details = []
        for row in rows:
            # Handle expirydate - could be date object or string
            expiry = row[16]
            if expiry:
                if hasattr(expiry, 'isoformat'):
                    expiry = expiry.isoformat()
                else:
                    expiry = str(expiry)
            
            product_details.append({
                "code": row[0],
                "name": row[1],
                "catagory": row[2],
                "product": row[3],
                "brand": row[4],
                "unit": row[5],
                "taxcode": row[6],
                "productcode": row[7],
                "barcode": row[8],
                "quantity": float(row[9]) if row[9] is not None else None,
                "cost": float(row[10]) if row[10] is not None else None,
                "bmrp": float(row[11]) if row[11] is not None else None,
                "salesprice": float(row[12]) if row[12] is not None else None,
                "secondprice": float(row[13]) if row[13] is not None else None,
                "thirdprice": float(row[14]) if row[14] is not None else None,
                "supplier": row[15],
                "expirydate": expiry
            })
        
        cur.close()
        conn.close()
        
        logging.info("✅ Retrieved %s product details", len(product_details))
        return JsonResponse({
            "status": "success",
            "count": len(product_details),
            "data": product_details
        })
        
    except Exception as e:
        logging.error("❌ Error fetching product details: %s", e)
        if cur:
            cur.close()
        if conn:
            conn.close()
        return JsonResponse({"detail": f"Failed to fetch product details: {e}"}, status=500)