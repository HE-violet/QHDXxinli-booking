import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
import qrcode
from PIL import Image
import io
import smtplib
from email.mime.text import MIMEText
from email.header import Header

# ================= 页面全局配置 =================
st.set_page_config(page_title="青海大学心理中心预约", page_icon="💖", layout="wide")

# ================= 1. 数据库配置 =================
def init_db():
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            room TEXT NOT NULL,
            date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            phone TEXT NOT NULL,
            create_time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ================= 2. 基础数据定义 =================
TIME_SLOTS = {
    "第1节": "08:30-09:15", "第2节": "09:25-10:10",
    "第3节": "10:35-11:20", "第4节": "11:30-12:15",
    "第5节": "14:00-14:45", "第6节": "14:55-15:40",
    "第7节": "16:00-16:45", "第8节": "16:55-17:40",
    "第9节": "19:20-20:05", "第10节": "20:15-21:00"
}

ROOMS = {
    "513": "空旷教室",
    "514": "团辅室（有座位、投影）",
    "515": "沙盘室（五彩斑斓）",
    "516": "团辅室（有座位、投影）"
}

# ================= 3. 业务逻辑判断 =================
def is_valid_date(target_date):
    return target_date > date.today()

def is_valid_time_slot(target_date, time_slot):
    weekday = target_date.weekday() 
    if weekday in [0, 1, 2, 3]: return True
    elif weekday == 4:
        if time_slot in ["第1节", "第2节", "第3节", "第4节", "第5节", "第6节", "第7节", "第8节"]: return True
        return False
    elif weekday == 5: return False
    elif weekday == 6:
        if time_slot in ["第9节", "第10节"]: return True
        return False
    return False

def check_room_available(room, target_date, time_slot):
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute("SELECT * FROM reservations WHERE room=? AND date=? AND time_slot=?", 
              (room, target_date.strftime("%Y-%m-%d"), time_slot))
    result = c.fetchone()
    conn.close()
    return result is None

def check_user_conflict(name, target_date, time_slot):
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute("SELECT * FROM reservations WHERE name=? AND date=? AND time_slot=?", 
              (name, target_date.strftime("%Y-%m-%d"), time_slot))
    result = c.fetchone()
    conn.close()
    return result is None

def add_reservation(name, class_name, room, target_date, time_slot, phone):
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute("INSERT INTO reservations (name, class_name, room, date, time_slot, phone, create_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (name, class_name, room, target_date.strftime("%Y-%m-%d"), time_slot, phone, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_schedule(target_date):
    conn = sqlite3.connect('booking.db')
    query = "SELECT room, time_slot FROM reservations WHERE date=?"
    df = pd.read_sql_query(query, conn, params=(target_date.strftime("%Y-%m-%d"),))
    conn.close()
    schedule = []
    for slot in TIME_SLOTS.keys():
        row = {"时间段": f"{slot} ({TIME_SLOTS[slot]})"}
        for room in ROOMS.keys():
            booked = not df[(df['room'] == room) & (df['time_slot'] == slot)].empty
            row[room] = "❌ 已预约" if booked else "✅ 可预约"
        schedule.append(row)
    return pd.DataFrame(schedule)

# ================= 4. 邮件通知功能 =================
def send_email_notification(name, class_name, room, target_date, time_slot_str, phone):
    try:
        sender = st.secrets["SENDER_EMAIL"]
        auth_code = st.secrets["SENDER_AUTH_CODE"]
        receiver = st.secrets["RECEIVER_EMAIL"]
        
        subject = f"🚨【新预约】{room}教室 - {target_date}"
        body = f"""
        管理员您好，青海大学心理中心有新的教室预约：
        
        -----------------------------
        预约教室：{room}
        预约日期：{target_date}
        预约时段：{time_slot_str}
        负责人：{name}
        班级：{class_name}
        联系电话：{phone}
        -----------------------------
        """
        
        message = MIMEText(body, 'plain', 'utf-8')
        message['From'] = Header("青大心理中心预约系统", 'utf-8')
        message['To'] = Header("管理员", 'utf-8')
        message['Subject'] = Header(subject, 'utf-8')
        
        smtp_server = "smtp.qq.com" if "qq.com" in sender else "smtp.163.com"
        server = smtplib.SMTP_SSL(smtp_server, 465)
        server.login(sender, auth_code)
        server.sendmail(sender, [receiver], message.as_string())
        server.quit()
    except Exception as e:
        print(f"邮件通知发送失败: {e}")

# ================= 5. 欢迎界面逻辑 =================
if 'entered' not in st.session_state:
    st.session_state.entered = False

if not st.session_state.entered:
    # 居中布局
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #4A90E2;'>💖 青海大学心理工作站 💖</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #2C3E50;'>志比昆仑，学竞江河</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 18px; color: #7F8C8D;'>在这里，为你留一盏灯，倾听你的声音。</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 进入按钮
        if st.button("🌟 点击进入预约系统", use_container_width=True):
            st.session_state.entered = True
            st.rerun()
    st.stop() # 隐藏后续内容

# ================= 6. 主界面设计 =================
# 侧边栏
st.sidebar.title("导航菜单")

# 二维码生成功能
st.sidebar.markdown("---")
st.sidebar.subheader("📱 扫码进入平台")
share_url = st.sidebar.text_input("网址", value="https://你的公网网址.streamlit.app")
if share_url:
    try:
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(share_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.sidebar.image(buf.getvalue(), caption="微信扫一扫", use_column_width=True)
    except Exception:
        pass
st.sidebar.markdown("---")

role = st.sidebar.radio("请选择您的身份：", ["学生/老师", "管理员"])

# --- 学生/老师端 ---
if role == "学生/老师":
    # 暖心头部设计
    st.title("🏫 校心理中心教室预约平台")
    st.success("🌻 **暖心寄语**：无论遇到什么烦恼，科技馆5楼的大门永远为你敞开。在这里，你可以放下疲惫，安心倾诉。")
    st.info("📍 地点：科技馆5楼 | 📞 中心电话：0971-5311690 | 💡 请至少提前一天预约")
    
    with st.expander("📖 请详细阅读预约教室细则（必读）", expanded=False):
        st.markdown("""
        1. 爱护公共器材与多媒体设备，轻拿轻放，勿违规操作。
        2. 保持场地整洁，垃圾入桶，不吸烟、不吐痰，活动结束自行清理杂物。
        3. 个人物品妥善保管，贵重物品随身携带，场地内遗失责任自负。
        4. 场地优先使用权归青海大学心理健康教育中心所属。
        5. 遵守法规，不大声喧哗，按规定人数、时间、类型活动，不得损坏消防等安全设施。
        6. **每天同一时间段只可预约一个教室。**
        7. **放映PPT需要自行带电脑进行投屏。**
        8. **可预约时间为工作日时间，周五晚上～周天下午不可预约，周天晚上可预约。**
        9. **至少提前一天进行预约。**
        
        **教室介绍：**
        * 513：空旷教室
        * 514，516：有座位有投影的团辅室
        * 515：五彩斑斓的沙盘室
        """)

    st.subheader("📅 查看教室预约状态")
    view_date = st.date_input("选择要查看的日期", min_value=date.today() + timedelta(days=1))
    
    if view_date:
        schedule_df = get_schedule(view_date)
        st.dataframe(schedule_df, use_container_width=True, hide_index=True)

    st.subheader("📝 提交预约申请")
    with st.form("booking_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("借用负责人姓名")
            class_name = st.text_input("学院年级班级 (例：计算机学院22级1班)")
            phone = st.text_input("联系电话")
        with col2:
            target_date = st.date_input("预约日期", min_value=date.today() + timedelta(days=1))
            selected_slots = st.multiselect("预约时间段 (可多选)", list(TIME_SLOTS.keys()), format_func=lambda x: f"{x} ({TIME_SLOTS[x]})")
            room = st.selectbox("预约教室", list(ROOMS.keys()), format_func=lambda x: f"{x} - {ROOMS[x]}")
            
        submit = st.form_submit_button("确认预约")
        
        if submit:
            if not all([name, class_name, phone, target_date, selected_slots, room]):
                st.error("请填写所有必填信息！")
            elif not is_valid_date(target_date):
                st.error("预约失败：必须至少提前一天预约！")
            else:
                has_error = False
                for slot in selected_slots:
                    if not is_valid_time_slot(target_date, slot):
                        st.error(f"预约失败：{slot} 属于不可预约时间（周五晚至周日下午）！")
                        has_error = True
                        break
                    if not check_room_available(room, target_date, slot):
                        st.error(f"预约失败：{room}教室在 {target_date} 的 {slot} 已被预约，请选择其他时间或教室。")
                        has_error = True
                        break
                    if not check_user_conflict(name, target_date, slot):
                        st.error(f"预约失败：您（该姓名）在 {target_date} 的 {slot} 已预约了一个教室，不可重复预约！")
                        has_error = True
                        break
                
                if not has_error:
                    for slot in selected_slots:
                        add_reservation(name, class_name, room, target_date, slot, phone)
                    
                    slot_str = "、".join(selected_slots)
                    send_email_notification(name, class_name, room, target_date, slot_str, phone)
                    
                    st.success(f"🎉 预约成功！已为您锁定 {room} 教室的 {slot_str}。祝您活动顺利！")
                    st.balloons()

# --- 管理员端（全面优化版） ---
else:
    st.title("🔐 管理员控制台")
    password = st.sidebar.text_input("请输入管理员密码", type="password")
    
    if password == st.secrets.get("ADMIN_PASSWORD", "admin123"):
        st.success("管理员身份已验证，欢迎回来！")
        
        conn = sqlite3.connect('booking.db')
        df = pd.read_sql_query("SELECT * FROM reservations ORDER BY date DESC, time_slot", conn)
        conn.close()
        
        if df.empty:
            st.info("目前没有任何预约记录。")
        else:
            # 1. 数据指标看板
            st.subheader("📊 数据总览")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("总预约人次", len(df))
            today_str = date.today().strftime("%Y-%m-%d")
            today_count = len(df[df['date'] == today_str])
            col2.metric("今日预约", today_count)
            col3.metric("最热教室", df['room'].mode()[0] if not df.empty else "-")
            col4.metric("联系人数", df['phone'].nunique())
            
            # 2. 教室热度图表
            st.subheader("📈 各教室预约热度")
            room_counts = df['room'].value_counts()
            st.bar_chart(room_counts)
            
            # 3. 详细数据表 (优化列顺序，隐藏不必要列)
            st.subheader("📋 所有预约详情")
            # 重新排列列顺序，方便管理员阅读
            display_cols = ['date', 'time_slot', 'room', 'name', 'class_name', 'phone', 'create_time', 'id']
            df_display = df[display_cols].rename(columns={
                'date': '预约日期', 'time_slot': '时间段', 'room': '教室', 
                'name': '负责人', 'class_name': '班级', 'phone': '联系电话', 
                'create_time': '提交时间', 'id': '记录ID'
            })
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # 4. 删除与导出功能
            st.subheader("🛠 管理操作")
            colA, colB = st.columns(2)
            with colA:
                # 下载 Excel 按钮
                csv = df_display.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 下载全部预约数据 (CSV)",
                    data=csv,
                    file_name=f"心理中心预约数据_{today_str}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with colB:
                delete_id = st.number_input("请输入要删除的预约记录ID", min_value=1, step=1)
                if st.button("🗑 确认删除该记录", use_container_width=True):
                    conn_del = sqlite3.connect('booking.db')
                    c = conn_del.cursor()
                    c.execute("DELETE FROM reservations WHERE id=?", (delete_id,))
                    conn_del.commit()
                    conn_del.close()
                    st.success(f"ID为 {delete_id} 的预约已删除。")
                    st.rerun()
    elif password != "":
        st.error("密码错误，请重新输入。")
