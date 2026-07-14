from database import get_connection


def add_waste_collection(vehicle_id, ward, waste_quantity, waste_type):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO waste_collection (vehicle_id, ward, waste_quantity, waste_type, status)
    VALUES (?, ?, ?, ?, ?)
    """, (vehicle_id, ward, waste_quantity, waste_type, 'Completed'))

    conn.commit()
    conn.close()

    print("Waste Collection Recorded Successfully")


def get_all_collections():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM waste_collection")
    rows = cursor.fetchall()
    conn.close()

    return rows


def view_collections():
    rows = get_all_collections()

    if len(rows) == 0:
        print("No Waste Collection Found")
    else:
        print("\n------ Waste Collection List ------")
        for row in rows:
            print("-------------------------------------")
            print("ID :", row[0])
            print("Vehicle ID :", row[1])
            print("Ward :", row[2])
            print("Collection Date :", row[3])
            print("Waste Quantity :", row[4])
            print("Waste Type :", row[5])
            print("Status :", row[6])


def get_collection_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(waste_quantity) FROM waste_collection")
    total_waste = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM waste_collection")
    total_collections = cursor.fetchone()[0]

    conn.close()

    return {"total_waste": total_waste, "total_collections": total_collections}
