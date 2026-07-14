from database import get_connection


def add_complaint(name, location, waste_type, complaint):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO complaints
    (name,location,waste_type,complaint,status)
    VALUES(?,?,?,?,?)
    """,
    (
        name,
        location,
        waste_type,
        complaint,
        "Pending"
    ))

    conn.commit()
    conn.close()

    print("Complaint Saved Successfully")


def view_complaints():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM complaints")

    rows = cursor.fetchall()

    conn.close()

    if len(rows) == 0:
        print("No Complaint Found")
    else:

        print("\n------ Complaint List ------")

        for row in rows:

            print("-------------------------------------")
            print("ID :", row[0])
            print("Name :", row[1])
            print("Mobile :", row[2])
            print("Ward :", row[3])
            print("Location :", row[4])
            print("Waste Type :", row[5])
            print("Complaint :", row[6])
            print("Status :", row[7])