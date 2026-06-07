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
    # 2. 投稿テーブル
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            text TEXT,
            image_bytes BLOB,
            time TEXT
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
    # 4. DMテーブル
    c.execute("""
        CREATE TABLE IF NOT EXISTS dms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            text TEXT,
            time TEXT
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

# CSSの定義（ダークモード風の投稿カードデザイン）
st.markdown("""
    <style>
        .post-card {
            background-color: #1e1e1e;
            padding: 15px;
            border-radius: 12px;
            margin-bottom: 10px;
            border: 1px solid #333;
        }
        .user-name {
            font-weight: bold;
            color: #fff;
        }
        .post-time {
            color: #888;
            font-size: 0.8em;
        }
        .post-text {
            color: #eee;
            margin-top: 5px;
            white-space: pre-wrap;
        }
    </style>
""", unsafe_allow_html=True)

# セッション状態の初期化
if "user" not in st.session_state:
    st.session_state.user = None

# --- ログイン後のメイン画面 ---
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
    tab1, tab2, tab3 = st.tabs(["🏠 ホーム", "💌 DM", "⚙️ 設定"])

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
            
            # カスタムカードUIの表示
            st.markdown(f"""
                <div class="post-card">
                    <span class="user-name">{username}</span> 
                    <span class="post-time">· {time}</span>
                    <div class="post-text">{text}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # 画像の表示
            if image_bytes:
                st.image(io.BytesIO(image_bytes), use_container_width=True)
                
            # いいねボタン
            like_label = f"❤️ {likes_count}" if user_liked else f"🖤 {likes_count}"
            if st.button(like_label, key=f"like_{post_id}"):
                toggle_like(post_id, st.session_state.user)
                st.rerun()
            st.markdown("---")

    # --- タブ2: DM (ダイレクトメッセージ) ---
    with tab2:
        st.subheader("💌 ダイレクトメッセージ")
        conn = sqlite3.connect("minishare.db")
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE username != ?", (st.session_state.user,))
        users = [row[0] for row in c.fetchall()]
        conn.close()
        
        if not users:
            st.info("まだ他のユーザーが登録されていません。")
        else:
            receiver = st.selectbox("話す相手を選ぶ", users)
            dm_text = st.text_input(f"{receiver} へメッセージを送る")
            if st.button("DMを送信"):
                if dm_text.strip():
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    conn = sqlite3.connect("minishare.db")
                    c = conn.cursor()
                    c.execute("INSERT INTO dms (sender, receiver, text, time) VALUES (?,?,?,?)", (st.session_state.user, receiver, dm_text, now))
                    conn.commit()
                    conn.close()
                    st.rerun()
            
            st.markdown("### チャット履歴")
            conn = sqlite3.connect("minishare.db")
            c = conn.cursor()
            c.execute("""
                SELECT sender, text, time FROM dms 
                WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
                ORDER BY id DESC
            """, (st.session_state.user, receiver, receiver, st.session_state.user))
            dms = c.fetchall()
            conn.close()
            
            for sender, text, time in dms:
                icon = get_user_icon(sender)
                is_me = " (あなた)" if sender == st.session_state.user else ""
                with st.chat_message("user", avatar=icon):
                    st.write(f"**{sender}{is_me}**  <small style='color:gray;'>{time}</small>", unsafe_allow_html=True)
                    st.write(text)

    # --- タブ3: 設定 ---
    with tab3:
        st.subheader("⚙️ プロフィール設定")
        new_icon_file = st.file_uploader("新しいアイコン画像を選択", type=["png", "jpg", "jpeg"])
        if st.button("アイコンを更新"):
            if new_icon_file:
                icon_data = new_icon_file.read()
                conn = sqlite3.connect("minishare.db")
                c = conn.cursor()
                c.execute("UPDATE users SET icon_bytes=? WHERE username=?", (icon_data, st.session_state.user))
                conn.commit()
                conn.close()
                st.success("アイコンを更新しました！")
                st.rerun()

# --- ログイン・サインアップ画面（未ログイン時） ---
else:
    st.title("🕊️ MiniShare X")
    menu = ["ログイン", "新アカウント作成"]
    choice = st.sidebar.selectbox("メニュー", menu)

    if choice == "新アカウント作成":
        st.subheader("👤 新しいアカウントを作る")
        new_user = st.text_input("ユーザー名（英語・数字推奨）", max_chars=15)
        new_password = st.text_input("パスワード", type="password")
        uploaded_file = st.file_uploader("アイコン画像を選択（任意）", type=["png", "jpg", "jpeg"])
        
        if st.button("登録する", type="primary"):
            if not new_user or not new_password:
                st.error("ユーザー名とパスワードを入力してください。")
            else:
                conn = sqlite3.connect("minishare.db")
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE username=?", (new_user,))
                if c.fetchone():
                    st.error("そのユーザー名はすでに使われています。")
                else:
                    icon_data = uploaded_file.read() if uploaded_file else None
                    c.execute("INSERT INTO users VALUES (?,?,?)", (new_user, make_hash(new_password), icon_data))
                    conn.commit()
                    st.success("アカウントが作成されました！ログインしてください。")
                conn.close()

    elif choice == "ログイン":
        st.subheader("🔒 ログイン")
        username = st.text_input("ユーザー名")
        password = st.text_input("パスワード", type="password")
        
        if st.button("ログイン", type="primary"):
            conn = sqlite3.connect("minishare.db")
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username=?", (username,))
            result = c.fetchone()
            conn.close()
            
            if result and check_hashes(password, result[0]):
                st.session_state.user = username
                st.success(f"{username} としてログインしました")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが違います。")
