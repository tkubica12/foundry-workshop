from datetime import datetime, timedelta, timezone

from .models import Complaint, Partner

# Real city/street geography, fictional premises, organizations and people.
LOCATIONS = [
    ("CZ", "Prague", "Prague", "Vinohradska", "120 00", 50.0755, 14.4378, "cs", "+420"),
    ("DE", "Berlin", "Berlin", "Friedrichstrasse", "10117", 52.5200, 13.4050, "de", "+49"),
    ("FR", "Paris", "Ile-de-France", "Rue de Lyon", "75012", 48.8566, 2.3522, "fr", "+33"),
    ("GB", "London", "England", "Kingsland Road", "E2 8AA", 51.5074, -0.1278, "en", "+44"),
    ("ES", "Madrid", "Madrid", "Calle de Alcala", "28009", 40.4168, -3.7038, "es", "+34"),
    ("IT", "Milan", "Lombardy", "Via Torino", "20123", 45.4642, 9.1900, "it", "+39"),
    ("SE", "Stockholm", "Stockholm", "Sveavagen", "113 50", 59.3293, 18.0686, "sv", "+46"),
    ("NL", "Amsterdam", "North Holland", "Overtoom", "1054 HL", 52.3676, 4.9041, "nl", "+31"),
    ("PL", "Warsaw", "Masovia", "Marszalkowska", "00-590", 52.2297, 21.0122, "pl", "+48"),
    ("CH", "Zurich", "Zurich", "Badenerstrasse", "8004", 47.3769, 8.5417, "de", "+41"),
    ("US", "Seattle", "Washington", "Pine Street", "98101", 47.6062, -122.3321, "en", "+1"),
    ("US", "Austin", "Texas", "South Congress Avenue", "78704", 30.2672, -97.7431, "en", "+1"),
    ("US", "Boston", "Massachusetts", "Boylston Street", "02116", 42.3601, -71.0589, "en", "+1"),
    ("CA", "Toronto", "Ontario", "Queen Street West", "M5V 2A5", 43.6532, -79.3832, "en", "+1"),
    ("CA", "Montreal", "Quebec", "Rue Saint-Denis", "H2X 3K8", 45.5019, -73.5674, "fr", "+1"),
    ("MX", "Mexico City", "Mexico City", "Avenida Insurgentes Sur", "03100", 19.4326, -99.1332, "es", "+52"),
    ("BR", "Sao Paulo", "Sao Paulo", "Rua Augusta", "01305-000", -23.5505, -46.6333, "pt", "+55"),
    ("CL", "Santiago", "Santiago", "Avenida Providencia", "7500000", -33.4489, -70.6693, "es", "+56"),
    ("JP", "Tokyo", "Tokyo", "Shibuya 2-chome", "150-0002", 35.6762, 139.6503, "ja", "+81"),
    ("KR", "Seoul", "Seoul", "Teheran-ro", "06134", 37.5665, 126.9780, "ko", "+82"),
    ("SG", "Singapore", "Central Region", "Kallang Avenue", "339407", 1.3521, 103.8198, "en", "+65"),
    ("IN", "Bengaluru", "Karnataka", "MG Road", "560001", 12.9716, 77.5946, "kn", "+91"),
    ("IN", "Mumbai", "Maharashtra", "Linking Road", "400050", 19.0760, 72.8777, "hi", "+91"),
    ("AE", "Dubai", "Dubai", "Al Wasl Road", "00000", 25.2048, 55.2708, "ar", "+971"),
    ("AU", "Sydney", "New South Wales", "King Street", "2042", -33.8688, 151.2093, "en", "+61"),
    ("AU", "Melbourne", "Victoria", "Bridge Road", "3121", -37.8136, 144.9631, "en", "+61"),
    ("NZ", "Auckland", "Auckland", "Great North Road", "1021", -36.8485, 174.7633, "en", "+64"),
    ("ZA", "Cape Town", "Western Cape", "Main Road", "7700", -33.9249, 18.4241, "en", "+27"),
    ("KE", "Nairobi", "Nairobi", "Ngong Road", "00100", -1.2921, 36.8219, "sw", "+254"),
    ("EG", "Cairo", "Cairo", "Tahrir Street", "11511", 30.0444, 31.2357, "ar", "+20"),
]
SPECIALTIES = ["hvac", "appliances", "solar", "electrical", "plumbing"]
SEED_TIME = datetime(2026, 9, 1, 9, tzinfo=timezone.utc)


def partners() -> list[Partner]:
    rows = []
    for index in range(120):
        country, city, region, street, postal, lat, lon, language, dial = LOCATIONS[index % 30]
        branch = index // 30
        rows.append(Partner(
            id=f"partner-{index + 1:03d}", version=1, updated_at=SEED_TIME,
            name=f"{['Northstar', 'Clearwave', 'Bluebridge', 'Silverline'][branch]} {city} Service",
            address=dict(street=f"{14 + branch * 22} {street}, Unit {branch + 1}", city=city,
                         region=region, postal_code=postal, country_code=country,
                         latitude=lat, longitude=lon),
            contact_name=f"{['Alex', 'Sam', 'Taylor', 'Robin'][branch]} Demo {index + 1}",
            email=f"service{index + 1}@partners.example",
            phone=f"{dial} 000 000 {index + 1:04d}", website=f"https://partner-{index + 1}.example",
            status=["active", "active", "active", "suspended", "pending"][index % 5],
            tier=["standard", "silver", "gold", "platinum"][(index + branch) % 4],
            specialties=[SPECIALTIES[index % 5], SPECIALTIES[(index + branch + 1) % 5]],
            languages=list(dict.fromkeys([language, "en"])),
            certifications=["Workshop safety training", f"{SPECIALTIES[index % 5].upper()} service authorization"],
            service_radius_km=20 + index % 8 * 15, emergency_service=index % 3 == 0,
            rating=round(3.2 + index % 19 / 10, 1), capacity_per_week=5 + index % 12 * 5,
            authorized_since=f"{2018 + index % 8}-0{index % 9 + 1}-15",
        ))
    return rows


def complaints() -> list[Complaint]:
    categories = ["late_arrival", "repair_quality", "billing", "communication", "warranty", "safety"]
    subjects = [
        "Technician missed the agreed arrival window", "Appliance still leaks after repair",
        "Invoice includes an unexplained service charge", "No update after the first service visit",
        "Warranty repair was declined", "Exposed cable after installation",
    ]
    statuses = ["new", "triaged", "in_progress", "awaiting_customer", "resolved", "closed"]
    rows = []
    for index in range(90):
        country, city, *rest = LOCATIONS[index % 30]
        language = rest[-2]
        created = SEED_TIME - timedelta(days=index % 28)
        status = statuses[(index // 6) % 6]
        rows.append(Complaint(
            id=f"complaint-{index + 1:03d}", version=1,
            customer=dict(name=f"Demo Customer {index + 1}", email=f"customer{index + 1}@customers.example",
                          country_code=country, preferred_language=language),
            subject=subjects[index % 6],
            description=f"Synthetic case in {city}. {subjects[index % 6]}. Request a written follow-up and a practical remedy.",
            category=categories[index % 6], priority=["low", "normal", "high", "critical"][index % 4],
            channel=["email", "phone", "web", "chat"][index % 4],
            product=["Heat pump", "Dishwasher", "Solar inverter", "Electrical panel", "Water heater"][index % 5],
            order_reference=f"ORDER-DEMO-{1000 + index}", status=status,
            assigned_partner_id=None if status == "new" else f"partner-{index % 120 + 1:03d}",
            assigned_agent=None if status == "new" else ["Casey Demo", "Jordan Demo", "Morgan Demo"][index % 3],
            resolution="Follow-up completed; customer accepted the synthetic remedy." if status in {"resolved", "closed"} else None,
            created_at=created, updated_at=created + timedelta(hours=2), due_at=created + timedelta(days=3),
            notes=[], history=[],
        ))
    return rows
