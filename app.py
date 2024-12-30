from flask import Flask,render_template,request,redirect,url_for,session,flash,jsonify
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import io
import base64
from datetime import datetime

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'registration'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

@app.route('/',methods=['GET','POST'])
def home():
    if 'alogin' in request.form:
        Admin_name = request.form['Admin_name']
        Password = request.form['Password']
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM admin WHERE Admin_name = %s AND Password = %s",[Admin_name,Password])
            res = cur.fetchone()
            if res:
                session["Admin_name"] = res['Admin_name']
                session["aid"] = res['aid']
                return redirect(url_for('admin_home'))
            else:
                return render_template("index.html")
        except Exception as e:
            print(e)
        finally:
            mysql.connection.commit()
            cur.close() 
    elif 'register' in request.form:
        if request.method == 'POST':
            uname = request.form['uname']
            upass = request.form['upass']
            repass = request.form['repass']
            mobile = request.form['mobile']
            dob = request.form['dob']
            email = request.form['email']
            city = request.form['city']
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO users(uname,upass,repass,mobile,dob,email,city) VALUES(%s,%s,%s,%s,%s,%s,%s)",[uname,upass,repass,mobile,dob,email,city])   
            mysql.connection.commit()
        return render_template('index.html')
    
    elif 'ulogin' in request.form:
        if request.method == 'POST':
            uname = request.form['uname']
            upass = request.form['upass']
            try:
                cur = mysql.connection.cursor()
                cur.execute("SELECT * FROM users WHERE uname = %s AND upass = %s",[uname,upass])
                res = cur.fetchone()
                if res:
                    session["uname"] = res['uname']
                    session["uid"] = res['uid']
                    return redirect(url_for('user_home'))
                else:
                    return render_template("index.html") 
            except Exception as e:
                print(e)    
            finally:
                mysql.connection.commit()
                cur.close()                   

    return render_template('index.html')

@app.route("/view_users")
def view_users():
    cur = mysql.connection.cursor()
    qry = "SELECT * FROM users"
    cur.execute(qry)
    data = cur.fetchall()
    cur.close()
    count = len(data)
    if count == 0:
        flash("Users Not Found...!!!")
    return render_template('view_users.html', res=data)

@app.route('/users', methods=['GET'])
def get_users():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT uid, uname, mobile, dob, email, city FROM users")
    users = cursor.fetchall()
    cursor.close()
    return jsonify(users)

@app.route('/users/<int:uid>', methods=['GET'])
def get_user(uid):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT uid, uname, mobile, dob, email, city FROM users WHERE uid=%s", (uid,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return jsonify(user)
    return jsonify({'message': 'User not found'}), 404

@app.route('/users', methods=['POST'])
def add_user():
    data = request.json
    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO users (uname, upass, repass, mobile, dob, email, city) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (data['uname'], data['upass'], data['upass'], data['mobile'], data['dob'], data['email'], data['city']),
    )
    mysql.connection.commit()
    cursor.close()
    return jsonify({'message': 'User added successfully!'})

@app.route('/users/<int:uid>', methods=['PUT'])
def update_user(uid):
    data = request.json
    cursor = mysql.connection.cursor()

    # Check if the password is provided. If not, don't include it in the update query.
    if 'upass' in data and data['upass']:  # Check if the password is not empty
        cursor.execute(
            "UPDATE users SET uname=%s, upass=%s, repass=%s, mobile=%s, dob=%s, email=%s, city=%s WHERE uid=%s",
            (data['uname'], data['upass'], data['upass'], data['mobile'], data['dob'], data['email'], data['city'], uid),
        )
    else:
        cursor.execute(
            "UPDATE users SET uname=%s, mobile=%s, dob=%s, email=%s, city=%s WHERE uid=%s",
            (data['uname'], data['mobile'], data['dob'], data['email'], data['city'], uid),
        )

    mysql.connection.commit()
    cursor.close()
    return jsonify({'message': 'User updated successfully!'})


@app.route('/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM users WHERE uid=%s", (uid,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'message': 'User deleted successfully!'})

@app.route('/user_home')
def user_home():
    cur = mysql.connection.cursor()

    # Fetch events data
    cur.execute("SELECT eid, etitle, capacity, price, address, image, status FROM add_events")
    events = []
    for row in cur.fetchall():
        events.append({
            'eid': row['eid'],
            'etitle': row['etitle'],
            'capacity': row['capacity'],
            'price': row['price'],
            'address': row['address'],
            'status': row['status'],
            'image': base64.b64encode(row['image']).decode('utf-8') if row['image'] else None
        })

    # Fetch notifications for the logged-in user
    user_id = session.get('uid')
    print(user_id)
    if user_id:
        cur.execute("SELECT message, created_at FROM notifications WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        notifications = cur.fetchall()
        print(notifications)
    else:
        notifications = ["Error"]

    # Pass both events and notifications to the template
    return render_template('user_home.html', events=events, notifications=notifications)


@app.route('/admin_home', methods=['GET', 'POST'])
def admin_home():
    if request.method == 'POST' and 'addevents' in request.form:
        etitle = request.form['etitle']
        capacity = request.form['capacity']
        price = request.form['price']
        address = request.form['address']
        
        # Handling image upload (getting the image file from the form)
        image_file = request.files['image']
        
        # Check if the image file exists
        if image_file:
            # Secure the file name and convert the file into binary data (BLOB)
            filename = secure_filename(image_file.filename)
            image_binary = image_file.read()  # Read the image as binary data
        
            # Insert data into the database
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO add_events (etitle, capacity, price, image, address) 
                VALUES (%s, %s, %s, %s, %s)
            """, (etitle, capacity, price, image_binary, address))
            mysql.connection.commit()
            cur.close()

    # Fetch events from the database
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM add_events")
    events = cur.fetchall()
    cur.close()

    # Base64 encode the image data for rendering in the template
    events = [
        {
            **event,
            'image': base64.b64encode(event['image']).decode('utf-8')  # Encoding the image as base64
        }
        for event in events
    ]

    return render_template('admin_home.html', events=events)

@app.route('/schedule_appointment', methods=['POST'])
def schedule_appointment():
    eid = request.form['eid']
    appointment_date = request.form['appointment_date']
    print(eid)
    print(appointment_date)

    try:
        cur = mysql.connection.cursor()
        # Update the appointment_date column in add_events table
        query = "UPDATE add_events SET appointment_date = %s WHERE eid = %s"
        cur.execute(query, (appointment_date, eid))
        mysql.connection.commit()
        print("Appointment scheduled successfully.")
        # Retrieve the user ID for the event to send a notification
        query = "SELECT u_id, etitle FROM add_events WHERE eid = %s"
        cur.execute(query, (eid,))
        result = cur.fetchone()
        user_id = result['u_id']
        hall_name = result['etitle']
        print(user_id, hall_name)

        # Insert a notification for the respective user
        notification_message = f"You have received an appointment on {appointment_date} regarding the hall {hall_name} you booked."
        query = "INSERT INTO notifications (user_id, message, created_at) VALUES (%s, %s, %s)"
        cur.execute(query, (user_id, notification_message, datetime.now()))
        mysql.connection.commit()

        flash("Appointment scheduled successfully and notification sent.", "success")
    except Exception as e:
        mysql.connection.rollback()
        print("Error:", e)
        flash("An error occurred while scheduling the appointment.", "danger")

    return redirect(url_for('view_bookings'))

@app.route('/book_event', methods=['POST'])
def book_event():
    # Capture data from the form
    eid = request.form['event_id']  # Event ID from the hidden input
    uid = request.form['user_id']
    event_name = request.form['event_name']
    no_of_people = request.form['no_of_people']
    event_date = request.form['event_date']
    event_description = request.form['event_description']
    food_required = request.form['food_required']
    # Insert booking details into the bookings table
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO bookings (bid,u_id,event_name, no_of_people, event_date, event_description, food_required) 
        VALUES (%s,%s,%s, %s, %s, %s, %s)
    """, (eid,uid,event_name, no_of_people, event_date, event_description, food_required))

    # Update the status in the add_events table
    cur.execute("UPDATE add_events SET status = 'Booked' WHERE eid = %s", [eid])
    cur.execute("UPDATE add_events SET u_id = %s WHERE eid = %s", [uid,eid])
    mysql.connection.commit()
    cur.close()

    # Redirect to user home
    return redirect(url_for('user_home'))

@app.route('/view_bookings')
def view_bookings():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM add_events")
    events = cur.fetchall()
    cur.close()

    # Base64 encode the image data for rendering in the template
    events = [
        {
            **event,
            'image': base64.b64encode(event['image']).decode('utf-8')  # Encoding the image as base64
        }
        for event in events
    ]

    return render_template('view_bookings.html', events=events)



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.secret_key = '123456'
    app.run(debug=True)