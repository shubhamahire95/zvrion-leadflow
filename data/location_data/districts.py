"""Maharashtra district database for scraper location planning."""

MAHARASHTRA_DISTRICT_DATABASE = {
    "Ahmednagar": {"division": "Nashik", "headquarters": "Ahmednagar", "aliases": ["Ahilyanagar"]},
    "Akola": {"division": "Amravati", "headquarters": "Akola", "aliases": []},
    "Amravati": {"division": "Amravati", "headquarters": "Amravati", "aliases": []},
    "Beed": {"division": "Chhatrapati Sambhajinagar", "headquarters": "Beed", "aliases": []},
    "Bhandara": {"division": "Nagpur", "headquarters": "Bhandara", "aliases": []},
    "Buldhana": {"division": "Amravati", "headquarters": "Buldhana", "aliases": []},
    "Chandrapur": {"division": "Nagpur", "headquarters": "Chandrapur", "aliases": []},
    "Chhatrapati Sambhajinagar": {"division": "Chhatrapati Sambhajinagar", "headquarters": "Chhatrapati Sambhajinagar", "aliases": ["Aurangabad"]},
    "Dharashiv": {"division": "Chhatrapati Sambhajinagar", "headquarters": "Dharashiv", "aliases": ["Osmanabad"]},
    "Dhule": {"division": "Nashik", "headquarters": "Dhule", "aliases": []},
    "Gadchiroli": {"division": "Nagpur", "headquarters": "Gadchiroli", "aliases": []},
    "Gondia": {"division": "Nagpur", "headquarters": "Gondia", "aliases": []},
    "Hingoli": {"division": "Chhatrapati Sambhajinagar", "headquarters": "Hingoli", "aliases": []},
    "Jalgaon": {"division": "Nashik", "headquarters": "Jalgaon", "aliases": []},
    "Jalna": {"division": "Chhatrapati Sambhajinagar", "headquarters": "Jalna", "aliases": []},
    "Kolhapur": {"division": "Pune", "headquarters": "Kolhapur", "aliases": []},
    "Latur": {"division": "Chhatrapati Sambhajinagar", "headquarters": "Latur", "aliases": []},
    "Mumbai City": {"division": "Konkan", "headquarters": "Mumbai", "aliases": []},
    "Mumbai Suburban": {"division": "Konkan", "headquarters": "Bandra", "aliases": []},
    "Nagpur": {"division": "Nagpur", "headquarters": "Nagpur", "aliases": []},
    "Nanded": {"division": "Chhatrapati Sambhajinagar", "headquarters": "Nanded", "aliases": []},
    "Nandurbar": {"division": "Nashik", "headquarters": "Nandurbar", "aliases": []},
    "Nashik": {"division": "Nashik", "headquarters": "Nashik", "aliases": []},
    "Palghar": {"division": "Konkan", "headquarters": "Palghar", "aliases": []},
    "Parbhani": {"division": "Chhatrapati Sambhajinagar", "headquarters": "Parbhani", "aliases": []},
    "Pune": {"division": "Pune", "headquarters": "Pune", "aliases": []},
    "Raigad": {"division": "Konkan", "headquarters": "Alibag", "aliases": []},
    "Ratnagiri": {"division": "Konkan", "headquarters": "Ratnagiri", "aliases": []},
    "Sangli": {"division": "Pune", "headquarters": "Sangli", "aliases": []},
    "Satara": {"division": "Pune", "headquarters": "Satara", "aliases": []},
    "Sindhudurg": {"division": "Konkan", "headquarters": "Oros", "aliases": []},
    "Solapur": {"division": "Pune", "headquarters": "Solapur", "aliases": []},
    "Thane": {"division": "Konkan", "headquarters": "Thane", "aliases": []},
    "Wardha": {"division": "Nagpur", "headquarters": "Wardha", "aliases": []},
    "Washim": {"division": "Amravati", "headquarters": "Washim", "aliases": []},
    "Yavatmal": {"division": "Amravati", "headquarters": "Yavatmal", "aliases": []},
}

MAHARASHTRA_DISTRICTS = list(MAHARASHTRA_DISTRICT_DATABASE.keys())
MAHARASHTRA_DISTRICT_HEADQUARTERS = {
    district: details["headquarters"] for district, details in MAHARASHTRA_DISTRICT_DATABASE.items()
}
