from database import create_database, create_ward_database, create_vehicle_database, create_waste_collection_database, reset_database
from complaint_manager import add_complaint, view_complaints
from ward_manager import add_ward, view_wards
from vehicle_manager import add_vehicle, view_vehicles
from waste_manager import add_waste_collection, view_collections

# Reset and recreate database with new schema
reset_database()
create_database()
create_ward_database()
create_vehicle_database()
create_waste_collection_database()

while True:

    print("\n==============================")
    print("      RCPI WASTE AI")
    print("==============================")

    print("1. Add Complaint")
    print("2. View Complaints")
    print("3. Add Ward")
    print("4. View Wards")
    print("5. Exit")

    choice = input("Enter Choice : ")

    if choice == "1":

        name = input("Citizen Name : ")
        location = input("Location / Ward : ")
        waste_type = input("Waste Type : ")
        complaint = input("Complaint : ")

        add_complaint(name, location, waste_type, complaint)

    elif choice == "2":

        view_complaints()

    elif choice == "3":

        ward = input("Ward Name : ")
        area = input("Area : ")
        email = input("Email : ")
        address = input("Address : ")

        add_ward(ward, area, email, address)

    elif choice == "4":

        view_wards()

    elif choice == "5":

        print("Thank You")
        break

    else:

        print("Invalid Choice")