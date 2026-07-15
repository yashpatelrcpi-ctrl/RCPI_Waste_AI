import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from database import get_connection, initialize_all_databases
from auth import auth_manager


random.seed(42)

WARD_NAMES = [
    'Ward 1', 'Ward 2', 'Ward 3', 'Ward 4', 'Ward 5', 'Ward 6', 'Ward 7', 'Ward 8', 'Ward 9', 'Ward 10',
    'Ward 11', 'Ward 12', 'Ward 13', 'Ward 14', 'Ward 15', 'Ward 16', 'Ward 17', 'Ward 18', 'Ward 19', 'Ward 20',
    'Ward 21', 'Ward 22', 'Ward 23', 'Ward 24', 'Ward 25', 'Ward 26', 'Ward 27', 'Ward 28', 'Ward 29', 'Ward 30',
    'Ward 31', 'Ward 32', 'Ward 33', 'Ward 34', 'Ward 35', 'Ward 36', 'Ward 37', 'Ward 38', 'Ward 39', 'Ward 40',
    'Ward 41', 'Ward 42', 'Ward 43', 'Ward 44', 'Ward 45', 'Ward 46', 'Ward 47', 'Ward 48', 'Ward 49', 'Ward 50',
]
WASTE_TYPES = ['organic', 'recyclable', 'electronic', 'construction', 'hazardous', 'mixed']
STATUSES = ['Pending', 'In Progress', 'Resolved', 'Closed']
PRIORITIES = ['Low', 'Medium', 'High', 'Critical']
VEHICLE_TYPES = ['Truck', 'Auto', 'Mini Truck', 'Compactor', 'E-Rickshaw']
PROCESSING_FACILITIES = ['Central Composting Plant', 'Material Recovery Plant', 'E-Waste Unit', 'Construction Waste Unit']
LANDFILL_SITES = ['North Landfill', 'East Landfill', 'South Landfill', 'West Landfill']


def clear_existing_data():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('PRAGMA foreign_keys = OFF')
    for table in [
        'waste_collection', 'complaints', 'households', 'citizens', 'sessions', 'password_reset_tokens',
        'activity_log', 'notifications', 'work_assignments', 'complaint_tracking', 'carbon_credits',
        'citizen_waste_history', 'vehicles', 'wards', 'users', 'staff', 'drivers', 'processing_facilities', 'landfill_sites'
    ]:
        try:
            cur.execute(f'DELETE FROM {table}')
        except sqlite3.OperationalError:
            pass
    for table in [
        'waste_collection', 'complaints', 'households', 'citizens', 'sessions', 'password_reset_tokens',
        'activity_log', 'notifications', 'work_assignments', 'complaint_tracking', 'carbon_credits',
        'citizen_waste_history', 'vehicles', 'wards', 'users', 'staff', 'drivers', 'processing_facilities', 'landfill_sites'
    ]:
        try:
            cur.execute(f'DELETE FROM sqlite_sequence WHERE name = ?', (table,))
        except sqlite3.OperationalError:
            pass
    cur.execute('PRAGMA foreign_keys = ON')
    conn.commit()
    conn.close()


def create_wards(count=50):
    conn = get_connection()
    cur = conn.cursor()
    for idx, ward_name in enumerate(WARD_NAMES[:count], start=1):
        cur.execute(
            '''INSERT INTO wards (ward_name, area, email, address, supervisor, population, waste_generation_kg, vehicle_assignment, complaint_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                ward_name,
                f'Area {idx % 10 + 1}',
                f'{ward_name.lower().replace(" ", "")}@rcpi.gov',
                f'{idx} Main Street',
                f'Supervisor {idx}',
                8000 + idx * 100,
                1200 + idx * 45,
                f'V-{idx:03d}',
                idx % 15,
            ),
        )
    conn.commit()
    conn.close()


def create_users_and_citizens(num_citizens=1000):
    conn = get_connection()
    cur = conn.cursor()
    ward_rows = [row[0] for row in cur.execute('SELECT ward_name FROM wards').fetchall()]
    created_count = 0
    for index in range(1, num_citizens + 1):
        username = f'citizen{index}'
        email = f'citizen{index}@example.com'
        password = 'Test@1234'
        full_name = f'Citizen {index}'
        phone = f'900000{index:06d}'[-10:]
        ward = random.choice(ward_rows)
        success, message = auth_manager.register_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            phone=phone,
            role='citizen',
            address=f'{index} {random.choice(["Main", "Cross", "Park", "Gandhi"]) } Road',
            ward=ward,
            house_id=f'H-{index:05d}',
            gps_location=f'{12.97 + (index % 10) * 0.01},{77.59 + (index % 10) * 0.01}'
        )
        if success:
            created_count += 1
            continue

        suffix = 1
        while True:
            alt_username = f'citizen{index}_{suffix}'
            alt_email = f'citizen{index}_{suffix}@example.com'
            success, message = auth_manager.register_user(
                username=alt_username,
                email=alt_email,
                password=password,
                full_name=full_name,
                phone=phone,
                role='citizen',
                address=f'{index} {random.choice(["Main", "Cross", "Park", "Gandhi"]) } Road',
                ward=ward,
                house_id=f'H-{index:05d}-{suffix}',
                gps_location=f'{12.97 + (index % 10) * 0.01},{77.59 + (index % 10) * 0.01}'
            )
            if success:
                created_count += 1
                break
            suffix += 1
            if suffix > 100:
                break
    conn.close()
    return created_count


def create_households(num_households=1000):
    conn = get_connection()
    cur = conn.cursor()
    user_rows = cur.execute('SELECT id FROM users WHERE role = ? ORDER BY id', ('citizen',)).fetchall()
    ward_rows = [row[0] for row in cur.execute('SELECT ward_name FROM wards').fetchall()]
    for idx, row in enumerate(user_rows[:num_households], start=1):
        user_id = row[0]
        cur.execute(
            '''INSERT INTO households (house_id, user_id, citizen_name, mobile, address, ward, family_members)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (
                f'HOUSE-{user_id:05d}',
                user_id,
                f'Citizen {idx}',
                f'888000{idx:06d}'[-10:],
                f'{idx} Residential Lane',
                random.choice(ward_rows),
                2 + (idx % 5),
            ),
        )
    conn.commit()
    conn.close()


def create_vehicles(num_vehicles=100):
    conn = get_connection()
    cur = conn.cursor()
    ward_rows = [row[0] for row in cur.execute('SELECT ward_name FROM wards').fetchall()]
    for idx in range(1, num_vehicles + 1):
        cur.execute(
            '''INSERT INTO vehicles (vehicle_number, vehicle_type, capacity, driver_name, status, ward_assigned, route, daily_collection_kg, history)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                f'V-{idx:03d}',
                random.choice(VEHICLE_TYPES),
                3000 + idx * 10,
                f'Driver {idx}',
                'Active' if idx % 5 else 'Maintenance',
                random.choice(ward_rows),
                f'Route {idx % 10 + 1}',
                100 + idx * 3,
                f'Last route {idx % 7 + 1}',
            ),
        )
    conn.commit()
    conn.close()


def create_staff_and_drivers(num_staff=200):
    conn = get_connection()
    cur = conn.cursor()
    created_count = 0
    for idx in range(1, num_staff + 1):
        role = 'staff' if idx % 2 == 0 else 'driver'
        username = f'{role}{idx}'
        email = f'{role}{idx}@example.com'
        success, _ = auth_manager.register_user(
            username=username,
            email=email,
            password='Staff@1234',
            full_name=f'{role.title()} {idx}',
            phone=f'777000{idx:06d}'[-10:],
            role=role,
            ward=random.choice(WARD_NAMES[:50]),
        )
        if success:
            created_count += 1
            continue

        suffix = 1
        while True:
            alt_username = f'{role}{idx}_{suffix}'
            alt_email = f'{role}{idx}_{suffix}@example.com'
            success, _ = auth_manager.register_user(
                username=alt_username,
                email=alt_email,
                password='Staff@1234',
                full_name=f'{role.title()} {idx}',
                phone=f'777000{idx:06d}'[-10:],
                role=role,
                ward=random.choice(WARD_NAMES[:50]),
            )
            if success:
                created_count += 1
                break
            suffix += 1
            if suffix > 100:
                break
    conn.close()
    return created_count


def create_complaints(num_complaints=1000):
    conn = get_connection()
    cur = conn.cursor()
    citizen_rows = cur.execute('SELECT id, username FROM users WHERE role = ?', ('citizen',)).fetchall()
    staff_rows = cur.execute('SELECT id, username FROM users WHERE role IN (?, ?)', ('staff', 'driver')).fetchall()
    vehicle_rows = cur.execute('SELECT vehicle_number, ward_assigned FROM vehicles').fetchall()
    ward_rows = [row[0] for row in cur.execute('SELECT ward_name FROM wards').fetchall()]
    for idx in range(1, num_complaints + 1):
        citizen = random.choice(citizen_rows)
        status = random.choice(STATUSES)
        priority = random.choice(PRIORITIES)
        ward = random.choice(ward_rows)
        assigned_staff = random.choice(staff_rows)[1] if staff_rows else None
        assigned_vehicle = random.choice(vehicle_rows)[0] if vehicle_rows else None
        complaint_id = f'CMP-{datetime.now().strftime("%Y%m%d")}-{idx:05d}'
        cur.execute(
            '''INSERT INTO complaints (complaint_id, user_id, name, mobile, ward, location, waste_type, complaint, status, priority, assigned_staff, assigned_vehicle, assigned_driver, assigned_ward_officer, created_date, updated_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                complaint_id,
                citizen[0],
                citizen[1],
                f'900000{idx:06d}'[-10:],
                ward,
                f'{idx} Street, {ward}',
                random.choice(WASTE_TYPES),
                f'{random.choice(["Overflow", "Dump", "Odour", "Collection delay", "Illegal disposal"])} complaint for {ward}',
                status,
                priority,
                assigned_staff,
                assigned_vehicle,
                assigned_staff,
                f'Officer {idx % 10 + 1}',
                (datetime.now() - timedelta(days=random.randint(0, 120))).isoformat(),
                (datetime.now() - timedelta(days=random.randint(0, 90))).isoformat(),
            ),
        )
    conn.commit()
    conn.close()


def create_waste_collections(num_records=10000):
    conn = get_connection()
    cur = conn.cursor()
    household_rows = cur.execute('SELECT id, ward FROM households').fetchall()
    vehicle_rows = cur.execute('SELECT id, vehicle_number, ward_assigned FROM vehicles').fetchall()
    complaint_rows = cur.execute('SELECT id, ward FROM complaints').fetchall()
    facilities = PROCESSING_FACILITIES
    landfills = LANDFILL_SITES
    for idx in range(1, num_records + 1):
        household = random.choice(household_rows)
        vehicle = random.choice(vehicle_rows)
        complaint = random.choice(complaint_rows)
        waste_quantity = round(random.uniform(5, 120), 2)
        waste_type = random.choice(WASTE_TYPES)
        collection_date = (datetime.now() - timedelta(days=random.randint(0, 365), hours=random.randint(0, 23))).isoformat()
        cur.execute(
            '''INSERT INTO waste_collection (vehicle_id, household_id, complaint_id, citizen_id, ward, collection_date, waste_quantity, waste_type, status, processing_facility, landfill_site)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                vehicle[0],
                household[0],
                complaint[0],
                random.randint(1, 1000),
                household[1] or complaint[1] or vehicle[2],
                collection_date,
                waste_quantity,
                waste_type,
                'Completed',
                random.choice(facilities),
                random.choice(landfills),
            ),
        )
    conn.commit()
    conn.close()


def create_processing_and_landfill_seed():
    conn = get_connection()
    cur = conn.cursor()
    for facility in PROCESSING_FACILITIES:
        cur.execute('INSERT INTO processing_facilities (name, ward, capacity_tons, status) VALUES (?, ?, ?, ?)', (facility, random.choice(WARD_NAMES[:10]), 1200 + random.randint(0, 1000), 'Active'))
    for landfill in LANDFILL_SITES:
        cur.execute('INSERT INTO landfill_sites (name, latitude, longitude, capacity_tons, status, last_inspection) VALUES (?, ?, ?, ?, ?, ?)', (
            landfill,
            12.90 + random.random(),
            77.50 + random.random(),
            5000 + random.randint(0, 3000),
            'Active',
            (datetime.now() - timedelta(days=10)).isoformat(),
        ))
    conn.commit()
    conn.close()


def run_bulk_test_data():
    initialize_all_databases()
    clear_existing_data()
    create_wards(50)
    citizen_count = create_users_and_citizens(1000)
    create_households(1000)
    create_vehicles(100)
    staff_count = create_staff_and_drivers(200)
    create_processing_and_landfill_seed()
    create_complaints(1000)
    create_waste_collections(10000)
    return {
        'citizens': citizen_count,
        'households': 1000,
        'complaints': 1000,
        'wards': 50,
        'vehicles': 100,
        'staff_drivers': staff_count,
        'waste_collections': 10000,
    }


if __name__ == '__main__':
    print(run_bulk_test_data())
