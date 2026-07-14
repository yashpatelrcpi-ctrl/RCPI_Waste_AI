from database import get_connection


def add_vehicle(vehicle_number, vehicle_type, capacity, driver_name, ward_assigned):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO vehicles (vehicle_number, vehicle_type, capacity, driver_name, status, ward_assigned)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (vehicle_number, vehicle_type, capacity, driver_name, 'Active', ward_assigned))

    conn.commit()
    conn.close()

    print("Vehicle Added Successfully")


def get_all_vehicles():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM vehicles")
    rows = cursor.fetchall()
    conn.close()

    return rows


def view_vehicles():
    rows = get_all_vehicles()

    if len(rows) == 0:
        print("No Vehicle Found")
    else:
        print("\n------ Vehicle List ------")
        for row in rows:
            print("-------------------------------------")
            print("ID :", row[0])
            print("Vehicle Number :", row[1])
            print("Vehicle Type :", row[2])
            print("Capacity :", row[3])
            print("Driver Name :", row[4])
            print("Status :", row[5])
            print("Ward Assigned :", row[6])
