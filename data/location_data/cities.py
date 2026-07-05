"""Maharashtra city and town database optimized for scraping queries."""

from .districts import MAHARASHTRA_DISTRICTS
from .talukas import MAHARASHTRA_TALUKAS_BY_DISTRICT

MAHARASHTRA_CITIES_BY_DISTRICT = {
    "Ahmednagar": {
        "major_cities": ["Ahmednagar", "Sangamner", "Shrirampur", "Kopargaon", "Rahuri", "Shirdi"],
        "towns": ["Akole", "Jamkhed", "Karjat", "Nevasa", "Parner", "Pathardi", "Rahata", "Shevgaon", "Shrigonda"],
    },
    "Akola": {
        "major_cities": ["Akola", "Akot", "Murtijapur"],
        "towns": ["Balapur", "Barshitakli", "Patur", "Telhara"],
    },
    "Amravati": {
        "major_cities": ["Amravati", "Achalpur", "Warud", "Daryapur", "Morshi"],
        "towns": ["Anjangaon Surji", "Bhatkuli", "Chandur Bazar", "Chandur Railway", "Chikhaldara", "Dhamangaon Railway", "Dharni", "Nandgaon-Khandeshwar", "Teosa"],
    },
    "Beed": {
        "major_cities": ["Beed", "Ambajogai", "Parli", "Majalgaon", "Georai"],
        "towns": ["Ashti", "Dharur", "Kaij", "Patoda", "Shirur Kasar", "Wadwani"],
    },
    "Bhandara": {
        "major_cities": ["Bhandara", "Tumsar", "Pauni"],
        "towns": ["Lakhandur", "Lakhani", "Mohadi", "Sakoli"],
    },
    "Buldhana": {
        "major_cities": ["Buldhana", "Khamgaon", "Malkapur", "Shegaon", "Chikhli"],
        "towns": ["Deulgaon Raja", "Jalgaon Jamod", "Lonar", "Mehkar", "Motala", "Nandura", "Sangrampur", "Sindkhed Raja"],
    },
    "Chandrapur": {
        "major_cities": ["Chandrapur", "Ballarpur", "Warora", "Brahmapuri", "Rajura"],
        "towns": ["Bhadravati", "Chimur", "Gondpipri", "Jiwati", "Korpana", "Mul", "Nagbhid", "Pombhurna", "Saoli", "Sindewahi"],
    },
    "Chhatrapati Sambhajinagar": {
        "major_cities": ["Chhatrapati Sambhajinagar", "Aurangabad", "Sillod", "Paithan", "Vaijapur"],
        "towns": ["Gangapur", "Kannad", "Khuldabad", "Phulambri", "Soegaon"],
    },
    "Dharashiv": {
        "major_cities": ["Dharashiv", "Osmanabad", "Tuljapur", "Omerga"],
        "towns": ["Bhum", "Kalamb", "Lohara", "Paranda", "Washi"],
    },
    "Dhule": {
        "major_cities": ["Dhule", "Shirpur"],
        "towns": ["Sakri", "Sindkheda"],
    },
    "Gadchiroli": {
        "major_cities": ["Gadchiroli", "Desaiganj", "Aheri"],
        "towns": ["Armori", "Bhamragad", "Chamorshi", "Dhanora", "Etapalli", "Korchi", "Kurkheda", "Mulchera", "Sironcha"],
    },
    "Gondia": {
        "major_cities": ["Gondia", "Tirora"],
        "towns": ["Amgaon", "Arjuni Morgaon", "Deori", "Goregaon", "Sadak Arjuni", "Salekasa"],
    },
    "Hingoli": {
        "major_cities": ["Hingoli", "Basmath"],
        "towns": ["Aundha Nagnath", "Kalamnuri", "Sengaon"],
    },
    "Jalgaon": {
        "major_cities": ["Jalgaon", "Bhusawal", "Amalner", "Chalisgaon", "Pachora", "Raver"],
        "towns": ["Bhadgaon", "Bodwad", "Chopda", "Dharangaon", "Erandol", "Jamner", "Muktainagar", "Parola", "Yawal"],
    },
    "Jalna": {
        "major_cities": ["Jalna", "Ambad", "Partur"],
        "towns": ["Badnapur", "Bhokardan", "Ghansawangi", "Jafrabad", "Mantha"],
    },
    "Kolhapur": {
        "major_cities": ["Kolhapur", "Ichalkaranji", "Gadhinglaj", "Jaysingpur", "Kagal"],
        "towns": ["Ajra", "Bavda", "Bhudargad", "Chandgad", "Gaganbawada", "Hatkanangale", "Karvir", "Panhala", "Radhanagari", "Shahuwadi", "Shirol"],
    },
    "Latur": {
        "major_cities": ["Latur", "Udgir", "Nilanga", "Ausa"],
        "towns": ["Ahmadpur", "Chakur", "Deoni", "Jalkot", "Renapur", "Shirur Anantpal"],
    },
    "Mumbai City": {
        "major_cities": ["Mumbai", "South Mumbai"],
        "towns": ["Byculla", "Colaba", "Dadar", "Fort", "Girgaon", "Malabar Hill", "Marine Lines", "Parel", "Worli"],
    },
    "Mumbai Suburban": {
        "major_cities": ["Andheri", "Bandra", "Borivali", "Kurla", "Goregaon", "Malad"],
        "towns": ["Bhandup", "Chembur", "Ghatkopar", "Jogeshwari", "Kandivali", "Mulund", "Powai", "Santacruz", "Vikhroli", "Vile Parle"],
    },
    "Nagpur": {
        "major_cities": ["Nagpur", "Kamptee", "Umred", "Katol", "Ramtek"],
        "towns": ["Bhiwapur", "Hingna", "Kalameshwar", "Kuhi", "Mauda", "Narkhed", "Parseoni", "Savner"],
    },
    "Nanded": {
        "major_cities": ["Nanded", "Deglur", "Kinwat", "Mukhed"],
        "towns": ["Ardhapur", "Bhokar", "Biloli", "Dharmabad", "Hadgaon", "Himayatnagar", "Kandhar", "Loha", "Mahur", "Mudkhed", "Naigaon", "Umri"],
    },
    "Nandurbar": {
        "major_cities": ["Nandurbar", "Shahada", "Navapur"],
        "towns": ["Akkalkuwa", "Akrani", "Taloda"],
    },
    "Nashik": {
        "major_cities": ["Nashik", "Malegaon", "Sinnar", "Manmad", "Yevla"],
        "towns": ["Baglan", "Chandwad", "Deola", "Dindori", "Igatpuri", "Kalwan", "Nandgaon", "Niphad", "Peint", "Surgana", "Trimbakeshwar"],
    },
    "Palghar": {
        "major_cities": ["Palghar", "Vasai", "Virar", "Boisar", "Dahanu"],
        "towns": ["Jawhar", "Mokhada", "Talasari", "Vikramgad", "Wada"],
    },
    "Parbhani": {
        "major_cities": ["Parbhani", "Gangakhed", "Jintur"],
        "towns": ["Manwath", "Palam", "Pathri", "Purna", "Sailu", "Sonpeth"],
    },
    "Pune": {
        "major_cities": ["Pune", "Pimpri Chinchwad", "Baramati", "Talegaon Dabhade", "Lonavala"],
        "towns": ["Ambegaon", "Bhor", "Chakan", "Daund", "Haveli", "Indapur", "Junnar", "Khed", "Maval", "Mulshi", "Purandar", "Rajgurunagar", "Shirur", "Saswad", "Velhe"],
    },
    "Raigad": {
        "major_cities": ["Panvel", "Alibag", "Uran", "Karjat", "Khopoli", "Pen"],
        "towns": ["Khalapur", "Mahad", "Mangaon", "Mhasla", "Murud", "Poladpur", "Roha", "Shrivardhan", "Sudhagad", "Tala"],
    },
    "Ratnagiri": {
        "major_cities": ["Ratnagiri", "Chiplun", "Khed"],
        "towns": ["Dapoli", "Guhagar", "Lanja", "Mandangad", "Rajapur", "Sangameshwar"],
    },
    "Sangli": {
        "major_cities": ["Sangli", "Miraj", "Islampur", "Vita", "Tasgaon"],
        "towns": ["Atpadi", "Jat", "Kadegaon", "Kavathe Mahankal", "Khanapur", "Palus", "Shirala", "Walwa"],
    },
    "Satara": {
        "major_cities": ["Satara", "Karad", "Phaltan", "Wai", "Mahabaleshwar"],
        "towns": ["Dahiwadi", "Jaoli", "Khandala", "Khatav", "Koregaon", "Patan", "Vaduj"],
    },
    "Sindhudurg": {
        "major_cities": ["Kankavli", "Sawantwadi", "Malvan", "Kudal"],
        "towns": ["Devgad", "Dodamarg", "Oros", "Vaibhavwadi", "Vengurla"],
    },
    "Solapur": {
        "major_cities": ["Solapur", "Pandharpur", "Barshi", "Akkalkot", "Akluj"],
        "towns": ["Karmala", "Madha", "Malshiras", "Mangalvedhe", "Mohol", "Sangole"],
    },
    "Thane": {
        "major_cities": ["Thane", "Kalyan", "Dombivli", "Bhiwandi", "Ulhasnagar", "Ambarnath", "Badlapur"],
        "towns": ["Murbad", "Shahapur"],
    },
    "Wardha": {
        "major_cities": ["Wardha", "Hinganghat", "Arvi"],
        "towns": ["Ashti", "Deoli", "Karanja", "Samudrapur", "Seloo"],
    },
    "Washim": {
        "major_cities": ["Washim", "Karanja", "Risod"],
        "towns": ["Malegaon", "Mangrulpir", "Manora"],
    },
    "Yavatmal": {
        "major_cities": ["Yavatmal", "Pusad", "Wani", "Umarkhed", "Darwha"],
        "towns": ["Arni", "Babulgaon", "Digras", "Ghatanji", "Kalamb", "Mahagaon", "Maregaon", "Ner", "Pandharkawada", "Ralegaon", "Zari Jamani"],
    },
}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


MAHARASHTRA_TOWNS_BY_DISTRICT = {
    district: _dedupe(
        values["major_cities"]
        + values["towns"]
        + MAHARASHTRA_TALUKAS_BY_DISTRICT.get(district, [])
    )
    for district, values in MAHARASHTRA_CITIES_BY_DISTRICT.items()
}

MAHARASHTRA_MAJOR_CITIES = sorted(
    {city for values in MAHARASHTRA_CITIES_BY_DISTRICT.values() for city in values["major_cities"]}
)

MAHARASHTRA_TOWNS = sorted(
    {town for towns in MAHARASHTRA_TOWNS_BY_DISTRICT.values() for town in towns}
)

MAHARASHTRA_CITIES = sorted(set(MAHARASHTRA_DISTRICTS + MAHARASHTRA_MAJOR_CITIES + MAHARASHTRA_TOWNS))
