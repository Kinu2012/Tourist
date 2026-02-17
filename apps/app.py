from flask import Flask, request, jsonify, session, send_from_directory, redirect
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import secrets
from flask_mail import Mail, Message
import requests
import json
from typing import Dict, List
import random

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import math

from functools import wraps

def login_required(f):
    """ログイン必須デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/'), 401
        return f(*args, **kwargs)
    return decorated_function

# 環境変数の読み込み
load_dotenv()
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# ベースディレクトリ（C:\travel）を取得
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 近畿各県の出発地データ
DEPARTURE_POINTS_BY_PREFECTURE = {
    'osaka': {
        'name': '大阪府',
        'train': [
            {'id': 'osaka_umeda', 'name': '梅田駅', 'lat': 34.7024, 'lon': 135.4959},
            {'id': 'osaka_namba', 'name': '難波駅', 'lat': 34.6658, 'lon': 135.5010},
            {'id': 'osaka_tennoji', 'name': '天王寺駅', 'lat': 34.6460, 'lon': 135.5140},
        ]
    },
    'kyoto': {
        'name': '京都府',
        'train': [
            {'id': 'kyoto_station', 'name': '京都駅', 'lat': 34.9859, 'lon': 135.7581},
            {'id': 'kawaramachi', 'name': '河原町駅', 'lat': 35.0040, 'lon': 135.7689},
            {'id': 'yamashina', 'name': '山科駅', 'lat': 34.9667, 'lon': 135.8167},
        ],
        'car': [
            {'id': 'kyoto_minami_ic', 'name': '京都南IC', 'lat': 34.9523, 'lon': 135.7503},
            {'id': 'kyoto_higashi_ic', 'name': '京都東IC', 'lat': 35.0147, 'lon': 135.8253},
            {'id': 'oeyama_ic', 'name': '大枝山IC', 'lat': 34.9680, 'lon': 135.6850},
        ]
    },
    'hyogo': {
        'name': '兵庫県',
        'train': [
            {'id': 'kobe_sannomiya', 'name': '三宮駅', 'lat': 34.6951, 'lon': 135.1955},
            {'id': 'himeji_station', 'name': '姫路駅', 'lat': 34.8273, 'lon': 134.6914},
            {'id': 'amagasaki', 'name': '尼崎駅', 'lat': 34.7200, 'lon': 135.4150},
        ],
        'car': [
            {'id': 'nishinomiya_ic', 'name': '西宮IC', 'lat': 34.7530, 'lon': 135.3450},
            {'id': 'kobe_nagata_ic', 'name': '神戸長田IC', 'lat': 34.6580, 'lon': 135.1520},
            {'id': 'himeji_ic', 'name': '姫路IC', 'lat': 34.8520, 'lon': 134.6280},
        ]
    },
    'nara': {
        'name': '奈良県',
        'train': [
            {'id': 'nara_station', 'name': '奈良駅', 'lat': 34.6812, 'lon': 135.8201},
            {'id': 'kintetsu_nara', 'name': '近鉄奈良駅', 'lat': 34.6825, 'lon': 135.8305},
            {'id': 'yamato_saidaiji', 'name': '大和西大寺駅', 'lat': 34.6917, 'lon': 135.7814},
        ],
        'car': [
            {'id': 'tenri_ic', 'name': '天理IC', 'lat': 34.5967, 'lon': 135.8380},
            {'id': 'koriyama_ic', 'name': '郡山IC', 'lat': 34.6480, 'lon': 135.7650},
            {'id': 'kashihara_ic', 'name': '橿原IC', 'lat': 34.5080, 'lon': 135.7620},
        ]
    },
    'shiga': {
        'name': '滋賀県',
        'train': [
            {'id': 'otsu_station', 'name': '大津駅', 'lat': 35.0041, 'lon': 135.8671},
            {'id': 'kusatsu_station', 'name': '草津駅', 'lat': 35.0168, 'lon': 135.9597},
            {'id': 'hikone_station', 'name': '彦根駅', 'lat': 35.2760, 'lon': 136.2590},
        ],
        'car': [
            {'id': 'seta_higashi_ic', 'name': '瀬田東IC', 'lat': 35.0180, 'lon': 135.9280},
            {'id': 'ryuo_ic', 'name': '竜王IC', 'lat': 35.1050, 'lon': 136.1350},
            {'id': 'maibara_ic', 'name': '米原IC', 'lat': 35.3150, 'lon': 136.3080},
        ]
    },
    'wakayama': {
        'name': '和歌山県',
        'train': [
            {'id': 'wakayama_station', 'name': '和歌山駅', 'lat': 34.2330, 'lon': 135.1880},
            {'id': 'wakayamashi_station', 'name': '和歌山市駅', 'lat': 34.2270, 'lon': 135.1710},
            {'id': 'hashimoto_station', 'name': '橋本駅', 'lat': 34.3150, 'lon': 135.6020},
        ],
        'car': [
            {'id': 'wakayama_ic', 'name': '和歌山IC', 'lat': 34.2620, 'lon': 135.2180},
            {'id': 'kainan_ic', 'name': '海南IC', 'lat': 34.1580, 'lon': 135.1980},
            {'id': 'gobo_ic', 'name': '御坊IC', 'lat': 33.8950, 'lon': 135.1650},
        ]
    }
}

#住所逆算
import time

def reverse_geocode(lat, lon):
    """座標から住所を取得（Nominatim API）- 郵便番号・番地付き"""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        'format': 'json',
        'lat': lat,
        'lon': lon,
        'addressdetails': 1,
        'accept-language': 'ja'
    }
    headers = {'User-Agent': 'TravelPlanApp/1.0 (Contact: your@email.com)'}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return '住所情報なし'
        
        data = response.json()
        addr = data.get('address', {})
        
        # 住所パーツを構築
        parts = []
        
        # 郵便番号（あれば）
        postcode = addr.get('postcode')
        if postcode:
            parts.append(f"〒{postcode} ")
        
        # 都道府県
        prefecture = addr.get('province') or addr.get('state')
        if prefecture:
            parts.append(prefecture)
        
        # 市区町村
        city = addr.get('city') or addr.get('town') or addr.get('village')
        if city:
            parts.append(city)
        
        # 区・町・丁目
        suburb = addr.get('suburb') or addr.get('neighbourhood') or addr.get('quarter')
        if suburb:
            parts.append(suburb)
        
        # 番地（house_number）
        house_number = addr.get('house_number')
        if house_number:
            parts.append(house_number)
        
        # roadは除外（道路名は不要）
        
        address = ''.join(parts)
        return address if address else '住所情報なし'
        
    except Exception as e:
        print(f"逆ジオコーディングエラー ({lat}, {lon}): {e}")
        return '住所情報なし'




# デバッグ用の出力
import sys
print("="*60, file=sys.stderr)
print(f"🔍 現在のディレクトリ: {CURRENT_DIR}", file=sys.stderr)
print(f"🔍 ベースディレクトリ: {BASE_DIR}", file=sys.stderr)

TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

print(f"🔍 テンプレートディレクトリ: {TEMPLATES_DIR}", file=sys.stderr)
print(f"🔍 存在チェック: {os.path.exists(TEMPLATES_DIR)}", file=sys.stderr)

if os.path.exists(TEMPLATES_DIR):
    print(f"📂 テンプレートファイル:", file=sys.stderr)
    try:
        for file in os.listdir(TEMPLATES_DIR):
            print(f"  - {file}", file=sys.stderr)
    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
else:
    print(f"❌ テンプレートディレクトリが見つかりません！", file=sys.stderr)
print("="*60, file=sys.stderr)

app = Flask(__name__, 
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)

# ★★★ これを修正 ★★★
_secret_key = os.getenv('SECRET_KEY')
if not _secret_key:
    raise RuntimeError('環境変数 SECRET_KEY が設定されていません。.env ファイルを確認してください。')
app.secret_key = _secret_key
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

# セッションCookie設定を追加
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # 開発環境用
app.config['SESSION_COOKIE_HTTPONLY'] = True

# CORS設定（1回だけ！）
CORS(app, 
     resources={r"/api/*": {"origins": "*"}},
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# データベース接続設定
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError('環境変数 DATABASE_URL が設定されていません。.env ファイルを確認してください。')

def get_db_connection():
    """データベース接続を取得"""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"データベース接続エラー: {e}")
        return None



def get_cache_from_db(cache_key: str):
    """キャッシュをデータベースから取得"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
            
        cursor = conn.cursor()
        
        # 有効期限内のキャッシュを取得
        cursor.execute("""
            SELECT spots_json, created_at 
            FROM spot_cache 
            WHERE cache_key = %s AND expires_at > NOW()
        """, (cache_key,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            cache_age = datetime.now() - result['created_at']
            print(f"✅ DBキャッシュヒット: {cache_key} (経過時間: {cache_age})")
            return json.loads(result['spots_json'])
        else:
            print(f"🔍 DBキャッシュなし: {cache_key}")
            return None
            
    except Exception as e:
        print(f"❌ キャッシュ取得エラー: {e}")
        return None


def save_cache_to_db(cache_key: str, spots: List[Dict], prefecture: str, categories: List[str]):
    """キャッシュをデータベースに保存"""
    try:
        conn = get_db_connection()
        if not conn:
            return
            
        cursor = conn.cursor()
        
        spots_json = json.dumps(spots, ensure_ascii=False)
        expires_at = datetime.now() + timedelta(hours=6)  # 6時間後に期限切れ
        categories_str = ','.join(categories)
        
        cursor.execute("""
            INSERT INTO spot_cache (cache_key, spots_json, prefecture, categories, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (cache_key) 
            DO UPDATE SET 
                spots_json = EXCLUDED.spots_json,
                created_at = CURRENT_TIMESTAMP,
                expires_at = EXCLUDED.expires_at
        """, (cache_key, spots_json, prefecture, categories_str, expires_at))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"💾 DBキャッシュ保存: {cache_key} ({len(spots)}件) - 期限: {expires_at.strftime('%H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ キャッシュ保存エラー: {e}")


def generate_cache_key(prefecture_key: str, categories: List[str]) -> str:
    """キャッシュのキーを生成"""
    categories_sorted = sorted(categories)
    return f"{prefecture_key}_{'-'.join(categories_sorted)}"


def cleanup_expired_cache():
    """期限切れキャッシュを削除（オプション：定期実行用）"""
    try:
        conn = get_db_connection()
        if not conn:
            return
            
        cursor = conn.cursor()
        cursor.execute("DELETE FROM spot_cache WHERE expires_at < NOW()")
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if deleted_count > 0:
            print(f"🗑️ 期限切れキャッシュを{deleted_count}件削除")
            
    except Exception as e:
        print(f"❌ キャッシュ削除エラー: {e}")      

def calculate_age(birthdate_str):
    """生年月日から年齢を計算（バリデーション付き）

    Returns:
        int: 年齢
        None: birthdate_str が空の場合
    Raises:
        ValueError: 日付が不正（未来・150年超・13歳未満）の場合
    """
    if not birthdate_str:
        return None

    try:
        birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError('生年月日の形式が正しくありません（YYYY-MM-DD）')

    today = datetime.now()

    # 未来日付チェック
    if birthdate.date() >= today.date():
        raise ValueError('生年月日に未来の日付は入力できません')

    # 年齢計算
    age = today.year - birthdate.year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        age -= 1

    # 上限チェック（150歳超は入力ミスとみなす）
    if age > 150:
        raise ValueError('有効な生年月日を入力してください')

    # 最低年齢チェック（13歳未満）
    if age < 13:
        raise ValueError('このサービスは13歳以上の方のみご利用いただけます')

    return age

@app.route('/<path:path>')
def serve_static(path):
    """静的ファイルを配信"""
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), path)


@app.route('/')
def index():
    """ログインページを表示"""
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'login.html')


@app.route('/api/login', methods=['POST'])
def login():
    """ログイン"""
    print("=== ログインリクエスト受信 ===")
    data = request.get_json()
    # セキュリティ: パスワードはログに出力しない
    print(f"ログイン試行: {data.get('email')}")
    
    email = data.get('email')
    password = data.get('password')
    
    # バリデーション
    if not email or not password:
        return jsonify({'success': False, 'message': 'メールアドレスとパスワードを入力してください'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        # ユーザー検索
        cur.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        
        if not user:
            return jsonify({'success': False, 'message': 'メールアドレスまたはパスワードが正しくありません'}), 401
        
        # パスワード検証
        if not check_password_hash(user['password'], password):
            return jsonify({'success': False, 'message': 'メールアドレスまたはパスワードが正しくありません'}), 401
        
        # セッションにユーザー情報を保存
        session.permanent = True
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        
        # 最終ログイン時刻を更新
        cur.execute('UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = %s', (user['id'],))
        conn.commit()
        
        print(f"ログイン成功: {user['email']}")
        
        return jsonify({
            'success': True,
            'message': 'ログインに成功しました',
            'user': {
                'id': user['id'],
                'user_id': user['user_id'],
                'name': user['name'],
                'email': user['email'],
                'age': user['age']
            }
        }), 200
        
    except Exception as e:
        print(f"ログインエラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラーが発生しました'}), 500
    finally:
        cur.close()
        conn.close()





# API エンドポイント
@app.route('/api/register', methods=['POST'])
def register():
    """ユーザー登録"""
    print("=== 登録リクエスト受信 ===")
    data = request.get_json()
    # セキュリティ: パスワードはログに出力しない
    safe_data = {k: v for k, v in data.items() if k != 'password'}
    print(f"受信データ: {safe_data}")
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    birthdate = data.get('birthdate')
    gender = data.get('gender')
    
    # バリデーション
    if not username or not email or not password:
        return jsonify({'success': False, 'message': '必須項目を入力してください'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        # メールアドレスの重複チェック
        cur.execute('SELECT * FROM users WHERE email = %s', (email,))
        if cur.fetchone():
            return jsonify({'success': False, 'message': 'このメールアドレスは既に登録されています'}), 400
        
        # ユーザーIDの重複チェック
        cur.execute('SELECT * FROM users WHERE user_id = %s', (username,))
        if cur.fetchone():
            return jsonify({'success': False, 'message': 'このユーザー名は既に使用されています'}), 400
        
        # パスワードのハッシュ化
        hashed_password = generate_password_hash(password)

        # 年齢計算（バリデーション込み）
        try:
            age = calculate_age(birthdate)
        except ValueError as e:
            return jsonify({'success': False, 'message': str(e)}), 400

        # ユーザー登録
        cur.execute(
            '''INSERT INTO users (user_id, password, name, email, age, created_at, updated_at) 
               VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) 
               RETURNING id, user_id, name, email, age, created_at''',
            (username, hashed_password, username, email, age)
        )
        
        user = cur.fetchone()
        conn.commit()
        
        print(f"登録成功: {user}")
        
        return jsonify({
            'success': True,
            'message': '登録が完了しました',
            'user': {
                'id': user['id'],
                'user_id': user['user_id'],
                'name': user['name'],
                'email': user['email'],
                'age': user['age']
            }
        }), 201
        
    except Exception as e:
        conn.rollback()
        print(f"登録エラー: {e}")
        return jsonify({'success': False, 'message': f'サーバーエラーが発生しました: {str(e)}'}), 500
    finally:
        cur.close()
        conn.close()



#パスワードリセット
########################################################################################################
########################################################################################################

@app.route('/api/reset-password', methods=['POST'])
@app.route('/api/password/reset', methods=['POST'])  # reset-password.html との互換性のため
def reset_password():
    """パスワードリセット"""
    print("=== パスワードリセットリクエスト受信 ===")
    data = request.get_json()
    
    token = data.get('token')
    # reset-password.html は new_password を送信するが、後方互換性のため newPassword も受け付ける
    new_password = data.get('new_password') or data.get('newPassword')
    
    # バリデーション
    if not token or not new_password:
        return jsonify({'success': False, 'message': '必須項目を入力してください'}), 400
    
    if len(new_password) < 8:
        return jsonify({'success': False, 'message': 'パスワードは8文字以上で入力してください'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        # トークンを検索（有効期限内、未使用）
        cur.execute(
            '''SELECT prt.*, u.email 
               FROM password_reset_tokens prt
               JOIN users u ON prt.user_id = u.id
               WHERE prt.token = %s 
               AND prt.expires_at > CURRENT_TIMESTAMP 
               AND prt.used = FALSE''',
            (token,)
        )
        
        token_data = cur.fetchone()
        
        if not token_data:
            return jsonify({
                'success': False, 
                'message': '無効または期限切れのトークンです'
            }), 400
        
        user_id = token_data['user_id']
        
        # パスワードをハッシュ化
        hashed_password = generate_password_hash(new_password)
        
        # パスワードを更新
        cur.execute(
            'UPDATE users SET password = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s',
            (hashed_password, user_id)
        )
        
        # トークンを使用済みにする
        cur.execute(
            'UPDATE password_reset_tokens SET used = TRUE WHERE token = %s',
            (token,)
        )
        
        conn.commit()
        
        print(f"パスワードリセット成功: {token_data['email']}")
        
        return jsonify({
            'success': True,
            'message': 'パスワードが正常に変更されました'
        }), 200
        
    except Exception as e:
        conn.rollback()
        print(f"パスワードリセットエラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラーが発生しました'}), 500
    finally:
        cur.close()
        conn.close()

# forgot-passwordエンドポイント内で使用
@app.route('/api/forgot-password', methods=['POST'])
@app.route('/api/request-password-reset', methods=['POST'])  # password-reset.html との互換性のため
def forgot_password():
    """パスワード復元リクエスト"""
    print("=== パスワード復元リクエスト受信 ===")
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'メールアドレスを入力してください'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        # ユーザー検索
        cur.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        
        if not user:
            print(f"ユーザーが見つかりません: {email}")
            # セキュリティ: ユーザーが存在しなくても成功メッセージを返す
            return jsonify({
                'success': True,
                'message': 'パスワード復元メールを送信しました'
            }), 200
        
        # トークン生成
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)
        
        # 既存の未使用トークンを無効化
        cur.execute(
            'UPDATE password_reset_tokens SET used = TRUE WHERE user_id = %s AND used = FALSE',
            (user['id'],)
        )
        
        # 新しいトークンを保存
        cur.execute(
            '''INSERT INTO password_reset_tokens (user_id, token, expires_at) 
               VALUES (%s, %s, %s)''',
            (user['id'], reset_token, expires_at)
        )
        
        conn.commit()
        
        # リセットURL生成
        # 本番環境では実際のドメインに変更
        reset_url = f"http://localhost:5000/reset-password.html?token={reset_token}"
        
        # メール送信
        email_sent = send_password_reset_email(
            to_email=email,
            reset_url=reset_url,
            user_name=user.get('name')
        )
        
        if email_sent:
            print(f"パスワードリセットメール送信成功: {email}")
        else:
            print(f"パスワードリセットメール送信失敗: {email}")
            # メール送信失敗でもトークンは生成されているので、
            # 開発環境ではコンソールにURLを出力
            print(f"リセットURL: {reset_url}")
        
        return jsonify({
            'success': True,
            'message': 'パスワード復元メールを送信しました'
        }), 200
        
    except Exception as e:
        conn.rollback()
        print(f"パスワード復元エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラーが発生しました'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/verify-reset-token', methods=['POST'])
@app.route('/api/password/validate-token', methods=['POST'])  # reset-password.html との互換性のため
def verify_reset_token():
    """リセットトークンの有効性を確認"""
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({'success': False, 'message': 'トークンが必要です'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        # トークンを検索
        cur.execute(
            '''SELECT * FROM password_reset_tokens 
               WHERE token = %s 
               AND expires_at > CURRENT_TIMESTAMP 
               AND used = FALSE''',
            (token,)
        )
        
        token_data = cur.fetchone()
        
        if token_data:
            return jsonify({'success': True, 'valid': True}), 200
        else:
            return jsonify({'success': True, 'valid': False}), 200
        
    except Exception as e:
        print(f"トークン検証エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラーが発生しました'}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/logout', methods=['POST'])
def logout():
    """ログアウト"""
    session.clear()
    return jsonify({'success': True, 'message': 'ログアウトしました'}), 200

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    """認証状態を確認（profile.html用）"""
    if 'user_id' in session:
        return jsonify({'authenticated': True, 'user_id': session['user_id']}), 200
    return jsonify({'authenticated': False}), 200


@app.route('/api/check-session', methods=['GET'])
def check_session():
    """セッション状態を確認"""
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user_id': session['user_id']
        }), 200
    else:
        return jsonify({
            'logged_in': False
        }), 401

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    """指定されたユーザーの情報を取得（本人のみ）"""
    # 認証チェック
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401

    # 本人確認（自分の情報のみ取得可能）
    if session['user_id'] != user_id:
        return jsonify({'success': False, 'message': '他のユーザーの情報は取得できません'}), 403
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute(
            'SELECT id, user_id, name, email, age, created_at FROM users WHERE id = %s',
            (user_id,)
        )
        user = cur.fetchone()
        
        if not user:
            return jsonify({'success': False, 'message': 'ユーザーが見つかりません'}), 404
        
        return jsonify(dict(user)), 200
        
    except Exception as e:
        print(f"ユーザー情報取得エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラーが発生しました'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """ユーザー情報を更新（本人のみ）"""
    # 認証チェック
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'ログインが必要です'}), 401

    # 本人確認
    if session['user_id'] != user_id:
        return jsonify({'success': False, 'error': '他のユーザーの情報は変更できません'}), 403

    data = request.get_json()
    print(f"=== ユーザー更新リクエスト受信 (ID: {user_id}) ===")
    
    name = data.get('name')
    email = data.get('email')
    age = data.get('age')
    password = data.get('password')  # オプション
    
    # バリデーション
    if not name or not email:
        return jsonify({'success': False, 'error': '名前とメールアドレスは必須です'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        # ユーザーの存在確認
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()
        if not user:
            return jsonify({'success': False, 'error': 'ユーザーが見つかりません'}), 404
        
        # メールアドレスの重複チェック（自分以外）
        cur.execute('SELECT * FROM users WHERE email = %s AND id != %s', (email, user_id))
        if cur.fetchone():
            return jsonify({'success': False, 'error': 'このメールアドレスは既に使用されています'}), 400
        
        # パスワードが指定されている場合はハッシュ化して更新
        if password:
            hashed_password = generate_password_hash(password)
            cur.execute(
                '''UPDATE users 
                   SET name = %s, email = %s, age = %s, password = %s, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = %s''',
                (name, email, age, hashed_password, user_id)
            )
        else:
            # パスワードなしで更新
            cur.execute(
                '''UPDATE users 
                   SET name = %s, email = %s, age = %s, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = %s''',
                (name, email, age, user_id)
            )
        
        conn.commit()
        
        print(f"ユーザー更新成功: {email}")
        
        return jsonify({
            'success': True,
            'message': 'ユーザー情報を更新しました'
        }), 200
        
    except Exception as e:
        conn.rollback()
        print(f"ユーザー更新エラー: {e}")
        return jsonify({'success': False, 'error': f'サーバーエラーが発生しました: {str(e)}'}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """ユーザーアカウントを削除"""
    print(f"=== ユーザー削除リクエスト受信 (ID: {user_id}) ===")
    
    # セッションチェック：ログイン中のユーザーのみ削除可能
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
    
    # 本人確認：ログイン中のユーザーのみ自分のアカウントを削除可能
    if session['user_id'] != user_id:
        return jsonify({'success': False, 'message': '他のユーザーのアカウントは削除できません'}), 403
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        # ユーザーの存在確認
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'ユーザーが見つかりません'}), 404
        
        # 関連データの削除（外部キー制約がある場合）
        # お気に入りを削除
        cur.execute('DELETE FROM favorites WHERE user_id = %s', (user_id,))
        
        # 旅行プランを削除（もしあれば）
        # cur.execute('DELETE FROM travel_plans WHERE user_id = %s', (user_id,))
        
        # ユーザー削除
        cur.execute('DELETE FROM users WHERE id = %s', (user_id,))
        
        conn.commit()
        
        # セッションをクリア（ログアウト）
        session.clear()
        
        print(f"ユーザー削除成功: {user['email']}")
        
        return jsonify({
            'success': True,
            'message': 'アカウントを削除しました'
        }), 200
        
    except Exception as e:
        conn.rollback()
        print(f"ユーザー削除エラー: {e}")
        return jsonify({'success': False, 'message': f'サーバーエラーが発生しました: {str(e)}'}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/user', methods=['GET'])
def get_user():
    """ログイン中のユーザー情報を取得"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '認証が必要です'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute(
            'SELECT id, user_id, name, email, age, created_at FROM users WHERE id = %s',
            (session['user_id'],)
        )
        user = cur.fetchone()
        
        if not user:
            return jsonify({'success': False, 'message': 'ユーザーが見つかりません'}), 404
        
        return jsonify({
            'success': True,
            'user': dict(user)
        }), 200
        
    except Exception as e:
        print(f"ユーザー情報取得エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラーが発生しました'}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/spots', methods=['GET'])
def get_spots():
    """スポットデータを取得"""
    import json
    
    try:
        # dataフォルダからspots.jsonを読み込む
        spots_file = os.path.join(BASE_DIR, 'data', 'spots.json')
        
        if not os.path.exists(spots_file):
            return jsonify({'success': False, 'message': 'スポットデータが見つかりません'}), 404
        
        with open(spots_file, 'r', encoding='utf-8') as f:
            spots_data = json.load(f)
        
        return jsonify({
            'success': True,
            'data': spots_data
        }), 200
        
    except Exception as e:
        print(f"スポットデータ読み込みエラー: {e}")
        return jsonify({'success': False, 'message': 'データの読み込みに失敗しました'}), 500

# app.pyの既存の設定部分に追加
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
    print('警告: MAIL_USERNAME または MAIL_PASSWORD が未設定です。メール送信は無効になります。', file=sys.stderr)

mail = Mail(app)

# メール送信関数
def send_password_reset_email(to_email, reset_url, user_name=None):
    """パスワードリセットメールを送信"""
    try:
        msg = Message(
            subject='【旅行プランサービス】パスワードリセットのご案内',
            recipients=[to_email]
        )
        
        # HTMLメール
        msg.html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background: #f8f9fa;
                    border-radius: 10px;
                    padding: 30px;
                    margin: 20px 0;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #ff6b6b;
                    margin: 0;
                }}
                .content {{
                    background: white;
                    border-radius: 8px;
                    padding: 25px;
                    margin: 20px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 15px 30px;
                    background: linear-gradient(135deg, #ff9a44, #ff6b6b);
                    color: white;
                    text-decoration: none;
                    border-radius: 25px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #7f8c8d;
                    font-size: 12px;
                    margin-top: 30px;
                }}
                .warning {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔒 パスワードリセット</h1>
                </div>
                
                <div class="content">
                    <p>こんにちは{", " + user_name if user_name else ""}様</p>
                    
                    <p>パスワードのリセットリクエストを受け付けました。</p>
                    
                    <p>以下のボタンをクリックして、新しいパスワードを設定してください：</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">パスワードをリセット</a>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ 注意事項</strong>
                        <ul>
                            <li>このリンクは<strong>1時間</strong>有効です</li>
                            <li>リンクは一度のみ使用できます</li>
                            <li>このメールに心当たりがない場合は、無視してください</li>
                        </ul>
                    </div>
                    
                    <p style="color: #7f8c8d; font-size: 14px;">
                        ボタンが動作しない場合は、以下のURLをブラウザにコピー&ペーストしてください：<br>
                        <a href="{reset_url}" style="color: #3498db;">{reset_url}</a>
                    </p>
                </div>
                
                <div class="footer">
                    <p>このメールは旅行プランサービスから自動送信されています。</p>
                    <p>© 2025 旅行プランサービス</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # テキスト版（HTMLが表示できない場合のフォールバック）
        msg.body = f'''
パスワードリセットのご案内

こんにちは{", " + user_name if user_name else ""}様

パスワードのリセットリクエストを受け付けました。

以下のリンクをクリックして、新しいパスワードを設定してください：
{reset_url}

【注意事項】
・このリンクは1時間有効です
・リンクは一度のみ使用できます
・このメールに心当たりがない場合は、無視してください

---
このメールは旅行プランサービスから自動送信されています。
© 2025 旅行プランサービス
        '''
        
        mail.send(msg)
        print(f"パスワードリセットメール送信成功: {to_email}")
        return True
        
    except Exception as e:
        print(f"メール送信エラー: {e}")
        return False
    
#######################################################################################################
#######################################################################################################


    
import re
import requests
from flask import jsonify, request

#API連携、スポット検索
########################################################################################################
########################################################################################################

import re
import time
from functools import wraps
import requests
from flask import jsonify, request

# ===========================
# 定数定義
# ===========================
OVERPASS_URL = "http://overpass-api.de/api/interpreter"
MAX_SPOTS_LIMIT = 500
MAX_NAME_LENGTH = 40
OVERPASS_TIMEOUT = 45
REQUEST_TIMEOUT = 50

BAD_KEYWORDS = ['詰所', '案内', '地図', '乗り場', '駐車場', 'トイレ',
                '入口', '出口', '受付', '売店', 'ゲート', '記念碑']

PREFECTURE_BOUNDS = {
    'osaka': ((34.30, 135.25, 34.80, 135.63), '大阪府'),  # 北端・東端を削減
    'kyoto': ((34.80, 135.50, 35.80, 136.05), '京都府'),  # 南端・西端を調整
    'hyogo': ((34.20, 134.25, 35.70, 135.40), '兵庫県'),  # 東端を削減
    'nara': ((33.95, 135.63, 34.75, 136.15), '奈良県'),   # 西端を調整
    'shiga': ((34.80, 135.85, 35.60, 136.45), '滋賀県'),  # 南端・西端を調整
    'wakayama': ((33.45, 135.05, 34.25, 135.90), '和歌山県'),
    'mie': ((33.70, 135.85, 35.20, 136.90), '三重県'),
}


# 都道府県の中心座標
PREFECTURE_CENTERS = {
    'osaka': {'name': '大阪府', 'lat': 34.6937, 'lon': 135.5023},
    'kyoto': {'name': '京都府', 'lat': 35.0116, 'lon': 135.7681},
    'hyogo': {'name': '兵庫県', 'lat': 34.6913, 'lon': 135.1830},
    'nara': {'name': '奈良県', 'lat': 34.6851, 'lon': 135.8048},
    'shiga': {'name': '滋賀県', 'lat': 35.0045, 'lon': 135.8686},
    'wakayama': {'name': '和歌山県', 'lat': 34.2261, 'lon': 135.1675},
    'mie': {'name': '三重県', 'lat': 34.7303, 'lon': 136.5086},
}

CATEGORY_TAGS = {
    'castle': ('historic', 'castle', '城'),
    'buddhist': ('religion', 'buddhist', '寺院'),
    'shinto': ('religion', 'shinto', '神社'),
    'museum': ('tourism', 'museum', '博物館'),
    'gallery': ('tourism', 'gallery', '美術館'),
    'theme_park': ('tourism', 'theme_park', 'テーマパーク'),
    'heritage': ('heritage', '1', '世界遺産'),
    'park': ('leisure', 'park', '公園'),
    'theatre': ('amenity', 'theatre', '劇場'),
    'restaurant': ('amenity', 'restaurant', '飲食店'),
    'library': ('amenity', 'library', '図書館'),
    'cinema': ('amenity', 'cinema', '映画館'),
    'water_park': ('leisure', 'water_park', 'ウォーターパーク'),
    'zoo': ('tourism', 'zoo', '動物園'),
    'aquarium': ('tourism', 'aquarium', '水族館'),
    'viewpoint': ('tourism', 'viewpoint', '展望台'),
}

# ===========================
# ユーティリティ関数
# ===========================

def escape_regex(text):
    """正規表現特殊文字をエスケープ"""
    if not text:
        return text
    return re.escape(text)

def retry_on_timeout(max_retries=2, backoff=2):
    """タイムアウト時にリトライするデコレータ"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.Timeout:
                    if attempt < max_retries:
                        wait_time = backoff ** attempt
                        print(f"タイムアウト発生。{wait_time}秒後にリトライ... (試行 {attempt + 1}/{max_retries + 1})")
                        time.sleep(wait_time)
                    else:
                        raise
            return None
        return wrapper
    return decorator

def safe_get_name(tags):
    """安全に名前を取得（空文字列対策）"""
    name = tags.get('name:ja') or tags.get('name') or tags.get('name:en') or ''
    return name.strip() if name else ''

def safe_get_address(tags):
    """住所を安全に取得・整形"""
    if tags.get('addr:full'):
        return tags['addr:full'].strip()
    
    parts = [
        tags.get('addr:city', ''),
        tags.get('addr:street', ''),
        tags.get('addr:housenumber', ''),
        tags.get('addr:postcode', '')
    ]
    address = ' '.join(p for p in parts if p).strip()
    address = re.sub(r'\s+', ' ', address)
    return address

def get_website(tags):
    """複数の可能性からウェブサイトを取得"""
    return (tags.get('website') or 
            tags.get('contact:website') or 
            tags.get('url') or 
            tags.get('official_website') or '')

def should_exclude_spot(name, tags):
    """スポットを除外すべきかチェック"""
    if not name or name == '名称不明':
        return True, '名称なし'
    
    if len(name) > MAX_NAME_LENGTH:
        return True, '名前が長すぎる'
    
    if any(kw in name for kw in BAD_KEYWORDS):
        return True, '除外キーワード'
    
    check_tags = {k: v for k, v in tags.items() if k != 'description'}
    if any(kw in str(v) for v in check_tags.values() for kw in BAD_KEYWORDS):
        return True, '除外キーワード'
    
    return False, None

def determine_spot_type(tags: Dict) -> str:
    """タグからスポットタイプを判定"""
    if tags.get('historic') == 'castle':
        return '城'
    elif tags.get('religion') == 'buddhist':
        return '寺院'
    elif tags.get('religion') == 'shinto':
        return '神社'
    elif tags.get('tourism') == 'museum':
        return '博物館'
    elif tags.get('tourism') == 'theme_park':
        return 'テーマパーク'
    elif tags.get('tourism') == 'zoo':
        return '動物園'
    elif tags.get('tourism') == 'aquarium':
        return '水族館'
    elif tags.get('tourism') == 'viewpoint':
        return '展望台'
    elif tags.get('natural') in ['peak', 'beach']:
        return '自然'
    elif tags.get('leisure') == 'spa':
        return '温泉'
    elif tags.get('amenity') == 'restaurant':
        return 'レストラン'
    elif tags.get('shop') == 'mall':
        return 'ショッピングモール'
    return '観光地'


def generate_tags(tags: Dict, spot_type: str) -> List[str]:
    """タグ生成（必ず配列を返す）"""
    result = []
    
    # スポットタイプを追加
    if spot_type:
        result.append(spot_type)
    
    # 都市名を追加
    city = tags.get('addr:city') or tags.get('addr:prefecture')
    if city:
        result.append(city)
    
    # 世界遺産チェック
    if tags.get('heritage') or tags.get('unesco'):
        result.append('世界遺産')
    
    # バリアフリー
    if tags.get('wheelchair') == 'yes':
        result.append('バリアフリー')
    
    # 駐車場
    if tags.get('parking') == 'yes':
        result.append('駐車場あり')
    
    return result[:5] if result else ['観光地']  # 最低1つは返す

def create_spot_dict(element, tags, name, lat, lon):
    """スポット辞書を作成"""
    element_id = element.get('id')
    element_type = element.get('type', 'node')
    
    return {
        'id': f"{element_type}_{element_id}",
        'osm_id': element_id,
        'osm_type': element_type,
        'name': name,
        'lat': lat,
        'lon': lon,
        'type': determine_spot_type(tags),
        'address': safe_get_address(tags),
        'description': tags.get('description', ''),
        'website': get_website(tags),
        'opening_hours': tags.get('opening_hours', ''),
        'phone': tags.get('phone', ''),
        'email': tags.get('contact:email', ''),
        'facebook': tags.get('contact:facebook', ''),
        'instagram': tags.get('contact:instagram', ''),
    }

def calculate_way_center(way_nodes, node_coords):
    """Wayの中心座標を計算"""
    lats = []
    lons = []
    
    for node_id in way_nodes:
        coord = node_coords.get(node_id)
        if coord and coord[0] and coord[1]:
            lats.append(coord[0])
            lons.append(coord[1])
    
    if lats and lons:
        return sum(lats) / len(lats), sum(lons) / len(lons)
    return None, None

def process_elements(elements):
    """要素を処理してスポット辞書を作成"""
    spots_dict = {}
    pending_ways = {}
    node_coords = {}
    
    rejection_stats = {
        '名称なし': 0,
        '名前が長すぎる': 0,
        '除外キーワード': 0,
        '座標なし': 0
    }
    
    for element in elements:
        element_type = element.get('type')
        element_id = element.get('id')
        
        if element_type == 'node':
            lat = element.get('lat')
            lon = element.get('lon')
            if lat and lon:
                node_coords[element_id] = (lat, lon)
        
        if 'tags' not in element:
            print(f"  ⚠️ タグなし要素をスキップ: {element.get('type')}_{element.get('id')}")
            continue
        
        tags = element['tags']
        name = safe_get_name(tags)
        
        should_exclude, reason = should_exclude_spot(name, tags)
        if should_exclude:
            rejection_stats[reason] += 1
            continue
        
        unique_id = f"{element_type}_{element_id}"
        
        if element_type == 'node':
            lat = element.get('lat')
            lon = element.get('lon')
            
            if lat and lon and unique_id not in spots_dict:
              spot = create_spot_dict(element, tags, name, lat, lon)
        
        # ★★★ 住所がない場合は逆ジオコーディング ★★★
              if not spot['address'] or spot['address'] == '':
                 print(f"  🔄 住所取得中: {spot['name']} ({lat}, {lon})")
                 spot['address'] = reverse_geocode(lat, lon)
                 time.sleep(1.1)  # レート制限対策（1秒に1リクエスト）
        
              spots_dict[unique_id] = spot
        
        elif element_type == 'way':
            if unique_id not in spots_dict:
                pending_ways[unique_id] = {
                    'element': element,
                    'tags': tags,
                    'name': name,
                    'nodes': element.get('nodes', [])
                }
    
    print(f"[処理統計] Node座標数: {len(node_coords)}, 保留中のWay: {len(pending_ways)}")
    
    ways_success = 0
    ways_failed = 0
    
    for unique_id, way_data in pending_ways.items():
        lat, lon = calculate_way_center(way_data['nodes'], node_coords)
        
        if lat and lon:
            spot = create_spot_dict(
                way_data['element'],
                way_data['tags'],
                way_data['name'],
                lat,
                lon
            )
            # ★★★ 住所がない場合は逆ジオコーディング ★★★
            if not spot['address'] or spot['address'] == '':
                print(f"  🔄 住所取得中: {spot['name']} ({lat}, {lon})")
                spot['address'] = reverse_geocode(lat, lon)
                time.sleep(1.1)  # レート制限対策
        
            spots_dict[unique_id] = spot
            ways_success += 1
        else:
            rejection_stats['座標なし'] += 1
            ways_failed += 1
            print(f"[Way座標計算失敗] {way_data['name']} (ID: {unique_id})")
    
    print(f"[Way処理結果] 成功: {ways_success}, 失敗: {ways_failed}")
    print(f"[除外統計] {rejection_stats}")
    print(f"[最終スポット数] {len(spots_dict)}件")
    
    return list(spots_dict.values())

# ===========================
# APIエンドポイント
# ===========================

@app.route('/api/overpass-spots', methods=['GET'])
@retry_on_timeout(max_retries=2, backoff=2)
def get_overpass_spots():
    """Overpass APIから厳選された観光スポットのみを取得"""

    overpass_query = f"""
    [out:json][timeout:{OVERPASS_TIMEOUT}];
    (
      node["historic"="castle"](33.5,134.5,35.8,136.8);
      way["historic"="castle"](33.5,134.5,35.8,136.8);

      node["amenity"="place_of_worship"]["religion"="buddhist"](33.5,134.5,35.8,136.8);
      node["amenity"="place_of_worship"]["religion"="shinto"](33.5,134.5,35.8,136.8);

      node["tourism"="museum"](33.5,134.5,35.8,136.8);
      way["tourism"="museum"](33.5,134.5,35.8,136.8);
      node["tourism"="gallery"](33.5,134.5,35.8,136.8);

      node["tourism"="theme_park"](33.5,134.5,35.8,136.8);
      way["tourism"="theme_park"](33.5,134.5,35.8,136.8);

      node["heritage"="1"](33.5,134.5,35.8,136.8);
      way["heritage"="1"](33.5,134.5,35.8,136.8);
      relation["heritage"="1"](33.5,134.5,35.8,136.8);

      node["leisure"="park"]["operator"~"国"](33.5,134.5,35.8,136.8);

      node["amenity"="theatre"](33.5,134.5,35.8,136.8);

      node["amenity"~"restaurant|cafe|fast_food|food_court|bar|pub"](33.5,134.5,35.8,136.8);

      node["amenity"="library"](33.5,134.5,35.8,136.8);
      node["amenity"="cinema"](33.5,134.5,35.8,136.8);
      node["leisure"="water_park"](33.5,134.5,35.8,136.8);
      node["tourism"="zoo"](33.5,134.5,35.8,136.8);
      node["tourism"="aquarium"](33.5,134.5,35.8,136.8);
      node["tourism"="viewpoint"](33.5,134.5,35.8,136.8);
    );
    out body {MAX_SPOTS_LIMIT};
    >;
    out skel qt;
    """

    try:
        print(f"[リクエスト開始] /api/overpass-spots")
        response = requests.post(OVERPASS_URL, data={'data': overpass_query}, timeout=REQUEST_TIMEOUT)

        if response.status_code != 200:
            error_msg = f'Overpass APIエラー (ステータス: {response.status_code})'
            print(f"[エラー] {error_msg}")
            return jsonify({'success': False, 'message': error_msg}), 500

        try:
            data = response.json()
        except ValueError as e:
            print(f"[JSONデコードエラー] {str(e)}")
            return jsonify({'success': False, 'message': 'APIレスポンスの解析に失敗しました'}), 500

        print(f"[取得データ] 全要素数: {len(data.get('elements', []))}件")
        
        spots = process_elements(data.get('elements', []))
        
        return jsonify({'success': True, 'count': len(spots), 'spots': spots}), 200

    except requests.exceptions.Timeout:
        print(f"[タイムアウト] APIリクエストが{REQUEST_TIMEOUT}秒でタイムアウト")
        return jsonify({'success': False, 'message': 'APIリクエストがタイムアウトしました。しばらく待ってから再試行してください。'}), 504
    except requests.exceptions.RequestException as e:
        print(f"[リクエストエラー] {type(e).__name__}: {str(e)}")
        return jsonify({'success': False, 'message': f'通信エラーが発生しました: {str(e)}'}), 500
    except Exception as e:
        print(f"[予期しないエラー] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'サーバー内部エラーが発生しました'}), 500


@app.route('/api/search-combined', methods=['GET'])
@retry_on_timeout(max_retries=2, backoff=2)
def search_combined():
    """複数の検索条件を組み合わせて観光スポットを検索"""
    
    keyword = request.args.get('keyword', '').strip()
    category = request.args.get('category', '').strip()
    prefecture = request.args.get('prefecture', '').strip()
    
    if not keyword and not category and not prefecture:
        return jsonify({
            'success': False,
            'message': '少なくとも1つの検索条件を入力してください'
        }), 400
    
    if prefecture and prefecture in PREFECTURE_BOUNDS:
        bounds, prefecture_name = PREFECTURE_BOUNDS[prefecture]
        min_lat, min_lon, max_lat, max_lon = bounds
    else:
        min_lat, min_lon, max_lat, max_lon = 33.5, 134.5, 35.8, 136.8
        prefecture_name = '近畿地方'
    
    safe_keyword = escape_regex(keyword) if keyword else ''
    
    query_parts = []
    
    # ========================================
    # パターン1: キーワード + カテゴリ検索
    # ========================================
    if safe_keyword:
        if category and category in CATEGORY_TAGS:
            tag_key, tag_value, category_name = CATEGORY_TAGS[category]
            
            if category == 'castle':
                query_parts.append(f'node["historic"="castle"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
                query_parts.append(f'way["historic"="castle"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
            
            elif category == 'buddhist':
                query_parts.append(f'node["amenity"="place_of_worship"]["religion"="buddhist"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
            
            elif category == 'shinto':
                query_parts.append(f'node["amenity"="place_of_worship"]["religion"="shinto"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
            
            elif category == 'museum':
                query_parts.append(f'node["tourism"="museum"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
                query_parts.append(f'way["tourism"="museum"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
            
            elif category == 'theme_park':
                query_parts.append(f'node["tourism"="theme_park"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
                query_parts.append(f'way["tourism"="theme_park"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
            
            elif category == 'restaurant':
                query_parts.append(f'node["amenity"~"restaurant|cafe"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
            
            elif category == 'park':
                query_parts.append(f'node["leisure"="park"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
                query_parts.append(f'way["leisure"="park"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
            
            else:
                query_parts.append(f'node["{tag_key}"="{tag_value}"]["name"~"{safe_keyword}",i]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        # キーワードのみの検索（カテゴリ指定なし）
        else:
            query_parts.append(f'node["name"~"{safe_keyword}",i]["tourism"]({min_lat},{min_lon},{max_lat},{max_lon});')
            query_parts.append(f'way["name"~"{safe_keyword}",i]["tourism"]({min_lat},{min_lon},{max_lat},{max_lon});')
            query_parts.append(f'node["name"~"{safe_keyword}",i]["historic"]({min_lat},{min_lon},{max_lat},{max_lon});')
            query_parts.append(f'node["name"~"{safe_keyword}",i]["amenity"="place_of_worship"]({min_lat},{min_lon},{max_lat},{max_lon});')
    
    # ========================================
    # パターン2: カテゴリのみ検索（キーワードなし）
    # ========================================
    elif category and category in CATEGORY_TAGS:
        tag_key, tag_value, category_name = CATEGORY_TAGS[category]
        
        if category == 'castle':
            query_parts.append(f'node["historic"="castle"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
            query_parts.append(f'way["historic"="castle"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'buddhist':
            # 名前付きの寺院のみ（小さな祠を除外）
            query_parts.append(f'node["amenity"="place_of_worship"]["religion"="buddhist"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'shinto':
            # 名前付きの神社のみ（小さな祠を除外）
            query_parts.append(f'node["amenity"="place_of_worship"]["religion"="shinto"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'museum':
            query_parts.append(f'node["tourism"="museum"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
            query_parts.append(f'way["tourism"="museum"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'theme_park':
            query_parts.append(f'node["tourism"="theme_park"]({min_lat},{min_lon},{max_lat},{max_lon});')
            query_parts.append(f'way["tourism"="theme_park"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'heritage':
            query_parts.append(f'node["heritage"="1"]({min_lat},{min_lon},{max_lat},{max_lon});')
            query_parts.append(f'way["heritage"="1"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'restaurant':
            # 飲食店は主要カテゴリのみ（fast_food等を除外して軽量化）
            query_parts.append(f'node["amenity"~"restaurant|cafe"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'park':
            # 国立公園・県立公園など主要な公園のみ
            query_parts.append(f'node["leisure"="park"]["name"]["operator"]({min_lat},{min_lon},{max_lat},{max_lon});')
            query_parts.append(f'way["leisure"="park"]["name"]["operator"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'zoo':
            query_parts.append(f'node["tourism"="zoo"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'aquarium':
            query_parts.append(f'node["tourism"="aquarium"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'viewpoint':
            query_parts.append(f'node["tourism"="viewpoint"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'library':
            query_parts.append(f'node["amenity"="library"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'cinema':
            query_parts.append(f'node["amenity"="cinema"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'theatre':
            query_parts.append(f'node["amenity"="theatre"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'water_park':
            query_parts.append(f'node["leisure"="water_park"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        elif category == 'gallery':
            query_parts.append(f'node["tourism"="gallery"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
        
        else:
            # その他のカテゴリは名前付きのみ
            query_parts.append(f'node["{tag_key}"="{tag_value}"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});')
    
    # ========================================
    # パターン3: 都道府県のみ検索（厳選スポット）
    # ========================================
    else:
        query_parts.extend([
            f'node["historic"="castle"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'way["historic"="castle"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'node["amenity"="place_of_worship"]["religion"="buddhist"]["name"]["wikidata"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'node["amenity"="place_of_worship"]["religion"="shinto"]["name"]["wikidata"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'node["tourism"="museum"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'way["tourism"="museum"]["name"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'node["tourism"="theme_park"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'way["tourism"="theme_park"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'node["heritage"="1"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'way["heritage"="1"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'node["tourism"="zoo"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'node["tourism"="aquarium"]({min_lat},{min_lon},{max_lat},{max_lon});',
            f'node["leisure"="water_park"]({min_lat},{min_lon},{max_lat},{max_lon});',
        ])
    
    overpass_query = f"""
    [out:json][timeout:{OVERPASS_TIMEOUT}];
    (
      {' '.join(query_parts)}
    );
    out body 20;
    >;
    out skel qt;
    """
    
    try:
        print(f"[検索リクエスト] keyword={keyword}, category={category}, prefecture={prefecture}")
        response = requests.post(OVERPASS_URL, data={'data': overpass_query}, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            error_msg = f'Overpass APIエラー (ステータス: {response.status_code})'
            print(f"[エラー] {error_msg}")
            return jsonify({'success': False, 'message': error_msg}), 500
        
        try:
            data = response.json()
        except ValueError as e:
            print(f"[JSONデコードエラー] {str(e)}")
            return jsonify({'success': False, 'message': 'APIレスポンスの解析に失敗しました'}), 500
        
        print(f"[取得データ] 全要素数: {len(data.get('elements', []))}件")
        
        spots = process_elements(data.get('elements', []))

        # 都道府県が指定されている場合、境界ボックス外のスポットを除外
        if prefecture and prefecture in PREFECTURE_BOUNDS:
            filter_bounds, _ = PREFECTURE_BOUNDS[prefecture]
            filter_min_lat, filter_min_lon, filter_max_lat, filter_max_lon = filter_bounds
    
            print(f"[フィルタ境界] {prefecture_name}: lat({filter_min_lat}~{filter_max_lat}), lon({filter_min_lon}~{filter_max_lon})")
            print(f"[フィルタ前] {len(spots)}件")
    
    # デバッグ: 最初の5件の座標を表示
            for i, s in enumerate(spots[:5]):
                print(f"  {i+1}. {s['name']}: lat={s['lat']}, lon={s['lon']}")
    
            spots_before = len(spots)
            spots = [
                s for s in spots 
                if filter_min_lat <= s['lat'] <= filter_max_lat and 
                    filter_min_lon <= s['lon'] <= filter_max_lon
            ]
            spots_after = len(spots)
    
            print(f"[都道府県フィルタ後] {spots_after}件 (除外: {spots_before - spots_after}件)")
        
        conditions = []
        if keyword:
            conditions.append(f'キーワード「{keyword}」')
        if category:
            conditions.append(f'カテゴリ「{CATEGORY_TAGS.get(category, ("", "", category))[2]}」')
        if prefecture:
            conditions.append(f'地域「{prefecture_name}」')
        
        condition_text = ' + '.join(conditions)
        
        print(f"[検索結果] {len(spots)}件（{condition_text}）")
        
        return jsonify({
            'success': True,
            'conditions': condition_text,
            'count': len(spots),
            'spots': spots
        }), 200
        
    except requests.exceptions.Timeout:
        print(f"[タイムアウト] 検索リクエストが{REQUEST_TIMEOUT}秒でタイムアウト")
        return jsonify({
            'success': False,
            'message': 'APIリクエストがタイムアウトしました。条件を絞って再試行してください。'
        }), 504
    except requests.exceptions.RequestException as e:
        print(f"[リクエストエラー] {type(e).__name__}: {str(e)}")
        return jsonify({'success': False, 'message': f'通信エラーが発生しました: {str(e)}'}), 500
    except Exception as e:
        print(f"[予期しないエラー] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'サーバー内部エラーが発生しました'
        }), 500
#####################################################################################################
#####################################################################################################





#APIからスポット情報取得し、旅行プラン作成
######################################################################################################
######################################################################################################

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import math

from math import radians, sin, cos, sqrt, atan2

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    2地点間の直線距離を計算（Haversine公式）
    
    Args:
        lat1, lon1: 地点1の緯度・経度
        lat2, lon2: 地点2の緯度・経度
    
    Returns:
        float: 距離（km）
    """
    R = 6371  # 地球の半径（km）
    
    # 度数法からラジアンに変換
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # 差分を計算
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Haversine公式
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    distance = R * c
    
    return round(distance, 2)  # 小数点2桁で四捨五入


def calculate_route_distance(spots):
    """
    スポットリストを順番に回った時の合計距離を計算
    
    Args:
        spots: スポットのリスト（各スポットにlat, lonが必要）
    
    Returns:
        float: 合計距離（km）
    """
    if len(spots) < 2:
        return 0.0
    
    total_distance = 0.0
    
    for i in range(len(spots) - 1):
        spot1 = spots[i]
        spot2 = spots[i + 1]
        
        # 緯度経度が存在するか確認
        if 'lat' in spot1 and 'lon' in spot1 and 'lat' in spot2 and 'lon' in spot2:
            distance = calculate_distance(
                spot1['lat'], spot1['lon'],
                spot2['lat'], spot2['lon']
            )
            total_distance += distance
            print(f"  {spot1.get('name', '?')} → {spot2.get('name', '?')}: {distance}km")
    
    return round(total_distance, 2)


def sort_spots_by_distance(base_spot, spots_list, max_distance=60):
    """
    基準スポットから近い順にスポットをソート
    
    Args:
        base_spot: 基準となるスポット（lat, lonが必要）
        spots_list: 並べ替えるスポットのリスト
        max_distance: 最大距離（km）この距離より遠いスポットは除外
    
    Returns:
        list: 距離でソートされたスポットリスト
    """
    base_lat = base_spot.get('lat')
    base_lon = base_spot.get('lon')
    
    if not base_lat or not base_lon:
        print("⚠️ 基準スポットに座標がありません")
        return spots_list
    
    # 各スポットに基準点からの距離を追加
    spots_with_distance = []
    for spot in spots_list:
        if 'lat' in spot and 'lon' in spot:
            distance = calculate_distance(
                base_lat, base_lon,
                spot['lat'], spot['lon']
            )
            
            # 最大距離以内のスポットのみ追加
            if distance <= max_distance:
                spot['distance_from_base'] = distance
                spots_with_distance.append(spot)
                print(f"  📍 {spot.get('name', '?')}: {distance}km")
            else:
                print(f"  ❌ {spot.get('name', '?')}: {distance}km（遠すぎるため除外）")
    
    # 距離でソート（近い順）
    sorted_spots = sorted(spots_with_distance, key=lambda x: x['distance_from_base'])
    
    print(f"\n✅ {len(sorted_spots)}個のスポットを距離順にソート完了")
    
    return sorted_spots

def optimize_daily_route(spots):
    """
    その日のスポットを最短ルートに並び替え（貪欲法）
    
    Args:
        spots: その日のスポットリスト
    
    Returns:
        list: 最適化されたスポットリスト
    """
    if len(spots) <= 1:
        return spots
    
    print(f"\n🔄 {len(spots)}スポットのルート最適化中...")
    
    # 最初のスポットは固定（拠点に近いスポット）
    optimized = [spots[0]]
    remaining = spots[1:].copy()
    
    # 貪欲法: 現在地から最も近いスポットを次に選ぶ
    while remaining:
        current_spot = optimized[-1]
        
        # 現在地から各スポットへの距離を計算
        nearest_spot = None
        nearest_distance = float('inf')
        
        for spot in remaining:
            if 'lat' in spot and 'lon' in spot and 'lat' in current_spot and 'lon' in current_spot:
                distance = calculate_distance(
                    current_spot['lat'], current_spot['lon'],
                    spot['lat'], spot['lon']
                )
                
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_spot = spot
        
        if nearest_spot:
            optimized.append(nearest_spot)
            remaining.remove(nearest_spot)
            print(f"  {current_spot.get('name', '?')} → {nearest_spot.get('name', '?')}: {nearest_distance}km")
        else:
            # 座標がないスポットは最後に追加
            optimized.extend(remaining)
            break
    
    # 最適化前後の距離を比較
    original_distance = calculate_route_distance(spots)
    optimized_distance = calculate_route_distance(optimized)
    
    print(f"  📉 最適化: {original_distance}km → {optimized_distance}km（{original_distance - optimized_distance:.1f}km削減）")
    
    return optimized


def map_type_to_category(spot_type: str) -> str:
    """スポットタイプからカテゴリー名を取得"""
    mapping = {
        '温泉': 'リラクゼーション',
        '自然': '自然・景色',
        '展望台': '自然・景色',
        '城': '文化・歴史',
        '寺院': '文化・歴史',
        '神社': '文化・歴史',
        '博物館': '文化・歴史',
        'レストラン': 'グルメ',
        'ショッピングモール': 'ショッピング',
        'テーマパーク': 'アクティビティ',
        '動物園': 'アクティビティ',
        '水族館': 'アクティビティ',
    }
    return mapping.get(spot_type, 'その他')


def determine_category_key(spot_type: str) -> str:
    """スポットタイプからカテゴリーキーを取得"""
    mapping = {
        '温泉': 'relax',
        '自然': 'nature',
        '展望台': 'nature',
        '山': 'nature',
        'ビーチ': 'nature',
        '城': 'culture',
        '寺院': 'culture',
        '神社': 'culture',
        '博物館': 'culture',
        '美術館': 'culture',
        'レストラン': 'gourmet',
        '飲食店': 'gourmet',
        'ショッピングモール': 'shopping',
        'テーマパーク': 'activity',
        '動物園': 'activity',
        '水族館': 'activity',
        'ウォーターパーク': 'activity',
        '公園': 'nature',
    }
    return mapping.get(spot_type, 'other')


def load_spots_data():
    """spots.jsonデータを読み込み"""
    try:
        spots_file = os.path.join(BASE_DIR, 'data', 'spots.json')
        if not os.path.exists(spots_file):
            print(f"警告: spots.jsonが見つかりません: {spots_file}")
            return {'categories': {}}
        
        with open(spots_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"spots.json読み込みエラー: {e}")
        return {'categories': {}}


def fetch_spots_from_overpass(category_keys: List[str], prefecture_key: str = None, limit: int = 30) -> List[Dict]:
    """Overpass APIから指定カテゴリーのスポットを取得（PostgreSQLキャッシュ対応版）"""
    
    # ★★★ キャッシュキーを生成 ★★★
    cache_key = generate_cache_key(prefecture_key or 'kansai', category_keys)
    
    # ★★★ データベースからキャッシュをチェック ★★★
    cached_spots = get_cache_from_db(cache_key)
    if cached_spots:
        return cached_spots
    
    # キャッシュがない場合は通常通りOverpass APIから取得
    # 都道府県の境界を取得
    if prefecture_key and prefecture_key in PREFECTURE_BOUNDS:
        bounds, pref_name = PREFECTURE_BOUNDS[prefecture_key]
        south, west, north, east = bounds
        print(f"📍 検索範囲: {pref_name} ({south}, {west}, {north}, {east})")
    else:
        # デフォルト: 関西全域
        south, west, north, east = 34.0, 135.0, 36.0, 136.5
        pref_name = "関西全域"
        print(f"📍 検索範囲: {pref_name}（デフォルト）")
    
    # カテゴリーごとに分割したクエリ定義
    category_queries = {
        'relax': f"""[out:json][timeout:15];
(
  node["leisure"="spa"]({south},{west},{north},{east});
  node["amenity"="onsen"]({south},{west},{north},{east});
);
out body 30;""",
        
        'nature': f"""[out:json][timeout:15];
(
  node["natural"="peak"]({south},{west},{north},{east});
  node["tourism"="viewpoint"]({south},{west},{north},{east});
  node["natural"="waterfall"]({south},{west},{north},{east});
  node["leisure"="garden"]({south},{west},{north},{east});
);
out body 30;""",
        
        'culture': f"""[out:json][timeout:15];
(
  node["historic"="castle"]({south},{west},{north},{east});
  node["tourism"="museum"]({south},{west},{north},{east});
  node["religion"="buddhist"]["name"]({south},{west},{north},{east});
  node["religion"="shinto"]["name"]({south},{west},{north},{east});
);
out body 30;""",
        
        'activity': f"""[out:json][timeout:15];
(
  node["tourism"="theme_park"]({south},{west},{north},{east});
  node["tourism"="zoo"]({south},{west},{north},{east});
  node["tourism"="aquarium"]({south},{west},{north},{east});
  node["amenity"="theatre"]({south},{west},{north},{east});
);
out body 30;""",
        
        'shopping': f"""[out:json][timeout:15];
(
  node["shop"="mall"]({south},{west},{north},{east});
  node["amenity"="marketplace"]({south},{west},{north},{east});
);
out body 30;"""
    }
    
    print(f"\n{'='*60}")
    print(f"🔍 Overpass APIクエリ実行（{pref_name}）")
    print(f"📊 対象カテゴリー: {category_keys}")
    print(f"{'='*60}\n")
    
    all_elements = []
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # カテゴリーごとに個別リクエスト
    for cat_key in category_keys:
        if cat_key not in category_queries:
            print(f"⚠️ 未定義カテゴリーをスキップ: '{cat_key}'")
            continue
        
        query = category_queries[cat_key]
        
        print(f"🔄 カテゴリー '{cat_key}' を取得中...")
        
        try:
            response = requests.post(
                overpass_url,
                data={'data': query},
                timeout=20
            )
            
            if response.status_code != 200:
                print(f"  ❌ ステータス {response.status_code}")
                continue
            
            data = response.json()
            elements = data.get('elements', [])
            
            print(f"  ✅ {len(elements)}件取得")
            
            if 'remark' in data:
                print(f"  ⚠️ remark: {data['remark']}")
            
            all_elements.extend(elements)
            
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            continue
    
    print(f"\n📦 合計取得: {len(all_elements)}件")
    
    if not all_elements:
        print("⚠️ 全カテゴリーで0件")
        return []
    
    # スポット変換処理
    spots_dict = {}
    stats = {'filtered': 0, 'no_name': 0, 'no_coords': 0}
    
    for element in all_elements:
        tags = element.get('tags', {})
        if not tags:
            continue
        
        element_id = element.get('id')
        lat = element.get('lat') or element.get('center', {}).get('lat')
        lon = element.get('lon') or element.get('center', {}).get('lon')
        
        if not lat or not lon:
            stats['no_coords'] += 1
            continue
        
        name = tags.get('name:ja') or tags.get('name') or tags.get('name:en')
        if not name:
            stats['no_name'] += 1
            continue
        
        if len(name) > 40:
            stats['filtered'] += 1
            continue
        
        bad_keywords = ['詰所', '案内', '駐車場', 'トイレ', '入口', '出口', '売店', 
                       'ゲート', '記念碑', '乗り場', '受付']
        if any(kw in name for kw in bad_keywords):
            stats['filtered'] += 1
            continue
        
        if element_id in spots_dict:
            continue
        
        # スポットタイプ判定（拡充版）
        spot_type = 'その他'
        
        # 文化・歴史系
        if tags.get('historic') == 'castle':
            spot_type = '城'
        elif tags.get('religion') == 'buddhist':
            spot_type = '寺院'
        elif tags.get('religion') == 'shinto':
            spot_type = '神社'
        elif tags.get('tourism') == 'museum':
            spot_type = '博物館'
        elif tags.get('tourism') == 'gallery':
            spot_type = '美術館'
        elif tags.get('amenity') == 'arts_centre':
            spot_type = 'アートセンター'
        elif tags.get('historic') == 'monument':
            spot_type = 'モニュメント'
        
        # アクティビティ系
        elif tags.get('tourism') == 'theme_park':
            spot_type = 'テーマパーク'
        elif tags.get('tourism') == 'zoo':
            spot_type = '動物園'
        elif tags.get('tourism') == 'aquarium':
            spot_type = '水族館'
        elif tags.get('leisure') == 'water_park':
            spot_type = 'ウォーターパーク'
        elif tags.get('leisure') == 'sports_centre':
            spot_type = 'スポーツセンター'
        elif tags.get('leisure') == 'stadium':
            spot_type = 'スタジアム'
        elif tags.get('amenity') == 'theatre':
            spot_type = '劇場'
        elif tags.get('amenity') == 'cinema':
            spot_type = '映画館'
        
        # 自然系
        elif tags.get('tourism') == 'viewpoint':
            spot_type = '展望台'
        elif tags.get('leisure') == 'park':
            spot_type = '公園'
        elif tags.get('leisure') == 'garden':
            spot_type = '庭園'
        elif tags.get('natural') == 'peak':
            spot_type = '山'
        elif tags.get('natural') == 'beach':
            spot_type = 'ビーチ'
        elif tags.get('natural') == 'waterfall':
            spot_type = '滝'
        elif tags.get('natural') == 'spring':
            spot_type = '泉'
        elif tags.get('natural') == 'cave_entrance':
            spot_type = '洞窟'
        
        # リラックス系
        elif tags.get('leisure') == 'spa':
            spot_type = '温泉'
        elif tags.get('amenity') == 'onsen':
            spot_type = '温泉'
        elif tags.get('leisure') == 'hot_spring':
            spot_type = '温泉'
        elif tags.get('amenity') == 'public_bath':
            spot_type = '銭湯'
        
        # ショッピング系
        elif tags.get('shop') == 'mall':
            spot_type = 'ショッピングモール'
        elif tags.get('shop') == 'department_store':
            spot_type = '百貨店'
        elif tags.get('amenity') == 'marketplace':
            spot_type = '市場'
        
        # その他
        elif tags.get('amenity') == 'restaurant':
            spot_type = 'レストラン'
        
        category = map_type_to_category(spot_type)
        category_key = determine_category_key(spot_type)
        
        city = tags.get('addr:city', '')
        street = tags.get('addr:street', '')
        address = f"{city} {street}".strip() or '住所情報なし'
        
        spots_dict[element_id] = {
            'id': f"overpass_{element_id}",
            'name': name,
            'lat': float(lat),
            'lon': float(lon),
            'type': spot_type,
            'category': category,
            'category_key': category_key,
            'address': address,
            'prefecture': pref_name
        }
    
    spots = list(spots_dict.values())
    
    print(f"\n✅ 最終スポット数: {len(spots)}件")
    print(f"🚫 統計: フィルタ={stats['filtered']}, 名前なし={stats['no_name']}, 座標なし={stats['no_coords']}")
    
    # ★★★ データベースに保存 ★★★
    if spots:
        save_cache_to_db(cache_key, spots, prefecture_key or 'kansai', category_keys)
    
    if spots:
        print(f"\n📋 取得例:")
        for i, spot in enumerate(spots[:5], 1):
            print(f"  {i}. {spot['name']} ({spot['type']}) - {spot['category_key']}")
    
    return spots
def get_recommended_spots_from_api(analysis: Dict, num_spots: int = 6, departure_point: Dict = None) -> List[Dict]:
    """Overpass APIを使ってスポットを推薦（都道府県フィルタ対応版）"""
    print(f"デバッグ: 分析結果 = {analysis}")
    
    # 都道府県キーを取得
    prefecture_key = None
    if departure_point and 'prefecture_key' in departure_point:
        prefecture_key = departure_point['prefecture_key']
    
    print(f"📍 検索対象都道府県: {prefecture_key or '指定なし'}")
    
    all_categories = analysis['primary'] + analysis['secondary']
    print(f"デバッグ: 対象カテゴリー = {all_categories}")
    
    # Overpass APIからスポットを取得（都道府県を渡す）
    spots = []
    try:
        spots = fetch_spots_from_overpass(all_categories, prefecture_key=prefecture_key, limit=50)
        print(f"デバッグ: Overpass APIから {len(spots)} 件取得")
    except Exception as e:
        print(f"Overpass API 例外: {e}")
        spots = []
    
    # フォールバック処理
    if not spots:
        print("警告: Overpass APIからデータ取得失敗。JSONデータを使用します")
        spots_data = load_spots_data()
        print(f"デバッグ: JSONデータ読み込み = {bool(spots_data)}")
        
        if spots_data and spots_data.get('categories'):
            print(f"デバッグ: JSONカテゴリー数 = {len(spots_data['categories'])}")
            
            # すべてのカテゴリーからスポットを集める
            all_fallback_spots = []
            for category_key, category_data in spots_data['categories'].items():
                for spot in category_data.get('spots', []):
                    spot['category_key'] = category_key
                    all_fallback_spots.append(spot)
            
            print(f"デバッグ: JSONスポット総数 = {len(all_fallback_spots)}")
            
            if all_fallback_spots:
                # カテゴリーでフィルタリング
                filtered_spots = [s for s in all_fallback_spots if s.get('category_key') in all_categories]
                
                if not filtered_spots:
                    filtered_spots = all_fallback_spots
                
                spots = filtered_spots
    
    # Overpass APIまたはJSONからスポットが取得できた場合
    if spots:
        # カテゴリー別に分類
        primary_spots = [s for s in spots if s.get('category_key') in analysis['primary']]
        secondary_spots = [s for s in spots if s.get('category_key') in analysis['secondary']]
        other_spots = [s for s in spots if s not in primary_spots and s not in secondary_spots]
        
        print(f"📦 カテゴリー別分類:")
        print(f"  - 主要: {len(primary_spots)}件")
        print(f"  - 補助: {len(secondary_spots)}件")
        print(f"  - その他: {len(other_spots)}件")
        
        recommended = []
        
        # 主要カテゴリーから60%選択
        primary_count = max(1, int(num_spots * 0.6))
        if primary_spots:
            selected = random.sample(primary_spots, min(primary_count, len(primary_spots)))
            recommended.extend(selected)
            print(f"  ✓ 主要から{len(selected)}件選択")
        
        # 補助カテゴリーから30%選択
        remaining = num_spots - len(recommended)
        secondary_count = max(0, min(int(num_spots * 0.3), remaining))
        if secondary_count > 0 and secondary_spots:
            selected = random.sample(secondary_spots, min(secondary_count, len(secondary_spots)))
            recommended.extend(selected)
            print(f"  ✓ 補助から{len(selected)}件選択")
        
        # まだ足りない場合は優先順に追加
        remaining = num_spots - len(recommended)
        if remaining > 0:
            pool = []
            if primary_spots:
                pool.extend([s for s in primary_spots if s not in recommended])
            if secondary_spots:
                pool.extend([s for s in secondary_spots if s not in recommended])
            if other_spots:
                pool.extend(other_spots)
            
            if pool:
                selected = random.sample(pool, min(remaining, len(pool)))
                recommended.extend(selected)
                print(f"  ✓ 不足分を補充: {len(selected)}件")
        
        print(f"\n✅ 最終選択: {len(recommended)}スポット")
        for i, spot in enumerate(recommended, 1):
            print(f"  {i}. {spot['name']} ({spot['type']})")
        
        return recommended[:num_spots]
    
    # 両方失敗した場合
    print("エラー: Overpass APIとJSONデータの両方が利用できません")
    return get_fallback_hardcoded_spots(analysis, num_spots)









# analyze_answers の修正
def analyze_answers(answers: Dict) -> Dict:
    """アンケート回答を分析してカテゴリーを決定（年齢層対応版）"""
    mood = answers.get('mood', '')
    purpose = answers.get('purpose', '')
    budget = answers.get('budget', '')
    duration = answers.get('duration', '')
    age = answers.get('age', '')  # ← companion → age
    
    result = {
        'primary': [],
        'secondary': [],
        'tertiary': [],
        'filters': {
            'budget': budget,
            'duration': duration,
            'age': age  # ← companion → age
        }
    }
    
    # ★★★ 目的からメインカテゴリーを決定（変更なし） ★★★
    purpose_mapping = {
        'relax': {
            'primary': ['nature', 'culture'],
            'secondary': ['relax', 'activity']
        },
        'adventure': {
            'primary': ['activity', 'nature'],
            'secondary': ['culture']
        },
        'culture': {
            'primary': ['culture', 'nature'],
            'secondary': ['activity']
        },
        'activity': {
            'primary': ['activity', 'nature'],
            'secondary': ['culture']
        }
    }
    
    if purpose in purpose_mapping:
        purpose_data = purpose_mapping[purpose]
        result['primary'].extend(purpose_data['primary'])
        result['secondary'].extend(purpose_data['secondary'])
    
    # ★★★ 気分による調整（変更なし） ★★★
    mood_adjustments = {
        'excited': {
            'boost': ['activity'],
            'add_secondary': ['culture']
        },
        'relaxed': {
            'boost': ['nature'],
            'add_secondary': ['culture', 'relax']
        },
        'adventurous': {
            'boost': ['activity', 'nature'],
            'add_secondary': []
        },
        'chilled': {
            'boost': ['nature', 'culture'],
            'add_secondary': ['relax']
        }
    }
    
    if mood in mood_adjustments:
        adjustment = mood_adjustments[mood]
        
        # boostされたカテゴリーをprimaryに昇格
        for cat in adjustment.get('boost', []):
            if cat in result['secondary'] and cat not in result['primary']:
                result['secondary'].remove(cat)
                result['primary'].append(cat)
            elif cat not in result['primary']:
                result['primary'].append(cat)
        
        # 追加のsecondaryカテゴリー
        for cat in adjustment.get('add_secondary', []):
            if cat not in result['primary'] and cat not in result['secondary']:
                result['secondary'].append(cat)
    
    # ★★★ 年齢層による調整（新規実装） ★★★
    age_adjustments = {
        'young': {  # 10代・20代
            'boost': ['activity'],  # テーマパーク、水族館、動物園を優先
            'add_secondary': ['shopping', 'nature']
        },
        'family': {  # 30代・40代（ファミリー層）
            'boost': ['activity', 'nature'],  # 家族向けスポット、公園
            'add_secondary': ['culture']
        },
        'senior': {  # 50代・60代
            'boost': ['culture', 'relax'],  # 温泉、神社仏閣、庭園を優先
            'add_secondary': ['nature']
        }
    }
    
    if age in age_adjustments:
        adjustment = age_adjustments[age]
        
        # boostされたカテゴリーをprimaryに昇格
        for cat in adjustment.get('boost', []):
            if cat in result['secondary'] and cat not in result['primary']:
                result['secondary'].remove(cat)
                result['primary'].append(cat)
            elif cat not in result['primary']:
                result['primary'].append(cat)
        
        # 追加のsecondaryカテゴリー
        for cat in adjustment.get('add_secondary', []):
            if cat not in result['primary'] and cat not in result['secondary']:
                result['secondary'].append(cat)
    
    # ★★★ 最低限のカテゴリー数を確保（変更なし） ★★★
    # primaryが2個未満なら、secondaryから昇格
    while len(result['primary']) < 2 and result['secondary']:
        result['primary'].append(result['secondary'].pop(0))
    
    # secondaryが1個未満なら、利用可能なカテゴリーから追加
    all_categories = ['culture', 'nature', 'activity', 'relax', 'shopping']
    available = [c for c in all_categories if c not in result['primary'] and c not in result['secondary']]
    
    while len(result['secondary']) < 2 and available:
        # relaxとshoppingは最後に追加（優先度低）
        if 'culture' in available:
            result['secondary'].append('culture')
            available.remove('culture')
        elif 'nature' in available:
            result['secondary'].append('nature')
            available.remove('nature')
        elif 'activity' in available:
            result['secondary'].append('activity')
            available.remove('activity')
        elif available:
            result['secondary'].append(available.pop(0))
    
    # 重複削除
    result['primary'] = list(dict.fromkeys(result['primary']))
    result['secondary'] = list(dict.fromkeys(result['secondary']))
    result['secondary'] = [c for c in result['secondary'] if c not in result['primary']]
    
    return result

# APIエンドポイントも修正
@app.route('/api/recommend', methods=['GET'])
def api_recommend():
    """推薦API（プラン生成版）"""
    import time
    start_time = time.time()
    
    print("\n" + "="*60)
    print("🚀 /api/recommend リクエスト受信")
    print("="*60)
    
    answers = {
        'prefecture': request.args.get('prefecture', ''),
        'mood': request.args.get('mood', ''),
        'purpose': request.args.get('purpose', ''),
        'budget': request.args.get('budget', ''),
        'duration': request.args.get('duration', ''),
        'age': request.args.get('age', '')
    }
    
    print(f"📝 回答内容:")
    for key, value in answers.items():
        print(f"  {key}: {value}")
    
    # バリデーション
    required_fields = ['prefecture', 'mood', 'purpose', 'budget', 'duration', 'age']
    missing_fields = [f for f in required_fields if not answers.get(f)]
    
    if missing_fields:
        print(f"❌ バリデーションエラー: 未回答あり - {missing_fields}")
        return jsonify({
            'success': False,
            'message': 'すべての質問に回答してください'
        }), 400
    
    try:
        # 分析
        analysis = analyze_answers(answers)
        print(f"\n📊 分析完了:")
        print(f"  主要: {analysis['primary']}")
        print(f"  補助: {analysis['secondary']}")
        
        # プラン付きで取得
        result = api_recommend_with_plan(answers, analysis)
        
        if not result['success']:
            print("⚠️ スポット取得失敗")
            return jsonify(result), 500
        
        elapsed_time = time.time() - start_time
        print(f"\n⏱️ プラン生成にかかった時間: {elapsed_time:.2f}秒")
        print(f"✅ プラン生成成功")
        print("="*60 + "\n")
        
        return jsonify(result), 200
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n⏱️ 処理時間（エラー発生）: {elapsed_time:.2f}秒")
        print(f"\n❌ 推薦処理エラー: {e}")
        import traceback
        traceback.print_exc()
        print("="*60 + "\n")
        
        return jsonify({
            'success': False,
            'message': f'エラーが発生しました: {str(e)}'
        }), 500
    







def generate_daily_itinerary(spots: List[Dict], duration_days: int = 1, 
                            start_time: str = "09:00") -> List[Dict]:
    """日ごとの詳細スケジュールを生成（type多様性対応版）"""
    
    max_spots_per_day = 3  # 1日最大3スポット
    max_distance_per_day = 250  # 1日の最大移動距離（km）
    
    itineraries = []
    remaining_spots = spots.copy()
    
    print(f"\n📅 日程配分: {len(spots)}スポット ÷ {duration_days}日")
    
    for day_num in range(1, duration_days + 1):
        if not remaining_spots:
            break
        
        day_schedule = {
            'day': day_num,
            'date': (datetime.now() + timedelta(days=day_num-1)).strftime('%Y年%m月%d日'),
            'activities': []
        }
        
        # 残り日数で均等に分配、ただし最大3スポットまで
        remaining_days = duration_days - day_num + 1
        remaining_spot_count = len(remaining_spots)
        
        if remaining_days == 1:
            day_spot_count = min(max_spots_per_day, remaining_spot_count)
        else:
            ideal_count = (remaining_spot_count + remaining_days - 1) // remaining_days
            day_spot_count = min(max_spots_per_day, ideal_count)
        
        print(f"  {day_num}日目: {day_spot_count}スポット（初期配分）")
        
        # ★★★ その日のスポットを選択（type重複チェック付き） ★★★
        day_spots = []
        used_types = set()  # その日に既に使われたtypeを記録
        
        attempts = 0  # 無限ループ防止
        max_attempts = len(remaining_spots) * 2
        
        while len(day_spots) < day_spot_count and remaining_spots and attempts < max_attempts:
            attempts += 1
            
            # 先頭のスポットを取得
            spot = remaining_spots.pop(0)
            spot_type = spot.get('type', 'その他')
            
            # まだ使われていないtypeなら追加
            if spot_type not in used_types:
                day_spots.append(spot)
                used_types.add(spot_type)
                print(f"    ✅ 追加: {spot['name']} ({spot_type})")
            else:
                # 既に同じtypeがある場合は、リストの最後に戻す
                remaining_spots.append(spot)
                print(f"    ⏭️ スキップ: {spot['name']} ({spot_type}) - 既に{spot_type}あり")
        
        if len(day_spots) < day_spot_count and attempts >= max_attempts:
            print(f"    ⚠️ 多様性確保のため、{day_spot_count}スポット中{len(day_spots)}スポットのみ選択")
        
        # ルート最適化
        if len(day_spots) > 1:
            day_spots = optimize_daily_route(day_spots)
        
        # 距離チェック：250kmを超えたらスポットを減らす
        total_distance = calculate_route_distance(day_spots)
        print(f"  📏 初期総距離: {total_distance}km")
        
        while total_distance > max_distance_per_day and len(day_spots) > 1:
            # 最後のスポットを削除して再計算
            removed_spot = day_spots.pop()
            remaining_spots.insert(0, removed_spot)  # 削除したスポットは次の日に回す
            total_distance = calculate_route_distance(day_spots)
            print(f"  ⚠️ {max_distance_per_day}km超過 → スポット削減: {total_distance}km")
        
        print(f"  ✅ 最終: {len(day_spots)}スポット, {total_distance}km")
        
        # 時刻を簡易計算（2-3時間ごとに配置）
        time_slots = ["09:00", "11:30", "14:00"]
        
        for i, spot in enumerate(day_spots):
            if i >= len(time_slots):
                break
            
            # スポット追加
            day_schedule['activities'].append({
                'type': 'spot',
                'time': time_slots[i],
                'name': f"{spot.get('image', '📍')} {spot['name']}",
                'spot_data': spot
            })
        
        # 終了時刻（最後のスポット + 2時間）
        last_time = time_slots[min(len(day_spots)-1, len(time_slots)-1)]
        hour, minute = map(int, last_time.split(':'))
        end_hour = hour + 2
        day_schedule['end_time'] = f"{end_hour:02d}:{minute:02d}"
        
        # その日の総距離を記録
        day_schedule['total_distance'] = total_distance
        print(f"  📊 {day_num}日目の移動距離: {total_distance}km")
        
        itineraries.append(day_schedule)
    
    return itineraries

def create_travel_plan(spots: List[Dict], answers: Dict) -> Dict:
    """完全な旅行プランを作成（住所補完対応版）"""
    
    # 期間の決定
    duration_mapping = {
        'short': 1,
        'medium': 3,
        'long': 5
    }
    duration_days = duration_mapping.get(answers.get('duration', 'short'), 1)
    
    print(f"\n📅 旅行期間: {duration_days}日間")
    print(f"📍 スポット総数: {len(spots)}件")
    
    # スポット数が少ない場合は日数を調整
    if len(spots) < duration_days * 3:
        duration_days = max(1, len(spots) // 3)
        print(f"⚠️ スポット数が少ないため、{duration_days}日間に調整")
    
    # 日程作成
    itineraries = generate_daily_itinerary(spots, duration_days)
    
    # ★★★ プラン内スポットの住所補完 ★★★
    # プランに含まれる全スポットのリストを作成
    plan_spots = []
    for day in itineraries:
        for activity in day['activities']:
            if activity['type'] == 'spot':
                plan_spots.append(activity['spot_data'])
    
    # 住所がないスポットだけ逆ジオコーディング
    print(f"\n🔄 プラン内スポットの住所補完中... ({len(plan_spots)}件)")
    address_updated = 0
    for i, spot in enumerate(plan_spots, 1):
      print(f"  [{i}/{len(plan_spots)}] {spot['name']}: 現在の住所=「{spot.get('address', 'なし')}」")
    
      if not spot.get('address') or spot['address'] == '住所情報なし' or spot['address'] == '':
        print(f"    🔄 住所取得中... ({spot['lat']}, {spot['lon']})")
        new_address = reverse_geocode(spot['lat'], spot['lon'])
        spot['address'] = new_address
        print(f"    ✅ 取得完了: {new_address}")
        address_updated += 1
        time.sleep(1.1)  # レート制限対策
      else:
        print(f"    ⏭️ スキップ（既に住所あり）")

    print(f"✅ 住所補完完了（{address_updated}件更新）")
    
    # プラン全体のサマリー
    total_distance = sum(day['total_distance'] for day in itineraries)
    total_spots = sum(len([a for a in day['activities'] if a['type'] == 'spot']) for day in itineraries)
    
    plan = {
        'title': f"{duration_days}日間の関西旅行プラン",
        'summary': {
            'duration_days': duration_days,
            'total_spots': total_spots,
            'total_distance': round(total_distance, 1),
            'budget_level': answers.get('budget', 'medium'),
            'age': answers.get('age', 'family')
        },
        'itineraries': itineraries
    }
    
    return plan

def filter_spots_by_prefecture(spots: List[Dict], prefecture_key: str) -> List[Dict]:
    """スポットを都道府県でフィルタリング"""
    if not prefecture_key or prefecture_key not in PREFECTURE_BOUNDS:
        return spots
    
    bounds, pref_name = PREFECTURE_BOUNDS[prefecture_key]
    min_lat, min_lon, max_lat, max_lon = bounds
    
    print(f"\n🔍 都道府県フィルタリング: {pref_name}")
    print(f"   境界: lat({min_lat}~{max_lat}), lon({min_lon}~{max_lon})")
    print(f"   フィルタ前: {len(spots)}件")
    
    filtered_spots = []
    for spot in spots:
        lat = spot.get('lat')
        lon = spot.get('lon')
        
        if lat and lon:
            # 境界ボックス内かチェック
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                filtered_spots.append(spot)
            else:
                print(f"   ❌ 除外: {spot['name']} ({lat}, {lon})")
    
    print(f"   フィルタ後: {len(filtered_spots)}件\n")
    
    return filtered_spots




def api_recommend_with_plan(answers: Dict, analysis: Dict) -> Dict:
    """プラン付き推薦APIレスポンスを生成（カテゴリー拡張機能付き）"""
    
    # 期間に応じたスポット数を決定
    duration = answers.get('duration', 'short')
    duration_to_spots = {
        'short': 7,
        'medium': 15,
        'long': 24
    }
    required_spots = duration_to_spots.get(duration, 4)
    
    print(f"\n🎯 期間「{duration}」に対して{required_spots}スポット必要")
    
    # 都道府県から出発地情報を生成
    prefecture_key = answers.get('prefecture', '')
    departure_point = None
    
    if prefecture_key in PREFECTURE_CENTERS:
        pref_data = PREFECTURE_CENTERS[prefecture_key]
        departure_point = {
            'name': pref_data['name'],
            'lat': pref_data['lat'],
            'lon': pref_data['lon'],
            'prefecture': pref_data['name'],
            'prefecture_key': prefecture_key
        }
        print(f"📍 都道府県中心を出発地に設定: {departure_point['name']} ({departure_point['lat']}, {departure_point['lon']})")
    else:
        print(f"⚠️ 不明な都道府県: {prefecture_key}")
    
    # ★★★ カテゴリー拡張ロジック ★★★
    max_retries = 3
    attempt = 1
    all_spots = []
    
    # 利用可能な全カテゴリー
    all_categories = ['culture', 'nature', 'activity', 'relax', 'shopping']
    current_analysis = analysis.copy()
    
    while len(all_spots) < required_spots and attempt <= max_retries:
        print(f"\n🔄 スポット取得試行 {attempt}/{max_retries}...")
        print(f"   📂 使用カテゴリー: primary={current_analysis['primary']}, secondary={current_analysis['secondary']}")
        
        # 取得するスポット数を増やす
        fetch_count = required_spots + (attempt - 1) * 10
        
        # スポット取得
        spots = get_recommended_spots_from_api(
            current_analysis, 
            num_spots=fetch_count,
            departure_point=departure_point
        )
        
        # 都道府県フィルタリング
        if prefecture_key and spots:
            spots = filter_spots_by_prefecture(spots, prefecture_key)
        
        # 重複を除いて追加
        for spot in spots:
            spot_id = spot.get('id') or f"{spot.get('lat')}_{spot.get('lon')}"
            existing_ids = [s.get('id') or f"{s.get('lat')}_{s.get('lon')}" for s in all_spots]
            
            if spot_id not in existing_ids:
                all_spots.append(spot)
        
        print(f"   📦 取得後の合計スポット数: {len(all_spots)}件")
        
        if len(all_spots) >= required_spots:
            print(f"   ✅ 必要数({required_spots}件)に到達しました")
            break
        
        # ★★★ 次の試行でカテゴリーを拡張 ★★★
        if attempt < max_retries:
            # まだ使っていないカテゴリーを追加
            used_categories = current_analysis['primary'] + current_analysis['secondary']
            unused_categories = [c for c in all_categories if c not in used_categories]
            
            if unused_categories:
                # 1つずつカテゴリーを追加
                new_category = unused_categories[0]
                current_analysis['secondary'].append(new_category)
                print(f"   🔄 カテゴリーを追加: {new_category}")
            else:
                # 全カテゴリー使い切った場合は取得数を大幅に増やす
                print(f"   ⚠️ 全カテゴリー使用済み。取得数を大幅に増やします")
        
        attempt += 1
    
    # ★★★ 最終チェック ★★★
    if len(all_spots) == 0:
        return {
            'success': False,
            'message': 'スポットを取得できませんでした。別の条件でお試しください。'
        }
    
    if len(all_spots) < 3:
        print(f"⚠️ スポット数が少なすぎます({len(all_spots)}件)")
        return {
            'success': False,
            'message': f'選択された条件で十分なスポットが見つかりませんでした（{len(all_spots)}件のみ）。別の都道府県や条件をお試しください。'
        }
    
    if len(all_spots) < required_spots:
        print(f"⚠️ 必要数({required_spots}件)に達していませんが、{len(all_spots)}件でプラン生成を続行")
    
    # 旅行プラン生成
    travel_plan = create_travel_plan(all_spots[:required_spots], answers)
    
    return {
        'success': True,
        'plan': travel_plan,
        'spots': all_spots[:required_spots],
        'analysis': analysis
    }




def get_fallback_hardcoded_spots(analysis: Dict, num_spots: int) -> List[Dict]:
    """最終フォールバック：ハードコードされたスポット"""
    print("警告: ハードコードされたスポットを使用します")
    
    # シンプルなフォールバックスポット
    fallback_spots = [
        {
            'id': 'fallback_1',
            'name': '大阪城公園',
            'lat': 34.6873,
            'lon': 135.5259,
            'category': '文化・歴史',
            'category_key': 'culture',
            'address': '大阪府大阪市中央区大阪城',
            'description': '大阪のシンボルである大阪城を中心とした広大な公園です。',
            'image': '🏯',
            'tags': ['城', '公園', '歴史']
        },
        {
            'id': 'fallback_2', 
            'name': '清水寺',
            'lat': 34.9949,
            'lon': 135.7851,
            'category': '文化・歴史',
            'category_key': 'culture',
            'address': '京都府京都市東山区清水',
            'description': '京都で最も有名な寺院の一つで、舞台からの景色が絶景です。',
            'image': '🏯',
            'tags': ['寺院', '世界遺産']
        },
        {
            'id': 'fallback_3',
            'name': 'ユニバーサル・スタジオ・ジャパン',
            'lat': 34.6654,
            'lon': 135.4323,
            'category': 'アクティビティ', 
            'category_key': 'activity',
            'address': '大阪府大阪市此花区桜島',
            'description': '人気のテーマパークで、ハリウッド映画の世界を体験できます。',
            'image': '🎢',
            'tags': ['テーマパーク', 'アトラクション']
        }
    ]
    
    # 分析結果に基づいてフィルタリング
    all_categories = analysis['primary'] + analysis['secondary']
    filtered = [spot for spot in fallback_spots if spot.get('category_key') in all_categories]
    
    if filtered:
        return random.sample(filtered, min(num_spots, len(filtered)))
    else:
        return random.sample(fallback_spots, min(num_spots, len(fallback_spots)))
# HTMLファイルの配信

# プラン保存API
@app.route('/api/plans/save', methods=['POST'])
def save_plan():
    """旅行プランを保存"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
    
    data = request.get_json()
    plan_title = data.get('plan_title')
    plan_data = data.get('plan_data')
    
    if not plan_title or not plan_data:
        return jsonify({'success': False, 'message': 'プランデータが不足しています'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        # プランを保存
        cur.execute(
            '''INSERT INTO saved_plans (user_id, plan_title, plan_data, created_at, updated_at)
               VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
               RETURNING id, plan_title, created_at''',
            (session['user_id'], plan_title, json.dumps(plan_data, ensure_ascii=False))
        )
        
        saved_plan = cur.fetchone()
        conn.commit()
        
        print(f"✅ プラン保存成功: plan_id={saved_plan['id']}, user_id={session['user_id']}")
        
        return jsonify({
            'success': True,
            'message': 'プランを保存しました',
            'plan': dict(saved_plan)
        }), 201
        
    except Exception as e:
        conn.rollback()
        print(f"❌ プラン保存エラー: {e}")
        return jsonify({'success': False, 'message': f'サーバーエラー: {str(e)}'}), 500
    finally:
        cur.close()
        conn.close()


# 保存済プラン一覧取得API
@app.route('/api/plans/saved', methods=['GET'])
def get_saved_plans():
    """ユーザーの保存済プラン一覧を取得"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute(
            '''SELECT id, plan_title, plan_data, created_at, updated_at
               FROM saved_plans
               WHERE user_id = %s
               ORDER BY created_at DESC''',
            (session['user_id'],)
        )
        
        plans = cur.fetchall()
        
        print(f"✅ 保存済プラン取得: {len(plans)}件")
        
        return jsonify({
            'success': True,
            'count': len(plans),
            'plans': [dict(plan) for plan in plans]
        }), 200
        
    except Exception as e:
        print(f"❌ プラン取得エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()


# 特定プラン取得API
@app.route('/api/plans/<int:plan_id>', methods=['GET'])
def get_plan_by_id(plan_id):
    """特定のプランを取得"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute(
            '''SELECT id, user_id, plan_title, plan_data, created_at, updated_at
               FROM saved_plans
               WHERE id = %s AND user_id = %s''',
            (plan_id, session['user_id'])
        )
        
        plan = cur.fetchone()
        
        if not plan:
            return jsonify({'success': False, 'message': 'プランが見つかりません'}), 404
        
        return jsonify({
            'success': True,
            'plan': dict(plan)
        }), 200
        
    except Exception as e:
        print(f"❌ プラン取得エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()


# プラン削除API
@app.route('/api/plans/<int:plan_id>', methods=['DELETE'])
def delete_plan(plan_id):
    """保存済プランを削除"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        # プランの所有者確認
        cur.execute(
            'SELECT * FROM saved_plans WHERE id = %s AND user_id = %s',
            (plan_id, session['user_id'])
        )
        plan = cur.fetchone()
        
        if not plan:
            return jsonify({'success': False, 'message': 'プランが見つからないか、削除権限がありません'}), 404
        
        # プラン削除
        cur.execute('DELETE FROM saved_plans WHERE id = %s', (plan_id,))
        conn.commit()
        
        print(f"✅ プラン削除成功: plan_id={plan_id}")
        
        return jsonify({'success': True, 'message': 'プランを削除しました'}), 200
        
    except Exception as e:
        conn.rollback()
        print(f"❌ プラン削除エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()




@app.route('/questionnaire')

def questionnaire():
    """アンケートページを表示"""
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'questionnaire.html')



@app.route('/proposal')
def proposal():
    """
    提案ページを表示（修正版）
    JavaScriptがlocalStorageから読み取るため、単純にHTMLを返す
    """
    print("=== 提案ページリクエスト受信 ===")
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'proposal.html')



def generate_simple_proposal_html(answers: Dict, spots: List[Dict], analysis: Dict) -> str:
    """簡易版の提案HTMLを生成（proposal.htmlがない場合のフォールバック）"""
    spots_html = ""
    for spot in spots:
        spots_html += f'''
        <div style="border: 2px solid #e0e0e0; border-radius: 15px; padding: 20px; margin-bottom: 20px;">
            <div style="font-size: 3em; text-align: center;">{spot.get('image', '📍')}</div>
            <h3 style="color: #667eea; text-align: center;">{spot.get('name', '')}</h3>
            <p style="color: #666;">{spot.get('description', '')}</p>
            <p style="color: #999; font-size: 0.9em;">📍 {spot.get('address', '')}</p>
        </div>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>旅行プラン提案</title>
        <style>
            body {{
                font-family: sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                margin: 0;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                padding: 40px;
            }}
            h1 {{
                color: #667eea;
                text-align: center;
            }}
            .spots-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }}
            .button {{
                display: inline-block;
                padding: 15px 30px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                font-weight: bold;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✨ あなたにおすすめの旅行プラン</h1>
            <div class="spots-grid">
                {spots_html}
            </div>
            <div style="text-align: center; margin-top: 40px;">
                <a href="/questionnaire" class="button">🔄 もう一度診断する</a>
                <a href="/" class="button">🏠 トップに戻る</a>
            </div>
        </div>
    </body>
    </html>
    ''',500
#####################################################################################################
#####################################################################################################


#レビュー機能
######################################################################################################
######################################################################################################
#レビュー機能ここから下全て変更した11/22

@app.route('/api/check-login', methods=['GET', 'OPTIONS'])
def check_login():
    """ログイン状態を確認"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
    
    print(f"\n=== ログイン状態確認 ===")
    print(f"Cookie: {request.cookies}")
    print(f"セッション: {dict(session)}")
    print(f"user_id in session: {'user_id' in session}")
    
    if 'user_id' in session:
        print(f"✅ ログイン中: user_id={session['user_id']}")
        return jsonify({
            'success': True,
            'logged_in': True,
            'user_id': session['user_id']
        }), 200
    else:
        print("❌ 未ログイン")
        return jsonify({
            'success': True,
            'logged_in': False
        }), 200




@app.route('/api/reviews', methods=['POST', 'OPTIONS'])
def create_review():
    """レビューを投稿（Overpass APIスポット対応）"""
   
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
   
    print("\n" + "="*60)
    print("【レビュー投稿リクエスト受信】")
    print(f"Cookie: {request.cookies}")
    print(f"セッション内容: {dict(session)}")
    print(f"user_id in session: {'user_id' in session}")
    if 'user_id' in session:
        print(f"user_id値: {session['user_id']}")
    print("="*60)
   
    if 'user_id' not in session:
        print("❌ エラー: セッションにuser_idがありません")
        return jsonify({
            'success': False,
            'message': 'ログインが必要です。ページを再読み込みしてください。'
        }), 401
   
    print(f"✅ ログイン確認: user_id={session['user_id']}")
   
    data = request.get_json()
    print(f"受信データ: {data}")
   
    osm_id = data.get('osm_id')
    osm_type = data.get('osm_type', 'node')
    spot_name = data.get('spot_name')
    spot_lat = data.get('spot_lat')
    spot_lon = data.get('spot_lon')
    spot_type = data.get('spot_type', 'その他')
   
    rating = data.get('rating')
    comment = data.get('comment', '')
    visit_date = data.get('visit_date')
   
    if not osm_id or not spot_name or not rating:
        print(f"❌ バリデーションエラー: osm_id={osm_id}, spot_name={spot_name}, rating={rating}")
        return jsonify({'success': False, 'message': '必須項目を入力してください'}), 400
   
    if not (1 <= rating <= 5):
        return jsonify({'success': False, 'message': '評価は1-5の範囲で入力してください'}), 400
   
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
   
    try:
        cur = conn.cursor()
       
        # 既存レビューの確認
        #cur.execute(
        #   'SELECT id FROM reviews WHERE user_id = %s AND osm_id = %s',
        #    (session['user_id'], osm_id)
        #)
        #existing = cur.fetchone()
       
        #if existing:
        #    print(f"⚠️ 既存レビュー検出: review_id={existing['id']}")
        #    return jsonify({
        #        'success': False,
        #        'message': 'このスポットには既にレビューを投稿しています。'
        #    }), 400
       
        # レビュー投稿
        print(f"📝 レビュー挿入開始...")
        cur.execute(
            '''INSERT INTO reviews
               (user_id, osm_id, osm_type, spot_name, spot_lat, spot_lon, spot_type,
                rating, comment, visit_date, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
               RETURNING id, user_id, osm_id, spot_name, rating, comment, visit_date, created_at''',
            (session['user_id'], osm_id, osm_type, spot_name, spot_lat, spot_lon, spot_type,
             rating, comment, visit_date)
        )
       
        review = cur.fetchone()
        conn.commit()
       
        print(f"✅ レビュー投稿成功: review_id={review['id']}, spot={spot_name}, user_id={session['user_id']}")
       
        # ★★★ ここから追加部分（tryブロック内に収める）★★★
        cur.execute(
            '''SELECT r.*, u.name as user_name, u.user_id as username
               FROM reviews r
               JOIN users u ON r.user_id = u.id
               WHERE r.osm_id = %s
               ORDER BY r.created_at DESC''',
            (osm_id,)
        )
        
        all_reviews = cur.fetchall()
        
        # 平均評価を計算
        avg_rating = 0
        if all_reviews:
            avg_rating = sum(r['rating'] for r in all_reviews) / len(all_reviews)
        
        print(f"📊 レビュー一覧取得: {len(all_reviews)}件, 平均評価: {avg_rating:.1f}")
        
        return jsonify({
            'success': True,
            'message': 'レビューを投稿しました',
            'review': dict(review),
            'all_reviews': [dict(r) for r in all_reviews],
            'average_rating': round(avg_rating, 1),
            'count': len(all_reviews)
        }), 201
       
    except Exception as e:
        conn.rollback()
        print(f"❌ レビュー投稿エラー: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'サーバーエラー: {str(e)}'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/reviews/spot/<int:osm_id>', methods=['GET', 'OPTIONS'])  # ← OPTIONSを追加
def get_spot_reviews(osm_id):
    """特定スポット（Overpass API）のレビュー一覧を取得"""
   
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
   
    print(f"\n=== レビュー取得: osm_id={osm_id} ===")
   
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
   
    try:
        cur = conn.cursor()
       
        # レビュー取得
        cur.execute(
            '''SELECT r.*, u.name as user_name, u.user_id as username
               FROM reviews r
               JOIN users u ON r.user_id = u.id
               WHERE r.osm_id = %s
               ORDER BY r.created_at DESC''',
            (osm_id,)
        )
       
        reviews = cur.fetchall()
       
        # 平均評価を計算
        avg_rating = 0
        if reviews:
            avg_rating = sum(review['rating'] for review in reviews) / len(reviews)
       
        print(f"✅ レビュー取得成功: {len(reviews)}件")
       
        return jsonify({
            'success': True,
            'osm_id': osm_id,
            'count': len(reviews),
            'average_rating': round(avg_rating, 1),
            'reviews': [dict(review) for review in reviews]
        }), 200
       
    except Exception as e:
        print(f"❌ レビュー取得エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/reviews/<int:review_id>', methods=['PUT', 'OPTIONS'])  # ← OPTIONSを追加
def update_review(review_id):
    """レビューを編集"""
   
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
   
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
   
    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment')
    visit_date = data.get('visit_date')
   
    if not (1 <= rating <= 5):
        return jsonify({'success': False, 'message': '評価は1-5の範囲で入力してください'}), 400
   
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
   
    try:
        cur = conn.cursor()
       
        # レビューの所有者確認
        cur.execute('SELECT * FROM reviews WHERE id = %s AND user_id = %s', (review_id, session['user_id']))
        review = cur.fetchone()
       
        if not review:
            return jsonify({'success': False, 'message': 'レビューが見つからないか、編集権限がありません'}), 404
       
        # レビュー更新
        cur.execute(
            '''UPDATE reviews
               SET rating = %s, comment = %s, visit_date = %s, updated_at = CURRENT_TIMESTAMP
               WHERE id = %s''',
            (rating, comment, visit_date, review_id)
        )
       
        conn.commit()
       
        return jsonify({'success': True, 'message': 'レビューを更新しました'}), 200
       
    except Exception as e:
        conn.rollback()
        print(f"❌ レビュー更新エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/reviews/<int:review_id>', methods=['DELETE', 'OPTIONS'])  # ← OPTIONSを追加
def delete_review(review_id):
    """レビューを削除"""
   
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
   
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
   
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
   
    try:
        cur = conn.cursor()
       
        # レビューの所有者確認
        cur.execute('SELECT * FROM reviews WHERE id = %s AND user_id = %s', (review_id, session['user_id']))
        review = cur.fetchone()
       
        if not review:
            return jsonify({'success': False, 'message': 'レビューが見つからないか、削除権限がありません'}), 404
       
        # レビュー削除
        cur.execute('DELETE FROM reviews WHERE id = %s', (review_id,))
        conn.commit()
       
        return jsonify({'success': True, 'message': 'レビューを削除しました'}), 200
       
    except Exception as e:
        conn.rollback()
        print(f"❌ レビュー削除エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/reviews/user', methods=['GET', 'OPTIONS'])  # ← OPTIONSを追加
def get_user_reviews():
    """ログイン中のユーザーのレビュー一覧を取得"""
   
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
   
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
   
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
   
    try:
        cur = conn.cursor()
       
        cur.execute(
            '''SELECT * FROM reviews
               WHERE user_id = %s
               ORDER BY created_at DESC''',
            (session['user_id'],)
        )
       
        reviews = cur.fetchall()
       
        return jsonify({
            'success': True,
            'count': len(reviews),
            'reviews': [dict(review) for review in reviews]
        }), 200
       
    except Exception as e:
        print(f"❌ ユーザーレビュー取得エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/reviews/user/check/<int:osm_id>', methods=['GET', 'OPTIONS'])  # ← OPTIONSを追加
def check_user_review(osm_id):
    """ユーザーが特定スポットにレビュー済みか確認"""
   
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
   
    print(f"\n=== レビューチェック: osm_id={osm_id} ===")
    print(f"セッション: {dict(session)}")
    print(f"user_id in session: {'user_id' in session}")
   
    if 'user_id' not in session:
        print("❌ 未ログイン")
        return jsonify({'success': True, 'has_review': False, 'logged_in': False}), 200
   
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
   
    try:
        cur = conn.cursor()
       
        cur.execute(
            'SELECT * FROM reviews WHERE user_id = %s AND osm_id = %s',
            (session['user_id'], osm_id)
        )
       
        review = cur.fetchone()
       
        if review:
            print(f"✅ 既存レビューあり: review_id={review['id']}")
            return jsonify({
                'success': True,
                'has_review': True,
                'logged_in': True,
                'review': dict(review)
            }), 200
        else:
            print("✅ レビューなし（投稿可能）")
            return jsonify({
                'success': True,
                'has_review': False,
                'logged_in': True
            }), 200
       
    except Exception as e:
        print(f"❌ レビュー確認エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()


##############################################
#お気に入り登録
##############################################
@app.route('/api/favorites/spot-detail/<int:osm_id>',methods=['GET','OPTIONS'])
def get_favorite_spot_detail(osm_id):
    if request.method == 'OPTIONS':
        response = jsonify({'success':True})
        response.headers.add('Access-Control-Allow-Origin','*')
        response.headers.add('Access-Control-Allow-Credentials','true')
        return response,200
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}),401
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}),500
    try:
        cur=conn.cursor()
        cur.execute(
            '''SELECT osm_id, osm_type, spot_name, spot_lat, spot_lon, spot_type, memo as description
               FROM favorites
               WHERE osm_id = %s AND user_id = %s''',
            (osm_id, session['user_id'])
        )
        favorite=cur.fetchone()
        if favorite:
            return jsonify({
                'success': True,
                'spot':dict(favorite)
            })
        else:
            return jsonify({
                'success': False,
                'message':'スポットが見つかりません'
            }),404
    except Exception as e:
        print(f"すぽっと詳細取得エラー: {e}")
        return jsonify({'success': False, 'message':'サーバーエラー'}),500
    finally:
        cur.close()
        conn.close()


@app.route('/favorites.html')
def favorites():
    """お気に入りページを表示"""
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'favorites.html')
@app.route('/api/favorites', methods=['POST', 'OPTIONS'])
def add_favorite():
    """お気に入りに追加"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
    
    data = request.get_json()
    
    osm_id = data.get('osm_id')
    osm_type = data.get('osm_type', 'node')
    spot_name = data.get('spot_name')
    spot_lat = data.get('spot_lat')
    spot_lon = data.get('spot_lon')
    spot_type = data.get('spot_type', 'その他')
    memo = data.get('memo', '')
    
    if not osm_id or not spot_name:
        return jsonify({'success': False, 'message': '必須項目を入力してください'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        # 既にお気に入り登録済みかチェック
        cur.execute(
            'SELECT id FROM favorites WHERE user_id = %s AND osm_id = %s',
            (session['user_id'], osm_id)
        )
        existing = cur.fetchone()
        
        if existing:
            return jsonify({
                'success': False,
                'message': 'このスポットは既にお気に入りに登録されています',
                'is_favorite': True
            }), 400
        
        # お気に入り登録
        cur.execute(
            '''INSERT INTO favorites
               (user_id, osm_id, osm_type, spot_name, spot_lat, spot_lon, spot_type, memo, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
               RETURNING id, spot_name, created_at''',
            (session['user_id'], osm_id, osm_type, spot_name, spot_lat, spot_lon, spot_type, memo)
        )
        
        favorite = cur.fetchone()
        conn.commit()
        
        print(f"✅ お気に入り登録成功: user_id={session['user_id']}, spot={spot_name}")
        
        return jsonify({
            'success': True,
            'message': 'お気に入りに追加しました',
            'favorite': dict(favorite),
            'is_favorite': True
        }), 201
        
    except Exception as e:
        conn.rollback()
        print(f"❌ お気に入り登録エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/favorites/check/<int:osm_id>', methods=['GET', 'OPTIONS'])
def check_favorite_status(osm_id):
    """特定スポットがお気に入り登録済みか確認"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
    
    if 'user_id' not in session:
        return jsonify({
            'success': True,
            'is_favorite': False,
            'logged_in': False
        }), 200
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute(
            'SELECT * FROM favorites WHERE user_id = %s AND osm_id = %s',
            (session['user_id'], osm_id)
        )
        
        favorite = cur.fetchone()
        
        if favorite:
            return jsonify({
                'success': True,
                'is_favorite': True,
                'logged_in': True,
                'favorite': dict(favorite)
            }), 200
        else:
            return jsonify({
                'success': True,
                'is_favorite': False,
                'logged_in': True
            }), 200
        
    except Exception as e:
        print(f"❌ お気に入りチェックエラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/favorites', methods=['GET', 'OPTIONS'])
def get_favorites():
    """ログイン中ユーザーのお気に入り一覧取得"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute(
            '''SELECT * FROM favorites
               WHERE user_id = %s
               ORDER BY display_order ASC, created_at DESC''',
            (session['user_id'],)
        )
        
        favorites = cur.fetchall()
        
        return jsonify({
            'success': True,
            'count': len(favorites),
            'favorites': [dict(fav) for fav in favorites]
        }), 200
        
    except Exception as e:
        print(f"❌ お気に入り取得エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/favorites/spot/<int:osm_id>', methods=['DELETE', 'OPTIONS'])
def delete_favorite_by_spot(osm_id):
    """スポットIDでお気に入りから削除"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'データベース接続エラー'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute(
            'SELECT * FROM favorites WHERE user_id = %s AND osm_id = %s',
            (session['user_id'], osm_id)
        )
        favorite = cur.fetchone()
        
        if not favorite:
            return jsonify({
                'success': False,
                'message': 'お気に入りが見つかりません',
                'is_favorite': False
            }), 404
        
        cur.execute(
            'DELETE FROM favorites WHERE user_id = %s AND osm_id = %s',
            (session['user_id'], osm_id)
        )
        conn.commit()
        
        print(f"✅ お気に入り削除成功: osm_id={osm_id}")
        
        return jsonify({
            'success': True,
            'message': 'お気に入りから削除しました',
            'is_favorite': False
        }), 200
        
    except Exception as e:
        conn.rollback()
        print(f"❌ お気に入り削除エラー: {e}")
        return jsonify({'success': False, 'message': 'サーバーエラー'}), 500
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    # データベース接続確認
    conn = get_db_connection()
    if conn:
        print("データベースに接続しました")
        conn.close()
    else:
        print("データベース接続に失敗しました")
    
    # 本番環境ではdebug=Falseにすること
    is_debug = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=is_debug, host='0.0.0.0', port=5000)