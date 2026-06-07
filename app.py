import streamlit as st
import sqlite3
import datetime
import hashlib
from PIL import Image
import io

# --- データベースの初期設定 ---
def init_db():
    conn = sqlite3.connect("minishare.db")
    c = conn.cursor()
    # 1. ユーザーテーブル
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            icon_bytes BLOB
        )
    """)
    # 2. 投稿テーブル（画像データ、いいね数を追加）
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            text TEXT,
            image_bytes BLOB,
            time TEXT,
            likes INTEGER DEFAULT 0
        )
    """)
    # 3. いいね追跡テーブル
    c.execute("""
        CREATE TABLE IF NOT EXISTS post_likes (
            post_id INTEGER,
            username TEXT,
            PRIMARY KEY (post_id, username)
        )
    """)
    conn.commit()
    conn.close()

# パスワードを暗号化（ハッシュ化）する関数
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hash(password) == hashed_text

init_db()

# --- アプリの設定 ---
st.set_page_config(page_title="MiniShare X", page_icon="🕊️", layout="centered")

# CSSの定義（ダークモードと投稿カードのデザイン）
st.markdown("""
    <style>
        .post-card {
            background-color: #1a1a1a;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            border: 1px solid #333;
        }
        .post-header {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        .user-name {
            font-weight: bold;
            margin-left: 10px;
            color: #fff;
        }
        .post-time {
            color: #888;
            font-size: 0.8em;
            margin-left: auto;
        }
        .post-text {
            color: #eee;
            margin-bottom: 15px;
        }
        .post-image {
            max-width: 100%;
            border-radius: 10px;
            margin-bottom: 15px;
        }
        .action-buttons {
            display: flex;
            gap: 15px;
            color: #888;
        }
    </style>
""", unsafe_allow_html=True)

# セッション状態の初期化
if "user" not in st.session_state:
    st.session_state.user = None

# ログイン後のメイン画面
if st.session_state.user:
    # ユーザーのアイコンを取得する関数
    def get_user_icon(username):
        conn = sqlite3.connect("minishare.db")
        c = conn.cursor()
        c.execute("SELECT icon_bytes FROM users WHERE username=?", (username,))
        res = c.fetchone()
        conn.close()
        if res and res[0]:
            return io.BytesIO(res[0]) # 保存された画像データ
        return "👤" # 画像がない場合はデフォルトの絵文字

    # いいね数を取得する関数
    def get_likes_count(post_id):
        conn = sqlite3.connect("minishare.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=?", (post_id,))
        count = c.fetchone()[0]
        conn.close()
        return count

    # ユーザーがすでにいいねしているか確認する関数
    def check_user_liked(post_id, username):
        conn = sqlite3.connect("minishare.db")
        c = conn.cursor()
        c.execute("SELECT * FROM post_likes WHERE post_id=? AND username=?", (post_id, username))
        liked = c.fetchone() is not None
        conn.close()
        return liked

    # いいねを追加/削除する関数
    def toggle_like(post_id, username):
        conn = sqlite3.connect("minishare.db")
        c = conn.cursor()
        if check_user_liked(post_id, username):
            c.execute("DELETE FROM post_likes WHERE post_id=? AND username=?", (post_id, username))
        else:
            c.execute("INSERT INTO post_likes (post_id, username) VALUES (?,?)", (post_id, username))
        conn.commit()
        conn.close()

    # サイドバー
    st.sidebar.title("🕊️ MiniShare X")
    st.sidebar.write(f"ログイン中: **{st.session_state.user}**")
    if st.sidebar.button("ログアウト"):
        st.session_state.user = None
        st.rerun()

    # タブの作成
    tab1, tab2 = st.tabs(["🏠 ホーム", "💌 メッセージ"])

    # --- タブ1: ホーム（タイムライン） ---
    with tab1:
        st.subheader("ホーム")
        
        # 投稿フォーム
        with st.form("post_form", clear_on_submit=True):
            user_text = st.text_area("いまどうしてる？", max_chars=140, placeholder="ここにつぶやきを入力")
            uploaded_image = st.file_uploader("画像を投稿（任意）", type=["png", "jpg", "jpeg"])
            submit_post = st.form_submit_button("つぶやく", type="primary")

            if submit_post:
                if user_text.strip():
                    image_bytes = uploaded_image.read() if uploaded_image else None
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    conn = sqlite3.connect("minishare.db")
                    c = conn.cursor()
                    c.execute("INSERT INTO posts (username, text, image_bytes, time) VALUES (?,?,?,?)", (st.session_state.user, user_text, image_bytes, now))
                    conn.commit()
                    conn.close()
                    st.rerun()

        st.markdown("---")
        
        # 投稿の表示
        conn = sqlite3.connect("minishare.db")
        c = conn.cursor()
        c.execute("SELECT id, username, text, image_bytes, time FROM posts ORDER BY id DESC")
        posts = c.fetchall()
        conn.close()

        for post_id, username, text, image_bytes, time in posts:
            icon = get_user_icon(username)
            likes_count = get_likes_count(post_id)
            user_liked = check_user_liked(post_id, st.session_state.user)
            
            with st.container():
                # HTMLとCSSを使って投稿カードを作成
                st.markdown(f"""
                    <div class="post-card">
                        <div class="post-header">
                            <img src="data:image/png;base64,{st.image(icon)._repr_png_()}" style="width:40px;height:40px;border-radius:50%;">
                            <div class="user-name">{username}</div>
                            <div class="post-time">{time}</div>
                        </div>
                        <div class="post-text">{text}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # 画像がある場合は表示
                if image_bytes:
                    st.image(io.BytesIO(image_bytes), use_column_width=True, caption="投稿画像")
                
                # いいねボタン（Streamlitのボタンを使って実装）
                col1, col2 = st.columns([1, 1])
                with col1:
                    like_label = f"❤️ {likes_count}" if user_liked else f"🖤 {likes_count}"
                    if st.button(like_label, key=f"like_{post_id}"):
                        toggle_like(post_id, st.session_state.user)
                        st.rerun()
                with col2:
                    if st.button("💬 コメント", key=f"comment_{post_id}"):
                        st.write("コメント機能は未実装です")

# ログイン・サインアップ画面
else:
    # (省略：以前のアカウント作成、ログイン処理と同じ)
