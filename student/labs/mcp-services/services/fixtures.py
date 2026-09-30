from datetime import datetime, timedelta, timezone
from typing import get_args

from .models import Complaint, Partner, Specialty

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
SPECIALTIES = list(get_args(Specialty))
SERVICE_PROFILES = [
    ["sales", "repairs", "rental", "setup"],
    ["sales", "repairs", "maintenance"],
    ["repairs", "setup", "restoration"],
    ["sales", "rental", "maintenance"],
    ["repairs", "maintenance", "tuning"],
    ["sales", "repairs", "rental", "restoration"],
    ["rental", "repairs", "setup", "tuning"],
]
PRODUCTS = [
    ("plucked_strings", "AG-300 Northlight steel-string acoustic guitar"),
    ("plucked_strings", "EG-300 Switchrail solid-body electric guitar"),
    ("plucked_strings", "EB-300 Deepfield four-string electric bass"),
    ("plucked_strings", "HP-300 Moonarc concert pedal harp"),
    ("bowed_strings", "VN-300 Skylark violin"),
    ("bowed_strings", "VA-300 Hearth viola"),
    ("bowed_strings", "VC-300 Riverstone cello"),
    ("bowed_strings", "DB-300 Dockside double bass"),
    ("keyboards", "GP-300 Aurora grand piano"),
    ("keyboards", "UP-300 Dayroom upright piano"),
    ("woodwinds", "FL-300 Silverwake concert flute"),
    ("woodwinds", "CL-300 Nightreed B-flat clarinet"),
    ("woodwinds", "OB-300 Willowline oboe"),
    ("woodwinds", "BS-300 Longshore bassoon"),
    ("woodwinds", "AS-300 Copperlane E-flat alto saxophone"),
    ("brass", "TR-300 Beacon B-flat trumpet"),
    ("brass", "HN-300 Cloudring F/B-flat double horn"),
    ("brass", "TB-300 Broadreach tenor trombone"),
    ("percussion", "TP-300 Roundwave pedal timpani"),
    ("percussion", "SD-300 Threadmark concert snare drum"),
]
QUALITY_SYMPTOMS = {
    "plucked_strings": "uneven string action and an unwanted buzz",
    "bowed_strings": "an open body seam and an uneven response under the bow",
    "keyboards": "a sticking key and uneven action regulation",
    "woodwinds": "a leaking pad and unreliable key closure",
    "brass": "a binding moving mechanism and inconsistent intonation",
    "percussion": "a loose tension fitting and uneven head response",
}
CASES = [
    ("delivery_delay", "purchase", "Instrument delivery missed the performance deadline",
     "The dealer confirmed dispatch, but the instrument did not arrive before the scheduled rehearsal."),
    ("instrument_quality", "purchase", "New instrument has a manufacturing-quality issue",
     "The newly delivered instrument has {symptom}. Request an inspection of the manufacturing record and a remedy."),
    ("repair_quality", "repair", "Instrument still has a playability issue after workshop repair",
     "After collection from the authorized workshop, the instrument still has {symptom}. Request a follow-up repair."),
    ("billing", "purchase", "Dealer invoice includes an unexplained setup charge",
     "The invoice adds a setup charge that was not included in the accepted instrument quote."),
    ("communication", "repair", "No update on the instrument repair estimate",
     "The repair workshop has the instrument but has not supplied the promised estimate or completion date."),
    ("warranty", "warranty", "Warranty claim for the instrument was declined",
     "The customer reported {symptom}. Request a written warranty decision from the authorized instrument workshop."),
    ("rental", "rental", "Rental deposit retained after the instrument was returned",
     "The rental instrument was returned on time, but the rental desk has not supplied the condition report supporting the deposit deduction."),
]
SEED_TIME = datetime(2026, 9, 1, 9, tzinfo=timezone.utc)


def partners() -> list[Partner]:
    rows = []
    for index in range(120):
        country, city, region, street, postal, lat, lon, language, dial = LOCATIONS[index % 30]
        branch = index // 30
        rows.append(Partner(
            id=f"partner-{index + 1:03d}", version=1, updated_at=SEED_TIME,
            name=f"{['Northstar', 'Clearwave', 'Bluebridge', 'Silverline'][branch]} {city} Music",
            address=dict(street=f"{14 + branch * 22} {street}, Unit {branch + 1}", city=city,
                         region=region, postal_code=postal, country_code=country,
                         latitude=lat, longitude=lon),
            contact_name=f"{['Alex', 'Sam', 'Taylor', 'Robin'][branch]} Demo {index + 1}",
            email=f"service{index + 1}@partners.example",
            phone=f"{dial} 000 000 {index + 1:04d}", website=f"https://partner-{index + 1}.example",
            status=["active", "active", "active", "suspended", "pending"][(index + branch) % 5],
            tier=["standard", "silver", "gold", "platinum"][(index + branch) % 4],
            specialties=[SPECIALTIES[index % len(SPECIALTIES)], SPECIALTIES[(index + branch + 1) % len(SPECIALTIES)]],
            services=SERVICE_PROFILES[(index + branch) % len(SERVICE_PROFILES)],
            languages=list(dict.fromkeys([language, "en"])),
            certifications=["Aster Vale Instruments authorized partner",
                            f"{SPECIALTIES[index % len(SPECIALTIES)].replace('_', ' ').title()} workshop training"],
            service_radius_km=20 + index % 8 * 15, emergency_service=index % 3 == 0,
            rating=round(3.2 + index % 19 / 10, 1), capacity_per_week=5 + index % 12 * 5,
            authorized_since=f"{2018 + index % 8}-0{index % 9 + 1}-15",
        ))
    return rows


def complaints() -> list[Complaint]:
    partner_rows = partners()
    statuses = ["new", "triaged", "in_progress", "awaiting_customer", "resolved", "closed"]
    rows = []
    for index in range(90):
        category, transaction, subject, explanation = CASES[index % len(CASES)]
        required_service = {"purchase": "sales", "repair": "repairs", "rental": "rental", "warranty": "repairs"}[transaction]
        family, product = PRODUCTS[index % len(PRODUCTS)]
        candidates = [p for p in partner_rows if p.status == "active" and required_service in p.services
                      and family in p.specialties]
        partner = candidates[(index * 7 + index // len(CASES)) % len(candidates)]
        country, city, language = partner.address.country_code, partner.address.city, partner.languages[0]
        created = SEED_TIME - timedelta(days=index % 28)
        status = statuses[(index // len(CASES)) % len(statuses)]
        priority = ["low", "normal", "high", "critical"][(index + 2 * (index // len(CASES))) % 4]
        rows.append(Complaint(
            id=f"complaint-{index + 1:03d}", version=1,
            customer=dict(name=f"Demo Customer {index + 1}", email=f"customer{index + 1}@customers.example",
                          country_code=country, preferred_language=language),
            subject=subject,
            description=f"Synthetic Aster Vale Instruments case in {city} for {product}. "
                        f"{explanation.format(symptom=QUALITY_SYMPTOMS[family])}",
            category=category, priority=priority,
            channel=["email", "phone", "web", "chat"][index % 4],
            product=product, instrument_family=family, transaction_type=transaction,
            instrument_serial=f"AVI-DEMO-{10001 + index}",
            order_reference=f"ORDER-DEMO-{1000 + index}", status=status,
            assigned_partner_id=None if status == "new" else partner.id,
            assigned_agent=None if status == "new" else ["Casey Demo", "Jordan Demo", "Morgan Demo"][index % 3],
            resolution="Follow-up completed; customer accepted the synthetic remedy." if status in {"resolved", "closed"} else None,
            created_at=created, updated_at=created + timedelta(hours=2),
            due_at=created + timedelta(days=1 if priority in {"high", "critical"} else 3),
            notes=[], history=[],
        ))
    return rows
