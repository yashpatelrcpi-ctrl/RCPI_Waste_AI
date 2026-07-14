from database import get_connection


def add_ward(ward_name, area, email, address):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO wards (ward_name, area, email, address) VALUES (?, ?, ?, ?)",
        (ward_name, area, email, address)
    )

    conn.commit()
    conn.close()

    print("Ward Added Successfully")


def view_wards():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM wards")

    rows = cursor.fetchall()

    conn.close()

    if len(rows) == 0:
        print("No Ward Found")
    else:
        print("\n------ Ward List ------")
        for row in rows:
            print("-------------------------------------")
            print("ID :", row[0])
            print("Ward Name :", row[1])
            print("Area :", row[2])
            print("Email :", row[3])
            print("Address :", row[4])